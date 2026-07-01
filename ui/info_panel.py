"""
右侧信息面板 — 实时参数 + 统计 + 控制按钮
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QProgressBar, QComboBox, QSpinBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class InfoPanel(QWidget):
    """封装右侧控制与显示面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # --- 实时参数组 ---
        realtime_group = QGroupBox("实时参数")
        realtime_layout = QVBoxLayout()
        realtime_layout.setSpacing(12)

        # 肘关节角度
        self._elbow_angle_label = self._make_param_row(realtime_layout, "肘关节角度:", "--°")

        # 按压频率
        self._bpm_label = self._make_param_row(realtime_layout, "按压频率:", "-- bpm")

        # 按压位置
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("按压位置:"))
        self._pos_value = QLabel("--")
        self._pos_value.setObjectName("param_value")
        self._pos_indicator = QLabel("●")
        self._pos_indicator.setObjectName("indicator_green")
        pos_layout.addStretch()
        pos_layout.addWidget(self._pos_value)
        pos_layout.addWidget(self._pos_indicator)
        realtime_layout.addLayout(pos_layout)

        # 回弹状态
        recoil_layout = QHBoxLayout()
        recoil_layout.addWidget(QLabel("回弹状态:"))
        self._recoil_value = QLabel("--")
        self._recoil_value.setObjectName("param_value")
        self._recoil_indicator = QLabel("✓")
        self._recoil_indicator.setObjectName("indicator_green")
        recoil_layout.addStretch()
        recoil_layout.addWidget(self._recoil_value)
        recoil_layout.addWidget(self._recoil_indicator)
        realtime_layout.addLayout(recoil_layout)

        # 按压深度
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("按压深度:"))
        self._depth_value = QLabel("--")
        self._depth_value.setObjectName("param_value")
        self._depth_indicator = QLabel("--")
        self._depth_indicator.setObjectName("param_value")
        depth_layout.addStretch()
        depth_layout.addWidget(self._depth_value)
        depth_layout.addWidget(self._depth_indicator)
        realtime_layout.addLayout(depth_layout)

        # 标定状态
        self._calib_status = QLabel("⚠ 未标定 — 点击下方按钮标定")
        self._calib_status.setStyleSheet("color: #ffc107; font-size: 11px;")
        self._calib_status.setWordWrap(True)
        realtime_layout.addWidget(self._calib_status)

        realtime_group.setLayout(realtime_layout)
        layout.addWidget(realtime_group)

        # --- 本次统计组 ---
        stats_group = QGroupBox("本次统计")
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(10)

        self._total_label = self._make_param_row(stats_layout, "按压总数:", "0")
        self._avg_bpm_label = self._make_param_row(stats_layout, "平均频率:", "-- bpm")

        # 优良率
        quality_layout = QVBoxLayout()
        quality_layout.addWidget(QLabel("优良率"))
        self._quality_bar = QProgressBar()
        self._quality_bar.setValue(0)
        self._quality_bar.setFormat("%p%")
        self._quality_bar.setFixedHeight(20)
        quality_layout.addWidget(self._quality_bar)
        stats_layout.addLayout(quality_layout)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # --- 角色分配 ---
        role_group = QGroupBox("角色分配")
        role_layout = QVBoxLayout()
        role_layout.setSpacing(8)

        rescuer_row = QHBoxLayout()
        rescuer_row.addWidget(QLabel("施救者:"))
        self._rescuer_spin = QSpinBox()
        self._rescuer_spin.setRange(-1, 9)
        self._rescuer_spin.setValue(0)
        self._rescuer_spin.setSpecialValueText("无")
        self._rescuer_spin.setToolTip("选择施救者编号 (-1=无)")
        rescuer_row.addWidget(self._rescuer_spin)
        role_layout.addLayout(rescuer_row)

        patient_row = QHBoxLayout()
        patient_row.addWidget(QLabel("患  者:"))
        self._patient_spin = QSpinBox()
        self._patient_spin.setRange(-1, 9)
        self._patient_spin.setValue(1)
        self._patient_spin.setSpecialValueText("无")
        self._patient_spin.setToolTip("选择患者编号 (-1=无)")
        patient_row.addWidget(self._patient_spin)
        role_layout.addLayout(patient_row)

        role_group.setLayout(role_layout)
        layout.addWidget(role_group)

        # --- 摄像头选择 ---
        cam_group = QGroupBox("摄像头")
        cam_layout = QHBoxLayout()
        self._camera_combo = QComboBox()
        self._camera_combo.setMinimumWidth(180)
        self._cam_refresh_btn = QPushButton("⟳")
        self._cam_refresh_btn.setFixedSize(36, 36)
        self._cam_refresh_btn.setToolTip("刷新摄像头列表")
        cam_layout.addWidget(self._camera_combo)
        cam_layout.addWidget(self._cam_refresh_btn)
        cam_group.setLayout(cam_layout)
        layout.addWidget(cam_group)

        # --- 控制按钮 ---
        btn_layout = QVBoxLayout()
        self._start_btn = QPushButton("▶ 开始评估")
        self._start_btn.setFixedHeight(45)
        self._reset_btn = QPushButton("↻ 重置")
        self._reset_btn.setFixedHeight(40)
        self._calib_btn = QPushButton("📍 标定 ROI")
        self._calib_btn.setFixedHeight(40)

        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._reset_btn)
        btn_layout.addWidget(self._calib_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _make_param_row(self, parent_layout, label_text, value_text):
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        value_label = QLabel(value_text)
        value_label.setObjectName("param_value")
        row.addStretch()
        row.addWidget(value_label)
        parent_layout.addLayout(row)
        return value_label

    # --- 公共更新接口 ---

    def update_realtime(self, analysis: dict):
        """更新实时参数显示"""
        angle = analysis.get("elbow_angle", 0)
        self._elbow_angle_label.setText(f"{angle:.0f}°")
        self._elbow_angle_label.setObjectName(
            "indicator_green" if analysis.get("arm_straight") else "indicator_red"
        )

        bpm = analysis.get("bpm", 0)
        self._bpm_label.setText(f"{bpm:.0f} bpm")
        # BPM 颜色
        if 100 <= bpm <= 120:
            self._bpm_label.setObjectName("indicator_green")
        elif bpm > 0:
            self._bpm_label.setObjectName("indicator_yellow")
        else:
            self._bpm_label.setObjectName("param_value")

        hand_ok = analysis.get("hand_in_roi", False)
        self._pos_value.setText(analysis.get("hand_position", "--"))
        self._pos_indicator.setText("●")
        self._pos_indicator.setObjectName(
            "indicator_green" if hand_ok else "indicator_red"
        )

        recoil_ok = analysis.get("recoil_ok", False)
        self._recoil_value.setText(analysis.get("recoil", "--"))
        self._recoil_indicator.setText("✓" if recoil_ok else "✗")
        self._recoil_indicator.setObjectName(
            "indicator_green" if recoil_ok else "indicator_red"
        )

        # 按压深度
        if analysis.get("calibrated"):
            depth = analysis.get("depth_pct", 0)
            self._depth_value.setText(f"{depth:.1f}%")
            depth_ok = analysis.get("depth_ok", False)
            self._depth_indicator.setText("✓" if depth_ok else "✗")
            self._depth_indicator.setObjectName(
                "indicator_green" if depth_ok else "indicator_red"
            )
            self._calib_status.setText("✓ 已标定")
            self._calib_status.setStyleSheet("color: #4caf50; font-size: 11px;")
        else:
            self._depth_value.setText("--")
            self._depth_indicator.setText("--")
            self._depth_indicator.setObjectName("param_value")
            self._calib_status.setText("⚠ 未标定 — 点击下方按钮标定")
            self._calib_status.setStyleSheet("color: #ffc107; font-size: 11px;")

        # 刷新样式
        for lbl in [self._elbow_angle_label, self._bpm_label,
                     self._pos_indicator, self._recoil_indicator,
                     self._depth_indicator]:
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

    def update_stats(self, analysis: dict):
        """更新统计面板"""
        self._total_label.setText(str(analysis.get("total_presses", 0)))
        bpm = analysis.get("bpm", 0)
        self._avg_bpm_label.setText(f"{bpm:.0f} bpm" if bpm > 0 else "-- bpm")
        self._quality_bar.setValue(int(analysis.get("quality_pct", 0)))

    # --- 按钮信号 ---
    @property
    def start_btn(self):
        return self._start_btn

    @property
    def reset_btn(self):
        return self._reset_btn

    @property
    def calib_btn(self):
        return self._calib_btn

    @property
    def camera_combo(self):
        return self._camera_combo

    @property
    def cam_refresh_btn(self):
        return self._cam_refresh_btn

    @property
    def rescuer_spin(self):
        return self._rescuer_spin

    @property
    def patient_spin(self):
        return self._patient_spin

    def update_person_count(self, count):
        """更新角色选择器的范围 (0 ~ count-1)"""
        for spin in [self._rescuer_spin, self._patient_spin]:
            spin.blockSignals(True)
            spin.setMaximum(count - 1 if count > 0 else -1)
            spin.blockSignals(False)
