# 智能 CPR 手势评估系统

基于单目摄像头的实时 CPR（心肺复苏）手势质量评估系统。使用双 YOLOv8 模型（目标检测 + 姿态估计）结合 PyQt5 桌面 GUI，实现对胸外按压动作的自动分析与反馈。

## 功能特性

- **实时双模型推理** — YOLOv8n 人体检测 + YOLOv8n-pose 17 关键点姿态估计并行运行
- **多维度 CPR 评估** — 肘部角度、按压频率 (BPM)、手部位置、回弹幅度、按压深度
- **手动角色分配** — 支持多人体场景，通过 QSpinBox 手动指定施救者/患者编号
- **ROI 标定** — 一键标定正确姿势，后续分析基于标定基准比较
- **深色主题 UI** — PyQt5 桌面应用，实时视频叠加骨架线与评估指标
- **摄像头热拔插** — 自动扫描可用摄像头，支持运行时切换

## 项目结构

```
.
├── main.py                     # 入口
├── config.py                   # 全局配置（阈值、COCO索引、UI颜色）
├── download_models.py          # 模型下载脚本（HF镜像/urllib 回退）
├── requirements.txt
├── analyzer/
│   └── cpr_analyzer.py         # CPR 分析核心（角度/BPM/深度/按压计数）
├── camera/
│   └── camera_thread.py        # QThread 全管线：采集→检测→姿态→分析→绘制
├── detector/
│   ├── object_detector.py      # YOLOv8n 人体检测
│   └── pose_estimator.py       # YOLOv8n-pose 姿态估计
├── ui/
│   ├── main_window.py          # 主窗口组装、信号连接
│   ├── video_widget.py         # QLabel + QPixmap 视频显示
│   └── info_panel.py           # 实时参数面板 + 控制按钮
└── utils/
    └── draw_utils.py           # 骨架叠加绘制、角色着色
```

## 环境要求

- Python 3.12+
- PyTorch ≥ 2.0.0
- CUDA 12.6（可选，CPU 亦可运行）

```bash
pip install -r requirements.txt
```

首次运行时会自动下载模型文件（`yolov8n.pt`、`yolov8n-pose.pt`）。若网络受限，可手动运行：

```bash
python download_models.py
```

## 运行

```bash
python main.py
```

## 使用说明

1. 启动后选择摄像头，点击「开始」
2. 画面中出现人体框和编号（P0、P1…），用面板中的数字框指定施救者/患者
3. 让施救者保持正确 CPR 姿势，点击「标定 ROI」记录基准
4. 开始按压后，系统实时评估：肘角、频率、手位、回弹、深度
5. 单次按压质量 = 所有维度达标数 / 维度总数

## 评估维度

| 维度 | 标准 | 权重 |
|------|------|------|
| 肘部角度 | ≥ 160°（手臂伸直） | ✓ |
| 按压频率 | 100–120 BPM | ✓ |
| 手部 X 位置 | 身体中心 ± 15% 身宽 | ✓ |
| 手部 Y 位置 | 身体 ± 10% 身高 | ✓ |
| 回弹幅度 | 手腕回至基线 ± 2% | ✓ |
| 按压深度 | 肩腕距变化 ≥ 5%（需标定） | ✓ |

## 技术栈

- **UI**: PyQt5 5.15
- **检测**: YOLOv8n
- **姿态**: YOLOv8n-pose（COCO 17 关键点）
- **视觉**: OpenCV 4.x
- **推理**: PyTorch + ultralytics
