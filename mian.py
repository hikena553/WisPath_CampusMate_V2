import subprocess
import sys
import os
import signal
import atexit
import time
import urllib.request
import urllib.error

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

processes = []


def cleanup():
    for p in processes:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


atexit.register(cleanup)
for sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(sig, lambda *_: cleanup())
    except AttributeError:
        pass


def _wait_for_backend(url="http://127.0.0.1:8000/api/health", timeout=30):
    """等待后端健康检查通过后再启动前端。"""
    print("等待后端启动...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status == 200:
                print("  ✓ 后端已就绪")
                return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    print("✗ 后端启动超时，请检查后端日志")
    sys.exit(1)


def _check_vite():
    """检查前端依赖是否已安装，未安装则提示并退出。"""
    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.isdir(node_modules):
        print("=" * 50)
        print("  ✗ 前端依赖未安装")
        print(f"  请运行: cd {FRONTEND_DIR} && npm install")
        print("=" * 50)
        sys.exit(1)


def main():
    print("=" * 50)
    print("  智慧校园AI服务平台 - 启动中...")
    print("=" * 50)
    print(f"  后端: http://localhost:8000")
    print(f"  前端: http://localhost:5173")
    print(f"  按 Ctrl+C 停止所有服务")
    print("=" * 50)

    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    processes.append(backend)

    _wait_for_backend()
    _check_vite()
    npm = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    processes.append(npm)

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
