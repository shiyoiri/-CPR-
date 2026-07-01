"""
YOLOv8n-pose 姿态估计 — 提取人体17个关键点
"""
from ultralytics import YOLO
import numpy as np

import config


class PoseEstimator:
    """使用 YOLOv8n-pose 估计人体姿态"""

    def __init__(self, model_path=None):
        self._model_path = model_path or config.MODEL_POSE
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = YOLO(self._model_path)
            self._model.to("cpu")
        return self._model

    def is_ready(self):
        import os
        return os.path.exists(self._model_path)

    def estimate_all(self, frame_rgb: np.ndarray, conf: float = 0.3):
        """
        返回所有检测到的人体姿态（不筛选）。
        返回: [
            {"keypoints": [(x, y, conf)*17], "bbox": (x1, y1, x2, y2), "confidence": float},
            ...
        ]
        未检测到时返回空列表。
        """
        results = self.model(frame_rgb, conf=conf, verbose=False)
        all_poses = []

        for result in results:
            if result.keypoints is None:
                continue
            kpts_data = result.keypoints.data  # (N, 17, 3)
            if kpts_data.shape[0] == 0:
                continue

            boxes = result.boxes
            for i, k in enumerate(kpts_data):
                k_arr = k.cpu().numpy()
                avg_conf = float(k_arr[:, 2].mean())

                bbox = None
                if boxes is not None and i < len(boxes):
                    x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                    bbox = (int(x1), int(y1), int(x2), int(y2))

                all_poses.append({
                    "keypoints": [(float(k[0]), float(k[1]), float(k[2])) for k in k_arr],
                    "bbox": bbox,
                    "confidence": avg_conf,
                })

        return all_poses

    def estimate(self, frame_rgb: np.ndarray, person_bbox=None, conf: float = 0.3):
        """
        提取人体17关键点。
        参数:
            frame_rgb: RGB 图像
            person_bbox: 可选 (x1, y1, x2, y2), 限定检测区域
        返回: {
            "keypoints": [(x, y, conf), ...]  17个点
        }
        未检测到时返回 None。
        """
        results = self.model(frame_rgb, conf=conf, verbose=False)

        best_kpts = None
        best_conf = 0.0

        for result in results:
            if result.keypoints is None:
                continue
            kpts_data = result.keypoints.data  # (N, 17, 3)
            if kpts_data.shape[0] == 0:
                continue

            if person_bbox is not None:
                # 只取在人体检测框内的关键点
                x1, y1, x2, y2 = person_bbox
                for k in kpts_data:
                    k_arr = k.cpu().numpy()
                    xs, ys = k_arr[:, 0], k_arr[:, 1]
                    confs = k_arr[:, 2]
                    valid = (xs >= x1) & (xs <= x2) & (ys >= y1) & (ys <= y2)
                    if valid.sum() >= 3:
                        avg_conf = float(confs[valid].mean())
                        if avg_conf > best_conf:
                            best_conf = avg_conf
                            best_kpts = k_arr
            else:
                k_arr = kpts_data[0].cpu().numpy()
                avg_conf = float(k_arr[:, 2].mean())
                if avg_conf > best_conf:
                    best_conf = avg_conf
                    best_kpts = k_arr

        if best_kpts is None:
            return None

        return {
            "keypoints": [(float(k[0]), float(k[1]), float(k[2])) for k in best_kpts],
            "avg_confidence": best_conf,
        }
