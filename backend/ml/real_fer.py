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

from PIL import Image

from .architectures import CLASS_NAMES
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


def main() -> None:
    ap = argparse.ArgumentParser(description="RAF-DB（真实场景表情）接入")
    ap.add_argument("--data-dir", type=str, default=str(Path(__file__).resolve().parent / "data" / "fer2013"))
    ap.add_argument("--crop", type=float, default=0.88, help="RAF-DB 中心裁切比例（1.0=不裁）")
    ap.add_argument("--build-combined", action="store_true",
                    help="生成 FER2013 训练集 + RAF-DB 训练集的合并训练集 .pt")
    ap.add_argument("--fer-train", type=str, default="train.pt",
                    help="FER2013 训练集文件名（可指向去噪后的 train_clean.pt）")
    ap.add_argument("--out", type=str, default="train_raf.pt")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

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
        out_p = data_dir / args.out
        with open(out_p, "wb") as f:
            pickle.dump(combined, f, protocol=4)
        print(f"合并训练集: {out_p}  共 {len(combined)} 条"
              f"（FER {len(fer)} + RAF {len(raf_tr)}）", flush=True)
        print(f"  合并分布: {stats(combined)['distribution']}", flush=True)


if __name__ == "__main__":
    main()