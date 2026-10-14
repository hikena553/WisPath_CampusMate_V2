"""对若干训练 run 的 best_model.pt 做 TTA 消融评测（有/无水平翻转 TTA）。

用途：与外部模型（如前端 face-api.js）做严格对等的同口径比较——
必须确认双方是否都用了 TTA，否则数字不可比。

用法（在 backend 目录下）：
  python -m ml.eval_checkpoints --runs 20261013-130843-strong64 20261013-115245-strong
"""
from __future__ import annotations

import argparse

import numpy as np
import torch

from .architectures import CLASS_NAMES
from .config import RUNS_DIR
from .ensemble import _probs_for_run
from .metrics import evaluate_predictions


def main() -> None:
    p = argparse.ArgumentParser(description="TTA 消融评测")
    p.add_argument("--runs", nargs="+", required=True, help="run_id 列表（runs/ 下的目录名）")
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    header = f"{'run_id':<34}{'model':<22}{'input':>6}{'no-TTA acc':>12}{'TTA acc':>10}{'TTA top2':>10}{'TTA macroF1':>13}"
    print(header, flush=True)
    print("-" * len(header), flush=True)

    for rid in args.runs:
        rd = RUNS_DIR / rid
        row = {}
        for tta in (False, True):
            m = _probs_for_run(rd, device, tta=tta)
            row[tta] = (evaluate_predictions(m["test_probs"], m["test_targets"], CLASS_NAMES),
                        m["cfg"])
        res0, cfg = row[False]
        res1, _ = row[True]
        print(f"{rid:<34}{cfg.model_name:<22}{cfg.input_size:>6}"
              f"{res0['accuracy']:>12.4f}{res1['accuracy']:>10.4f}"
              f"{res1['top2_accuracy']:>10.4f}{res1['macro_f1']:>13.4f}", flush=True)


if __name__ == "__main__":
    main()