"""
预下载 YOLO 模型文件
  运行: python download_models.py

下载源:
  1. GitHub Releases (urllib, 直连)
  2. HuggingFace 镜像 (hf-mirror.com, 仅检测模型)
"""
import sys
import os
import urllib.request
import ssl

MODELS = {
    "yolov8n.pt": (
        "YOLOv8n 目标检测 (人体检测)",
        [
            "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt",
            "https://hf-mirror.com/Ultralytics/YOLOv8/resolve/main/yolov8n.pt",
        ],
    ),
    "yolov8n-pose.pt": (
        "YOLOv8n-pose 姿态估计 (17关键点)",
        [
            "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n-pose.pt",
        ],
    ),
}

def _download_urllib(url, dest):
    """使用 urllib 下载，绕过某些网络环境中 curl 的限制"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        with open(dest, "wb") as f:
            f.write(resp.read())
    return os.path.getsize(dest)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    for filename, (desc, urls) in MODELS.items():
        dest = os.path.join(base_dir, filename)

        # 已存在则跳过
        if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
            size_mb = os.path.getsize(dest) / 1024 / 1024
            print(f"[SKIP] {filename} already exists ({size_mb:.1f} MB)")
            continue

        print(f"Downloading {filename} ({desc})...")
        ok = False
        for url in urls:
            try:
                size = _download_urllib(url, dest)
                if size > 1_000_000:
                    print(f"  => OK ({size/1024/1024:.1f} MB) from {url.split('/')[2]}")
                    ok = True
                    break
            except Exception as e:
                print(f"  => Failed ({url.split('/')[2]}): {e}")

        if not ok:
            print(f"  => ALL SOURCES FAILED for {filename}", file=sys.stderr)
            print(f"     Please download manually and place in: {base_dir}", file=sys.stderr)
            return 1

    print("\nAll models ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
