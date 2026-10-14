"""多模型 logits 融合评测：判断"实验室(FER)模型 + 真实场景(RAF)模型"取平均
能否同时兼顾两个域。

用法：
  python -m ml.eval_blend --runs 20261013-174022-improved,20261014-121827-rafmix --data test_raf.pt
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .architectures import CLASS_NAMES
from .backbones import build_model
from .config import RUNS_DIR, TrainingConfig
from .dataset import FER2013Dataset
from .metrics import evaluate_predictions


@torch.no_grad()
def _logits(run_id: str, recs: list[dict], device, tta: bool = True):
    run_dir = RUNS_DIR / run_id
    cfg = TrainingConfig.load(run_dir / "config.json")
    model = build_model(cfg.model_name, num_classes=cfg.num_classes, pretrained=False,
                        dropout=cfg.dropout, width_mult=cfg.width_mult,
                        use_se=cfg.use_se, se_ratio=cfg.se_ratio).to(device)
    ckpt = torch.load(run_dir / "best_model.pt", map_location=device)
    state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()
    loader = DataLoader(FER2013Dataset(recs, cfg, augment=False), batch_size=256, shuffle=False)
    out, tgts = [], []
    for x, y in loader:
        x = x.to(device)
        o = model(x)
        if tta:
            o = 0.5 * (o + model(torch.flip(x, dims=[3])))
        out.append(o.float().cpu().numpy())
        tgts.append(y.numpy())
    return np.concatenate(out), np.concatenate(tgts)


def main() -> None:
    ap = argparse.ArgumentParser(description="多模型融合评测")
    ap.add_argument("--runs", type=str, required=True, help="逗号分隔的 run_id")
    ap.add_argument("--data", type=str, default="test_raf.pt")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cfg0 = TrainingConfig.load(RUNS_DIR / args.runs.split(",")[0] / "config.json")
    with open(Path(cfg0.data_dir) / args.data, "rb") as f:
        recs = pickle.load(f)

    runs = [r.strip() for r in args.runs.split(",") if r.strip()]
    lgs, tgt = [], None
    for r in runs:
        lg, t = _logits(r, recs, device)
        lgs.append(lg)
        tgt = t
        res = evaluate_predictions(lg, tgt, CLASS_NAMES)
        print(f"[{r}] acc={res['accuracy']:.4f} macroF1={res['macro_f1']:.4f}")

    blend = np.mean(np.stack(lgs), axis=0)
    res = evaluate_predictions(blend, tgt, CLASS_NAMES)
    print(f"[融合 {len(runs)} 个] 数据={args.data} acc={res['accuracy']:.4f} "
          f"top2={res['top2_accuracy']:.4f} macroF1={res['macro_f1']:.4f}")
    for r in res["per_class"]:
        print(f"    {r['name']:10s} n={r['support']:5d} recall={r['recall']:.3f} f1={r['f1']:.3f}")


if __name__ == "__main__":
    main()