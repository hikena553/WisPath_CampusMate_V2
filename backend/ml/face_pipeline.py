"""打通"YOLOv8 检测人脸 -> 裁剪 -> 表情分类"链路，并对其正确性做验证。

流程（与前端部署链路一致）：
  1) YOLOv8n 单类检测器在一帧里找到人脸框（取置信度最高的"主要目标人脸"）；
  2) 以框中心做方形补边裁剪，缩放到表情模型输入尺寸；
  3) 灰度化并按训练口径归一化，送入表情分类模型；
  4) 输出 7 类概率与中文标签。

验证内容：
  - 检测质量：在合成的 val 集上跑 ultralytics 官方 val，报告 mAP50 / mAP50-95 / 精确率 / 召回率；
  - 分类正确性：把 FER2013 测试集人脸贴到随机背景上，走完整链路看表情识别是否仍准确；
  - 可视化：输出带检测框与表情标签的样张，便于人工核对。

用法（在 backend 目录下）：
  python -m ml.face_pipeline --det ml/runs/yolo-face/weights/best.pt --expr-run 20261013-130843-strong64
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw

from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .backbones import build_model
from .config import RUNS_DIR, TrainingConfig
from .dataset import FER_LABEL_MAP, _load_split, ensure_dataset
from .face_detect_data import OUT_ROOT, _random_background

SHOW_DIR = Path(__file__).resolve().parent / "runs" / "face-pipeline"


def load_expression_model(run_id: str, device: torch.device):
    run_dir = RUNS_DIR / run_id
    cfg = TrainingConfig.load(run_dir / "config.json")
    model = build_model(cfg.model_name, num_classes=cfg.num_classes, pretrained=False,
                        dropout=cfg.dropout, width_mult=cfg.width_mult,
                        use_se=cfg.use_se, se_ratio=cfg.se_ratio).to(device)
    ckpt = torch.load(run_dir / "best_model.pt", map_location=device)
    state = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()
    return model, cfg


def crop_square(img: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    """按检测框做方形补边裁剪（与前端 cropFace 的几何逻辑一致）。"""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    side = max(w, h)
    cx, cy = x0 + w / 2, y0 + h / 2
    nx0, ny0 = cx - side / 2, cy - side / 2
    return img.crop((int(round(nx0)), int(round(ny0)), int(round(nx0 + side)), int(round(ny0 + side))))


def preprocess(crop: Image.Image, size: int, imagenet_norm: bool = False) -> torch.Tensor:
    g = crop.convert("L").resize((size, size), Image.BILINEAR)
    arr = np.asarray(g, dtype=np.float32) / 255.0
    if imagenet_norm:
        arr = np.repeat(arr[None, :, :], 3, axis=0)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)[:, None, None]
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)[:, None, None]
        return torch.from_numpy((arr - mean) / std)
    arr = (arr - 0.5) / 0.5
    return torch.from_numpy(np.repeat(arr[None, :, :], 3, axis=0))


@torch.no_grad()
def classify(model, cfg: TrainingConfig, crop: Image.Image, device: torch.device) -> tuple[str, float, np.ndarray]:
    x = preprocess(crop, cfg.input_size, cfg.imagenet_norm)[None].to(device)
    logits = model(x)
    probs = torch.softmax(logits.float(), dim=1)[0].cpu().numpy()
    i = int(probs.argmax())
    return CLASS_NAMES[i], float(probs[i]), probs


def main() -> None:
    ap = argparse.ArgumentParser(description="YOLOv8 检测 + 表情分类链路")
    ap.add_argument("--det", type=str, default="ml/runs/yolo-face/weights/best.pt")
    ap.add_argument("--expr-run", type=str, default="20261013-130843-strong64")
    ap.add_argument("--samples", type=int, default=300, help="分类链路抽样验证张数")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--data", type=str, default="",
                    help="检测 val 用的 dataset.yaml；留空则用合成集")
    ap.add_argument("--imgsz-det", type=int, default=320, help="检测推理尺寸")
    ap.add_argument("--device", type=str, default="auto", help="auto|cuda|cpu")
    args = ap.parse_args()

    device = torch.device("cuda" if (args.device in ("auto", "cuda") and torch.cuda.is_available())
                          else "cpu")
    det_device = 0 if device.type == "cuda" else "cpu"
    det_path = Path(args.det)
    if not det_path.is_absolute():
        det_path = Path(__file__).resolve().parent.parent / det_path
    if not det_path.exists():
        raise SystemExit(f"检测器权重不存在：{det_path}，请先运行 ml.train_yolo_face")

    from ultralytics import YOLO
    detector = YOLO(str(det_path))

    print("=" * 70)
    val_yaml = Path(args.data) if args.data else (OUT_ROOT / "dataset.yaml")
    print(f"步骤 1/3：检测器质量评估（{val_yaml.parent.name}，ultralytics 官方 val）")
    metrics = detector.val(data=str(val_yaml), imgsz=args.imgsz_det, device=det_device,
                           workers=0, plots=False, verbose=False)
    box = metrics.box
    print(f"  mAP50={box.map50:.4f} | mAP50-95={box.map:.4f} | "
          f"precision={box.mp:.4f} | recall={box.mr:.4f}")

    print("=" * 70)
    print("步骤 2/3：检测 -> 裁剪 -> 表情分类 全链路验证")
    expr_model, cfg = load_expression_model(args.expr_run, device)
    print(f"  表情模型：{args.expr_run}（{cfg.model_name}, 输入 {cfg.input_size}）")

    random.seed(7)
    np.random.seed(7)
    _, test_p = ensure_dataset(cfg)
    test_recs = _load_split(test_p)
    random.shuffle(test_recs)
    test_recs = test_recs[: args.samples]

    n_ok = n_det = n_expr_ok = 0
    show_samples = []
    for idx, rec in enumerate(test_recs):
        face = Image.open(__import__("io").BytesIO(rec["img_bytes"])).convert("L")
        gt_label = FER_LABEL_MAP[rec["labels"]]
        # 合成一帧 320×240：人脸贴在随机位置
        canvas = _random_background(320, 240).convert("RGB")
        fh = int(240 * random.uniform(0.3, 0.5))
        cx = random.randint(fh, 320 - fh)
        cy = random.randint(fh, 240 - fh)
        # paste 的坐标是左上角，因此人脸实际占据 [cx-fh/2, cx+fh/2] × [cy-fh/2, cy+fh/2]
        canvas.paste(face.convert("RGB").resize((fh, fh), Image.BILINEAR),
                     (cx - fh // 2, cy - fh // 2))
        gt_box = (cx - fh / 2, cy - fh / 2, cx + fh / 2, cy + fh / 2)

        res = detector.predict(canvas, imgsz=args.imgsz_det, conf=args.conf, device=det_device,
                               verbose=False)[0]
        n_ok += 1
        if len(res.boxes) == 0:
            continue
        # 取置信度最高的框作为"主要目标人脸"
        confs = res.boxes.conf.cpu().numpy()
        best = int(confs.argmax())
        xyxy = res.boxes.xyxy.cpu().numpy()[best]
        det_box = (float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3]))
        # IoU（相对贴图位置）
        ix0, iy0 = max(gt_box[0], det_box[0]), max(gt_box[1], det_box[1])
        ix1, iy1 = min(gt_box[2], det_box[2]), min(gt_box[3], det_box[3])
        inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
        union = (gt_box[2] - gt_box[0]) * (gt_box[3] - gt_box[1]) + \
                (det_box[2] - det_box[0]) * (det_box[3] - det_box[1]) - inter
        iou = inter / union if union > 0 else 0.0
        if iou < 0.3:
            continue
        n_det += 1
        crop = crop_square(canvas, det_box)
        emo, p, _ = classify(expr_model, cfg, crop, device)
        if CLASS_NAMES.index(emo) == gt_label:
            n_expr_ok += 1
        if len(show_samples) < 8:
            vis = canvas.copy()
            d = ImageDraw.Draw(vis)
            d.rectangle([det_box[0], det_box[1], det_box[2], det_box[3]], outline=(255, 60, 60), width=2)
            d.text((max(2, det_box[0]), max(2, det_box[1] - 12)),
                   f"{emo} {p:.2f} | gt:{CLASS_NAMES[gt_label]}", fill=(255, 220, 0))
            show_samples.append(vis)

    hit = n_det / max(1, n_ok)
    expr_acc = n_expr_ok / max(1, n_det)
    print(f"  检测命中率（IoU>=0.3）: {hit:.4f}  ({n_det}/{n_ok})")
    print(f"  链路表情准确率: {expr_acc:.4f}  ({n_expr_ok}/{n_det})")

    print("=" * 70)
    print("步骤 3/3：保存可视化样张")
    SHOW_DIR.mkdir(parents=True, exist_ok=True)
    grid = Image.new("RGB", (320 * 4, 240 * 2), (24, 24, 24))
    for i, im in enumerate(show_samples[:8]):
        grid.paste(im, ((i % 4) * 320, (i // 4) * 240))
    out = SHOW_DIR / "pipeline_samples.jpg"
    grid.save(out, quality=92)
    print(f"  已保存: {out}")

    (SHOW_DIR / "pipeline_report.txt").write_text(
        f"detector: {det_path}\n"
        f"mAP50={box.map50:.4f} mAP50-95={box.map:.4f} precision={box.mp:.4f} recall={box.mr:.4f}\n"
        f"expression_model: {args.expr_run} ({cfg.model_name}, input {cfg.input_size})\n"
        f"detection_hit_rate_iou30: {hit:.4f} ({n_det}/{n_ok})\n"
        f"chain_expression_accuracy: {expr_acc:.4f} ({n_expr_ok}/{n_det})\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()