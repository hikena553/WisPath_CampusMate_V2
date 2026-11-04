"""Voice TTS 测试脚本。

启动后端 uvicorn，登录 admin，逐个测试 VOICE_MODEL_CATALOG 中的 voice，
把结果写入 voice_test_results.json，最后关闭 uvicorn。
"""
from __future__ import annotations

import json
import os
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
RESULT_FILE = BACKEND_DIR / "scripts" / "voice_test_results.json"
LOG_FILE = BACKEND_DIR / "scripts" / "voice_test_output.log"
INFO_FILE = BACKEND_DIR / "scripts" / "voice_info_dump.json"


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
    import ctypes

    # 通过 PowerShell 找到占用端口的进程
    ps = (
        f"Get-NetTCPConnection -LocalPort {port} -State Listen "
        f"-ErrorAction SilentlyContinue | ForEach-Object "
        f"{{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)


def start_backend() -> subprocess.Popen:
    # 清理端口
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
        # 登录
        csrf_headers = {"X-Requested-With": "XMLHttpRequest"}
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{BASE}/api/auth/login", json={"username": LOGIN[0], "password": LOGIN[1]}, headers=csrf_headers)
            r.raise_for_status()
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}", **csrf_headers}

            # 拿音色目录
            ir = client.get(f"{BASE}/api/settings/voice/info", headers=headers)
            ir.raise_for_status()
            info = ir.json()
            INFO_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
            groups = info.get("voice_groups", [])
            total = sum(len(g.get("voices", [])) for g in groups)
            print(f"groups={len(groups)} total={total}", flush=True)

            # 逐个测试
            results: list[dict] = []
            ok_count = 0
            for g in groups:
                model = g["model"]
                for v in g["voices"]:
                    voice = v["voice"]
                    entry = {"model": model, "voice": voice, "status": 0, "ok": False, "size": 0, "detail": ""}
                    try:
                        resp = client.post(
                            f"{BASE}/api/settings/tts/test",
                            json={"text": "测试", "voice": voice},
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
                        f"[{tag}] {model:<32} {voice:<26} status={entry['status']:<4} bytes={entry['size']:<7} {detail_short}",
                        flush=True,
                    )
                    time.sleep(0.25)

            RESULT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nTOTAL={total} OK={ok_count} FAIL={total - ok_count}", flush=True)
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