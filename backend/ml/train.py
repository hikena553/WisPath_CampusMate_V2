"""FaceExpressionNet 训练 / 微调主流程。

用法示例：
  # 从头训练（默认配置）
  python -m ml.train --run-name full

  # 使用更"强"的训练配方（更大宽度 + 更长训练 + RandomErasing + EMA + TTA）
  python -m ml.train --config ml/configs/strong.json --run-name strong

  # 快速冒烟（少量样本 + 2 轮）
  python -m ml.train --smoke

  # 基于已训练 checkpoint 微调（更小学习率）
  python -m ml.train --init-weights ml/runs/<run_id>/best_model.pt --finetune-lr 3e-4

产物：runs/<run_id>/ 下的 config.json / metrics.json / history.csv /
training_curves.png / confusion_matrix.png / classification_report.txt / best_model.pt
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler

from . import artifacts
from .architectures import CLASS_NAMES, CLASS_NAMES_CN, FaceExpressionNet, count_parameters
from .backbones import build_model, head_prefix_for
from .config import RUNS_DIR, TrainingConfig
from .dataset import (build_datasets, compute_class_weights, dataset_stats, sampler_weights,
                      _load_split, FER2013Dataset, ensure_dataset)
from .losses import build_loss
from .metrics import classification_report_text, evaluate_predictions


def _setup_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _resolve_device(cfg: TrainingConfig) -> torch.device:
    if cfg.device == "cpu":
        return torch.device("cpu")
    if cfg.device == "cuda" or (cfg.device == "auto" and torch.cuda.is_available()):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device("cpu")


class ModelEMA:
    """权重指数滑动平均（EMA）。

    维护一份模型参数的滑动平均副本；评测时用它通常比原始权重更稳定、精度更高
    （相当于对训练后期多个 checkpoint 做隐式集成）。decay 建议 0.999 左右。
    """

    def __init__(self, model: nn.Module, decay: float) -> None:
        self.ema = copy.deepcopy(model).eval()
        for p in self.ema.parameters():
            p.requires_grad_(False)
        self.decay = decay
        self.steps = 0

    @torch.no_grad()
    def update(self, model: nn.Module) -> None:
        # 衰减预热：训练初期用较小 decay，让 EMA 快速跟上原始权重，
        # 避免 decay=0.999 时前若干轮仍停留在随机初始化附近。
        self.steps += 1
        d = min(self.decay, (1.0 + self.steps) / (10.0 + self.steps))
        msd = model.state_dict()
        for k, v in self.ema.state_dict().items():
            mv = msd[k]
            if v.dtype.is_floating_point:
                v.mul_(d).add_(mv.detach(), alpha=1.0 - d)
            else:
                v.copy_(mv)


def _build_optimizer(model: nn.Module, cfg: TrainingConfig, base_lr: float,
                     head_prefix: str = "head."):
    """分组学习率：分类头 head_lr_mult 倍，主干 backbone_lr_mult 倍。"""
    head_params, backbone_params = [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        (head_params if name.startswith(head_prefix) else backbone_params).append(p)

    groups = [
        {"params": backbone_params, "lr": base_lr * cfg.backbone_lr_mult},
        {"params": head_params, "lr": base_lr * cfg.head_lr_mult},
    ]
    if cfg.optimizer.lower() == "sgd":
        opt = torch.optim.SGD(groups, momentum=cfg.momentum, weight_decay=cfg.weight_decay, nesterov=True)
    else:
        opt = torch.optim.AdamW(groups, lr=base_lr, weight_decay=cfg.weight_decay)
    return opt, [g["lr"] for g in groups]


def _lr_factor(epoch: int, cfg: TrainingConfig) -> float:
    """学习率调度因子：warmup 线性升温 + cosine 衰减。"""
    if cfg.warmup_epochs > 0 and epoch < cfg.warmup_epochs:
        return (epoch + 1) / cfg.warmup_epochs
    if cfg.scheduler == "none":
        return 1.0
    remain = max(1, cfg.epochs - cfg.warmup_epochs)
    progress = min(1.0, max(0.0, (epoch - cfg.warmup_epochs) / remain))
    if cfg.scheduler == "step":
        return 0.5 ** int(progress * 3)
    return 0.5 * (1 + np.cos(np.pi * progress))  # cosine


@torch.no_grad()
def _evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device,
              use_amp: bool = False, tta: bool = False):
    """评估；tta=True 时对原图与水平翻转图分别前向并平均 logits（免费的小幅提分）。"""
    model.eval()
    total_loss, n = 0.0, 0
    logits_all, targets_all = [], []
    for x, y in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            out = model(x)
            if tta:
                out = 0.5 * (out + model(torch.flip(x, dims=[3])))
            loss = criterion(out, y)
        total_loss += loss.item() * x.size(0)
        n += x.size(0)
        logits_all.append(out.float().cpu().numpy())
        targets_all.append(y.cpu().numpy())
    logits = np.concatenate(logits_all) if logits_all else np.zeros((0, 7))
    targets = np.concatenate(targets_all) if targets_all else np.zeros((0,), dtype=np.int64)
    acc = float((logits.argmax(1) == targets).mean()) if n else 0.0
    return total_loss / max(1, n), acc, logits, targets


def run_training(
    cfg: TrainingConfig,
    progress: Optional[Callable[[dict], None]] = None,
) -> dict:
    """执行一次完整训练，返回 run 元信息（含关键指标与产物路径）。"""
    _setup_seed(cfg.seed)
    device = _resolve_device(cfg)
    threads = os.cpu_count() or 4
    try:
        torch.set_num_threads(threads)
    except Exception:
        pass
    # GPU 加速：cuDNN 自动调优 + TF32（如可用）
    if device.type == "cuda":
        try:
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        except Exception:
            pass

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if cfg.run_name:
        run_id = f"{run_id}-{cfg.run_name}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 数据 ----------
    train_set, val_set, test_set = build_datasets(cfg)
    stats = dataset_stats(cfg)
    # 长尾重采样：用温和逆频权重让长尾类获得更多曝光
    if cfg.balance_sampler:
        sw = sampler_weights(train_set.records, cfg.num_classes, cfg.sampler_power)
        sampler = WeightedRandomSampler(torch.as_tensor(sw, dtype=torch.double),
                                        num_samples=len(sw), replacement=True)
        train_loader = DataLoader(train_set, batch_size=cfg.batch_size, sampler=sampler,
                                  num_workers=cfg.num_workers, drop_last=False,
                                  pin_memory=device.type == "cuda",
                                  persistent_workers=cfg.num_workers > 0)
    else:
        train_loader = DataLoader(train_set, batch_size=cfg.batch_size, shuffle=True,
                                  num_workers=cfg.num_workers, drop_last=False,
                                  pin_memory=device.type == "cuda",
                                  persistent_workers=cfg.num_workers > 0)
    val_loader = DataLoader(val_set, batch_size=cfg.batch_size, shuffle=False, num_workers=cfg.num_workers,
                            pin_memory=device.type == "cuda", persistent_workers=cfg.num_workers > 0)
    test_loader = DataLoader(test_set, batch_size=cfg.batch_size, shuffle=False, num_workers=cfg.num_workers,
                             pin_memory=device.type == "cuda", persistent_workers=cfg.num_workers > 0)

    # ---------- 模型 ----------
    model = build_model(
        cfg.model_name, num_classes=cfg.num_classes,
        pretrained=cfg.pretrained, dropout=cfg.dropout,
        width_mult=cfg.width_mult, use_se=cfg.use_se, se_ratio=cfg.se_ratio,
    ).to(device)
    n_params = count_parameters(model)
    head_prefix = head_prefix_for(cfg.model_name)

    init_info = "从头训练"
    if cfg.init_weights:
        sd = torch.load(cfg.init_weights, map_location=device)
        if isinstance(sd, dict) and "model_state" in sd:
            sd = sd["model_state"]
        missing, unexpected = model.load_state_dict(sd, strict=False)
        init_info = f"载入 {Path(cfg.init_weights).name} 微调（missing={len(missing)}, unexpected={len(unexpected)}）"

    if cfg.freeze_backbone:
        for name, p in model.named_parameters():
            if not name.startswith(head_prefix):
                p.requires_grad = False

    base_lr = cfg.finetune_lr if cfg.finetune_lr > 0 else cfg.lr
    optimizer, base_lrs = _build_optimizer(model, cfg, base_lr, head_prefix)

    class_weight = None
    if cfg.use_class_weight:
        class_weight = compute_class_weights(train_set.records, cfg.num_classes).to(device)
    criterion = build_loss(cfg, class_weight)

    # 权重滑动平均（EMA）
    ema = ModelEMA(model, cfg.ema_decay) if cfg.ema_decay > 0 else None

    # 混合精度：仅在 CUDA 生效（CPU 自动关闭）
    use_amp = bool(cfg.amp) and device.type == "cuda"
    try:
        scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    except Exception:  # 兼容旧版 torch
        scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    mixup_alpha = float(cfg.mixup_alpha or 0.0)

    # ---------- 训练循环 ----------
    history: list[dict] = []
    best_val_acc, best_epoch = -1.0, 0
    patience = 0
    t0 = time.time()

    print(f"设备: {device} | 模型: {cfg.model_name} (pretrained={cfg.pretrained}) | 输入: {cfg.input_size} | "
          f"训练样本: {len(train_set)} | 验证: {len(val_set)} | 测试: {len(test_set)} | "
          f"batch: {cfg.batch_size} | AMP: {use_amp} | 预解码: {cfg.preload} | "
          f"width_mult: {cfg.width_mult} | EMA: {cfg.ema_decay} | RandomErasing: {cfg.random_erase_prob} | "
          f"MixUp: {mixup_alpha} | TTA: {cfg.tta}", flush=True)

    for epoch in range(1, cfg.epochs + 1):
        t_epoch = time.time()
        factor = _lr_factor(epoch - 1, cfg)
        for g, lr0 in zip(optimizer.param_groups, base_lrs):
            g["lr"] = lr0 * factor

        model.train()
        run_loss, seen, correct = 0.0, 0, 0
        for x, y in train_loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            if mixup_alpha > 0:
                lam = float(np.random.beta(mixup_alpha, mixup_alpha))
                perm = torch.randperm(x.size(0), device=device)
                x_mix = lam * x + (1.0 - lam) * x[perm]
                with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                    out = model(x_mix)
                    loss = lam * criterion(out, y) + (1.0 - lam) * criterion(out, y[perm])
            else:
                with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                    out = model(x)
                    loss = criterion(out, y)
            if use_amp:
                scaler.scale(loss).backward()
                if cfg.grad_clip > 0:
                    scaler.unscale_(optimizer)
                    nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                if cfg.grad_clip > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                optimizer.step()
            if ema is not None:
                ema.update(model)
            run_loss += loss.item() * x.size(0)
            seen += x.size(0)
            correct += int((out.argmax(1) == y).sum().item())

        train_loss, train_acc = run_loss / max(1, seen), correct / max(1, seen)

        # 逐轮同时评估"原始权重"与"EMA 权重"，取更优者用于模型选择与保存。
        # 这样即使 EMA 早期滞后，也不会拖累最终精度。
        live_loss, live_acc, _, _ = _evaluate(model, val_loader, criterion, device, use_amp)
        ema_acc = None
        if ema is not None:
            ema_loss, ema_acc, _, _ = _evaluate(ema.ema, val_loader, criterion, device, use_amp)
            if ema_acc >= live_acc:
                eval_model, val_loss, val_acc = ema.ema, ema_loss, ema_acc
            else:
                eval_model, val_loss, val_acc = model, live_loss, live_acc
        else:
            eval_model, val_loss, val_acc = model, live_loss, live_acc

        rec = {
            "epoch": epoch,
            "lr_backbone": round(optimizer.param_groups[0]["lr"], 8),
            "lr_head": round(optimizer.param_groups[1]["lr"], 8),
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4),
            "val_acc_live": round(live_acc, 4),
            "val_acc_ema": round(ema_acc, 4) if ema_acc is not None else "",
        }
        history.append(rec)
        ema_txt = f" | ema={ema_acc:.4f}" if ema_acc is not None else ""
        print(f"[ep {epoch:>2}/{cfg.epochs}] train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
              f"val_acc={val_acc:.4f} (live={live_acc:.4f}{ema_txt}) lr={optimizer.param_groups[1]['lr']:.2e} "
              f"耗时 {time.time() - t_epoch:.1f}s", flush=True)
        if progress:
            progress(rec)

        if val_acc > best_val_acc:
            best_val_acc, best_epoch, patience = val_acc, epoch, 0
            torch.save({"model_state": eval_model.state_dict(), "class_names": CLASS_NAMES,
                        "config": cfg.to_dict(), "epoch": epoch}, run_dir / "best_model.pt")
        else:
            patience += 1
            if cfg.early_stop_patience > 0 and patience >= cfg.early_stop_patience:
                print(f"验证准确率连续 {patience} 轮未提升，提前停止于 epoch {epoch}", flush=True)
                break

    # ---------- 用最佳权重评估测试集（可选 TTA） ----------
    final_model = ema.ema if ema is not None else model
    if cfg.train_on_all:
        # 全量重训：验证集已并入训练，改用最后一轮权重（不做验证集选优）
        torch.save({"model_state": final_model.state_dict(), "class_names": CLASS_NAMES,
                    "config": cfg.to_dict(), "epoch": len(history)}, run_dir / "best_model.pt")
    best_path = run_dir / "best_model.pt"
    if best_path.exists():
        sd = torch.load(best_path, map_location=device)
        final_model.load_state_dict(sd["model_state"] if isinstance(sd, dict) and "model_state" in sd else sd)

    val_loss, val_acc, val_logits, val_targets = _evaluate(final_model, val_loader, criterion, device, use_amp, cfg.tta)
    test_loss, test_acc, test_logits, test_targets = _evaluate(final_model, test_loader, criterion, device, use_amp, cfg.tta)

    val_result = evaluate_predictions(val_logits, val_targets, CLASS_NAMES)
    test_result = evaluate_predictions(test_logits, test_targets, CLASS_NAMES)
    test_result["loss"] = round(test_loss, 4)
    val_result["loss"] = round(val_loss, 4)
    test_result["class_names_cn"] = CLASS_NAMES_CN
    test_result["tta"] = bool(cfg.tta)

    # ---------- 落盘产物 ----------
    cfg.save(run_dir / "config.json")
    artifacts.save_history_csv(history, run_dir / "history.csv")
    artifacts.plot_curves(history, run_dir / "training_curves.png")
    artifacts.plot_confusion_matrix(test_result["confusion_matrix"], CLASS_NAMES,
                                    run_dir / "confusion_matrix.png", normalize=False,
                                    title="Test Confusion Matrix (counts)")
    artifacts.plot_confusion_matrix(test_result["confusion_matrix"], CLASS_NAMES,
                                    run_dir / "confusion_matrix_normalized.png", normalize=True,
                                    title="Test Confusion Matrix (row-normalized)")
    report = classification_report_text(test_result, CLASS_NAMES)
    (run_dir / "classification_report.txt").write_text(report, encoding="utf-8")

    device_name = "cpu"
    if device.type == "cuda":
        try:
            device_name = torch.cuda.get_device_name(0)
        except Exception:
            device_name = "cuda"

    run_meta = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "device_name": device_name,
        "amp": use_amp,
        "ema_decay": cfg.ema_decay,
        "mixup_alpha": mixup_alpha,
        "tta": bool(cfg.tta),
        "random_erase_prob": cfg.random_erase_prob,
        "threads": threads,
        "architecture": (f"{cfg.model_name}"
                         + (" + ImageNet 预训练（迁移学习）" if cfg.pretrained else "（从头训练）")),
        "params": n_params,
        "input_size": cfg.input_size,
        "num_classes": cfg.num_classes,
        "class_names": CLASS_NAMES,
        "init_info": init_info,
        "data": stats,
        "hyperparams": cfg.to_dict(),
        "epochs_trained": len(history),
        "epochs_planned": cfg.epochs,
        "best_val_acc": round(best_val_acc, 4),
        "best_epoch": best_epoch,
        "val": val_result,
        "test": test_result,
        "elapsed_sec": round(time.time() - t0, 1),
        "artifacts": [
            "config.json", "metrics.json", "history.csv", "training_curves.png",
            "confusion_matrix.png", "confusion_matrix_normalized.png",
            "classification_report.txt", "best_model.pt", "summary.md",
        ],
    }
    artifacts.save_json(run_meta, run_dir / "metrics.json")
    artifacts.write_summary_md(run_meta, run_dir / "summary.md")

    print(f"\n训练完成：{run_id}", flush=True)
    print(f"最佳验证准确率 {best_val_acc:.4f} @ epoch {best_epoch}", flush=True)
    print(f"测试集准确率 {test_result['accuracy']:.4f} | Top-2 {test_result['top2_accuracy']:.4f} "
          f"| Macro-F1 {test_result['macro_f1']:.4f} | TTA={cfg.tta}", flush=True)
    print(f"产物目录：{run_dir}", flush=True)
    return run_meta


def _apply_smoke(cfg: TrainingConfig) -> TrainingConfig:
    return replace(cfg, max_samples=2000, epochs=2, batch_size=64, early_stop_patience=0,
                   warmup_epochs=0, run_name=(cfg.run_name or "smoke"))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FaceExpressionNet 训练/微调")
    p.add_argument("--config", type=str, default="", help="config.json 路径（可选）")
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=None)
    p.add_argument("--lr", type=float, default=None)
    p.add_argument("--finetune-lr", type=float, default=None)
    p.add_argument("--init-weights", type=str, default=None)
    p.add_argument("--freeze-backbone", action="store_true", default=None)
    p.add_argument("--width-mult", type=float, default=None)
    p.add_argument("--input-size", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--device", type=str, default=None)
    p.add_argument("--num-workers", type=int, default=None)
    p.add_argument("--amp", dest="amp", action="store_true", default=None, help="启用混合精度（CUDA）")
    p.add_argument("--no-amp", dest="amp", action="store_false", help="关闭混合精度")
    p.add_argument("--run-name", type=str, default=None)
    p.add_argument("--smoke", action="store_true", help="快速冒烟测试")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = TrainingConfig.load(Path(args.config)) if args.config else TrainingConfig()
    overrides = {
        "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr,
        "finetune_lr": args.finetune_lr, "init_weights": args.init_weights,
        "freeze_backbone": args.freeze_backbone, "width_mult": args.width_mult,
        "input_size": args.input_size, "seed": args.seed, "device": args.device,
        "run_name": args.run_name, "num_workers": args.num_workers, "amp": args.amp,
    }
    cfg = cfg.from_kwargs(**{**cfg.to_dict(), **{k: v for k, v in overrides.items() if v is not None}})
    if args.smoke:
        cfg = _apply_smoke(cfg)
    run_training(cfg)


if __name__ == "__main__":
    main()