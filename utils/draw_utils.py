"""
骨架 & 关键点 & 指示器绘制工具
"""
import cv2
import numpy as np
import math

import config


def draw_skeleton(frame_bgr, keypoints, person_bbox=None, index=0, role=None):
    """
    在 BGR 帧上绘制骨架连线 + 关键点 + 人员编号。
    keypoints: [(x, y, conf), ...] 17点 (None 则只画 bbox)
    role: "rescuer" | "patient" | None (未分配)
    """
    h, w = frame_bgr.shape[:2]

    if role == "rescuer":
        pt_color = (0, 255, 0)
        line_color = (0, 255, 255)
        bbox_color = (0, 255, 0)
        role_label = "Rescuer"
    elif role == "patient":
        pt_color = (0, 0, 255)
        line_color = (0, 140, 255)
        bbox_color = (0, 0, 255)
        role_label = "Patient"
    else:
        pt_color = (180, 180, 180)
        line_color = (150, 150, 150)
        bbox_color = (120, 120, 120)
        role_label = None

    # 画关键点 + 骨架 (仅当有关键点时)
    if keypoints is not None:
        ks = keypoints
        pt_radius = 4
        for i, (x, y, conf) in enumerate(ks):
            if conf < 0.3:
                continue
            px, py = int(x), int(y)
            if 0 <= px < w and 0 <= py < h:
                cv2.circle(frame_bgr, (px, py), pt_radius, pt_color, -1)

        line_thick = 2
        for a, b in config.SKELETON_EDGES:
            ka, kb = ks[a], ks[b]
            if ka[2] < 0.3 or kb[2] < 0.3:
                continue
            pta = (int(ka[0]), int(ka[1]))
            ptb = (int(kb[0]), int(kb[1]))
            if _in_bounds(pta, w, h) and _in_bounds(ptb, w, h):
                cv2.line(frame_bgr, pta, ptb, line_color, line_thick)

    # 画 bbox + 标签
    if person_bbox:
        x1, y1, x2, y2 = person_bbox
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), bbox_color, 2)
        # 编号
        cv2.putText(frame_bgr, f"P{index}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, bbox_color, 2)
        # 角色标签
        if role_label:
            cv2.putText(frame_bgr, role_label, (x1, y2 + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, bbox_color, 2)

    return frame_bgr


def draw_cpr_overlay(frame_bgr, analysis, keypoints):
    """绘制 CPR 分析结果的文字叠加层"""
    if keypoints is None:
        return frame_bgr

    h = frame_bgr.shape[0]
    ks = keypoints

    # 文字参数
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    y0 = 30
    dy = 28

    def _put(text, color, row):
        y = y0 + row * dy
        cv2.putText(frame_bgr, text, (10, y), font, font_scale, color, thickness)

    _put(f"BPM: {analysis['bpm']:.0f}", (0, 255, 0), 0)
    _put(f"Elbow: {analysis['elbow_angle']:.0f} deg", (0, 255, 255), 1)
    _put(f"Position: {analysis['hand_position']}", (0, 255, 0) if analysis['hand_in_roi'] else (0, 0, 255), 2)
    _put(f"Recoil: {analysis['recoil']}", (0, 255, 0) if analysis['recoil_ok'] else (0, 0, 255), 3)

    return frame_bgr


def _in_bounds(pt, w, h):
    return 0 <= pt[0] < w and 0 <= pt[1] < h
