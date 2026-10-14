"""生成"伪摄像头"视频（Y4M）用于真实浏览器端到端实测。

原理：Chromium/Edge 支持 --use-file-for-fake-video-capture=<file.y4m>，
可把一段 Y4M 视频当作摄像头输入。这样浏览器里跑的是**真实链路**：
getUserMedia -> tinyFaceDetector -> 裁剪 -> ONNX 推理，而我们完全掌握
画面内容与时间轴，于是可以算出"端到端"（含人脸检测与裁剪环节）的准确率。

视频内容：把 FER2013 测试集人脸按顺序各显示若干秒，并记录每张脸的时间区间，
供对齐使用。人脸放大到约 160px，模拟真实摄像头中人脸在画面中的占比。

用法：
  python -m ml.fake_camera --out <file.y4m> --schedule <schedule.json> --per-face 3 --fps 5
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image

from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .config import TrainingConfig
from .dataset import FER_LABEL_MAP, _load_split, ensure_dataset

W, H = 320, 240


def _blank() -> Image.Image:
    """中灰背景，模拟摄像头画面底色。"""
    arr = np.full((H, W, 3), 96, dtype=np.uint8)
    arr += np.random.randint(0, 18, (H, W, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _compose(face: Image.Image, size: int = 160, keep_color: bool = False) -> Image.Image:
    canvas = _blank()
    f = (face if keep_color else face.convert("L").convert("RGB")).resize((size, size), Image.BILINEAR)
    x = (W - size) // 2
    y = (H - size) // 2 - 10
    canvas.paste(f, (x, max(0, y)))
    return canvas


def _frame_bytes(rgb: Image.Image) -> bytes:
    """RGB -> I420（Y 全分辨率，Cb/Cr 2×2 均值降采样）。"""
    arr = np.asarray(rgb.convert("YCbCr"))
    y = arr[:, :, 0].astype(np.uint8)
    cb = arr[:, :, 1].astype(np.float32).reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))
    cr = arr[:, :, 2].astype(np.float32).reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))
    return y.tobytes() + cb.astype(np.uint8).tobytes() + cr.astype(np.uint8).tobytes()


def main() -> None:
    ap = argparse.ArgumentParser(description="生成伪摄像头 Y4M 视频")
    ap.add_argument("--out", type=str, required=True)
    ap.add_argument("--schedule", type=str, required=True)
    ap.add_argument("--faces", type=int, default=14, help="人脸张数（每类尽量均匀）")
    ap.add_argument("--per-face", type=float, default=3.0, help="每张脸显示秒数")
    ap.add_argument("--fps", type=int, default=5)
    ap.add_argument("--source", choices=["fer", "rafdb"], default="fer",
                    help="fer=FER2013 实验室图；rafdb=RAF-DB 真实场景彩色人脸（更贴近真实摄像头）")
    args = ap.parse_args()

    cfg = TrainingConfig()
    keep_color = args.source == "rafdb"
    if args.source == "rafdb":
        _, test_p = ensure_dataset(cfg)
        raf_p = Path(cfg.data_dir) / "test_raf.pt"
        if not raf_p.exists():
            raise SystemExit(f"缺少真实场景测试集 {raf_p}，请先运行 python -m ml.real_fer")
        recs = _load_split(raf_p)
    else:
        _, test_p = ensure_dataset(cfg)
        recs = _load_split(test_p)

    by_class: dict[int, list[dict]] = {}
    for r in recs:
        by_class.setdefault(FER_LABEL_MAP[r["labels"]], []).append(r)
    rng = random.Random(20261014)
    per_class_picks: dict[int, list[dict]] = {}
    per = max(1, args.faces // 7)
    for lab in range(7):
        pool = list(by_class.get(lab, []))
        rng.shuffle(pool)
        per_class_picks[lab] = pool[:per]
    # 轮转交错排列：让相邻两张脸尽量属于不同类别。
    # 否则相邻同类别会让"平滑滞后"把上一张脸的标签带过来后仍然判对，
    # 从而虚高准确率；交错后得到的是更保守、更诚实的结果。
    picked: list[dict] = []
    for i in range(per):
        for lab in range(7):
            if i < len(per_class_picks.get(lab, [])):
                picked.append(per_class_picks[lab][i])
    while len(picked) < args.faces and len(recs) > len(picked):
        picked.append(rng.choice(recs))

    frames_per_face = int(round(args.per_face * args.fps))
    # 必须用"实际帧数换算出的秒数"写时间轴：per_face*fps 可能不是整数
    # （例如 2.5*5=12.5，round 后是 12 帧 = 2.4s）。若时间轴仍写 2.5s，
    # 累计到第 56 张脸会错位 5.6 秒（实测已复现），把正确预测判成错误。
    per_face_eff = frames_per_face / args.fps
    schedule = []
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "wb") as fh:
        fh.write(f"YUV4MPEG2 W{W} H{H} F{args.fps}:1 Ip A1:1 C420mpeg2\n".encode("ascii"))
        for i, rec in enumerate(picked):
            import io
            face = Image.open(io.BytesIO(rec["img_bytes"]))
            if not keep_color:
                face = face.convert("L")
            frame = _compose(face, keep_color=keep_color)
            payload = _frame_bytes(frame)
            for _ in range(frames_per_face):
                fh.write(b"FRAME\n")
                fh.write(payload)
            t0 = i * per_face_eff
            schedule.append({
                "index": i,
                "start": round(t0, 3),
                "end": round(t0 + per_face_eff, 3),
                "label": CLASS_NAMES[FER_LABEL_MAP[rec["labels"]]],
                "label_cn": CLASS_NAMES_CN[FER_LABEL_MAP[rec["labels"]]],
            })

    Path(args.schedule).write_text(json.dumps({
        "fps": args.fps,
        "per_face_sec": per_face_eff,
        "duration_sec": len(picked) * per_face_eff,
        "faces": schedule,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已生成 {out}（{out.stat().st_size / 1e6:.1f} MB，{len(picked)} 张脸，"
          f"每张 {per_face_eff}s（{frames_per_face} 帧 @ {args.fps}fps），总时长 {len(picked) * per_face_eff:.1f}s）")
    print(f"时间轴: {args.schedule}")
    from collections import Counter
    print("类别分布:", dict(Counter(s["label"] for s in schedule)))


if __name__ == "__main__":
    main()