# 智能CPR手势评估系统 — 工作日志

## 项目信息

| 项目 | 说明 |
|------|------|
| 课程 | 医学仪器原理与设计 |
| 项目名称 | 智能CPR手势评估系统 |
| 路径 | `D:\25Summer_py3.12\26S\class\` |
| Python环境 | `D:\anaconda\envs\25Summer(py3.12\python.exe` |
| 创建日期 | 2026-05-07 |

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.12 | 运行环境 |
| PyTorch | 2.6.0+cu126 | 深度学习框架 |
| Ultralytics | 8.4.47 | YOLOv8 模型加载与推理 |
| OpenCV | 4.13.0 | 摄像头采集、图像绘制 |
| PyQt5 | 5.15.10 | 桌面GUI |
| NumPy | 2.1.2 | 数值计算 |

## 项目结构

```
D:\25Summer_py3.12\26S\class\
├── main.py                    # 入口文件
├── config.py                  # 全局配置
├── requirements.txt           # 依赖清单
├── download_models.py         # 模型预下载脚本（多源fallback）
├── .gitignore
├── 1.py                       # 原始UI原型（保留）
├── yolov8n.pt                 # 目标检测模型（6.5 MB）
├── yolov8n-pose.pt            # 姿态估计模型（6.5 MB）
├── camera/
│   └── camera_thread.py       # QThread 摄像头线程
├── detector/
│   ├── object_detector.py     # YOLOv8n 人体检测（延迟加载）
│   └── pose_estimator.py      # YOLOv8n-pose 关键点估计
├── analyzer/
│   └── cpr_analyzer.py        # CPR按压质量分析
├── ui/
│   ├── main_window.py         # 主窗口（组装+信号槽）
│   ├── video_widget.py        # 视频显示组件
│   └── info_panel.py          # 右侧参数面板
└── utils/
    └── draw_utils.py          # 骨架/文字绘制工具
```

## CPR分析指标

| 指标 | 方法 | 目标值 |
|------|------|--------|
| 肘关节角度 | shoulder→elbow→wrist 三点夹角 | ≥160° |
| 按压频率(BPM) | wrist Y坐标峰值间隔，5s滑动窗口 | 100–120 bpm |
| 手部位置 | wrist X是否在身体中心±20%范围内 | 胸骨下半段 |
| 回弹状态 | wrist Y是否回到基线±2%范围 | 充分回弹 |
| 优良率 | 达标按压数/总按压数 | - |

## 关键设计决策

1. **延迟加载模型**：ObjectDetector 和 PoseEstimator 在首次推理时才加载 .pt 文件，UI 可先启动
2. **跳帧推理**：每 2 帧推理一次（`INFER_EVERY_N_FRAMES = 2`），保证实时性
3. **线程模型**：仅摄像头采集在 QThread，YOLO 推理和 UI 更新在主线程
4. **单目深度限制**：无法测量精确厘米深度，使用肩-腕距离的相对变化判断按压幅度
5. **原有文件保留**：`1.py` 和 `模拟UI.png` 未修改

## 已知问题

| 问题 | 说明 | 解决方案 |
|------|------|----------|
| GitHub下载失败 | 国内网络curl无法连接GitHub | 使用urllib+自定义UA；HF镜像下载检测模型 |
| 单目深度不准 | 无法精确测量按压深度(cm) | 使用相对距离变化判断"有无按压"和一致性 |
| 无GPU | 默认CPU推理 | 如有NVIDIA GPU，修改 `model.to("cuda")` |

## 启动方式

```bash
# 激活环境 & 运行
D:\anaconda\envs\25Summer(py3.12\python.exe D:\25Summer_py3.12\26S\class\main.py

# 如模型丢失，重新下载
D:\anaconda\envs\25Summer(py3.12\python.exe D:\25Summer_py3.12\26S\class\download_models.py
```

## 验证结果 (2026-05-07)

- [x] 所有模块导入成功
- [x] yolov8n.pt 加载成功（检测）
- [x] yolov8n-pose.pt 加载成功（姿态）
- [x] UI 窗口创建正常（暗色主题 + 左右布局）
- [x] CPR 分析器单元测试通过（角度计算、空输入、模拟按压）
- [x] 摄像头线程、检测器、分析器、UI 面板全部初始化正常
