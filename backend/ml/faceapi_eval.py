"""在同一个 FER2013 测试集上评测前端 face-api.js 的 faceExpressionNet。

目的：回答"接入的模型 vs 我们训练的模型，谁更好"——必须在同口径下比较。

复现依据（全部来自本地依赖 face-api.js 0.22.2 的源码，非猜测）：
- build/es6/faceFeatureExtractor/FaceFeatureExtractor.js
    输入 112×112；归一化 (x - [122.782, 117.001, 104.298]) / 255；
    denseBlock4 ×4（stride 2）后 avgPool([7,7],[2,2],'valid') → 1×1×256
- build/es6/faceFeatureExtractor/denseBlock.js
    DenseNet 式残差相加：out = relu(out1+out2+out3+out4)，其中 conv0 做下采样、conv1..3 stride 1
- build/es6/common/depthwiseSeparableConv.js
    tf.separableConv2d(dw, pw, stride, 'same') + bias
- build/es6/common/fullyConnectedLayer.js + FaceProcessor.js
    flatten → fc(256→7)（tf.matMul(x, W)）→ softmax
- 权重：face_expression_model-weights_manifest.json + shard1，
    按 manifest 顺序读取，量化权重 value = quantized * scale + min，未量化权重为 float32。

用法（在 backend 目录下）：
  python -m ml.faceapi_eval
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from . import artifacts
from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .config import RUNS_DIR, TrainingConfig
from .dataset import FER_LABEL_MAP, _base_image, _load_split, ensure_dataset
from .metrics import classification_report_text, evaluate_predictions

MODEL_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "models"
MEAN_RGB = (122.782, 117.001, 104.298)
INPUT_SIZE = 112

# face-api.js 输出通道顺序（FaceExpressions.js 的 FACE_EXPRESSION_LABELS），
# 与本项目 CLASS_NAMES 不同，必须重排后才能比较。
FACEAPI_LABELS = ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"]
FACEAPI_TO_OURS = [FACEAPI_LABELS.index(n) for n in CLASS_NAMES]  # -> [3,5,4,1,0,2,6]

# TF 'same' 填充：pad_total 的额外部分放在后面（与 PyTorch 对称 padding 不同）
def _pad_same(x: torch.Tensor, k: int, stride: int) -> torch.Tensor:
    n = x.shape[-1]
    out = math.ceil(n / stride)
    total = max((out - 1) * stride + k - n, 0)
    before = total // 2
    after = total - before
    return F.pad(x, (before, after, before, after)) if total else x


def _conv_same(x, w, b, stride):
    return F.conv2d(_pad_same(x, w.shape[2], stride), w, b, stride=stride)


def _sep_same(x, dw, pw, b, stride):
    """深度可分离卷积：depthwise(stride) + pointwise(1) + bias。"""
    x = F.conv2d(_pad_same(x, dw.shape[2], stride), dw, stride=stride, groups=dw.shape[0])
    x = F.conv2d(x, pw)
    return x + b.view(1, -1, 1, 1)


def _dense_block4(x, p, is_first):
    if is_first:
        out1 = F.relu(_conv_same(x, p["conv0.filters"], p["conv0.bias"], 2))
    else:
        out1 = F.relu(_sep_same(x, p["conv0.dw"], p["conv0.pw"], p["conv0.bias"], 2))
    out2 = _sep_same(out1, p["conv1.dw"], p["conv1.pw"], p["conv1.bias"], 1)
    in3 = F.relu(out1 + out2)
    out3 = _sep_same(in3, p["conv2.dw"], p["conv2.pw"], p["conv2.bias"], 1)
    in4 = F.relu(out1 + out2 + out3)
    out4 = _sep_same(in4, p["conv3.dw"], p["conv3.pw"], p["conv3.bias"], 1)
    return F.relu(out1 + out2 + out3 + out4)


def load_faceapi_weights(model_dir: Path = MODEL_DIR) -> dict[str, np.ndarray]:
    """按 manifest 顺序反量化 shard，返回 {name: ndarray}。"""
    manifest = json.loads((model_dir / "face_expression_model-weights_manifest.json").read_text("utf-8"))
    entries = manifest[0]["weights"]
    buf = (model_dir / "face_expression_model-shard1").read_bytes()

    out: dict[str, np.ndarray] = {}
    offset = 0
    for w in entries:
        size = int(np.prod(w["shape"]))
        if "quantization" not in w and w["dtype"] == "float32":
            arr = np.frombuffer(buf, dtype="<f4", count=size, offset=offset).astype(np.float32)
            offset += size * 4
        else:
            q = np.frombuffer(buf, dtype=np.uint8, count=size, offset=offset).astype(np.float32)
            offset += size
            qc = w["quantization"]
            arr = q * float(qc["scale"]) + float(qc["min"])
        out[w["name"]] = arr.reshape(w["shape"])
    if offset != len(buf):
        raise ValueError(f"shard 解析长度不符：offset={offset} size={len(buf)}")
    return out


def _to(name: str, perm=None) -> torch.Tensor:
    t = torch.from_numpy(W[name]).clone()
    return t.permute(*perm).contiguous() if perm else t


def _pack_block(block: str, first_is_plain: bool) -> dict:
    p: dict[str, torch.Tensor] = {}
    if first_is_plain:
        # 首层是普通卷积 [kh,kw,in,out] -> [out,in,kh,kw]
        p["conv0.filters"] = _to(f"{block}/conv0/filters", (3, 2, 0, 1))
        p["conv0.bias"] = _to(f"{block}/conv0/bias")
    else:
        # 深度可分离：[3,3,C,1] -> [C,1,3,3]；[1,1,in,out] -> [out,in,1,1]
        p["conv0.dw"] = _to(f"{block}/conv0/depthwise_filter", (2, 3, 0, 1))
        p["conv0.pw"] = _to(f"{block}/conv0/pointwise_filter", (3, 2, 0, 1))
        p["conv0.bias"] = _to(f"{block}/conv0/bias")
    for c in ("conv1", "conv2", "conv3"):
        p[f"{c}.dw"] = _to(f"{block}/{c}/depthwise_filter", (2, 3, 0, 1))
        p[f"{c}.pw"] = _to(f"{block}/{c}/pointwise_filter", (3, 2, 0, 1))
        p[f"{c}.bias"] = _to(f"{block}/{c}/bias")
    return p


W: dict[str, np.ndarray] = {}
BLOCKS: dict[str, dict] = {}
FC_W: torch.Tensor | None = None
FC_B: torch.Tensor | None = None


def _faceapi_logits(x: torch.Tensor) -> torch.Tensor:
    out = _dense_block4(x, BLOCKS["dense0"], True)
    out = _dense_block4(out, BLOCKS["dense1"], False)
    out = _dense_block4(out, BLOCKS["dense2"], False)
    out = _dense_block4(out, BLOCKS["dense3"], False)
    out = F.avg_pool2d(out, 7, 2)
    out = out.flatten(1)
    return out @ FC_W + FC_B


@torch.no_grad()
def evaluate(records: list[dict], device: torch.device, batch_size: int = 256,
             tta: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """返回 (概率矩阵, 真实标签)。tta=True 时对原图与水平翻转图平均概率。"""
    imgs = np.stack([
        np.asarray(_base_image(r["img_bytes"], 48), dtype=np.float32) for r in records
    ])
    labels = np.array([FER_LABEL_MAP[r["labels"]] for r in records], dtype=np.int64)
    mean = torch.tensor(MEAN_RGB, dtype=torch.float32, device=device).view(1, 3, 1, 1)

    probs_all = []
    use_amp = device.type == "cuda"
    for i in range(0, len(imgs), batch_size):
        b = torch.from_numpy(imgs[i:i + batch_size]).to(device)[:, None]
        b = F.interpolate(b, size=(INPUT_SIZE, INPUT_SIZE), mode="bilinear", align_corners=False)
        b = b.repeat(1, 3, 1, 1)
        b = (b - mean) / 255.0
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            logits = _faceapi_logits(b)
            if tta:
                logits = 0.5 * (logits + _faceapi_logits(torch.flip(b, dims=[3])))
        probs_all.append(torch.softmax(logits.float(), dim=1).cpu().numpy()[:, FACEAPI_TO_OURS])
    return np.concatenate(probs_all), labels


def main() -> None:
    global W, BLOCKS, FC_W, FC_B
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    W = load_faceapi_weights()
    BLOCKS = {
        "dense0": _pack_block("dense0", True),
        "dense1": _pack_block("dense1", False),
        "dense2": _pack_block("dense2", False),
        "dense3": _pack_block("dense3", False),
    }
    FC_W = _to("fc/weights")          # [256,7]，对应 tf.matMul(x, W)
    FC_B = _to("fc/bias")
    for p in BLOCKS.values():
        for k in list(p):
            p[k] = p[k].to(device)
    FC_W, FC_B = FC_W.to(device), FC_B.to(device)

    n_params = int(sum(int(np.prod(v.shape)) for v in W.values()))
    shard_bytes = (MODEL_DIR / "face_expression_model-shard1").stat().st_size

    cfg = TrainingConfig()
    _, test_p = ensure_dataset(cfg)
    records = _load_split(test_p)
    print(f"设备: {device} | face-api 权重: {n_params:,} 参数 / {shard_bytes:,} 字节 | "
          f"测试集: {len(records)} 张 | 输入: {INPUT_SIZE}×{INPUT_SIZE}", flush=True)

    probs, labels = evaluate(records, device, tta=False)
    result = evaluate_predictions(probs, labels, CLASS_NAMES)
    print(f"[face-api 无 TTA] 准确率 {result['accuracy']:.4f} | Top-2 {result['top2_accuracy']:.4f} "
          f"| Top-3 {result['top3_accuracy']:.4f} | Macro-F1 {result['macro_f1']:.4f}", flush=True)

    probs_tta, _ = evaluate(records, device, tta=True)
    result_tta = evaluate_predictions(probs_tta, labels, CLASS_NAMES)
    print(f"[face-api + TTA] 准确率 {result_tta['accuracy']:.4f} | Top-2 {result_tta['top2_accuracy']:.4f} "
          f"| Macro-F1 {result_tta['macro_f1']:.4f}", flush=True)

    result["class_names_cn"] = CLASS_NAMES_CN
    result_tta["class_names_cn"] = CLASS_NAMES_CN

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-faceapi-eval"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts.plot_confusion_matrix(result["confusion_matrix"], CLASS_NAMES,
                                    run_dir / "confusion_matrix.png", normalize=False,
                                    title="face-api.js FaceExpressionNet (counts)")
    artifacts.plot_confusion_matrix(result["confusion_matrix"], CLASS_NAMES,
                                    run_dir / "confusion_matrix_normalized.png", normalize=True,
                                    title="face-api.js FaceExpressionNet (row-normalized)")
    (run_dir / "classification_report.txt").write_text(
        classification_report_text(result, CLASS_NAMES), encoding="utf-8")

    meta = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "external_model_eval",
        "model": "face-api.js FaceExpressionNet (前端已接入模型)",
        "source": "frontend/public/models/face_expression_model-shard1",
        "reproduction": "按 face-api.js 0.22.2 源码 1:1 复现到 PyTorch（见 ml/faceapi_eval.py 文件头）",
        "params": n_params,
        "shard_bytes": shard_bytes,
        "input_size": INPUT_SIZE,
        "preprocess": "(x - [122.782,117.001,104.298]) / 255（padToSquare -> resizeBilinear 112 -> 3 通道）",
        "test_samples": len(records),
        "result_no_tta": result,
        "result_tta": result_tta,
    }
    artifacts.save_json(meta, run_dir / "metrics.json")
    print(f"产物目录：{run_dir}", flush=True)


if __name__ == "__main__":
    main()