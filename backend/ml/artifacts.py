"""训练产物落盘：曲线图、混淆矩阵、指标 JSON、历史 CSV、分类报告。

所有产物写入 runs/<run_id>/，便于回溯与前端展示。
图表统一使用 Agg 后端（无显示环境可用），中文标签做字体回退。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# 中文字体回退：优先 noto/wqy，Windows 上回退微软雅黑/黑体
plt.rcParams["font.sans-serif"] = [
    "Noto Sans CJK SC", "WenQuanYi Micro Hei", "Microsoft YaHei", "SimHei", "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


def save_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def save_history_csv(history: list[dict], path: Path) -> None:
    if not history:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(history[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(history)


def plot_curves(history: list[dict], path: Path) -> None:
    """训练曲线：损失 + 准确率（训练/验证对照），并标注最佳验证轮次。"""
    if not history:
        return
    epochs = [h["epoch"] for h in history]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))

    axes[0].plot(epochs, [h["train_loss"] for h in history], label="Train Loss", marker="o", ms=3)
    axes[0].plot(epochs, [h["val_loss"] for h in history], label="Val Loss", marker="s", ms=3)
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].set_title("Loss Curve")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(epochs, [h["train_acc"] for h in history], label="Train Acc", marker="o", ms=3)
    axes[1].plot(epochs, [h["val_acc"] for h in history], label="Val Acc", marker="s", ms=3)
    best = max(history, key=lambda h: h["val_acc"])
    axes[1].scatter([best["epoch"]], [best["val_acc"]], color="red", zorder=5,
                    label=f"Best Val Acc={best['val_acc']:.4f} @ep{best['epoch']}")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].set_title("Accuracy Curve")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def plot_confusion_matrix(
    cm: list[list[int]] | np.ndarray,
    class_names: list[str],
    path: Path,
    normalize: bool = False,
    title: str = "Confusion Matrix",
) -> None:
    """混淆矩阵热力图；normalize=True 时按行归一化显示召回率。"""
    cm = np.asarray(cm, dtype=np.float64)
    if normalize:
        row = cm.sum(axis=1, keepdims=True)
        cm = np.divide(cm, np.maximum(row, 1), out=np.zeros_like(cm), where=row > 0)

    fig, ax = plt.subplots(figsize=(8.2, 7))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=35, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)

    vmax = cm.max() if cm.max() > 0 else 1
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            val = cm[i, j]
            txt = f"{val:.2f}" if normalize else f"{int(val)}"
            ax.text(j, i, txt, ha="center", va="center",
                    color="white" if val > vmax * 0.6 else "black", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def write_summary_md(run_meta: dict, path: Path) -> None:
    """生成 run 目录下的摘要 Markdown（技术 + 关键参数 + 结果）。"""
    lines = [
        f"# 训练运行 {run_meta['run_id']}",
        "",
        "## 模型与数据",
        f"- 架构: {run_meta['architecture']}",
        f"- 参数量: {run_meta['params']:,}",
        f"- 训练设备: {run_meta.get('device_name', 'cpu')}（{run_meta.get('device', 'cpu')}），"
        f"混合精度 AMP: {run_meta.get('amp', False)}",
        f"- 数据集: FER2013（train {run_meta['data']['train']['total']} / test {run_meta['data']['test']['total']}）",
        f"- 输入尺寸: {run_meta['input_size']}×{run_meta['input_size']}，类别数: {run_meta['num_classes']}",
        "",
        "## 关键超参数",
        f"- epochs={run_meta['hyperparams']['epochs']}, batch_size={run_meta['hyperparams']['batch_size']}",
        f"- optimizer={run_meta['hyperparams']['optimizer']}, lr={run_meta['hyperparams']['lr']}, "
        f"weight_decay={run_meta['hyperparams']['weight_decay']}",
        f"- scheduler={run_meta['hyperparams']['scheduler']}, warmup_epochs={run_meta['hyperparams']['warmup_epochs']}",
        f"- label_smoothing={run_meta['hyperparams']['label_smoothing']}, "
        f"aug(hflip={run_meta['hyperparams']['aug_hflip']}, rot={run_meta['hyperparams']['aug_rotation']})",
        f"- init_weights={run_meta['hyperparams']['init_weights'] or '（从头训练）'}, "
        f"freeze_backbone={run_meta['hyperparams']['freeze_backbone']}",
        "",
        "## 结果",
        f"- 训练轮数: {run_meta['epochs_trained']}（早停耐心 {run_meta['hyperparams']['early_stop_patience']}）",
        f"- 最佳验证准确率: {run_meta['best_val_acc']:.4f} @ epoch {run_meta['best_epoch']}",
        f"- 测试集准确率: {run_meta['test']['accuracy']:.4f}",
        f"- 测试集 Top-2 准确率: {run_meta['test']['top2_accuracy']:.4f}",
        f"- 测试集 Macro-F1: {run_meta['test']['macro_f1']:.4f} / Weighted-F1: {run_meta['test']['weighted_f1']:.4f}",
        "",
        "## 产物",
        "- `config.json` 完整配置",
        "- `metrics.json` 全部指标（含混淆矩阵、每类 P/R/F1）",
        "- `history.csv` 逐轮训练/验证指标",
        "- `training_curves.png` 损失与准确率曲线",
        "- `confusion_matrix.png` 混淆矩阵（计数）",
        "- `confusion_matrix_normalized.png` 混淆矩阵（召回率归一化）",
        "- `classification_report.txt` 分类报告",
        "- `best_model.pt` 最佳权重",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")