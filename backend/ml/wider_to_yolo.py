"""把 WIDER FACE 转换为 YOLO 单类（face）检测数据集。

WIDER FACE 是真实场景人脸检测基准：3.2 万张图、39 万张标注人脸，
尺度/姿态/遮挡变化极大——这正是"外推到真实摄像头"所需要的数据分布。

标注格式（wider_face_split/wider_face_val_bbx_gt.txt）：
    <相对图片路径>
    <人脸数量 N>
    N 行：x y w h blur expression illumination invalid occlusion pose
其中 invalid=1 的框属于无效标注，直接丢弃。

图片不复制，改用硬链接（同卷零成本），标注写为 YOLO 的归一化 cx cy w h。
用法：
  python -m ml.wider_to_yolo --root <wider目录> --out <输出目录> [--val-ratio 0.2]
"""
from __future__ import annotations

import argparse
import os
import random
import shutil
import zipfile
from pathlib import Path


def ensure_extracted(root: Path) -> Path:
    img_root = root / "WIDER_val" / "images"
    if img_root.exists() and any(img_root.iterdir()):
        return img_root
    zf = root / "WIDER_val.zip"
    if not zf.exists():
        raise SystemExit(f"缺少 {zf}")
    print(f"解压 {zf.name} ...", flush=True)
    with zipfile.ZipFile(zf) as z:
        z.extractall(root)
    print("解压完成", flush=True)
    return img_root


def ensure_annotations(root: Path) -> Path:
    gt = root / "wider_face_split" / "wider_face_val_bbx_gt.txt"
    if gt.exists():
        return gt
    zf = root / "wider_face_split.zip"
    if not zf.exists():
        raise SystemExit(f"缺少 {zf}")
    with zipfile.ZipFile(zf) as z:
        z.extractall(root)
    return gt


def parse_gt(gt_path: Path) -> dict[str, list[tuple[int, int, int, int]]]:
    lines = gt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: dict[str, list[tuple[int, int, int, int]]] = {}
    i = 0
    n = len(lines)
    while i < n:
        name = lines[i].strip()
        i += 1
        if not name:
            continue
        if i >= n:
            break
        try:
            cnt = int(lines[i].strip())
        except ValueError:
            continue
        i += 1
        boxes: list[tuple[int, int, int, int]] = []
        for _ in range(cnt):
            if i >= n:
                break
            parts = lines[i].strip().split()
            i += 1
            if len(parts) < 9:
                continue
            x, y, w, h = (int(float(parts[k])) for k in range(4))
            invalid = int(float(parts[7]))
            if invalid == 1 or w <= 2 or h <= 2:
                continue
            boxes.append((x, y, w, h))
        out[name] = boxes
    return out


def link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser(description="WIDER FACE -> YOLO 数据集")
    ap.add_argument("--root", type=str,
                    default=r"c:\Users\29199\.trae-cn\work\6ace07c7090f3196aeac65f3\wider")
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--val-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.root)
    out = Path(args.out) if args.out else root / "wider_yolo"
    img_root = ensure_extracted(root)
    gt_path = ensure_annotations(root)
    print(f"图片根目录: {img_root}", flush=True)

    gt = parse_gt(gt_path)
    print(f"标注条目: {len(gt)}", flush=True)

    for split in ("train", "val"):
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)

    names = sorted(gt.keys())
    rng = random.Random(args.seed)
    rng.shuffle(names)
    n_val = int(len(names) * args.val_ratio)
    val_set = set(names[:n_val])

    n_img = n_box = 0
    skipped = 0
    for name in names:
        src = img_root / name
        if not src.exists():
            skipped += 1
            continue
        boxes = gt[name]
        if not boxes:
            continue
        from PIL import Image
        try:
            with Image.open(src) as im:
                W, H = im.size
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
        split = "val" if name in val_set else "train"
        stem = Path(name).name
        lines = []
        for (x, y, w, h) in boxes:
            cx = (x + w / 2) / W
            cy = (y + h / 2) / H
            bw = w / W
            bh = h / H
            if not (0 < cx < 1 and 0 < cy < 1 and 0 < bw <= 1 and 0 < bh <= 1):
                continue
            lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        if not lines:
            continue
        link_or_copy(src, out / "images" / split / stem)
        (out / "labels" / split / (Path(stem).stem + ".txt")).write_text(
            "\n".join(lines), encoding="utf-8")
        n_img += 1
        n_box += len(lines)

    yaml = out / "dataset.yaml"
    yaml.write_text(f"path: {out.as_posix()}\ntrain: images/train\nval: images/val\n"
                    f"nc: 1\nnames:\n  0: face\n", encoding="utf-8")
    print(f"完成：{n_img} 张图 / {n_box} 个框（跳过 {skipped}）", flush=True)
    print(f"train={n_img - len(val_set & set(names))} 量级, val≈{len(val_set)}", flush=True)
    print(f"dataset.yaml: {yaml}", flush=True)
    for split in ("train", "val"):
        c = len(list((out / "images" / split).iterdir()))
        print(f"  {split}: {c} 张", flush=True)


if __name__ == "__main__":
    main()