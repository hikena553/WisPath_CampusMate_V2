"""训练 YOLOv8n 单类人脸检测器（用于"先检测人脸再识别表情"链路）。

以 COCO 预训练权重为起点做迁移（面部不在 COCO 类别里，但低层边缘/纹理特征可复用），
在 ml/face_detect_data.py 合成的 320×240 检测数据上微调。

用法（在 backend 目录下）：
  python -m ml.train_yolo_face --epochs 40 --imgsz 320

产物：ml/runs/yolo-face/weights/best.pt
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .face_detect_data import OUT_ROOT

RUN_DIR = Path(__file__).resolve().parent / "runs"


def main() -> None:
    ap = argparse.ArgumentParser(description="训练 YOLOv8n 人脸检测器")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--model", type=str, default="yolov8n.pt", help="预训练权重（COCO）")
    ap.add_argument("--name", type=str, default="yolo-face")
    ap.add_argument("--data", type=str, default="",
                    help="dataset.yaml 路径；留空则用合成的 ml/data/face_detect/dataset.yaml")
    ap.add_argument("--device", type=str, default="0")
    ap.add_argument("--patience", type=int, default=15)
    args = ap.parse_args()

    from ultralytics import YOLO

    data_yaml = Path(args.data) if args.data else (OUT_ROOT / "dataset.yaml")
    if not data_yaml.exists():
        raise SystemExit(f"检测数据集不存在：{data_yaml}")

    model = YOLO(args.model)
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=0,          # Windows 下取 0，避免 dataloader 子进程问题
        project=str(RUN_DIR),
        name=args.name,
        exist_ok=True,
        pretrained=True,
        optimizer="auto",
        patience=args.patience,
        val=True,
        plots=False,
        verbose=True,
        seed=42,
        deterministic=False,
    )
    best = RUN_DIR / args.name / "weights" / "best.pt"
    print(f"训练完成，最佳权重: {best}")


if __name__ == "__main__":
    main()