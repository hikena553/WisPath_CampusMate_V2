"""接入真实场景表情数据集 RAF-DB，用于缩小"领域差距"。

为什么需要它
------------
FER2013 是实验室摆拍的 48×48 灰度图，与真实摄像头画面分布差异很大
（肤色、光照、发型、姿态、分辨率都不同）。只在其上训练的模型，
换到真实摄像头会明显掉点。RAF-DB（Real-world Affective Faces Database）
是 "in-the-wild" 真实场景人脸，100×100 彩色，7 类基本表情，
训练集 12,271 张、测试集 3,068 张——正好用来：
  1) 并入训练集做领域适配（domain adaptation）；
  2) 作为"真实场景测试集"，给出贴近真实摄像头的准确率。

数据来源：HuggingFace 镜像 hf-mirror.com 上的 elipaluma/RAF-DB_Kaggle
（parquet，字段 image={bytes,path}、label∈1..7）。

RAF-DB 原始标签语义（已用样张拼图人工核对）：
  1 惊讶  2 害怕  3 厌恶  4 开心  5 悲伤  6 生气  7 平静
映射到本项目类序（angry/disgusted/fearful/happy/neutral/sad/surprised）后，
生成的记录与 FER2013 记录同构（{img_bytes, labels}），因此可直接复用
ml.dataset / ml.train 的全套流程。

用法：
  # 生成合并训练集（FER2013 训练集 + RAF-DB 训练集）
  python -m ml.real_fer --build-combined

  # 仅检查数据
  python -m ml.real_fer --stats
"""
from __future__ import annotations

import argparse
import io
import pickle
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .dataset import FER_LABEL_MAP

MIRROR = "https://hf-mirror.com/datasets/elipaluma/RAF-DB_Kaggle/resolve/main/data"
FILES = {
    "train": "train-00000-of-00001.parquet",
    "test": "test-00000-of-00001.parquet",
}
# RAF-DB 原始标签(1..7) -> FER2013 字符串标签
RAF_TO_FER = {
    1: "surprise",
    2: "fear",
    3: "disgust",
    4: "happy",
    5: "sad",
    6: "angry",
    7: "neutral",
}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def default_root(data_dir: str | Path) -> Path:
    return Path(data_dir).parent / "rafdb"


def _download(url: str, dst: Path) -> None:
    """带 Range 断点续传的下载（镜像会限速/中断）。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 31):
        if dst.exists() and dst.stat().st_size > 1024 * 1024:
            return
        pos = dst.stat().st_size if dst.exists() else 0
        req = urllib.request.Request(url, headers={"Range": f"bytes={pos}-", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(dst, "ab") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if dst.stat().st_size > 1024 * 1024:
                return
        except Exception as e:  # noqa: BLE001
            print(f"    [{attempt}] 中断：{e}", flush=True)
            time.sleep(2)
    raise SystemExit(f"下载失败：{url}")


def ensure_raf(root: Path) -> dict[str, Path]:
    out = {}
    for split, fn in FILES.items():
        p = root / fn
        if not (p.exists() and p.stat().st_size > 1024 * 1024):
            print(f"  下载 RAF-DB {split} ...", flush=True)
            _download(f"{MIRROR}/{fn}", p)
        out[split] = p
    return out


# ---------- AffectNet 子集：更大量的真实场景样本 ----------
AFFECTNET_MIRROR = "https://hf-mirror.com/datasets/Mauregato/affectnet_short/resolve/main/data"
AFFECTNET_FILES = {
    "train": "train-00000-of-00001-7cbcbf03ccc4c14c.parquet",
    "val": "val-00000-of-00001-15bd8d507ff5dd11.parquet",
}


def default_affectnet_root(data_dir: str | Path) -> Path:
    return Path(data_dir).parent / "affectnet"


def ensure_affectnet(root: Path) -> dict[str, Path]:
    out = {}
    for split, fn in AFFECTNET_FILES.items():
        p = root / fn
        if not (p.exists() and p.stat().st_size > 1024 * 1024):
            print(f"  下载 AffectNet {split}（约 {'412' if split == 'train' else '103'} MB）...", flush=True)
            _download(f"{AFFECTNET_MIRROR}/{fn}", p)
        out[split] = p
    return out


def read_parquet_pairs(path: Path) -> list[tuple[bytes, object]]:
    """通用 parquet 读取：返回 (图片字节, 原始标签) 列表。

    不同镜像的列名不一致，这里按名字自动识别图片列与标签列，
    避免写死列名导致换数据集就报错。
    """
    import pyarrow.parquet as pq

    t = pq.read_table(path)
    names = t.schema.names
    img_col = next((n for n in names if "image" in n.lower() or "img" in n.lower()), None)
    lab_col = next((n for n in names if n.lower() in
                    ("label", "labels", "emotion", "target", "expression", "class")), None)
    if img_col is None or lab_col is None:
        raise SystemExit(f"无法识别列名：{names}")
    pairs: list[tuple[bytes, object]] = []
    for im, lab in zip(t.column(img_col).to_pylist(), t.column(lab_col).to_pylist()):
        if isinstance(im, dict):
            raw = im.get("bytes") or im.get("path")
            raw = raw if isinstance(raw, (bytes, bytearray)) else None
        elif isinstance(im, (bytes, bytearray)):
            raw = bytes(im)
        else:
            raw = None
        if raw:
            pairs.append((bytes(raw), lab))
    return pairs


def probe_affectnet(root: Path, out_dir: Path) -> None:
    """打印 AffectNet 的结构与标签计数，并输出按标签分组的样张拼图供人工核对语义。

    标签语义必须核对：把 0/1/2… 猜成某类而实际是另一类，会让整轮训练白做。
    """
    paths = ensure_affectnet(root)
    for split, p in paths.items():
        pairs = read_parquet_pairs(p)
        c = Counter(str(lab) for _raw, lab in pairs)
        print(f"[{split}] {p.name}  n={len(pairs)}  标签取值数={len(c)}", flush=True)
        for k, v in sorted(c.items()):
            print(f"    label={k:<12} {v}", flush=True)
        im = Image.open(io.BytesIO(pairs[0][0]))
        print(f"    首图尺寸={im.size} 模式={im.mode}", flush=True)

    # 样张拼图（每个标签取 6 张）
    pairs = read_parquet_pairs(paths["train"])
    labs = sorted({str(l) for _r, l in pairs})
    per, cell = 6, 96
    grid = Image.new("RGB", (cell * per, (cell + 20) * len(labs)), (18, 20, 24))
    d = ImageDraw.Draw(grid)
    for ri, lab in enumerate(labs):
        picks = [raw for raw, l in pairs if str(l) == lab][:per]
        for ci, raw in enumerate(picks):
            im = Image.open(io.BytesIO(raw)).convert("RGB").resize((cell, cell), Image.BILINEAR)
            grid.paste(im, (ci * cell, ri * (cell + 20)))
        d.text((4, ri * (cell + 20) + cell + 3), f"label={lab}", fill=(255, 200, 87))
    out = out_dir / "affectnet_labels_check.jpg"
    grid.save(out, quality=88)
    print(f"样张拼图: {out}", flush=True)


def _center_crop(img: Image.Image, keep: float) -> Image.Image:
    """RAF-DB 是 100×100 的"半身/带背景"裁剪，而部署链路的输入是紧贴人脸的
    方形框。做一个轻度中心裁切可以让两者的取景口径更接近，减少训练/推理的
    几何分布错配。keep=1.0 表示不裁。"""
    if keep >= 0.999:
        return img
    w, h = img.size
    cw, ch = int(w * keep), int(h * keep)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    return img.crop((x0, y0, x0 + cw, y0 + ch))


def load_split(path: Path, crop: float = 1.0) -> list[dict]:
    """把 RAF-DB parquet 转成与 FER2013 同构的记录列表。"""
    import pyarrow.parquet as pq

    t = pq.read_table(path)
    imgs = t.column("image").to_pylist()
    labs = t.column("label").to_pylist()
    recs: list[dict] = []
    for im, lab in zip(imgs, labs):
        raw = im.get("bytes") if isinstance(im, dict) else None
        if not raw:
            continue
        fer = RAF_TO_FER.get(int(lab))
        if fer is None:
            continue
        if crop < 0.999:
            b = io.BytesIO()
            _center_crop(Image.open(io.BytesIO(raw)).convert("RGB"), crop).save(b, format="JPEG", quality=95)
            raw = b.getvalue()
        recs.append({"img_bytes": raw, "labels": fer, "src": "rafdb"})
    return recs


def stats(recs: list[dict]) -> dict:
    c = Counter(CLASS_NAMES[FER_LABEL_MAP[r["labels"]]] for r in recs)
    return {"total": len(recs), "distribution": {k: c.get(k, 0) for k in CLASS_NAMES}}


# AffectNet 原始标签 -> FER2013 字符串标签。
# 依据该镜像数据卡（dataset_info.features.label.class_label.names）：
#   0=anger 1=surprise 2=contempt 3=happy 4=neutral 5=fear 6=sad 7=disgust
# 其中 2=contempt（轻蔑）不在本项目 7 类之内，直接剔除。
# 该映射已用样张拼图人工核对：surprise / happy / disgust 三行与目视结果一致。
AFFECTNET_TO_FER = {
    0: "angry",
    1: "surprise",
    3: "happy",
    4: "neutral",
    5: "fear",
    6: "sad",
    7: "disgust",
}


def load_affectnet_split(path: Path, crop: float = 1.0) -> list[dict]:
    """把 AffectNet 子集 parquet 转成与 FER2013 同构的记录列表（剔除 contempt）。"""
    recs: list[dict] = []
    for raw, lab in read_parquet_pairs(path):
        fer = AFFECTNET_TO_FER.get(int(lab))
        if fer is None:
            continue
        if crop < 0.999:
            b = io.BytesIO()
            _center_crop(Image.open(io.BytesIO(raw)).convert("RGB"), crop).save(
                b, format="JPEG", quality=95)
            raw = b.getvalue()
        recs.append({"img_bytes": raw, "labels": fer, "src": "affectnet"})
    return recs


def verify_mapping_montage(recs: list[dict], out: Path, per: int = 6, cell: int = 96) -> None:
    """按"映射后的类名"重新拼图，用于核对映射是否确实对得上人眼判断。"""
    by: dict[str, list[bytes]] = {k: [] for k in CLASS_NAMES}
    for r in recs:
        by[CLASS_NAMES[FER_LABEL_MAP[r["labels"]]]].append(r["img_bytes"])
    grid = Image.new("RGB", (cell * per, (cell + 20) * len(CLASS_NAMES)), (18, 20, 24))
    d = ImageDraw.Draw(grid)
    for ri, k in enumerate(CLASS_NAMES):
        for ci, raw in enumerate(by[k][:per]):
            im = Image.open(io.BytesIO(raw)).convert("RGB").resize((cell, cell), Image.BILINEAR)
            grid.paste(im, (ci * cell, ri * (cell + 20)))
        d.text((4, ri * (cell + 20) + cell + 3),
               f"{CLASS_NAMES_CN[CLASS_NAMES.index(k)]} {k}  n={len(by[k])}", fill=(255, 200, 87))
    grid.save(out, quality=88)
    print(f"映射核对拼图: {out}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="RAF-DB（真实场景表情）接入")
    ap.add_argument("--data-dir", type=str, default=str(Path(__file__).resolve().parent / "data" / "fer2013"))
    ap.add_argument("--crop", type=float, default=0.88, help="RAF-DB 中心裁切比例（1.0=不裁）")
    ap.add_argument("--affectnet-crop", type=float, default=1.0,
                    help="AffectNet 中心裁切比例（默认 1.0：其 96×96 已紧贴人脸）")
    ap.add_argument("--build-combined", action="store_true",
                    help="生成 FER2013 训练集 + RAF-DB 训练集的合并训练集 .pt")
    ap.add_argument("--fer-train", type=str, default="train.pt",
                    help="FER2013 训练集文件名（可指向去噪后的 train_clean.pt）")
    ap.add_argument("--out", type=str, default="train_raf.pt")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--probe-affectnet", action="store_true",
                    help="下载 AffectNet 子集并打印结构/标签计数，输出语义核对样张")
    ap.add_argument("--with-affectnet", action="store_true",
                    help="构建合并训练集时并入 AffectNet 子集（剔除 contempt）")
    ap.add_argument("--verify-affectnet", action="store_true",
                    help="按映射后的类名输出 AffectNet 样张拼图，用于核对映射")
    args = ap.parse_args()

    if args.probe_affectnet:
        probe_affectnet(default_affectnet_root(args.data_dir), Path(args.data_dir))
        return

    data_dir = Path(args.data_dir)
    root = default_root(data_dir)
    paths = ensure_raf(root)
    print(f"RAF-DB 目录: {root}", flush=True)

    raf_tr = load_split(paths["train"], args.crop)
    raf_te = load_split(paths["test"], args.crop)
    print(f"RAF-DB train {len(raf_tr)} | test {len(raf_te)} | crop={args.crop}", flush=True)
    print(f"  train 分布: {stats(raf_tr)['distribution']}", flush=True)
    print(f"  test  分布: {stats(raf_te)['distribution']}", flush=True)

    # RAF-DB 测试集单独落盘，供"真实场景"评测使用
    raf_test_pt = data_dir / "test_raf.pt"
    with open(raf_test_pt, "wb") as f:
        pickle.dump(raf_te, f, protocol=4)
    print(f"已写出真实场景测试集: {raf_test_pt}", flush=True)

    if args.build_combined:
        fer_train_p = data_dir / args.fer_train
        if not fer_train_p.exists():
            raise SystemExit(f"缺少 FER2013 训练集：{fer_train_p}")
        with open(fer_train_p, "rb") as f:
            fer = pickle.load(f)
        combined = list(fer) + list(raf_tr)
        src = f"FER {len(fer)} + RAF {len(raf_tr)}"
        if args.with_affectnet:
            af_paths = ensure_affectnet(default_affectnet_root(data_dir))
            # AffectNet 的 96×96 本身就是"紧贴人脸"的裁剪，再中心裁切会切进脸，
            # 因此这里单独用 --affectnet-crop 控制（默认 1.0 不裁）。
            af_tr = load_affectnet_split(af_paths["train"], args.affectnet_crop)
            af_va = load_affectnet_split(af_paths["val"], args.affectnet_crop)
            combined += af_tr
            src += f" + AffectNet {len(af_tr)}"
            print(f"AffectNet train 分布: {stats(af_tr)['distribution']}", flush=True)
            p_va = data_dir / "test_affnet.pt"
            with open(p_va, "wb") as f:
                pickle.dump(af_va, f, protocol=4)
            print(f"已写出 AffectNet 验证集（额外真实场景测试集）: {p_va}  n={len(af_va)}", flush=True)
            if args.verify_affectnet:
                verify_mapping_montage(af_tr, data_dir / "affectnet_mapped_check.jpg")
        out_p = data_dir / args.out
        with open(out_p, "wb") as f:
            pickle.dump(combined, f, protocol=4)
        print(f"合并训练集: {out_p}  共 {len(combined)} 条（{src}）", flush=True)
        print(f"  合并分布: {stats(combined)['distribution']}", flush=True)


if __name__ == "__main__":
    main()