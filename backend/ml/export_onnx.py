"""把最优单模型导出为 ONNX（供前端 onnxruntime-web 推理），并做双重验证。

验证内容：
1. 数值一致性：PyTorch 与 ONNX Runtime 在同一批输入上的 logits 最大绝对误差；
2. 精度一致性：ONNX 模型在 FER2013 测试集上的准确率/Top-2/Macro-F1（应与 PyTorch 对齐）。

预处理必须与训练严格一致（ml/dataset.py）：
  灰度图 -> size×size -> x/255 -> (x-0.5)/0.5 -> 复制为 3 通道 -> CHW

用法（在 backend 目录下）：
  python -m ml.export_onnx --run 20261013-130843-strong64
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .backbones import build_model
from .config import RUNS_DIR, TrainingConfig
from .dataset import FER_LABEL_MAP, _base_image, _load_split, ensure_dataset
from .metrics import evaluate_predictions

FRONTEND_MODELS = Path(__file__).resolve().parents[2] / "frontend" / "public" / "models"


def _preprocess(records: list[dict], size: int) -> np.ndarray:
    """与训练预处理严格一致：[-1,1] 归一化 + 灰度复制 3 通道。"""
    arr = np.stack([
        np.asarray(_base_image(r["img_bytes"], size), dtype=np.float32) for r in records
    ]) / 255.0
    arr = (arr - 0.5) / 0.5
    return np.repeat(arr[:, None, :, :], 3, axis=1).astype(np.float32)


def main() -> None:
    p = argparse.ArgumentParser(description="导出 ONNX 并验证")
    p.add_argument("--run", required=True, help="run_id（runs/ 下的目录名）")
    p.add_argument("--out", default="", help="输出路径，默认 frontend/public/models/emotion_strong64.onnx")
    args = p.parse_args()

    run_dir = RUNS_DIR / args.run
    cfg = TrainingConfig.load(run_dir / "config.json")
    size = cfg.input_size
    out_path = Path(args.out) if args.out else FRONTEND_MODELS / "emotion_strong64.onnx"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ---------- 构建模型并载入权重 ----------
    model = build_model(cfg.model_name, num_classes=cfg.num_classes, pretrained=False,
                        dropout=cfg.dropout, width_mult=cfg.width_mult,
                        use_se=cfg.use_se, se_ratio=cfg.se_ratio)
    ckpt = torch.load(run_dir / "best_model.pt", map_location="cpu")
    state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()
    n_params = sum(p.numel() for p in model.parameters())
    print(f"模型: {cfg.model_name} | 输入: 3×{size}×{size} | 参数量: {n_params:,}", flush=True)

    # ---------- 导出 ONNX ----------
    dummy = torch.zeros(1, 3, size, size)
    torch.onnx.export(
        model, dummy, str(out_path),
        input_names=["input"], output_names=["logits"],
        opset_version=17, do_constant_folding=True,
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        dynamo=False,  # 使用经典 TorchScript 导出器，避免额外依赖 onnxscript
    )
    print(f"已导出: {out_path} ({out_path.stat().st_size:,} 字节)", flush=True)

    # ---------- 验证 1/2：数值一致性 + 测试集精度 ----------
    _, test_p = ensure_dataset(cfg)
    records = _load_split(test_p)
    X = _preprocess(records, size)
    y = np.array([FER_LABEL_MAP[r["labels"]] for r in records], dtype=np.int64)
    with torch.no_grad():
        logits_torch = model(torch.from_numpy(X[:256])).numpy()

    # 下面两步依赖 onnxruntime；该环境未安装时优雅跳过（ONNX 文件本身已导出成功），
    # 目标环境可用 `pip install onnxruntime` 后再跑同一命令完成校验。
    result = None
    max_diff = None
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(out_path), providers=["CPUExecutionProvider"])
        logits_onnx = sess.run(["logits"], {"input": X[:256]})[0]
        max_diff = float(np.abs(logits_torch - logits_onnx).max())
        print(f"数值一致性: 前 256 张的 logits 最大绝对误差 = {max_diff:.3e}", flush=True)

        probs_all = []
        for i in range(0, len(X), 512):
            out = sess.run(["logits"], {"input": X[i:i + 512]})[0]
            e = np.exp(out - out.max(axis=1, keepdims=True))
            probs_all.append(e / e.sum(axis=1, keepdims=True))
        probs = np.concatenate(probs_all)
        result = evaluate_predictions(probs, y, CLASS_NAMES)
        result["class_names_cn"] = CLASS_NAMES_CN
        print(f"ONNX 测试集: 准确率 {result['accuracy']:.4f} | Top-2 {result['top2_accuracy']:.4f} "
              f"| Top-3 {result['top3_accuracy']:.4f} | Macro-F1 {result['macro_f1']:.4f}", flush=True)
    except ImportError:
        print("跳过 ONNX 校验：当前环境未安装 onnxruntime（ONNX 文件已正常导出）", flush=True)

    # ---------- 与训练时记录的指标比对 ----------
    ref = json.loads((run_dir / "metrics.json").read_text("utf-8"))
    print(f"训练记录(TTA): 准确率 {ref['test']['accuracy']:.4f}（本次 ONNX 无 TTA，略低属正常）", flush=True)

    meta = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_run": args.run,
        "onnx_path": str(out_path),
        "onnx_bytes": out_path.stat().st_size,
        "params": int(n_params),
        "input": f"1x3x{size}x{size} float32",
        "preprocess": "gray->size->x/255->(x-0.5)/0.5->repeat 3ch->CHW（与训练一致）",
        "output": "logits(7) 顺序 = " + ",".join(CLASS_NAMES),
        "max_logit_diff_first256": max_diff,
        "test_accuracy_no_tta": result["accuracy"] if result else None,
        "test_top2_no_tta": result["top2_accuracy"] if result else None,
        "test_macro_f1_no_tta": result["macro_f1"] if result else None,
        "verified_with_onnxruntime": result is not None,
        "train_record_accuracy_with_tta": ref["test"]["accuracy"],
    }
    (run_dir / "onnx_export.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"验证报告: {run_dir / 'onnx_export.json'}", flush=True)


if __name__ == "__main__":
    main()