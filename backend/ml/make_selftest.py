"""生成浏览器端 ONNX 推理自测页（frontend/public/emotion-selftest.html）。

目的：验证"浏览器里加载 ONNX Runtime Web + 跑通预处理 + 得到正确预测"这条链路。
页面把若干张 FER2013 测试人脸以 base64 内联（自包含，不需要额外图片文件），
用与前端 useEmotionDetection.ts 完全相同的预处理与推理方式逐张预测，
在页面上显示 预测 / 期望 / 是否正确 以及总体准确率。

用法（在 backend 目录下）：
  python -m ml.make_selftest --n 12
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import random
from pathlib import Path

from .architectures import CLASS_NAMES, CLASS_NAMES_CN
from .config import TrainingConfig
from .dataset import FER_LABEL_MAP, _load_split, ensure_dataset

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "emotion-selftest.html"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12, help="内联的测试张数（每类尽量均匀）")
    args = ap.parse_args()

    cfg = TrainingConfig()
    _, test_p = ensure_dataset(cfg)
    recs = _load_split(test_p)

    # 每个类别各取若干张，保证覆盖 7 类
    by_class: dict[int, list[dict]] = {}
    for r in recs:
        by_class.setdefault(FER_LABEL_MAP[r["labels"]], []).append(r)
    rng = random.Random(7)
    picked: list[dict] = []
    per = max(1, args.n // 7)
    for lab in range(7):
        pool = by_class.get(lab, [])
        rng.shuffle(pool)
        picked.extend(pool[:per])

    items = []
    for r in picked:
        from PIL import Image
        img = Image.open(io.BytesIO(r["img_bytes"])).convert("L")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        items.append({
            "src": f"data:image/png;base64,{b64}",
            "label": FER_LABEL_MAP[r["labels"]],
            "labelName": CLASS_NAMES[FER_LABEL_MAP[r["labels"]]],
            "labelCn": CLASS_NAMES_CN[FER_LABEL_MAP[r["labels"]]],
        })

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>浏览器端 ONNX 表情推理自测</title>
<style>
  body { font: 14px/1.6 system-ui, "Microsoft YaHei", sans-serif; margin: 24px; color: #171717; background: #f7f7f8; }
  h1 { font-size: 18px; }
  .meta { color: #52525b; margin-bottom: 16px; }
  table { border-collapse: collapse; background: #fff; }
  th, td { border: 1px solid #e4e4e7; padding: 6px 10px; text-align: left; }
  th { background: #fafafa; }
  .ok { color: #15803d; font-weight: 600; }
  .bad { color: #b91c1c; font-weight: 600; }
  #summary { margin: 16px 0; padding: 12px 16px; background: #fff; border-left: 3px solid #4b3fe3; }
  img { width: 48px; height: 48px; image-rendering: pixelated; }
  .hint { color: #71717a; font-size: 12px; }
</style>
</head>
<body>
<h1>浏览器端 ONNX 表情推理自测</h1>
<p class="meta">
  模型 <code>/models/emotion_strong64.onnx</code>　运行时 <code>/ort/</code>（ONNX Runtime Web 1.30.0, WASM, 单线程）<br>
  预处理与前端 <code>useEmotionDetection.ts</code> 完全一致：画布缩放 64×64 → 灰度 → x/255 → (x−0.5)/0.5 → 复制 3 通道 → CHW
</p>
<div id="summary">正在加载模型…</div>
<table>
  <thead><tr><th>#</th><th>人脸</th><th>期望</th><th>预测</th><th>置信度</th><th>Top-3</th><th>结果</th></tr></thead>
  <tbody id="rows"></tbody>
</table>
<p class="hint">说明：这是开发自测页，不参与业务功能；验证完成后可直接删除。</p>
<script type="module">
const ITEMS = __ITEMS__;
const CLASS_NAMES = __CLASS_NAMES__;
const CLASS_NAMES_CN = __CLASS_NAMES_CN__;
const SIZE = 64;

function log(msg, cls) {
  const el = document.getElementById('summary');
  el.innerHTML = cls ? `<span class="${cls}">${msg}</span>` : msg;
}

async function main() {
  try {
    const ort = await import('/ort/ort.wasm.min.mjs');
    ort.env.wasm.wasmPaths = '/ort/';
    ort.env.wasm.numThreads = 1;
    ort.env.logLevel = 'error';
    const session = await ort.InferenceSession.create('/models/emotion_se64_improved.onnx', { executionProviders: ['wasm'] });
    log('模型已加载，开始推理…');

    const canvas = document.createElement('canvas');
    canvas.width = SIZE; canvas.height = SIZE;
    const ctx = canvas.getContext('2d');
    const tbody = document.getElementById('rows');
    let ok = 0;

    for (let i = 0; i < ITEMS.length; i++) {
      const it = ITEMS[i];
      const img = new Image();
      img.src = it.src;
      await img.decode();
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(img, 0, 0, SIZE, SIZE);

      const { data } = ctx.getImageData(0, 0, SIZE, SIZE);
      const area = SIZE * SIZE;
      const input = new Float32Array(3 * area);
      const flip = new Float32Array(3 * area);
      for (let y = 0; y < SIZE; y++) {
        for (let x = 0; x < SIZE; x++) {
          const p = y * SIZE + x;
          const r = data[p * 4], g = data[p * 4 + 1], b = data[p * 4 + 2];
          const gray = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
          const v = (gray - 0.5) / 0.5;
          input[p] = v; input[area + p] = v; input[2 * area + p] = v;
          const fp = y * SIZE + (SIZE - 1 - x);
          flip[fp] = v; flip[area + fp] = v; flip[2 * area + fp] = v;
        }
      }
      const [oa, ob] = await Promise.all([
        session.run({ input: new ort.Tensor('float32', input, [1, 3, SIZE, SIZE]) }),
        session.run({ input: new ort.Tensor('float32', flip, [1, 3, SIZE, SIZE]) }),
      ]);
      const logits = new Float32Array(oa.logits.data.length);
      for (let i = 0; i < logits.length; i++) logits[i] = 0.5 * (oa.logits.data[i] + ob.logits.data[i]);
      const mx = Math.max(...logits);
      const exps = Array.from(logits, (x) => Math.exp(x - mx));
      const sum = exps.reduce((a, b) => a + b, 0);
      const probs = exps.map((x) => x / sum);
      const order = probs.map((p, idx) => [p, idx]).sort((a, b) => b[0] - a[0]);
      const best = order[0][1];
      const pass = best === it.label;
      if (pass) ok++;
      const top3 = order.slice(0, 3).map(([p, idx]) => `${CLASS_NAMES[idx]}:${p.toFixed(2)}`).join(', ');

      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${i + 1}</td>
        <td><img src="${it.src}" alt=""></td>
        <td>${it.labelName} / ${it.labelCn}</td>
        <td>${CLASS_NAMES[best]}</td>
        <td>${probs[best].toFixed(3)}</td>
        <td class="hint">${top3}</td>
        <td class="${pass ? 'ok' : 'bad'}">${pass ? '正确' : '错误'}</td>`;
      tbody.appendChild(tr);
    }
    const acc = ok / ITEMS.length;
    log(`自测完成：${ok}/${ITEMS.length} 正确，准确率 <b>${(acc * 100).toFixed(1)}%</b>` +
        `（样本少，仅用于验证链路是否跑通，不代表模型精度）`, acc >= 0.6 ? 'ok' : 'bad');
  } catch (e) {
    log('自测失败：' + (e && e.message ? e.message : e), 'bad');
    console.error(e);
  }
}
main();
</script>
</body>
</html>
"""
    html = (html.replace("__ITEMS__", json.dumps(items, ensure_ascii=False))
                .replace("__CLASS_NAMES__", json.dumps(list(CLASS_NAMES)))
                .replace("__CLASS_NAMES_CN__", json.dumps(list(CLASS_NAMES_CN))))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"已生成自测页: {OUT}（内联 {len(items)} 张测试人脸，覆盖 {len(set(i['label'] for i in items))} 类）")


if __name__ == "__main__":
    main()