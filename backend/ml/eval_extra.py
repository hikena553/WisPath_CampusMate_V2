"""在"真实场景"数据集上评测已训练的表情模型（RAF-DB 测试集）。

意义：FER2013 测试集是同分布的实验室数据，只能说明"模型记住了 FER"。
真实摄像头画面更接近 RAF-DB（in-the-wild）。因此这里用 RAF-DB 测试集
（3,068 张真实人脸）评测，作为"外推到真实摄像头"的量化依据。

用法（在 backend 目录下）：
  python -m ml.eval_extra --run-id 20261013-174022-improved --data test_raf.pt --tag raf
  python -m ml.eval_extra --run-id <id> --data test.pt --tag fer
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from . import artifacts
from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .backbones import build_model
from .config import RUNS_DIR, TrainingConfig
from .dataset import FER2013Dataset
from .losses import build_loss
from .metrics import classification_report_text, evaluate_predictions


@torch.no_grad()
def _evaluate(model, loader, device, tta: bool):
    logits_all, targets_all = [], []
    for x, y in loader:
        x = x.to(device, non_blocking=True)
        out = model(x)
        if tta:
            out = 0.5 * (out + model(torch.flip(x, dims=[3])))
        logits_all.append(out.float().cpu().numpy())
        targets_all.append(y.numpy())
    return (np.concatenate(logits_all) if logits_all else np.zeros((0, 7)),
            np.concatenate(targets_all) if targets_all else np.zeros((0,), dtype=np.int64))


def main() -> None:
    ap = argparse.ArgumentParser(description="真实场景/其它数据集评测")
    ap.add_argument("--run-id", type=str, required=True)
    ap.add_argument("--data", type=str, default="test_raf.pt")
    ap.add_argument("--tag", type=str, default="raf")
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--tta", action="store_true", default=True)
    ap.add_argument("--no-tta", dest="tta", action="store_false")
    args = ap.parse_args()

    run_dir = RUNS_DIR / args.run_id
    if not run_dir.exists():
        raise SystemExit(f"run 不存在：{run_dir}")
    cfg = TrainingConfig.load(run_dir / "config.json")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = build_model(cfg.model_name, num_classes=cfg.num_classes, pretrained=False,
                        dropout=cfg.dropout, width_mult=cfg.width_mult,
                        use_se=cfg.use_se, se_ratio=cfg.se_ratio).to(device)
    ckpt = torch.load(run_dir / "best_model.pt", map_location=device)
    state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()

    data_p = Path(cfg.data_dir) / args.data
    if not data_p.exists():
        raise SystemExit(f"数据不存在：{data_p}")
    with open(data_p, "rb") as f:
        recs = pickle.load(f)

    ds = FER2013Dataset(recs, cfg, augment=False)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    logits, targets = _evaluate(model, loader, device, args.tta)
    res = evaluate_predictions(logits, targets, CLASS_NAMES)

    pf = run_dir / f"{args.tag}_eval_metrics.json"
    prev = json.loads(pf.read_text("utf-8")) if pf.exists() else {}
    prev[args.data] = {
        "n": len(recs), "tta": bool(args.tta), "accuracy": res["accuracy"],
        "top2_accuracy": res["top2_accuracy"], "macro_f1": res["macro_f1"],
        "per_class": res.get("per_class"),
        "class_names_cn": CLASS_NAMES_CN,
    }
    pf.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")

    artifacts.plot_confusion_matrix(res["confusion_matrix"], CLASS_NAMES,
                                    run_dir / f"{args.tag}_confusion_matrix.png",
                                    normalize=True, title=f"{args.tag.upper()} Test (row-normalized)")
    (run_dir / f"{args.tag}_classification_report.txt").write_text(
        classification_report_text(res, CLASS_NAMES), encoding="utf-8")

    print(f"数据集: {data_p}  n={len(recs)}  TTA={args.tta}")
    print(f"准确率 {res['accuracy']:.4f} | Top-2 {res['top2_accuracy']:.4f} | Macro-F1 {res['macro_f1']:.4f}")
    for r in res.get("per_class") or []:
        print(f"  {r['name']:10s} n={r['support']:5d} precision={r['precision']:.3f} "
              f"recall={r['recall']:.3f} f1={r['f1']:.3f}")
    print(f"产物: {pf}")


if __name__ == "__main__":
    main()