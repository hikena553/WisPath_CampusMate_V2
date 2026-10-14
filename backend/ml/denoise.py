"""标签噪声处理：用 K 折交叉验证的"袋外（OOF）预测"识别疑似错标样本。

为什么必须用 OOF：
  直接用"在训练集上训练过的模型"去预测训练集，模型已经记住了这些样本，
  冲突样本反映的是记忆噪声而不是标签错误。只有让每个样本都被"没见过它"的
  模型预测（K 折交叉验证），得到的预测才是相对可信的第三方判断。

判定规则：
  某样本的 OOF 预测类别 != 原标签，且预测置信度 >= threshold，
  即视为疑似错标，从训练集中剔除（不做重标，避免引入新的错误）。

产物：
  - data/fer2013/<out>            去噪后的训练集（pickle，与 train.pt 同格式）
  - runs/<ts>-denoise/report.json 去噪报告（剔除数量、按类分布、整体统计）

用法（在 backend 目录下）：
  python -m ml.denoise --folds 3 --epochs 15 --threshold 0.8
"""
from __future__ import annotations

import argparse
import json
import pickle
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .architectures import CLASS_NAMES, FaceExpressionNet
from .config import RUNS_DIR, TrainingConfig
from .dataset import FER_LABEL_MAP, FER2013Dataset, ensure_dataset, _load_split
from .losses import build_loss


def _assign_folds(labels: list[int], k: int, seed: int = 42) -> list[int]:
    """按类别做轮转分折，保证每折的类别分布与整体接近。"""
    rng = random.Random(seed)
    by_class: dict[int, list[int]] = {}
    for i, lab in enumerate(labels):
        by_class.setdefault(lab, []).append(i)
    folds = [0] * len(labels)
    for lab, idxs in by_class.items():
        rng.shuffle(idxs)
        for pos, i in enumerate(idxs):
            folds[i] = pos % k
    return folds


def _train_one_fold(train_recs: list[dict], cfg: TrainingConfig, device: torch.device,
                    epochs: int, seed: int) -> FaceExpressionNet:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    ds = FER2013Dataset(train_recs, cfg, augment=True)
    loader = DataLoader(ds, batch_size=256, shuffle=True, num_workers=0,
                        drop_last=False, pin_memory=device.type == "cuda")
    model = FaceExpressionNet(width_mult=cfg.width_mult, dropout=cfg.dropout).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=5e-4)
    criterion = build_loss(cfg)
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    steps_per_epoch = max(1, len(loader))
    total = epochs * steps_per_epoch
    step = 0
    model.train()
    for ep in range(epochs):
        for x, y in loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            # warmup + cosine
            lr = 3e-3 * min(1.0, (step + 1) / max(1, steps_per_epoch))
            lr *= 0.5 * (1 + np.cos(np.pi * min(1.0, step / total)))
            lr = max(lr, 1e-5)
            for g in opt.param_groups:
                g["lr"] = lr
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                out = model(x)
                loss = criterion(out, y)
            if use_amp:
                scaler.scale(loss).backward()
                scaler.unscale_(opt)
                nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                scaler.step(opt)
                scaler.update()
            else:
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                opt.step()
            step += 1
    return model


@torch.no_grad()
def _predict(model: FaceExpressionNet, recs: list[dict], cfg: TrainingConfig,
             device: torch.device) -> np.ndarray:
    ds = FER2013Dataset(recs, cfg, augment=False)
    loader = DataLoader(ds, batch_size=512, shuffle=False, num_workers=0)
    model.eval()
    probs = []
    use_amp = device.type == "cuda"
    for x, _ in loader:
        x = x.to(device, non_blocking=True)
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            out = model(x)
        probs.append(torch.softmax(out.float(), dim=1).cpu().numpy())
    return np.concatenate(probs)


def main() -> None:
    ap = argparse.ArgumentParser(description="OOF 交叉验证标签噪声过滤")
    ap.add_argument("--folds", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--threshold", type=float, default=0.80, help="判定错标的置信度阈值")
    ap.add_argument("--width-mult", type=float, default=1.0)
    ap.add_argument("--out", type=str, default="train_clean.pt")
    ap.add_argument("--report-name", type=str, default="denoise")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cfg = TrainingConfig(input_size=48, width_mult=args.width_mult, loss="focal",
                         label_smoothing=0.1, use_class_weight=False)
    train_p, _ = ensure_dataset(cfg)
    records = _load_split(train_p)
    labels = [FER_LABEL_MAP[r["labels"]] for r in records]
    print(f"设备: {device} | 训练样本 {len(records)} | {args.folds} 折 OOF | "
          f"输入 {cfg.input_size} | width {args.width_mult} | epochs {args.epochs}", flush=True)

    folds = _assign_folds(labels, args.folds, cfg.seed)
    oof = np.zeros((len(records), len(CLASS_NAMES)), dtype=np.float32)

    for k in range(args.folds):
        tr_idx = [i for i, f in enumerate(folds) if f != k]
        va_idx = [i for i, f in enumerate(folds) if f == k]
        print(f"[fold {k + 1}/{args.folds}] 训练 {len(tr_idx)} / 预测 {len(va_idx)} ...", flush=True)
        model = _train_one_fold([records[i] for i in tr_idx], cfg, device, args.epochs, cfg.seed + k)
        oof[va_idx] = _predict(model, [records[i] for i in va_idx], cfg, device)
        del model
        torch.cuda.empty_cache()

    pred = oof.argmax(axis=1)
    conf = oof.max(axis=1)
    true = np.array(labels, dtype=np.int64)
    oof_acc = float((pred == true).mean())
    suspect = (pred != true) & (conf >= args.threshold)
    print(f"OOF 准确率（在训练集上）: {oof_acc:.4f}", flush=True)
    print(f"疑似错标样本: {int(suspect.sum())} / {len(records)} "
          f"({suspect.mean() * 100:.2f}%)，阈值 {args.threshold}", flush=True)

    drop_by_class = Counter(CLASS_NAMES[true[i]] for i in np.where(suspect)[0])
    total_by_class = Counter(CLASS_NAMES[t] for t in true)
    keep = [r for i, r in enumerate(records) if not suspect[i]]

    out_path = Path(cfg.data_dir) / args.out
    with open(out_path, "wb") as f:
        pickle.dump(keep, f)
    print(f"已写出 {out_path}（保留 {len(keep)} / {len(records)}）", flush=True)

    run_dir = RUNS_DIR / (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + f"-{args.report_name}")
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "label_noise_filter",
        "method": "K-fold out-of-fold prediction; drop samples whose OOF argmax != given label "
                  "and whose confidence >= threshold",
        "folds": args.folds,
        "epochs_per_fold": args.epochs,
        "threshold": args.threshold,
        "input_size": cfg.input_size,
        "width_mult": args.width_mult,
        "oof_accuracy_on_train": round(oof_acc, 4),
        "total": len(records),
        "kept": len(keep),
        "dropped": int(suspect.sum()),
        "dropped_ratio": round(float(suspect.mean()), 4),
        "dropped_by_true_class": {k: int(v) for k, v in sorted(drop_by_class.items())},
        "total_by_class": {k: int(v) for k, v in sorted(total_by_class.items())},
        "dropped_ratio_by_class": {
            k: round(drop_by_class.get(k, 0) / max(1, total_by_class.get(k, 1)), 4)
            for k in CLASS_NAMES
        },
        "output": str(out_path),
    }
    (run_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["dropped_ratio_by_class"], ensure_ascii=False), flush=True)
    print(f"报告目录: {run_dir}", flush=True)


if __name__ == "__main__":
    main()