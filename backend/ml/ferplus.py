"""标签语义优化：用 FER+ 的众包聚合标签清洗 FER2013 的原始标签。

背景
----
FER2013 的标签是单人标注，噪声大、类间边界模糊（本报告的误差分析已证实错误高度集中在
"平静 / 难过 / 害怕"之间）。FER+（Microsoft, 2016）用**每张图约 10 名标注者投票再聚合**
的方式重新标注了同一批图像，是公开数据里最直接可得的"更干净标签"版本。

做法（不引入泄漏）
------------------
FER+ 的数据集只有 35,481 张（不含原始划分），若直接拿它当训练集、再在 FER2013 测试集上评估，
会把测试图混进训练集造成虚高。因此这里**只替换训练集的标签**：
  1. 对 FER2013 训练集每张图算感知哈希（aHash）+ 48×48 灰度，在 FER+ 里找同一张图；
  2. 命中则采用 FER+ 的聚合标签，未命中则保留原标签；
  3. 测试集（7,178 张）完全不动，因此与历史结果**逐张可比**。
同时输出标签改动统计，它本身就是"标签噪声有多大"的直接度量。

用法（在 backend 目录下）：
  python -m ml.ferplus --report                 # 只统计标签改动
  python -m ml.ferplus --build-combined         # 生成 train_ferplus.pt（FER+清洗后的FER训练集 + RAF-DB）
"""
from __future__ import annotations

import argparse
import io
import pickle
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .dataset import FER_LABEL_MAP
from .real_fer import _download, stats

MIRROR = "https://hf-mirror.com/datasets/deanngkl/ferplus-7cls/resolve/main/data"
FILE = "train-00000-of-00001.parquet"
# 数据卡 dataset_info.features.label.class_label.names
FERPLUS_TO_FER = {
    0: "angry",
    1: "disgust",
    2: "fear",
    3: "happy",
    4: "neutral",
    5: "sad",
    6: "surprise",
}


def default_root(data_dir: str | Path) -> Path:
    return Path(data_dir).parent / "ferplus"


def ensure_ferplus(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    p = root / FILE
    if not (p.exists() and p.stat().st_size > 1024 * 1024):
        print("  下载 FER+ (ferplus-7cls, 约 83 MB) ...", flush=True)
        _download(f"{MIRROR}/{FILE}", p)
    return p


def load_ferplus(path: Path) -> list[tuple[bytes, str]]:
    """读 FER+ parquet，返回 (图片字节, 本项目标签字符串)。"""
    import pyarrow.parquet as pq

    t = pq.read_table(path)
    imgs = t.column("image").to_pylist()
    labs = t.column("label").to_pylist()
    out = []
    for im, lab in zip(imgs, labs):
        raw = im.get("bytes") if isinstance(im, dict) else None
        fer = FERPLUS_TO_FER.get(int(lab))
        if raw and fer:
            out.append((bytes(raw), fer))
    return out


def ahash(gray48: np.ndarray) -> int:
    """8×8 平均哈希：对 JPEG/PNG 重编码鲁棒，用于跨数据集找同一张图。"""
    small = np.asarray(Image.fromarray(gray48).resize((8, 8), Image.BILINEAR), dtype=np.float32)
    bits = (small > small.mean()).flatten()
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v


def to_gray48(raw: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(raw)).convert("L").resize((48, 48), Image.BILINEAR),
                      dtype=np.uint8)


def build_match_table(fer_records: list[dict], fp_pairs: list[tuple[bytes, str]]) -> dict:
    """给 FER 每张训练图找 FER+ 里的同一张图，返回 (匹配结果, 统计)。"""
    buckets: dict[int, list[int]] = {}
    fp_gray: list[np.ndarray] = []
    for i, (raw, _lab) in enumerate(fp_pairs):
        g = to_gray48(raw)
        fp_gray.append(g)
        buckets.setdefault(ahash(g), []).append(i)

    matched = 0
    changed = 0
    pairs: list[tuple[str, str]] = []
    new_labels: list[str] = []
    for rec in fer_records:
        g = to_gray48(rec["img_bytes"])
        old = rec["labels"]
        cand = buckets.get(ahash(g), [])
        best_i, best_mse = None, None
        for i in cand:
            mse = float(((fp_gray[i].astype(np.float32) - g.astype(np.float32)) ** 2).mean())
            if best_mse is None or mse < best_mse:
                best_i, best_mse = i, mse
        if best_i is not None and best_mse is not None and best_mse <= 25.0:
            new = fp_pairs[best_i][1]
            matched += 1
            if new != old:
                changed += 1
                pairs.append((old, new))
            new_labels.append(new)
        else:
            new_labels.append(old)
    return {"new_labels": new_labels, "matched": matched, "changed": changed, "pairs": pairs}


def report(fer_records: list[dict], fp_pairs: list[tuple[bytes, str]]) -> dict:
    r = build_match_table(fer_records, fp_pairs)
    n = len(fer_records)
    print(f"\nFER2013 训练集 {n} 张；FER+ 提供 {len(fp_pairs)} 张", flush=True)
    print(f"  找到同一张图: {r['matched']} ({r['matched'] / n * 100:.1f}%)", flush=True)
    print(f"  标签被改动的: {r['changed']} ({r['changed'] / n * 100:.1f}%)"
          f"（占已匹配的 {r['changed'] / max(1, r['matched']) * 100:.1f}%）", flush=True)

    cm = Counter(r["pairs"])
    print("\n改动最多的前 12 类（FER2013 原标签 -> FER+ 聚合标签）:", flush=True)
    for (a, b), c in cm.most_common(12):
        ia, ib = FER_LABEL_MAP[a], FER_LABEL_MAP[b]
        print(f"  {CLASS_NAMES_CN[ia]:<4}{a:<10} -> {CLASS_NAMES_CN[ib]:<4}{b:<10} {c:>5}", flush=True)

    # 用 FER+ 标签后各类分布的变化
    before = Counter(CLASS_NAMES[FER_LABEL_MAP[x["labels"]]] for x in fer_records)
    after = Counter(CLASS_NAMES[FER_LABEL_MAP[l]] for l in r["new_labels"])
    print("\n各类样本数变化:", flush=True)
    print(f"  {'类别':<14}{'原标签':>9}{'FER+标签':>10}{'变化':>9}")
    for k in CLASS_NAMES:
        print(f"  {CLASS_NAMES_CN[CLASS_NAMES.index(k)] + ' ' + k:<14}"
              f"{before.get(k, 0):>9}{after.get(k, 0):>10}{after.get(k, 0) - before.get(k, 0):>9}")
    print(f"  {'合计':<14}{sum(before.values()):>9}{sum(after.values()):>10}")
    r["before"] = dict(before)
    r["after"] = dict(after)
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description="用 FER+ 清洗 FER2013 训练标签")
    ap.add_argument("--data-dir", type=str,
                    default=str(Path(__file__).resolve().parent / "data" / "fer2013"))
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--build-combined", action="store_true",
                    help="生成 train_ferplus.pt（清洗后的 FER 训练集 + RAF-DB 训练集）")
    ap.add_argument("--out", type=str, default="train_ferplus.pt")
    ap.add_argument("--relabel-test", action="store_true",
                    help="额外把测试集也按 FER+ 重标，写出 test_ferplus.pt（用于量化标签噪声）")
    ap.add_argument("--agree-subset", action="store_true",
                    help="切出「两套独立标注一致」的无争议子集 test_agree.pt / 有争议子集 test_disagree.pt")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    fp_path = ensure_ferplus(default_root(data_dir))
    fp_pairs = load_ferplus(fp_path)

    with open(data_dir / "train.pt", "rb") as f:
        fer_train = pickle.load(f)
    r = report(fer_train, fp_pairs)

    if args.build_combined:
        cleaned = [{"img_bytes": rec["img_bytes"], "labels": lab, "src": "ferplus"}
                   for rec, lab in zip(fer_train, r["new_labels"])]
        # RAF-DB 部分：从 train_raf.pt 里按顺序切出来（前 len(train_clean) 条是 FER）
        with open(data_dir / "train_clean.pt", "rb") as f:
            n_clean = len(pickle.load(f))
        with open(data_dir / "train_raf.pt", "rb") as f:
            raf_part = pickle.load(f)[n_clean:]
        combined = cleaned + raf_part
        out_p = data_dir / args.out
        with open(out_p, "wb") as f:
            pickle.dump(combined, f, protocol=4)
        print(f"\n已写出 {out_p}  共 {len(combined)} 条"
              f"（FER+清洗 {len(cleaned)} + RAF {len(raf_part)}）", flush=True)
        print(f"  合并分布: {stats(combined)['distribution']}", flush=True)

    if args.relabel_test:
        with open(data_dir / "test.pt", "rb") as f:
            fer_test = pickle.load(f)
        print("\n" + "=" * 70, flush=True)
        print("测试集按 FER+ 重标（仅用于量化标签噪声，不改动原测试集文件）", flush=True)
        rt = build_match_table(fer_test, fp_pairs)
        n_t = len(fer_test)
        print(f"  找到同一张图: {rt['matched']} ({rt['matched'] / n_t * 100:.1f}%)", flush=True)
        print(f"  标签被改动的: {rt['changed']} ({rt['changed'] / n_t * 100:.1f}%)"
              f"（占已匹配的 {rt['changed'] / max(1, rt['matched']) * 100:.1f}%）", flush=True)
        relabeled = [{"img_bytes": rec["img_bytes"], "labels": lab, "src": "ferplus-test"}
                     for rec, lab in zip(fer_test, rt["new_labels"])]
        p_t = data_dir / "test_ferplus.pt"
        with open(p_t, "wb") as f:
            pickle.dump(relabeled, f, protocol=4)
        print(f"  已写出 {p_t}  分布: {stats(relabeled)['distribution']}", flush=True)

    if args.agree_subset:
        # 无争议子集：FER2013 原始标注与 FER+ 聚合标注**一致**的样本。
        # 这是两套彼此独立的标注流程都给出同一答案的样本，可视为"标注无歧义"，
        # 与 FER+ 论文中"按标注一致度分层评估"的做法一致。
        with open(data_dir / "test.pt", "rb") as f:
            fer_test = pickle.load(f)
        with open(data_dir / "test_ferplus.pt", "rb") as f:
            fp_test = pickle.load(f)
        if len(fer_test) != len(fp_test):
            raise SystemExit("两个测试集长度不一致，无法按下标对齐")

        agree, disagree = [], []
        for a, b in zip(fer_test, fp_test):
            lab = a["labels"]
            (agree if b["labels"] == lab else disagree).append(
                {"img_bytes": a["img_bytes"], "labels": lab,
                 "src": "agree" if b["labels"] == lab else "disagree"})
        for name, subset, note in (("test_agree.pt", agree, "无争议（两套标注一致）"),
                                   ("test_disagree.pt", disagree, "有争议（两套标注不一致）")):
            p = data_dir / name
            with open(p, "wb") as f:
                pickle.dump(subset, f, protocol=4)
            print(f"  {note}: {p}  n={len(subset)}  "
                  f"({len(subset) / len(fer_test) * 100:.1f}%)  分布 {stats(subset)['distribution']}",
                  flush=True)


if __name__ == "__main__":
    main()