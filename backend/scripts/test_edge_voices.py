"""Edge TTS 中文音色实测：逐个合成短句，验证音频可生成。

通过 /api/settings/tts/test 接口触发后端 synthesize_speech()，
按 Edge 音色走 Edge TTS 引擎，验证返回真实 PCM。
"""
from __future__ import annotations

import json
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

BACKEND_DIR = Path(r"D:\StudyNote\Mian02\backend")
PYTHON = r"D:\conda\envs\mianyang\python.exe"
BASE = "http://127.0.0.1:8000"
LOGIN = ("admin", "admin123")
RESULT_FILE = BACKEND_DIR / "scripts" / "edge_test_results.json"
INFO_FILE = BACKEND_DIR / "scripts" / "voice_info_dump.json"
LOG_FILE = BACKEND_DIR / "scripts" / "edge_test_output.log"


def wait_port(host: str, port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.5)
    return False


def kill_port(port: int) -> None:
    ps = (
        f"Get-NetTCPConnection -LocalPort {port} -State Listen "
        f"-ErrorAction SilentlyContinue | ForEach-Object "
        f"{{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)


def start_backend() -> subprocess.Popen:
    kill_port(8000)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    out_log = open(BACKEND_DIR / "logs" / "uvicorn.out.log", "wb")
    err_log = open(BACKEND_DIR / "logs" / "uvicorn.err.log", "wb")
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        stdout=out_log,
        stderr=err_log,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    print(f"backend pid={proc.pid}", flush=True)
    if not wait_port("127.0.0.1", 8000, timeout=60):
        proc.kill()
        raise RuntimeError("backend not ready")
    print("backend ready", flush=True)
    return proc


def main() -> int:
    proc = start_backend()
    try:
        csrf = {"X-Requested-With": "XMLHttpRequest"}
        with httpx.Client(timeout=30.0) as client:
            lr = client.post(f"{BASE}/api/auth/login", json={"username": LOGIN[0], "password": LOGIN[1]}, headers=csrf)
            lr.raise_for_status()
            token = lr.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}", **csrf}

            ir = client.get(f"{BASE}/api/settings/voice/info", headers=headers)
            ir.raise_for_status()
            info = ir.json()
            INFO_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

            # 收集 Edge 分组的所有 voice
            edge_voices: list[str] = []
            for g in info.get("voice_groups", []):
                if g.get("provider") == "edge":
                    for v in g.get("voices", []):
                        edge_voices.append(v["voice"])
            print(f"edge_voices={len(edge_voices)}", flush=True)

            results: list[dict] = []
            ok_count = 0
            for voice in edge_voices:
                entry = {"voice": voice, "provider": "edge", "status": 0, "ok": False, "size": 0, "detail": ""}
                try:
                    resp = client.post(
                        f"{BASE}/api/settings/tts/test",
                        json={"text": "你好，这是音色测试。", "voice": voice},
                        headers=headers,
                        timeout=30.0,
                    )
                    entry["status"] = resp.status_code
                    entry["size"] = len(resp.content)
                    if 200 <= resp.status_code < 300:
                        entry["ok"] = True
                        ok_count += 1
                    else:
                        try:
                            entry["detail"] = resp.text
                        except Exception:
                            entry["detail"] = str(resp.text)
                except Exception as e:
                    entry["detail"] = repr(e)[:400]
                results.append(entry)
                tag = "OK " if entry["ok"] else "ERR"
                detail_short = (entry["detail"] or "")[:80].replace("\n", " ")
                print(
                    f"[{tag}] {voice:<32} status={entry['status']:<4} bytes={entry['size']:<7} {detail_short}",
                    flush=True,
                )
                time.sleep(0.5)

            RESULT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nTOTAL={len(edge_voices)} OK={ok_count} FAIL={len(edge_voices) - ok_count}", flush=True)
        return 0
    finally:
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT if sys.platform == "win32" else signal.SIGTERM)
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())