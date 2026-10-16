"""误差结构分析：定位"准确率上不去"的瓶颈到底在哪。

思路：把混淆矩阵拆开看三件事——
  1) 每个类贡献了多少错误（support × (1-recall)），错误是均匀分散还是集中在少数类；
  2) 最大的几对混淆是什么（真实类 -> 误判类），它们占总错误的比例；
  3) 反事实上限：假如把最易混的那几对完全修好、或者只做剩下的类，准确率能到多少。

用法（在 backend 目录下）：
  python -m ml.error_analysis --run 20261015-015756-rafmix4
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .config import RUNS_DIR


def restricted_acc(cm: np.ndarray, keep: list[int]) -> float:
    """只在给定类别子集内做判别（真实类与预测都限制在该子集）时的准确率。"""
    sub = cm[np.ix_(keep, keep)]
    return float(np.diag(sub).sum() / sub.sum()) if sub.sum() else 0.0


def oracle_acc(cm: np.ndarray, pairs: list[tuple[int, int]]) -> float:
    """假设指定的混淆对被完全修正后的准确率上限。"""
    c = cm.astype(np.int64).copy()
    for i, j in pairs:
        c[i, i] += c[i, j]
        c[i, j] = 0
    return float(np.diag(c).sum() / c.sum())


def analyse(tag: str, data: dict, title: str) -> dict:
    cm = np.array(data["confusion_matrix"], dtype=np.int64)
    n = cm.sum()
    support = cm.sum(axis=1)
    correct = np.diag(cm)
    off = cm.copy()
    np.fill_diagonal(off, 0)
    total_err = int(off.sum())

    print(f"\n{'=' * 74}\n{title}   n={n}  准确率={data['accuracy']:.4f}  错误数={total_err}\n{'=' * 74}")
    print(f"{'类别':<12}{'样本':>7}{'召回':>9}{'F1':>9}{'错误数':>9}{'占总错误':>10}")
    rows = []
    for i, name in enumerate(CLASS_NAMES):
        p = data["per_class"][i]
        e = int(support[i] - correct[i])
        share = e / total_err if total_err else 0
        rows.append((name, int(support[i]), p["recall"], p["f1"], e, share))
        print(f"{CLASS_NAMES_CN[i] + ' ' + name:<12}{support[i]:>7}{p['recall']:>9.3f}{p['f1']:>9.3f}"
              f"{e:>9}{share * 100:>9.1f}%")

    order = sorted(rows, key=lambda r: -r[4])
    top2 = order[:2]
    print(f"\n错误最集中：{'、'.join(r[0] for r in top2)} 两类合计占总错误 "
          f"{sum(r[5] for r in top2) * 100:.1f}%；前三类合计 {sum(r[5] for r in order[:3]) * 100:.1f}%")

    flat = sorted(((int(off[i, j]), i, j) for i in range(len(CLASS_NAMES)) for j in range(len(CLASS_NAMES))
                   if i != j), reverse=True)
    print("\n最大的混淆对（真实 -> 误判）:")
    acc_pairs = []
    cum = 0
    for cnt, i, j in flat[:6]:
        cum += cnt
        acc_pairs.append((i, j))
        print(f"  {CLASS_NAMES_CN[i]} {CLASS_NAMES[i]:<10} -> {CLASS_NAMES_CN[j]} {CLASS_NAMES[j]:<10}"
              f"{cnt:>6} 个  占该真实类错的 {cnt / max(1, support[i] - correct[i]) * 100:5.1f}%"
              f"  占总错误 {cnt / max(1, total_err) * 100:5.1f}%")

    cheap = oracle_acc(cm, acc_pairs[:2])
    cheap3 = oracle_acc(cm, acc_pairs[:3])
    keep5 = [i for i, nm in enumerate(CLASS_NAMES) if nm not in ("fearful", "disgusted")]
    r5 = restricted_acc(cm, keep5)
    print(f"\n反事实上限：")
    print(f"  修好最大的 2 对混淆后准确率上限 = {cheap:.4f}（当前 {data['accuracy']:.4f}）")
    print(f"  修好最大的 3 对混淆后准确率上限 = {cheap3:.4f}")
    print(f"  只做 {len(keep5)} 类（去掉害怕/厌恶）时准确率 = {r5:.4f}")
    return {"n": int(n), "acc": data["accuracy"], "top_classes": [r[0] for r in top2],
            "top2_err_share": float(sum(r[5] for r in top2)),
            "oracle_fix2": cheap, "oracle_fix3": cheap3, "restricted5": r5,
            "per_class": [{"name": r[0], "support": r[1], "recall": r[2], "f1": r[3],
                           "errors": r[4], "err_share": round(r[5], 4)} for r in rows]}


def main() -> None:
    ap = argparse.ArgumentParser(description="误差结构分析")
    ap.add_argument("--run", type=str, required=True)
    args = ap.parse_args()
    run_dir = RUNS_DIR / args.run

    out = {}
    for tag, title in (("raf", "RAF-DB 真实场景测试集"), ("fer", "FER2013 测试集")):
        p = run_dir / f"{tag}_eval_metrics.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text("utf-8"))
        key = next(iter(d))
        out[tag] = analyse(tag, d[key], title)

    # 过拟合诊断：读训练历史
    h = run_dir / "history.csv"
    if h.exists():
        lines = h.read_text("utf-8").strip().splitlines()
        head = lines[0].split(",")
        last = lines[-1].split(",")
        rec = dict(zip(head, last))
        print(f"\n{'=' * 74}\n过拟合诊断（最后一轮）\n{'=' * 74}")
        print(f"  train_acc={rec.get('train_acc')}  val_acc={rec.get('val_acc')}  "
              f"train_loss={rec.get('train_loss')}  val_loss={rec.get('val_loss')}")

    outp = run_dir / "error_analysis.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存: {outp}")


if __name__ == "__main__":
    main()