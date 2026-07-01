"""
主窗口 — 组装摄像头、UI显示 (推理在子线程，主线程仅更新UI)
"""
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from camera.camera_thread import CameraThread
from ui.video_widget import VideoWidget
from ui.info_panel import InfoPanel
import config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能 CPR 手势评估系统")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(self._stylesheet())

        self.camera = None
        self._running = False
        self._empty_analysis = {
            "elbow_angle": 0.0, "arm_straight": False,
            "bpm": 0.0, "hand_position": "--", "hand_in_roi": False,
            "recoil": "--", "recoil_ok": False,
            "depth_ok": False, "depth_pct": 0.0, "calibrated": False,
            "total_presses": 0, "good_presses": 0,
            "quality_pct": 0.0, "side": "--",
        }

        self._init_ui()
        self._connect_signals()
        self._check_models()
        self._scan_cameras()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(12)

        # --- 顶部状态栏 ---
        self._status_frame = QFrame()
        self._status_frame.setObjectName("status_bar")
        self._status_frame.setFixedHeight(50)
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(20, 5, 20, 5)

        self._status_light = QLabel("●")
        self._status_light.setObjectName("indicator_green")
        self._status_light.setFont(QFont("Arial", 16))
        self._status_text = QLabel("系统就绪 — 点击「开始评估」启动")
        self._status_text.setFont(QFont("Arial", 12, QFont.Bold))

        self._fps_label = QLabel("FPS: --")
        self._fps_label.setFont(QFont("Arial", 12))

        status_layout.addWidget(self._status_light)
        status_layout.addWidget(self._status_text)
        status_layout.addStretch()
        status_layout.addWidget(self._fps_label)

        main_layout.addWidget(self._status_frame)

        # --- 主体：左视频 + 右面板 ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        self._video_widget = VideoWidget()
        content_layout.addWidget(self._video_widget, stretch=3)

        self._info_panel = InfoPanel()
        content_layout.addWidget(self._info_panel, stretch=1)

        main_layout.addLayout(content_layout)

    def _connect_signals(self):
        self._info_panel.start_btn.clicked.connect(self._toggle_running)
        self._info_panel.reset_btn.clicked.connect(self._reset)
        self._info_panel.calib_btn.clicked.connect(self._calibrate)
        self._info_panel.cam_refresh_btn.clicked.connect(self._scan_cameras)

    def _toggle_running(self):
        if self._running:
            self._stop()
        else:
            self._start()

    def _start(self):
        cam_id = self._info_panel.camera_combo.currentData()
        self.camera = CameraThread(camera_id=cam_id)
        self.camera.frame_processed.connect(self._on_frame_processed)
        self.camera.analysis_ready.connect(self._on_analysis)
        self.camera.fps_updated.connect(self._on_fps)
        self.camera.person_count_changed.connect(self._info_panel.update_person_count)

        # 用户角色选择 → 同步到子线程
        self._info_panel.rescuer_spin.valueChanged.connect(self._on_rescuer_changed)
        self._info_panel.patient_spin.valueChanged.connect(self._on_patient_changed)
        self.camera.rescuer_index = self._info_panel.rescuer_spin.value()
        self.camera.patient_index = self._info_panel.patient_spin.value()

        self.camera.start()

        self._running = True
        self._info_panel.start_btn.setText("⏸ 停止评估")
        self._status_text.setText("运行中 — 请进行 CPR 操作")
        self._status_light.setObjectName("indicator_green")
        self._refresh_status_style()

    def _stop(self):
        if self.camera:
            self.camera.stop()
            self.camera = None

        self._running = False
        self._info_panel.start_btn.setText("▶ 开始评估")
        self._info_panel.update_person_count(0)
        self._status_text.setText("已停止")
        self._status_light.setObjectName("indicator_yellow")
        self._refresh_status_style()
        self._video_widget.update_placeholder()

    def _reset(self):
        if self.camera:
            self.camera.reset_analyzer()
        self._info_panel.update_realtime(self._empty_analysis)
        self._info_panel.update_stats(self._empty_analysis)
        self._status_text.setText("统计已重置")
        self._fps_label.setText("FPS: --")

    def _calibrate(self):
        if self.camera:
            self.camera.calibrate_next_frame = True
        self._status_text.setText("标定中 — 请保持标准CPR姿势不动...")
        self._refresh_status_style()

    def _on_frame_processed(self, frame_bgr: np.ndarray):
        """接收已处理的帧 (叠加了骨架和分析结果), 仅做 UI 显示"""
        self._video_widget.update_frame(frame_bgr)

    def _on_analysis(self, analysis: dict):
        self._info_panel.update_realtime(analysis)
        self._info_panel.update_stats(analysis)
        # 标定成功提示
        if analysis.get("calibrated") and analysis.get("hand_position") == "已标定":
            self._status_text.setText("标定完成 — 按压位置和深度基线已记录")
            self._refresh_status_style()

    def _on_fps(self, fps: float):
        self._fps_label.setText(f"FPS: {fps:.1f}")

    def _on_rescuer_changed(self, idx):
        if self.camera:
            self.camera.rescuer_index = idx

    def _on_patient_changed(self, idx):
        if self.camera:
            self.camera.patient_index = idx

    def _refresh_status_style(self):
        for lbl in [self._status_light, self._status_text]:
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

    def _check_models(self):
        import os
        det_ok = os.path.exists(config.MODEL_DETECT)
        pose_ok = os.path.exists(config.MODEL_POSE)
        if not det_ok or not pose_ok:
            missing = []
            if not det_ok:
                missing.append("yolov8n.pt")
            if not pose_ok:
                missing.append("yolov8n-pose.pt")
            self._status_text.setText(
                f"模型未下载: {', '.join(missing)} — 运行 download_models.py"
            )
            self._status_light.setObjectName("indicator_yellow")
            self._refresh_status_style()

    def _scan_cameras(self):
        combo = self._info_panel.camera_combo
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.read()  # 丢弃首帧
                combo.addItem(f"Camera {i}", i)
            cap.release()
        if combo.count() == 0:
            combo.addItem("无摄像头", -1)
        elif current is not None and any(combo.itemData(j) == current for j in range(combo.count())):
            combo.setCurrentIndex([combo.itemData(j) for j in range(combo.count())].index(current))
        combo.blockSignals(False)

    def _stylesheet(self):
        return """
            QMainWindow { background-color: #1e1e2f; }
            QLabel { color: #e0e0e0; }
            QGroupBox {
                color: #ffffff; font-weight: bold;
                border: 1px solid #3a3a5a; border-radius: 8px;
                margin-top: 12px; padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 8px 0 8px;
                background-color: #1e1e2f;
            }
            QPushButton {
                background-color: #2d2d4a; color: #ffffff;
                border: 1px solid #4a4a7a; border-radius: 6px;
                padding: 8px 16px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #3d3d6a; }
            QPushButton:pressed { background-color: #1e1e3a; }
            QProgressBar {
                border: 1px solid #4a4a7a; border-radius: 4px;
                text-align: center; color: white;
            }
            QProgressBar::chunk {
                background-color: #4caf50; border-radius: 3px;
            }
            #video_label {
                background-color: #0a0a14;
                border: 2px solid #2a2a4a; border-radius: 8px;
            }
            #status_bar {
                background-color: #252540; border-radius: 6px; padding: 6px;
            }
            #param_value { font-size: 18px; font-weight: bold; color: #aadcff; }
            #indicator_green { color: #4caf50; font-weight: bold; }
            #indicator_red { color: #f44336; font-weight: bold; }
            #indicator_yellow { color: #ffc107; font-weight: bold; }
        """

    def closeEvent(self, event):
        if self.camera:
            self.camera.stop()
        super().closeEvent(event)
