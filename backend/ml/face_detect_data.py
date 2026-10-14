"""为 YOLOv8 人脸检测合成训练数据（单类 face）。

背景问题：本项目所处的网络环境拿不到 WIDER FACE 等带框的人脸检测数据集
（HuggingFace 主站不可达，Kaggle 需要凭证）。因此用**本地可得的 FER2013
人脸图**合成检测数据：把人脸贴到随机灰度背景上的随机位置与尺度，bbox 由
合成过程直接给出，标注精确且零成本。

用途与边界（必须如实说明）：
  - 该数据集只覆盖"单张人脸 / 少量人脸 + 简单背景"，用于验证
    "YOLOv8 定位人脸 -> 裁剪 -> 表情分类"这条链路；
  - 与真实摄像头画面（复杂背景、遮挡、姿态）存在域差异，
    不宣称可替代在真实检测数据集上训练的模型。

画布默认 320×240，与前端的摄像头采集分辨率一致。
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import DATA_DIR
from .dataset import FER_LABEL_MAP, _base_image, _load_split, ensure_dataset
from .config import TrainingConfig

OUT_ROOT = DATA_DIR.parent / "face_detect"


def _random_background(w: int, h: int) -> Image.Image:
    """随机灰度背景：底色 + 噪声 + 若干随机矩形，避免背景过于单一。"""
    base = random.randint(30, 200)
    arr = np.full((h, w), base, dtype=np.float32)
    # 低频梯度
    gy, gx = np.mgrid[0:h, 0:w]
    arr += np.sin(gx / random.uniform(40, 160)) * random.uniform(0, 18)
    arr += np.cos(gy / random.uniform(40, 160)) * random.uniform(0, 18)
    # 随机矩形块
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="L")
    d = ImageDraw.Draw(img)
    for _ in range(random.randint(0, 5)):
        x0, y0 = random.randint(0, w - 1), random.randint(0, h - 1)
        x1, y1 = x0 + random.randint(8, w // 2), y0 + random.randint(8, h // 2)
        d.rectangle([x0, y0, x1, y1], fill=random.randint(20, 235))
    # 高斯噪声
    arr = np.asarray(img, dtype=np.float32) + np.random.normal(0, 6, (h, w))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="L")


def _paste_face(canvas: Image.Image, face: Image.Image, box_hw: tuple[int, int],
                center: tuple[int, int], angle: float) -> tuple[int, int, int, int]:
    """把人脸缩放/旋转后贴到画布，返回其在画布上的边界框 (x0, y0, x1, y1)。"""
    fw, fh = box_hw
    f = face.resize((fw, fh), Image.BILINEAR).rotate(angle, resample=Image.BILINEAR, expand=True,
                                                     fillcolor=None)
    # 旋转后尺寸变化，重新计算贴图位置
    rw, rh = f.size
    cx, cy = center
    x0, y0 = int(cx - rw / 2), int(cy - rh / 2)
    if f.mode == "L":
        canvas.paste(f, (x0, y0))
    return (x0, y0, x0 + rw, y0 + rh)


def _make_one(records: list[dict], w: int, h: int, size: int) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    canvas = _random_background(w, h)
    n_face = 1 if random.random() < 0.75 else 2
    boxes: list[tuple[int, int, int, int]] = []
    for _ in range(n_face):
        rec = random.choice(records)
        face = _base_image(rec["img_bytes"], size)
        # 人脸高度占画布的 22% ~ 62%
        fh = int(h * random.uniform(0.22, 0.62))
        fw = fh
        cx = random.randint(int(fw * 0.5), w - int(fw * 0.5))
        cy = random.randint(int(fh * 0.5), h - int(fh * 0.5))
        ang = random.uniform(-12, 12)
        boxes.append(_paste_face(canvas, face, (fw, fh), (cx, cy), ang))
    # 轻微模糊，模拟摄像头成像
    if random.random() < 0.35:
        canvas = canvas.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.4, 1.2)))
    return canvas, boxes


def build(split: str, n: int, w: int, h: int, size: int, records: list[dict], seed: int) -> int:
    random.seed(seed)
    np.random.seed(seed)
    img_dir = OUT_ROOT / "images" / split
    lbl_dir = OUT_ROOT / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    kept = 0
    for i in range(n):
        canvas, boxes = _make_one(records, w, h, size)
        lines = []
        for (x0, y0, x1, y1) in boxes:
            # 裁剪到画布内
            cx0, cy0 = max(0, x0), max(0, y0)
            cx1, cy1 = min(w, x1), min(h, y1)
            if cx1 - cx0 < size // 2 or cy1 - cy0 < size // 2:
                continue
            # 画布内可见目标占比过低则丢弃（避免过小的半张脸标签）
            if (cx1 - cx0) * (cy1 - cy0) < 0.35 * (x1 - x0) * (y1 - y0):
                continue
            cx = (cx0 + cx1) / 2 / w
            cy = (cy0 + cy1) / 2 / h
            bw = (cx1 - cx0) / w
            bh = (cy1 - cy0) / h
            lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        if not lines:
            continue
        name = f"{split}_{i:05d}"
        canvas.save(img_dir / f"{name}.jpg", quality=92)
        (lbl_dir / f"{name}.txt").write_text("\n".join(lines), encoding="utf-8")
        kept += 1
    return kept


def main() -> None:
    ap = argparse.ArgumentParser(description="合成 YOLOv8 人脸检测数据")
    ap.add_argument("--train", type=int, default=4000)
    ap.add_argument("--val", type=int, default=600)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--face-size", type=int, default=64)
    args = ap.parse_args()

    cfg = TrainingConfig()
    train_p, _ = ensure_dataset(cfg)
    recs = _load_split(train_p)
    # 合成用的人脸只取前 60%，与表情训练的验证切分错开，降低"认出训练脸"的假象
    recs = recs[: int(len(recs) * 0.6)]

    n_tr = build("train", args.train, args.width, args.height, args.face_size, recs, seed=11)
    n_va = build("val", args.val, args.width, args.height, args.face_size, recs, seed=22)

    yaml = OUT_ROOT / "dataset.yaml"
    yaml.write_text(
        f"path: {OUT_ROOT.as_posix()}\ntrain: images/train\nval: images/val\n"
        f"nc: 1\nnames:\n  0: face\n",
        encoding="utf-8",
    )
    print(f"合成完成：train {n_tr} / val {n_va}，画布 {args.width}×{args.height}")
    print(f"数据根目录: {OUT_ROOT}")
    print(f"dataset.yaml: {yaml}")


if __name__ == "__main__":
    main()