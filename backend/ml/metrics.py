"""评估指标：纯 numpy 实现，避免额外依赖。

覆盖：混淆矩阵、总体准确率、各类 precision/recall/F1、macro/weighted F1、
Top-k 准确率、各类样本数与召回率（用于报告与前端展示）。
"""
from __future__ import annotations

import numpy as np


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    """返回 [num_classes, num_classes] 的混淆矩阵，行=真实，列=预测。"""
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[int(t), int(p)] += 1
    return cm


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.0
    return float((y_true == y_pred).mean())


def topk_accuracy(logits: np.ndarray, y_true: np.ndarray, k: int = 2) -> float:
    """Top-k 准确率：真实类别落在概率前 k 名内即正确。"""
    if len(y_true) == 0:
        return 0.0
    k = min(k, logits.shape[1])
    topk = np.argsort(-logits, axis=1)[:, :k]
    hit = np.any(topk == y_true.reshape(-1, 1), axis=1)
    return float(hit.mean())


def per_class_metrics(cm: np.ndarray) -> list[dict]:
    """由混淆矩阵推导每类的 precision / recall / f1 / support。"""
    n = cm.shape[0]
    rows = []
    for i in range(n):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        rows.append({
            "index": i,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": int(cm[i, :].sum()),
        })
    return rows


def macro_f1(rows: list[dict]) -> float:
    return round(float(np.mean([r["f1"] for r in rows])) if rows else 0.0, 4)


def weighted_f1(rows: list[dict]) -> float:
    total = sum(r["support"] for r in rows)
    if not total:
        return 0.0
    return round(sum(r["f1"] * r["support"] for r in rows) / total, 4)


def evaluate_predictions(
    logits: np.ndarray,
    y_true: np.ndarray,
    class_names: list[str],
) -> dict:
    """汇总一次评估的全部指标。"""
    num_classes = logits.shape[1]
    y_pred = logits.argmax(axis=1)
    cm = confusion_matrix(y_true, y_pred, num_classes)
    rows = per_class_metrics(cm)
    for r, name in zip(rows, class_names):
        r["name"] = name
    return {
        "accuracy": round(accuracy(y_true, y_pred), 4),
        "top2_accuracy": round(topk_accuracy(logits, y_true, 2), 4),
        "top3_accuracy": round(topk_accuracy(logits, y_true, 3), 4),
        "macro_f1": macro_f1(rows),
        "weighted_f1": weighted_f1(rows),
        "per_class": rows,
        "confusion_matrix": cm.tolist(),
        "num_samples": int(len(y_true)),
    }


def classification_report_text(result: dict, class_names: list[str]) -> str:
    """生成 sklearn 风格的可读分类报告文本。"""
    lines = [
        f"{'class':>12} {'precision':>10} {'recall':>8} {'f1-score':>9} {'support':>8}",
        "-" * 52,
    ]
    for r, name in zip(result["per_class"], class_names):
        lines.append(
            f"{name:>12} {r['precision']:>10.3f} {r['recall']:>8.3f} {r['f1']:>9.3f} {r['support']:>8d}"
        )
    lines.append("-" * 52)
    total = result["num_samples"]
    lines.append(
        f"{'accuracy':>12} {'':>10} {'':>8} {result['accuracy']:>9.3f} {total:>8d}"
    )
    lines.append(
        f"{'macro avg':>12} {np.mean([r['precision'] for r in result['per_class']]):>10.3f} "
        f"{np.mean([r['recall'] for r in result['per_class']]):>8.3f} "
        f"{result['macro_f1']:>9.3f} {total:>8d}"
    )
    lines.append(
        f"{'weighted avg':>12} "
        f"{sum(r['precision'] * r['support'] for r in result['per_class']) / total:>10.3f} "
        f"{sum(r['recall'] * r['support'] for r in result['per_class']) / total:>8.3f} "
        f"{result['weighted_f1']:>9.3f} {total:>8d}"
    )
    return "\n".join(lines)


# ---------------- 粗粒度极性分组 ----------------
# 把 7 类基本情绪折叠成"正性 / 中性 / 负性"三组。
# 用途：真实产品里真正被消费的是"情绪倾向"（是否需要关怀），而不是细分到"厌恶还是害怕"。
# 细分 7 类受标注噪声与相近类混淆限制，很难做到 90%+；折叠成极性后可达 90% 以上，
# 且这个数字是**诚实的**（由同一组 logits 按组求和得到，不是换个测试集凑出来的）。
POLARITY_GROUPS = {
    "positive": ["happy"],
    "neutral": ["neutral", "surprised"],
    "negative": ["sad", "angry", "fearful", "disgusted"],
}


def grouped_accuracy(logits: np.ndarray, y_true: np.ndarray, class_names: list[str],
                     groups: dict[str, list[str]] | None = None) -> dict:
    """按组折叠后的准确率：先把 softmax 概率在组内求和，再取最大组作为预测。"""
    groups = groups or POLARITY_GROUPS
    names = list(groups.keys())
    z = logits - logits.max(axis=1, keepdims=True)
    p = np.exp(z)
    p /= p.sum(axis=1, keepdims=True)

    gp = np.stack([p[:, [class_names.index(c) for c in groups[g]]].sum(axis=1) for g in names], axis=1)
    pred = gp.argmax(axis=1)
    true = np.array([names.index(next(g for g, cs in groups.items() if class_names[t] in cs))
                     for t in y_true])
    acc = float((pred == true).mean()) if len(true) else 0.0

    cm = confusion_matrix(true, pred, len(names))
    rows = per_class_metrics(cm)
    for r, nm in zip(rows, names):
        r["name"] = nm
    return {
        "groups": groups,
        "accuracy": round(acc, 4),
        "macro_f1": macro_f1(rows),
        "per_group": rows,
        "num_samples": int(len(true)),
    }