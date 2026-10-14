"""真实浏览器端到端实测：子进程启动 Edge，跑生产链路跑的表情检测。

为什么不用 Playwright：本机沙箱不允许 Playwright 的 Node 驱动创建临时目录（EPERM）。
因此改为
  1) 以普通子进程方式启动 Edge（系统自带，无需下载浏览器）；
  2) 探针页把逐帧采样与画面截图 POST 回本脚本起的本地 HTTP 服务；
  3) 由本脚本完成对齐与准确率计算。
链路本身仍是真实的：getUserMedia -> tinyFaceDetector -> 裁剪 -> ONNX + TTA。

两种模式：
  file     伪摄像头：--use-file-for-fake-video-capture 喂 Y4M 视频，画面与时间轴已知，
           因此可算**端到端准确率**（含人脸检测与裁剪环节）。
  realtime 真实摄像头：不伪造画面，直接用本机摄像头，确认真实硬件上链路可跑通。

用法（在 backend 目录下）：
  python -m ml.e2e_emotion --mode file --y4m <file.y4m> --schedule <schedule.json>
  python -m ml.e2e_emotion --mode realtime --seconds 25
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import socket
import subprocess
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image

RUNS_DIR = Path(__file__).resolve().parent / "runs"
DEFAULT_URL = "http://localhost:5173/e2e/emotion-probe.html"
WORK = Path(r"c:\Users\29199\.trae-cn\work\6ace07c7090f3196aeac65f3")
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


class Collector:
    """收集探针页回传的状态、采样与画面。"""

    def __init__(self) -> None:
        self.status: dict = {}
        self.samples: list[dict] = []
        self.shots: list[tuple[float, Image.Image]] = []
        self.done: dict | None = None
        self.console: list[dict] = []
        self.lock = threading.Lock()

    def handle(self, path: str, payload: dict) -> None:
        with self.lock:
            if path.endswith("/status"):
                self.status = payload
            elif path.endswith("/samples"):
                self.status = {"status": payload.get("status"), "error": payload.get("error"),
                                "videoSize": payload.get("videoSize"), "total": payload.get("total"),
                                "detectorBackend": payload.get("detectorBackend")}
                # 探针页按"新增"增量回传，这里累加，避免只保留末尾若干条
                self.samples.extend(payload.get("fresh") or [])
            elif path.endswith("/shot"):
                b64 = payload.get("jpeg") or ""
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                try:
                    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
                    self.shots.append((float(payload.get("t") or 0.0), img))
                except Exception:  # noqa: BLE001
                    pass
            elif path.endswith("/console"):
                self.console.append(payload)
                if len(self.console) > 200:
                    self.console = self.console[-200:]
            elif path.endswith("/done"):
                self.done = payload


def start_server(collector: Collector) -> tuple[ThreadingHTTPServer, int]:
    class Handler(BaseHTTPRequestHandler):
        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:  # noqa: BLE001
                payload = {}
            collector.handle(self.path, payload if isinstance(payload, dict) else {})
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a) -> None:  # 静默
            return

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def find_edge() -> str:
    for p in EDGE_CANDIDATES:
        if Path(p).exists():
            return p
    raise SystemExit("未找到 Edge")


def edge_args(mode: str, y4m: str, profile: Path, url: str, headless: bool) -> list[str]:
    args = [
        f"--user-data-dir={profile}",
        "--no-first-run", "--no-default-browser-check",
        "--use-fake-ui-for-media-stream",
        "--autoplay-policy=no-user-gesture-required",
        "--window-size=1000,820",
        "--disable-features=Translate,msEdgeIdentityFeature",
    ]
    if headless:
        args.append("--headless=new")
        args += ["--disable-gpu", "--use-gl=swiftshader", "--enable-unsafe-swiftshader"]
    if mode == "file":
        args += [
            "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-video-capture={y4m}",
        ]
    args.append(url)
    return args


def analyze(samples: list[dict], sched: dict, guard: float) -> dict:
    ts = [s["t"] for s in samples]
    use_video_t = bool(ts) and (max(ts) - min(ts)) > 5.0
    axis = "video.currentTime" if use_video_t else "wall-clock(ms from camera start)"
    key = "t" if use_video_t else "wt"
    scale = 1.0 if use_video_t else 1000.0

    faces = sched["faces"]
    duration = float(sched["duration_sec"])

    total = correct = 0
    per_class: dict[str, list[int]] = {}
    covered: Counter = Counter()
    for s in samples:
        raw = float(s[key]) / scale
        # 只用视频第一轮循环内的时间：Y4M 会循环播放，长跑会因播放速率微小偏差累积漂移
        if raw >= duration:
            continue
        sec = raw % duration
        hit = None
        for f in faces:
            if f["start"] + guard <= sec < f["end"] - guard:
                hit = f
                break
        if hit is None:
            continue
        total += 1
        ok = s["emotion"] == hit["label"]
        correct += int(ok)
        covered[hit["index"]] += 1
        st = per_class.setdefault(hit["label"], [0, 0])
        st[0] += 1
        st[1] += int(ok)

    return {
        "timeline_used": axis,
        "samples_total": len(samples),
        "samples_matched": total,
        "end_to_end_accuracy": round(correct / total, 4) if total else None,
        "correct": correct,
        "faces_total": len(faces),
        "faces_with_samples": len(covered),
        "face_coverage": round(len(covered) / len(faces), 4),
        "per_class": {k: {"n": v[0], "acc": round(v[1] / v[0], 4) if v[0] else None}
                      for k, v in sorted(per_class.items())},
        "guard_sec": guard,
    }


def save_shot_grid(shots: list[tuple[float, Image.Image]], out: Path) -> str | None:
    if not shots:
        return None
    picks = shots if len(shots) <= 8 else [shots[i] for i in
                                           (0, len(shots) // 7, 2 * len(shots) // 7, 3 * len(shots) // 7,
                                            4 * len(shots) // 7, 5 * len(shots) // 7, 6 * len(shots) // 7,
                                            len(shots) - 1)]
    w, h = picks[0][1].size
    cols, rows = 4, 2
    grid = Image.new("RGB", (w * cols, h * rows), (20, 20, 20))
    for i, (_t, im) in enumerate(picks[:8]):
        grid.paste(im, ((i % cols) * w, (i // cols) * h))
    grid.save(out, quality=92)
    return str(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Edge 真实浏览器端到端实测")
    ap.add_argument("--mode", choices=["file", "realtime"], default="file")
    ap.add_argument("--y4m", type=str, default=str(WORK / "fake_camera.y4m"))
    ap.add_argument("--schedule", type=str, default=str(WORK / "fake_camera_schedule.json"))
    ap.add_argument("--url", type=str, default=DEFAULT_URL)
    ap.add_argument("--seconds", type=float, default=0, help="最长等待秒数，0=自动")
    ap.add_argument("--loops", type=float, default=1.3, help="file 模式采集的视频循环数")
    ap.add_argument("--guard", type=float, default=0.8, help="每段前后忽略的秒数（平滑滞后）")
    ap.add_argument("--headed", action="store_true", help="显示浏览器窗口（默认无头）")
    ap.add_argument("--no-shots", action="store_true",
                    help="不回传画面（真实摄像头模式建议开启，避免把摄像头画面落盘）")
    ap.add_argument("--name", type=str, default="")
    args = ap.parse_args()

    sched = json.loads(Path(args.schedule).read_text("utf-8")) if args.mode == "file" else None
    duration = float(sched["duration_sec"]) if sched else (args.seconds or 25.0)
    budget = args.seconds or (duration * args.loops + 30)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-e2e-" + (args.name or args.mode)
    out_dir = RUNS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    edges = find_edge()
    collector = Collector()
    srv, port = start_server(collector)
    report_url = f"http://127.0.0.1:{port}"
    url = f"{args.url}?report={report_url}" + ("&shots=0" if args.no_shots else "")

    profile = WORK / f"edge-profile-{args.mode}"
    profile.mkdir(parents=True, exist_ok=True)
    cmd = [edges] + edge_args(args.mode, args.y4m, profile, url, headless=not args.headed)

    print(f"模式={args.mode}  时长={duration:.0f}s  预算={budget:.0f}s", flush=True)
    print(f"Edge={edges}", flush=True)
    print(f"回传服务={report_url}  浏览器窗口={'显示' if args.headed else '无头'}", flush=True)
    print("启动 Edge ...", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env={**os.environ, "TMPDIR": str(WORK / "pw-tmp"), "TEMP": str(WORK / "pw-tmp"),
                                 "TMP": str(WORK / "pw-tmp")})

    t0 = time.time()
    target = int(duration * args.loops * 9)
    try:
        while time.time() - t0 < budget:
            time.sleep(3)
            with collector.lock:
                n = len(collector.samples)
                st = collector.status.get("status")
                err = collector.status.get("error")
                vs = collector.status.get("videoSize")
                shots = len(collector.shots)
                fin = collector.done
            print(f"  [{time.time() - t0:5.0f}s] status={st} samples={n} shots={shots} "
                  f"video={vs} err={err or ''}", flush=True)
            if err:
                break
            if fin:
                break
            if args.mode == "file" and n >= target:
                break
    finally:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except Exception:  # noqa: BLE001
            proc.kill()
        srv.shutdown()

    shots_path = save_shot_grid(collector.shots, out_dir / f"e2e-{args.mode}-frames.jpg")
    report: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "browser_e2e_emotion",
        "mode": args.mode,
        "driver": "Edge subprocess + local HTTP collector（未使用 Playwright）",
        "url": args.url,
        "probe_status": collector.status,
        "samples": len(collector.samples),
        "shots": len(collector.shots),
        "frames_grid": shots_path,
        "emotion_distribution": dict(Counter(s["emotion"] for s in collector.samples)),
        "console": collector.console[-40:],
    }
    if args.mode == "file":
        report["fake_camera"] = {
            "y4m": args.y4m, "schedule": args.schedule, "duration_sec": duration,
            "video_mb": round(Path(args.y4m).stat().st_size / 1e6, 1) if Path(args.y4m).exists() else None,
        }
        report["result"] = analyze(collector.samples, sched, args.guard)

    (out_dir / "e2e_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "samples.json").write_text(json.dumps(collector.samples, ensure_ascii=False), encoding="utf-8")

    print("=" * 70)
    print(f"探针状态: {json.dumps(collector.status, ensure_ascii=False)}")
    print(f"采样 {len(collector.samples)} 条　画面 {len(collector.shots)} 帧")
    if args.mode == "file":
        r = report["result"]
        print(f"时间轴: {r['timeline_used']}")
        print(f"端到端准确率: {r['end_to_end_accuracy']}（{r['correct']}/{r['samples_matched']}）")
        print(f"人脸覆盖: {r['face_coverage']}（{r['faces_with_samples']}/{r['faces_total']}）")
        print("分类别:", json.dumps(r["per_class"], ensure_ascii=False))
    print("情绪分布:", json.dumps(report["emotion_distribution"], ensure_ascii=False))
    print("--- 浏览器控制台（末尾）---")
    for c in collector.console[-12:]:
        print(f"  {c.get('level')}: {str(c.get('text'))[:320]}")
    if shots_path:
        print(f"画面证据: {shots_path}")
    print(f"报告目录: {out_dir}")


if __name__ == "__main__":
    main()