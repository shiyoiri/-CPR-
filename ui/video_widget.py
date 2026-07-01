"""
视频显示组件 — QLabel + QPixmap 承载摄像头画面
"""
from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont
import numpy as np
import cv2


class VideoWidget(QLabel):
    """显示实时视频帧，支持自适应缩放"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("video_label")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(640, 400)

        self._current_frame_bgr = None
        self._placeholder_text = "摄像头画面区域\n(实时姿态叠加显示)"

        self._show_placeholder()

    def _show_placeholder(self):
        pixmap = QPixmap(640, 400)
        pixmap.fill(QColor(10, 10, 20))
        painter = QPainter(pixmap)
        painter.setPen(QColor(100, 100, 120))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, self._placeholder_text)
        painter.end()
        self.setPixmap(pixmap)

    def update_frame(self, frame_bgr: np.ndarray):
        """
        更新视频画面。
        frame_bgr: BGR 格式的 numpy 数组 (H, W, 3)
        """
        self._current_frame_bgr = frame_bgr
        h, w, ch = frame_bgr.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_bgr.data, w, h, bytes_per_line, QImage.Format_BGR888)

        pixmap = QPixmap.fromImage(qimg)
        self._display_scaled(pixmap)

    def update_placeholder(self, text=None):
        if text:
            self._placeholder_text = text
        self._show_placeholder()

    def _display_scaled(self, pixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event):
        pixmap = self.pixmap()
        if pixmap and not pixmap.isNull():
            self._display_scaled(pixmap)
        super().resizeEvent(event)

    @property
    def current_frame(self):
        return self._current_frame_bgr
