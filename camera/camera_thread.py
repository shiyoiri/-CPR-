"""
摄像头采集+推理线程 — OpenCV + YOLO + CPR分析 (全部在子线程)
"""
import cv2
import time
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np

from detector.object_detector import ObjectDetector
from detector.pose_estimator import PoseEstimator
from analyzer.cpr_analyzer import CPRAnalyzer
from utils.draw_utils import draw_skeleton, draw_cpr_overlay
import config


class CameraThread(QThread):
    """采集帧 → 双模型检测 → 用户手动分配角色 → CPR分析 → 绘图 → 发射结果"""
    frame_processed = pyqtSignal(np.ndarray)
    analysis_ready = pyqtSignal(dict)
    fps_updated = pyqtSignal(float)
    person_count_changed = pyqtSignal(int)

    def __init__(self, camera_id=None):
        super().__init__()
        self.camera_id = camera_id if camera_id is not None else config.CAMERA_ID
        self._running = False
        self._cap = None

        self.detector = ObjectDetector()
        self.pose_estimator = PoseEstimator()
        self.analyzer = CPRAnalyzer()

        # 用户手动选择的角色索引 (-1 = 未选择)
        self.rescuer_index = 0
        self.patient_index = 1
        self._last_person_count = 0

        # 标定触发
        self.calibrate_next_frame = False

        # 关键点平滑缓冲 {index: [(x,y,conf)*17]}
        self._smoothed_kpts = {}

    def run(self):
        self._cap = cv2.VideoCapture(self.camera_id)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

        self._running = True
        frame_count = 0
        fps_timer = time.perf_counter()

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_h, frame_w = frame_rgb.shape[:2]

            # --- 双模型检测 ---
            det_result = self.detector.detect(frame_rgb, conf=0.15)
            all_poses = self.pose_estimator.estimate_all(frame_rgb, conf=0.2)
            persons = self._merge_detections(det_result, all_poses)

            # 通知主线程更新人数
            if len(persons) != self._last_person_count:
                self._last_person_count = len(persons)
                self.person_count_changed.emit(len(persons))

            # --- 根据用户选择确定角色 ---
            ri = self.rescuer_index
            pi = self.patient_index

            rescuer = persons[ri] if 0 <= ri < len(persons) else None
            patient = persons[pi] if 0 <= pi < len(persons) and pi != ri else None

            rescuer_kpts = rescuer.get("keypoints") if rescuer else None
            rescuer_bbox = rescuer.get("bbox") if rescuer else None

            # --- 标定触发 ---
            if self.calibrate_next_frame:
                if self.analyzer.calibrate(rescuer_kpts, rescuer_bbox):
                    self.calibrate_next_frame = False
                    self.analysis_ready.emit({"calibrated": True, "hand_position": "已标定"})

            # --- CPR 分析 (仅施救者) ---
            analysis = self.analyzer.analyze(rescuer_kpts, rescuer_bbox, frame_h)

            # --- 关键点时序平滑 ---
            for i, p in enumerate(persons):
                raw = p.get("keypoints")
                if raw is None:
                    continue
                # 施救者轻平滑 (保持响应)，患者重平滑 (去抖)
                alpha = 0.7 if i == ri else 0.3
                prev = self._smoothed_kpts.get(i)
                if prev is not None and len(prev) == len(raw):
                    smoothed = []
                    for (rx, ry, rc), (px, py, pc) in zip(raw, prev):
                        if rc > 0.3 and pc > 0.3:
                            smoothed.append((alpha * rx + (1 - alpha) * px,
                                             alpha * ry + (1 - alpha) * py,
                                             max(rc, pc)))
                        elif rc > 0.3:
                            smoothed.append((rx, ry, rc))
                        else:
                            smoothed.append((px, py, pc))
                    p["keypoints"] = smoothed
                self._smoothed_kpts[i] = p["keypoints"]

            # 清理不再出现的人员缓冲
            for idx in list(self._smoothed_kpts.keys()):
                if idx >= len(persons):
                    del self._smoothed_kpts[idx]

            # --- 绘制所有检测到的人 ---
            for i, p in enumerate(persons):
                if i == ri:
                    role = "rescuer"
                elif i == pi:
                    role = "patient"
                else:
                    role = None
                frame = draw_skeleton(frame, p.get("keypoints"), p.get("bbox"),
                                      index=i, role=role)

            frame = draw_cpr_overlay(frame, analysis, rescuer_kpts)

            self.frame_processed.emit(frame)
            self.analysis_ready.emit(analysis)

            # FPS 统计
            frame_count += 1
            elapsed = time.perf_counter() - fps_timer
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                self.fps_updated.emit(fps)
                frame_count = 0
                fps_timer = time.perf_counter()

        if self._cap is not None:
            self._cap.release()

    def _merge_detections(self, det_result, all_poses):
        """合并检测器bbox和姿态关键点，互相补漏，按画面位置排序"""
        persons = []

        pose_bboxes = []
        for pose in all_poses:
            bbox = pose.get("bbox")
            entry = {
                "keypoints": pose["keypoints"],
                "bbox": bbox,
                "confidence": pose.get("confidence", 0),
            }
            persons.append(entry)
            if bbox:
                pose_bboxes.append(bbox)

        if det_result and det_result.get("all_persons"):
            for px1, py1, px2, py2, conf in det_result["all_persons"]:
                if self._is_covered((px1, py1, px2, py2), pose_bboxes):
                    continue
                persons.append({
                    "keypoints": None,
                    "bbox": (px1, py1, px2, py2),
                    "confidence": conf,
                })

        # 按 bbox 顶部 Y 排序 — 施救者在上方，序号始终更小
        persons.sort(key=lambda p: p["bbox"][1] if p.get("bbox") else 9999)

        return persons

    def _is_covered(self, det_bbox, pose_bboxes):
        if not pose_bboxes:
            return False
        dx1, dy1, dx2, dy2 = det_bbox
        d_area = (dx2 - dx1) * (dy2 - dy1)
        if d_area <= 0:
            return False
        for px1, py1, px2, py2 in pose_bboxes:
            ix1 = max(dx1, px1)
            iy1 = max(dy1, py1)
            ix2 = min(dx2, px2)
            iy2 = min(dy2, py2)
            if ix2 > ix1 and iy2 > iy1:
                i_area = (ix2 - ix1) * (iy2 - iy1)
                iou = i_area / (d_area + (px2 - px1) * (py2 - py1) - i_area)
                if iou > 0.3:
                    return True
        return False

    def stop(self):
        self._running = False
        self.wait(timeout=5000)

    def reset_analyzer(self):
        self.analyzer.reset()
