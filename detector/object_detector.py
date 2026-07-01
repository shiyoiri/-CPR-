"""
YOLOv8n 目标检测 — 检测画面中的人体
"""
from ultralytics import YOLO
import numpy as np

import config


class ObjectDetector:
    """使用 YOLOv8n 检测人体 (COCO class 0)"""

    def __init__(self, model_path=None):
        self._model_path = model_path or config.MODEL_DETECT
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

    def detect(self, frame_rgb: np.ndarray, conf: float = 0.3):
        """
        检测帧中的人体。
        返回: {
            "bbox": (x1, y1, x2, y2),   # 主目标人体框
            "confidence": float,
            "all_persons": [(x1, y1, x2, y2, conf), ...]
        }
        未检测到时返回 None。
        """
        results = self.model(frame_rgb, conf=conf, verbose=False)

        persons = []
        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for i, cls in enumerate(boxes.cls):
                if int(cls.item()) == 0:  # COCO person
                    x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                    conf_val = float(boxes.conf[i].item())
                    persons.append((int(x1), int(y1), int(x2), int(y2), conf_val))

        if not persons:
            return None

        # 选取置信度最高的人体
        best = max(persons, key=lambda p: p[4])
        return {
            "bbox": (best[0], best[1], best[2], best[3]),
            "confidence": best[4],
            "all_persons": persons,
        }
