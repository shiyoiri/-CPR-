"""
CPR 按压分析引擎
"""
from collections import deque
import math
import time

import config


def _angle_between(a, b, c):
    """
    计算三点夹角 (矢量 BA → BC), 返回角度 (0~180°)
    a, b, c = (x, y),  b 为顶点
    """
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba < 1e-6 or mag_bc < 1e-6:
        return 0.0
    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


class CPRAnalyzer:
    """
    CPR 按压质量评估:
      - 手臂伸直度 (肘关节角度)
      - 按压频率 (BPM)
      - 手部按压位置
      - 回弹状态
      - 优良率
    """

    def __init__(self):
        # 按压检测
        self.wrist_y_history = deque(maxlen=150)
        self.compression_timestamps = deque()
        self.last_wrist_y = None
        self.baseline_wrist_y = None
        self.compressing = False
        self.total_presses = 0
        self.good_presses = 0

        # 标定数据 (用户点击"标定 ROI"时记录)
        self.calibrated = False
        self.calib_hand_x_offset = 0.0    # 手 X 相对人体中心的偏移 (归一化: 比例)
        self.calib_hand_y_ratio = 0.0     # 手 Y 在人体框中的位置 (0=顶, 1=底)
        self.calib_sw_dist = 0.0          # 肩-腕距离基线 (用于深度估算)

        self._last_analysis_time = time.perf_counter()

    def analyze(self, keypoints, person_bbox, frame_h):
        """
        传入关键点和人体框，返回分析结果字典。
        keypoints: [(x, y, conf), ...]  17点
        """
        if keypoints is None:
            return self._empty_result()

        ks = keypoints

        # 获取关键点
        ls = ks[config.COCO["LEFT_SHOULDER"]]
        rs = ks[config.COCO["RIGHT_SHOULDER"]]
        le = ks[config.COCO["LEFT_ELBOW"]]
        re = ks[config.COCO["RIGHT_ELBOW"]]
        lw = ks[config.COCO["LEFT_WRIST"]]
        rw = ks[config.COCO["RIGHT_WRIST"]]

        # 置信度过滤
        min_conf = 0.3
        left_ok  = all(c > min_conf for c in (ls[2], le[2], lw[2]))
        right_ok = all(c > min_conf for c in (rs[2], re[2], rw[2]))

        if not left_ok and not right_ok:
            return self._empty_result()

        # --- 选置信度更高的一侧手臂 ---
        left_conf  = (ls[2] + le[2] + lw[2]) / 3
        right_conf = (rs[2] + re[2] + rw[2]) / 3

        if left_conf >= right_conf:
            shoulder, elbow, wrist = ls, le, lw
            side = "left"
        else:
            shoulder, elbow, wrist = rs, re, rw
            side = "right"

        # --- 肘关节角度 ---
        elbow_angle = _angle_between(
            (shoulder[0], shoulder[1]),
            (elbow[0], elbow[1]),
            (wrist[0], wrist[1]),
        )
        arm_straight = elbow_angle >= config.CPR_ELBOW_ANGLE_MIN

        # --- 按压频率 ---
        bpm, is_new_press = self._update_compression_rate(wrist[1], frame_h)

        # --- 手部按压位置 ---
        hand_in_roi = False
        hand_y_ok = False
        pos_x = wrist[0]
        pos_y = wrist[1]
        if person_bbox:
            px1, py1, px2, py2 = person_bbox
            body_cx = (px1 + px2) / 2
            body_w  = px2 - px1
            body_h  = py2 - py1
            if self.calibrated:
                # 标定模式：相对于标定位置检查
                target_x = body_cx + self.calib_hand_x_offset * body_w
                tolerance_x = body_w * config.CALIB["HAND_X_TOLERANCE"]
                hand_in_roi = abs(pos_x - target_x) <= tolerance_x
                # Y 位置检查
                target_y = py1 + self.calib_hand_y_ratio * body_h
                tolerance_y = body_h * config.CALIB["HAND_Y_TOLERANCE"]
                hand_y_ok = abs(pos_y - target_y) <= tolerance_y
            else:
                # 未标定：仅检查 X 在身体中心附近
                roi_left  = body_cx - body_w * 0.2
                roi_right = body_cx + body_w * 0.2
                hand_in_roi = roi_left <= pos_x <= roi_right
                hand_y_ok = True  # 未标定时不检查 Y

        # --- 按压深度 (基于肩-腕距离变化) ---
        depth_ok = False
        depth_pct = 0.0
        if self.calibrated and self.calib_sw_dist > 0:
            sw_dist = math.hypot(shoulder[0] - wrist[0], shoulder[1] - wrist[1])
            depth_pct = max(0, (self.calib_sw_dist - sw_dist) / self.calib_sw_dist * 100)
            depth_ok = depth_pct >= config.CALIB["DEPTH_CHANGE_MIN"] * 100

        # --- 回弹 ---
        recoil_ok = self._check_recoil(wrist[1])

        # --- 优良统计 ---
        if self.calibrated:
            is_good = arm_straight and hand_in_roi and hand_y_ok and recoil_ok
        else:
            is_good = arm_straight and hand_in_roi and recoil_ok
        if is_new_press:
            self.total_presses += 1
            if is_good:
                self.good_presses += 1

        quality_pct = (self.good_presses / self.total_presses * 100) if self.total_presses > 0 else 0.0

        now = time.perf_counter()
        self._last_analysis_time = now

        # 手部位置描述
        if self.calibrated:
            if hand_in_roi and hand_y_ok:
                hand_desc = "正确"
            elif not hand_in_roi:
                hand_desc = "左右偏移"
            else:
                hand_desc = "上下偏移"
        else:
            hand_desc = "正确" if hand_in_roi else "偏移"

        return {
            "elbow_angle": round(elbow_angle, 1),
            "arm_straight": arm_straight,
            "bpm": round(bpm, 1),
            "hand_position": hand_desc,
            "hand_in_roi": hand_in_roi,
            "recoil": "充分" if recoil_ok else "不足",
            "recoil_ok": recoil_ok,
            "depth_ok": depth_ok,
            "depth_pct": round(depth_pct, 1),
            "calibrated": self.calibrated,
            "total_presses": self.total_presses,
            "good_presses": self.good_presses,
            "quality_pct": round(quality_pct, 1),
            "side": side,
        }

    def _update_compression_rate(self, wrist_y, frame_h):
        """跟踪手腕 Y 坐标波动，估算 BPM"""
        now = time.perf_counter()

        self.wrist_y_history.append(wrist_y)

        if self.last_wrist_y is None:
            self.last_wrist_y = wrist_y
            self.baseline_wrist_y = wrist_y
            return 0.0, False

        # 下压检测: wrist_y 增加 (手在画面中向下移动)
        dy = wrist_y - self.last_wrist_y
        threshold = frame_h * 0.005

        is_new_press = False

        if dy > threshold and not self.compressing:
            self.compressing = True
            is_new_press = True
            self.compression_timestamps.append(now)
            # 清理超过窗口的时间戳
            window = config.CPR_WINDOW_SEC
            while self.compression_timestamps and \
                  self.compression_timestamps[0] < now - window:
                self.compression_timestamps.popleft()

        elif dy < -threshold and self.compressing:
            self.compressing = False
            self.baseline_wrist_y = wrist_y

        self.last_wrist_y = wrist_y

        # 计算 BPM
        ts_list = list(self.compression_timestamps)
        if len(ts_list) < 2:
            return 0.0, is_new_press

        window = config.CPR_WINDOW_SEC
        recent = [t for t in ts_list if t > now - window]
        if len(recent) < 2:
            return 0.0, is_new_press

        intervals = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval <= 0:
            return 0.0, is_new_press
        return 60.0 / avg_interval, is_new_press

    def _check_recoil(self, wrist_y):
        """检查手腕是否回到基线位置"""
        if self.baseline_wrist_y is None:
            self.baseline_wrist_y = wrist_y
            return True

        # 回弹充分: 当前手腕 Y 接近基线 (在基线附近 1% 范围内属于充分回弹)
        threshold = abs(self.baseline_wrist_y) * 0.02
        return abs(wrist_y - self.baseline_wrist_y) < threshold or \
               wrist_y < self.baseline_wrist_y  # 手腕回到基线以上

    def reset(self):
        self.wrist_y_history.clear()
        self.compression_timestamps.clear()
        self.last_wrist_y = None
        self.baseline_wrist_y = None
        self.compressing = False
        self.total_presses = 0
        self.good_presses = 0

    def calibrate(self, keypoints, person_bbox):
        """标定按压位置 — 记录当前手部相对于人体的位置作为参考"""
        if keypoints is None or person_bbox is None:
            return False

        ks = keypoints
        ls = ks[config.COCO["LEFT_SHOULDER"]]
        rs = ks[config.COCO["RIGHT_SHOULDER"]]
        lw = ks[config.COCO["LEFT_WRIST"]]
        rw = ks[config.COCO["RIGHT_WRIST"]]

        # 选置信度更高的一侧
        left_conf = (ls[2] + lw[2]) / 2
        right_conf = (rs[2] + rw[2]) / 2
        if left_conf >= right_conf:
            shoulder, wrist = ls, lw
        else:
            shoulder, wrist = rs, rw

        if shoulder[2] < 0.3 or wrist[2] < 0.3:
            return False

        px1, py1, px2, py2 = person_bbox
        body_cx = (px1 + px2) / 2
        body_w = px2 - px1
        body_h = py2 - py1

        if body_w <= 0 or body_h <= 0:
            return False

        # 记录手部相对于人体的位置
        self.calib_hand_x_offset = (wrist[0] - body_cx) / body_w
        self.calib_hand_y_ratio = (wrist[1] - py1) / body_h
        self.calib_sw_dist = math.hypot(shoulder[0] - wrist[0], shoulder[1] - wrist[1])
        self.calibrated = True

        # 重置按压统计 (标定后重新开始)
        self.total_presses = 0
        self.good_presses = 0

        return True

    @staticmethod
    def classify_person(keypoints, bbox):
        """
        多信号投票分类：施救者(跪姿) vs 被救者(平躺)。
        返回 "standing" | "lying" | "unknown"
        """
        pc = config.PERSON_CLASSIFY
        votes_rescuer = 0
        votes_victim = 0

        # --- 信号1: 膝盖角度 (俯视下最稳定) ---
        if keypoints is not None:
            ks = keypoints

            # 取置信度较高的一侧腿
            lh = ks[config.COCO["LEFT_HIP"]]
            rh = ks[config.COCO["RIGHT_HIP"]]
            l_leg_ok = all(c > 0.3 for c in (ks[config.COCO["LEFT_HIP"]][2],
                                              ks[config.COCO["LEFT_KNEE"]][2],
                                              ks[config.COCO["LEFT_ANKLE"]][2]))
            r_leg_ok = all(c > 0.3 for c in (ks[config.COCO["RIGHT_HIP"]][2],
                                              ks[config.COCO["RIGHT_KNEE"]][2],
                                              ks[config.COCO["RIGHT_ANKLE"]][2]))
            if l_leg_ok or r_leg_ok:
                if l_leg_ok and (not r_leg_ok or
                   (ks[11][2] + ks[13][2] + ks[15][2]) >= (ks[12][2] + ks[14][2] + ks[16][2])):
                    hip, knee, ankle = ks[11], ks[13], ks[15]
                else:
                    hip, knee, ankle = ks[12], ks[14], ks[16]

                knee_angle = _angle_between(
                    (hip[0], hip[1]), (knee[0], knee[1]), (ankle[0], ankle[1]),
                )
                if knee_angle < pc["KNEE_BENT_MAX"]:
                    votes_rescuer += 1      # 弯腿 → 跪姿
                else:
                    votes_victim += 1       # 直腿 → 平躺

            # --- 信号2: 躯干倾斜角 (肩中点 → 髋中点) ---
            ls = ks[config.COCO["LEFT_SHOULDER"]]
            rs = ks[config.COCO["RIGHT_SHOULDER"]]
            shoulder_conf = (ls[2] + rs[2]) / 2
            hip_conf = (lh[2] + rh[2]) / 2
            if shoulder_conf > 0.3 and hip_conf > 0.3:
                sx = (ls[0] + rs[0]) / 2
                sy = (ls[1] + rs[1]) / 2
                hx = (lh[0] + rh[0]) / 2
                hy = (lh[1] + rh[1]) / 2
                dx = sx - hx
                dy = sy - hy
                torso_angle = abs(math.degrees(math.atan2(dy, dx)))
                if torso_angle > pc["TORSO_ANGLE_STANDING_MIN"]:
                    votes_rescuer += 1
                elif torso_angle < pc["TORSO_ANGLE_LYING_MAX"]:
                    votes_victim += 1

            # --- 信号3: 头 vs 髋 Y坐标 (头高于髋 → 跪姿) ---
            nose = ks[config.COCO["NOSE"]]
            if nose[2] > 0.3 and hip_conf > 0.3:
                hy_mid = (lh[1] + rh[1]) / 2
                # 在图像坐标中，nose Y < hip Y 说明头在身体上方
                if (hy_mid - nose[1]) > 0:  # 头在上面(画面中Y值更小)
                    votes_rescuer += 1
                else:
                    votes_victim += 1

        # --- 信号4: bbox 宽高比 ---
        if bbox:
            x1, y1, x2, y2 = bbox
            bw = x2 - x1
            bh = y2 - y1
            if bw > 0 and bh > 0:
                if bh / bw > pc["BBOX_HW_RATIO_STANDING"]:
                    votes_rescuer += 1
                elif bw / bh > pc["BBOX_WH_RATIO_LYING"]:
                    votes_victim += 1

        # --- 投票裁决 ---
        if votes_rescuer > votes_victim:
            return "standing"
        elif votes_victim > votes_rescuer:
            return "lying"
        return "unknown"

    def _empty_result(self):
        return {
            "elbow_angle": 0.0,
            "arm_straight": False,
            "bpm": 0.0,
            "hand_position": "--",
            "hand_in_roi": False,
            "recoil": "--",
            "recoil_ok": False,
            "depth_ok": False,
            "depth_pct": 0.0,
            "calibrated": self.calibrated,
            "total_presses": self.total_presses,
            "good_presses": self.good_presses,
            "quality_pct": 0.0,
            "side": "--",
        }
