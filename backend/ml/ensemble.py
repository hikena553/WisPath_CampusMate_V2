"""多模型集成评估（Ensemble）。

把若干次训练产出的 best_model.pt 在测试集上做概率平均（各自带 TTA），
输出集成后的准确率、Top-k、混淆矩阵与分类报告。

用法（在 backend 目录下）：
  python -m ml.ensemble --runs 20261013-115245-strong 20261013-123000-transfer --name ensemble

要点：
- 每个 run 按自己的 config.json 重建模型、输入尺寸与归一化方式，
  因此自训练模型（48px、[-1,1]）与迁移模型（96px、ImageNet 归一化）可以混合集成；
- 权重默认按 (验证准确率 - 随机基线) 归一化，避免弱模型拖累；
- 结果写入 ml/runs/<timestamp>-<name>/，含 metrics.json / confusion_matrix.png /
  classification_report.txt / summary.md。
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from . import artifacts
from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .backbones import build_model
from .config import RUNS_DIR, TrainingConfig
from .dataset import build_datasets
from .metrics import classification_report_text, evaluate_predictions


@torch.no_grad()
def _probs_for_run(run_dir: Path, device: torch.device, tta: bool = True, use_amp: bool = True):
    """对单个 run 的 best_model.pt 计算验证集与测试集的概率矩阵。"""
    cfg = TrainingConfig.load(run_dir / "config.json")
    cfg.preload = False  # 集成只需前向，无需预解码整个训练集

    model = build_model(cfg.model_name, num_classes=cfg.num_classes,
                        pretrained=False, dropout=cfg.dropout,
                        width_mult=cfg.width_mult).to(device)
    ckpt = torch.load(run_dir / "best_model.pt", map_location=device)
    state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()

    _, val_set, test_set = build_datasets(cfg)
    val_loader = DataLoader(val_set, batch_size=256, shuffle=False, num_workers=0,
                            pin_memory=device.type == "cuda")
    test_loader = DataLoader(test_set, batch_size=256, shuffle=False, num_workers=0,
                             pin_memory=device.type == "cuda")

    def _infer(loader):
        probs_all, targets_all = [], []
        for x, y in loader:
            x = x.to(device, non_blocking=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                logits = model(x)
                if tta:
                    logits = 0.5 * (logits + model(torch.flip(x, dims=[3])))
            probs_all.append(F.softmax(logits.float(), dim=1).cpu().numpy())
            targets_all.append(y.numpy())
        return np.concatenate(probs_all), np.concatenate(targets_all)

    val_probs, val_targets = _infer(val_loader)
    test_probs, test_targets = _infer(test_loader)
    return {
        "cfg": cfg,
        "val_probs": val_probs,
        "val_targets": val_targets,
        "test_probs": test_probs,
        "test_targets": test_targets,
        "val_acc": float((val_probs.argmax(1) == val_targets).mean()),
        "test_acc": float((test_probs.argmax(1) == test_targets).mean()),
    }


def run_ensemble(run_ids: list[str], name: str = "ensemble", tta: bool = True) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    t0 = time.time()

    members: list[dict] = []
    for rid in run_ids:
        rd = RUNS_DIR / rid
        if not (rd / "best_model.pt").exists():
            raise FileNotFoundError(f"run 不存在或缺少 best_model.pt：{rd}")
        print(f"[集成] 加载 {rid} ...", flush=True)
        res = _probs_for_run(rd, device, tta=tta)
        res["run_id"] = rid
        res["model_name"] = res["cfg"].model_name
        members.append(res)
        print(f"[集成] {rid}: val_acc={res['val_acc']:.4f} test_acc={res['test_acc']:.4f}", flush=True)

    # 权重：按 (验证准确率 - 随机基线) 归一化；若全部接近基线则退化为等权
    baseline = 1.0 / 7.0
    raw_w = np.array([max(1e-6, m["val_acc"] - baseline) for m in members], dtype=np.float64)
    weights = raw_w / raw_w.sum()

    test_targets = members[0]["test_targets"]
    val_targets = members[0]["val_targets"]

    val_ens = np.zeros_like(members[0]["val_probs"])
    test_ens = np.zeros_like(members[0]["test_probs"])
    for w, m in zip(weights, members):
        val_ens += w * m["val_probs"]
        test_ens += w * m["test_probs"]

    result = evaluate_predictions(test_ens, test_targets, CLASS_NAMES)
    result["class_names_cn"] = CLASS_NAMES_CN
    val_result = evaluate_predictions(val_ens, val_targets, CLASS_NAMES)
    result["tta"] = bool(tta)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + f"-{name}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts.plot_confusion_matrix(result["confusion_matrix"], CLASS_NAMES,
                                    run_dir / "confusion_matrix.png", normalize=False,
                                    title="Ensemble Test Confusion Matrix (counts)")
    artifacts.plot_confusion_matrix(result["confusion_matrix"], CLASS_NAMES,
                                    run_dir / "confusion_matrix_normalized.png", normalize=True,
                                    title="Ensemble Test Confusion Matrix (row-normalized)")
    (run_dir / "classification_report.txt").write_text(
        classification_report_text(result, CLASS_NAMES), encoding="utf-8")

    meta = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "ensemble",
        "members": [
            {"run_id": m["run_id"], "model_name": m["model_name"],
             "val_acc": round(m["val_acc"], 4), "test_acc": round(m["test_acc"], 4),
             "weight": round(float(w), 4)}
            for m, w in zip(members, weights)
        ],
        "tta": bool(tta),
        "val": val_result,
        "test": result,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    artifacts.save_json(meta, run_dir / "metrics.json")

    print(f"\n集成完成：{run_id}", flush=True)
    print(f"集成测试准确率 {result['accuracy']:.4f} | Top-2 {result['top2_accuracy']:.4f} "
          f"| Macro-F1 {result['macro_f1']:.4f}", flush=True)
    print(f"产物目录：{run_dir}", flush=True)
    return meta


def main() -> None:
    p = argparse.ArgumentParser(description="多模型集成评估")
    p.add_argument("--runs", nargs="+", required=True, help="run_id 列表（runs/ 下的目录名）")
    p.add_argument("--name", type=str, default="ensemble")
    p.add_argument("--no-tta", dest="tta", action="store_false", default=True)
    args = p.parse_args()
    run_ensemble(args.runs, args.name, tta=args.tta)


if __name__ == "__main__":
    main()