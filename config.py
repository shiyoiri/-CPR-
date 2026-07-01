"""
智能CPR识别系统 — 全局配置
"""
import os

# --- 路径 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- YOLO 模型 ---
MODEL_DETECT = "yolov8n.pt"       # 目标检测 (人体)
MODEL_POSE   = "yolov8n-pose.pt"  # 姿态估计 (17关键点)

# --- 摄像头 ---
CAMERA_ID = 1          # 默认摄像头索引
FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720
CAMERA_FPS  = 30

# --- 推理间隔 (跳帧策略，保持实时) ---
INFER_EVERY_N_FRAMES = 2

# --- COCO 关键点索引 ---
COCO = {
    "NOSE": 0, "LEFT_EYE": 1, "RIGHT_EYE": 2, "LEFT_EAR": 3, "RIGHT_EAR": 4,
    "LEFT_SHOULDER": 5, "RIGHT_SHOULDER": 6, "LEFT_ELBOW": 7, "RIGHT_ELBOW": 8,
    "LEFT_WRIST": 9, "RIGHT_WRIST": 10, "LEFT_HIP": 11, "RIGHT_HIP": 12,
    "LEFT_KNEE": 13, "RIGHT_KNEE": 14, "LEFT_ANKLE": 15, "RIGHT_ANKLE": 16,
}

# 骨架连线 (哪两个关键点之间画线)
SKELETON_EDGES = [
    (5, 7), (7, 9),    # 左肩 → 左肘 → 左腕
    (6, 8), (8, 10),   # 右肩 → 右肘 → 右腕
    (5, 6),            # 双肩
    (5, 11), (6, 12),  # 肩 → 髋
    (11, 12),          # 双髋
]

# --- CPR 分析阈值 ---
CPR_BPM_MIN = 100           # 目标最小按压频率
CPR_BPM_MAX = 120           # 目标最大按压频率
CPR_ELBOW_ANGLE_MIN = 160   # 手臂伸直最小角度 (度)
CPR_WINDOW_SEC = 5.0        # 按压统计滑动窗口 (秒)
CPR_DEPTH_RELATIVE_MIN = 0.03  # 相对深度变化最小阈值

# --- 标定容差 ---
CALIB = {
    "HAND_X_TOLERANCE": 0.15,    # 手部 X 偏移容差 (相对人体宽度)
    "HAND_Y_TOLERANCE": 0.10,    # 手部 Y 位置容差 (相对人体高度)
    "DEPTH_CHANGE_MIN": 0.05,    # 肩腕距相对变化最小值 (按压深度)
}

# --- 施救者/被救者分类 ---
PERSON_CLASSIFY = {
    "KNEE_BENT_MAX": 140,            # 膝角 < 此值 → 跪姿 (施救者)
    "KNEE_STRAIGHT_MIN": 140,        # 膝角 ≥ 此值 → 直腿 (平躺)
    "TORSO_ANGLE_STANDING_MIN": 40,  # 躯干与水平面夹角 > 此值 → 施救者 (俯视下调)
    "TORSO_ANGLE_LYING_MAX": 25,     # 躯干与水平面夹角 < 此值 → 平躺
    "HEAD_HIP_DY_RESCUER_MIN": 0.05, # 头-髋 Y差/画面高 > 此值 → 头高于髋 (施救者)
    "BBOX_HW_RATIO_STANDING": 1.15,  # bbox 高/宽 > 此值 → 施救者 (放宽)
    "BBOX_WH_RATIO_LYING": 1.15,     # bbox 宽/高 > 此值 → 平躺
}

# --- UI 样式 ---
DARK_THEME_COLORS = {
    "bg_primary":    "#1e1e2f",
    "bg_secondary":  "#252540",
    "border":        "#3a3a5a",
    "text_primary":  "#e0e0e0",
    "text_white":    "#ffffff",
    "accent_blue":   "#aadcff",
    "accent_green":  "#4caf50",
    "accent_red":    "#f44336",
    "accent_yellow": "#ffc107",
    "btn_bg":        "#2d2d4a",
    "btn_hover":     "#3d3d6a",
    "btn_pressed":   "#1e1e3a",
    "video_bg":      "#0a0a14",
}
