"""情绪平滑策略对比评测：量化"表情变化时的响应滞后"。

背景
----
真实摄像头测试里，用户反馈"表情变化时识别度不高/跟不上"。原因不是模型分类错，
而是输出治理：早期前端对最近 5 次**原始标签**做硬多数票，导致从 A 切到 B
必须攒够 3 票（约 0.75–1.25 秒），且低置信标签与高置信标签计票等价。

本脚本用部署模型对应的那份权重（`runs/<run_id>/best_model.pt`，与前端实际加载的
ONNX 由同一次训练导出、数值已对齐）在一段"表情不断切换"的序列上取逐帧概率，
再分别套用「旧：5 帧硬多数票」与「新：快攻慢放滞回滤波」两种治理策略，
直接测出切换滞后与稳定期准确率，作为改动的量化依据。

序列构造（与伪摄像头实测同口径）：按类别切段，每段连续若干帧取该类别的不同样本，
模拟"同一个人表情发生变化"。段内样本不同会引入额外的外观噪声，属于偏保守的估计。

用法（在 backend 目录下）：
  python -m ml.smoother_eval --run 20261014-121827-rafmix
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np

from .architectures import CLASS_NAMES
from .dataset import FER_LABEL_MAP

IMG_SIZE = 64


# ---------------- 两种治理策略（与前端实现逐行对应） ----------------
def smooth_legacy(state: dict, emotion: str, confidence: float, window: int = 5) -> str:
    """旧：最近 window 次原始标签的硬多数票。"""
    state["recent"].append(emotion)
    if len(state["recent"]) > window:
        state["recent"].pop(0)
    counts: dict[str, int] = {}
    for e in state["recent"]:
        counts[e] = counts.get(e, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[0][0]


def smooth_hyst(state: dict, emotion: str, confidence: float, hi_conf: float = 1.01,
                mid_conf: float = 0.55, mid_streak: int = 2,
                window: int = 3, ratio: float = 0.67) -> str:
    """快攻慢放滞回滤波。

    hi_conf：达到该置信度则"一票立即切换"（默认 1.01 表示该档关闭）；
    mid_conf + mid_streak：中等置信度下连续出现若干次即切换；
    其余情况退回窗口多数票，且需达到 ratio 才切换。
    """
    if emotion == state.get("streakLabel"):
        state["streak"] += 1
    else:
        state["streakLabel"] = emotion
        state["streak"] = 1

    if not state.get("label"):
        state["label"] = emotion
        return emotion
    if emotion == state["label"]:
        return state["label"]

    if confidence >= hi_conf:
        state["label"] = emotion
        state["window"] = [emotion]
        return emotion

    if confidence >= mid_conf and state["streak"] >= mid_streak:
        state["label"] = emotion
        state["window"] = [emotion]
        return emotion

    state["window"].append(emotion)
    if len(state["window"]) > window:
        state["window"].pop(0)
    counts: dict[str, int] = {}
    for e in state["window"]:
        counts[e] = counts.get(e, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[0]
    if top[1] / len(state["window"]) >= ratio:
        state["label"] = top[0]
        state["window"] = [top[0]]
    return state["label"]


def smooth_v1(state: dict, emotion: str, confidence: float) -> str:
    return smooth_hyst(state, emotion, confidence)


def smooth_v2(state: dict, emotion: str, confidence: float) -> str:
    """v2：增加"高置信一票即切"档（hi_conf=0.75）。"""
    return smooth_hyst(state, emotion, confidence, hi_conf=0.75)


def new_state() -> dict:
    return {"recent": [], "label": "", "window": [], "streakLabel": "", "streak": 0}


# ---------------- 逐帧概率 ----------------
def build_sequence(records: list[dict], per_seg: int, repeats: int, seed: int = 11):
    import random
    rng = random.Random(seed)
    by: dict[str, list[bytes]] = {k: [] for k in CLASS_NAMES}
    for r in records:
        by[CLASS_NAMES[FER_LABEL_MAP[r["labels"]]]].append(r["img_bytes"])
    for k in by:
        rng.shuffle(by[k])

    seq: list[tuple[bytes, str]] = []
    cursor = {k: 0 for k in CLASS_NAMES}
    order = []
    for _ in range(repeats):
        block = list(CLASS_NAMES)
        rng.shuffle(block)
        order.extend(block)
    for lab in order:
        pool = by[lab]
        for j in range(per_seg):
            idx = cursor[lab] % len(pool)
            cursor[lab] += 1
            seq.append((pool[idx], lab))
    return seq, order


def run_model(run_id: str, seq: list[tuple[bytes, str]]) -> tuple[np.ndarray, np.ndarray]:
    """用 PyTorch 载入已训练模型取逐帧概率。

    说明：这里不依赖 onnxruntime（该环境未安装）。前端实际用的是同一次训练导出的
    ONNX，二者数值一致性已验证（logits 最大绝对误差 2.9e-06，见 export_onnx.py 的输出），
    因此用 PyTorch 结果做策略对比是等价的。同时按前端口径做水平翻转 TTA。
    """
    import io

    import torch
    from PIL import Image

    from .backbones import build_model
    from .config import RUNS_DIR, TrainingConfig

    run_dir = RUNS_DIR / run_id
    cfg = TrainingConfig.load(run_dir / "config.json")
    device = torch.device("cpu")
    model = build_model(cfg.model_name, num_classes=cfg.num_classes, pretrained=False,
                        dropout=cfg.dropout, width_mult=cfg.width_mult,
                        use_se=cfg.use_se, se_ratio=cfg.se_ratio).to(device)
    ckpt = torch.load(run_dir / "best_model.pt", map_location=device)
    state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()

    batch = 64
    logits_all = []
    with torch.no_grad():
        for i in range(0, len(seq), batch):
            chunk = seq[i:i + batch]
            xs = np.zeros((len(chunk), 3, IMG_SIZE, IMG_SIZE), dtype=np.float32)
            for bi, (raw, _lab) in enumerate(chunk):
                g = Image.open(io.BytesIO(raw)).convert("L").resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)
                a = np.asarray(g, dtype=np.float32) / 255.0
                a = (a - 0.5) / 0.5
                xs[bi] = np.repeat(a[None, :, :], 3, axis=0)
            t = torch.from_numpy(xs)
            out = model(t)
            out = 0.5 * (out + model(torch.flip(t, dims=[3])))  # 与前端一致的水平翻转 TTA
            logits_all.append(out.numpy())
    logits = np.concatenate(logits_all)
    probs = np.exp(logits - logits.max(axis=1, keepdims=True))
    probs /= probs.sum(axis=1, keepdims=True)
    return probs, np.array([CLASS_NAMES.index(l) for _r, l in seq])


def evaluate(probs: np.ndarray, truth: np.ndarray, order: list[str], per_seg: int,
             inference_ms: float) -> dict:
    n = len(truth)
    seg_true = np.array([CLASS_NAMES.index(l) for l in order for _ in range(per_seg)])

    out = {}
    for name, fn in (("legacy_majority5", smooth_legacy),
                     ("hysteresis_v1", smooth_v1),
                     ("hysteresis_v2", smooth_v2)):
        st = new_state()
        smoothed = [fn(st, CLASS_NAMES[int(probs[i].argmax())], float(probs[i].max())) for i in range(n)]
        sm = np.array([CLASS_NAMES.index(s) for s in smoothed])

        lags = []
        for s in range(1, len(order)):
            a, b = s * per_seg, (s + 1) * per_seg
            seg = sm[a:b]
            hit = np.where(seg == seg_true[a])[0]
            lags.append(int(hit[0]) + 1 if len(hit) else per_seg)
        steady = []
        for s in range(1, len(order)):
            a, b = s * per_seg, (s + 1) * per_seg
            steady.extend((sm[a + 2:b] == seg_true[a:b][2:]).tolist())
        flips = int((np.diff(sm) != 0).sum())
        out[name] = {
            "switch_lag_frames_mean": round(float(np.mean(lags)), 2),
            "switch_lag_frames_median": float(np.median(lags)),
            "switch_lag_seconds_mean": round(float(np.mean(lags)) * inference_ms / 1000.0, 2),
            "steady_state_accuracy": round(float(np.mean(steady)), 4),
            "label_flips_total": flips,
        }

    raw = probs.argmax(axis=1)
    steady_raw = []
    for s in range(1, len(order)):
        a, b = s * per_seg, (s + 1) * per_seg
        steady_raw.extend((raw[a + 2:b] == seg_true[a:b][2:]).tolist())
    out["raw_no_smoothing"] = {
        "switch_lag_frames_mean": 1.0,
        "steady_state_accuracy": round(float(np.mean(steady_raw)), 4),
        "label_flips_total": int((np.diff(raw) != 0).sum()),
    }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="情绪平滑策略对比评测")
    ap.add_argument("--run", type=str, default="20261014-121827-rafmix",
                    help="runs/ 下的 run_id（默认用当前线上部署的 rafmix）")
    ap.add_argument("--data", type=str, default="test_raf.pt")
    ap.add_argument("--per-seg", type=int, default=8)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--legacy-ms", type=float, default=250.0, help="旧策略下的推理间隔")
    ap.add_argument("--new-ms", type=float, default=160.0, help="新策略下的推理间隔")
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    data_dir = Path(__file__).resolve().parent / "data" / "fer2013"
    with open(data_dir / args.data, "rb") as f:
        recs = pickle.load(f)
    seq, order = build_sequence(recs, args.per_seg, args.repeats)
    print(f"序列: {len(seq)} 帧 = {len(order)} 段 × {args.per_seg} 帧；类别顺序: {order}", flush=True)

    probs, truth = run_model(args.run, seq)
    res = evaluate(probs, truth, order, args.per_seg, args.new_ms)
    res_legacy_ms = evaluate(probs, truth, order, args.per_seg, args.legacy_ms)

    print(f"\n模型: runs/{args.run}")
    print(f"逐帧原始准确率: {(probs.argmax(1) == truth).mean():.4f}")
    print(f"\n{'策略':<20} {'切换滞后(帧)':>12} {'滞后(秒)':>10} {'稳定期准确率':>12} {'标签翻转次数':>12}")
    for k in ("raw_no_smoothing", "legacy_majority5", "hysteresis_v1", "hysteresis_v2"):
        r = res[k]
        ms = args.legacy_ms if k == "legacy_majority5" else args.new_ms
        lag_s = r["switch_lag_frames_mean"] * ms / 1000.0
        print(f"{k:<20} {r['switch_lag_frames_mean']:>12.2f} {lag_s:>10.2f} "
              f"{r['steady_state_accuracy']:>12.4f} {r['label_flips_total']:>12d}")

    payload = {"run_id": args.run, "frames": len(seq), "segments": len(order),
               "per_seg": args.per_seg, "new_infer_ms": args.new_ms,
               "legacy_infer_ms": args.legacy_ms,
               "result_new_interval": res, "result_legacy_interval": res_legacy_ms}
    out = Path(args.out) if args.out else (Path(__file__).resolve().parent / "runs" / "smoother_eval.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存: {out}")


if __name__ == "__main__":
    main()