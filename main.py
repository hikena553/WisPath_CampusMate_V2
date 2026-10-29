"""一键启动：后端 (uvicorn) + 前端 (vite)。

针对"进程经常自己关闭"的稳定性改造（p4_2）：

1. **日志双写**：子进程输出同时进控制台和 logs/backend.out.log、logs/frontend.out.log。
   窗口关掉、进程没了，日志还在，事后能查到死前最后几行。
2. **退出码可见**：任一子进程意外退出，打印退出码 + 最后 40 行日志，
   而不是像以前那样 p.wait() 一返回整个窗口就静默关掉。
3. **崩溃自愈**：后端异常退出按指数退避自动重启（默认最多 5 次）；
   达到上限才退出，并给出明确的"该看哪个日志"。
4. **端口预检**：8000/5173 被占用时立刻报出占用 PID 和处置命令，
   不再"等 30 秒健康检查超时 → sys.exit(1)"式静默失败。
5. **进程树清理**：退出时按进程树 kill（Windows `taskkill /T`），不留孤儿
   python.exe 占着 8000 端口——孤儿进程正是下一次启动直接失败的常见元凶。
6. **默认关闭 --reload**：Windows 上热重载要额外递归监控整个 backend 目录
   （含 .venv 里上千个 .py），内存近乎翻倍、且改任何文件都整进程重启。
   需要热重载：`RELOAD=1 python main.py`，且只监控 app/ 目录。

用法：
    python main.py                # 正常启动
    RELOAD=1 python main.py       # 带后端热重载
    MAX_RESTARTS=0 python main.py # 崩溃不自动重启，便于看第一次的错误现场
"""
import atexit
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
LOG_DIR = os.path.join(BACKEND_DIR, "logs")

BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
RELOAD = os.getenv("RELOAD", "0") == "1"
MAX_RESTARTS = int(os.getenv("MAX_RESTARTS", "5"))
HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/api/health"

_IS_WINDOWS = sys.platform == "win32"
_win_flags = subprocess.CREATE_NEW_PROCESS_GROUP if _IS_WINDOWS else 0

_stopping = threading.Event()
_stop_done = False
_logged_exit = False

# ---------------------------------------------------------------- Windows Job Object
# atexit / 信号处理只能覆盖"优雅退出"。关控制台窗口、任务管理器结束任务、IDE 点
# 停止，都是硬终止，atexit 不执行 → 子进程变孤儿，继续占着 8000 端口。
# 结果就是：下次启动后端 bind 失败 → 健康检查 30 秒超时 → 窗口自动关闭，
# 看起来像"进程老是自己关掉"。Job Object 让操作系统在父进程消失时连带回收整棵树。
_job_handle = None


def _install_job_object() -> None:
    global _job_handle
    if not _IS_WINDOWS or os.getenv("NO_JOB_OBJECT") == "1":
        return
    try:
        import ctypes
        from ctypes import wintypes

        class _IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _BASIC_LIMITS(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _EXTENDED_LIMITS(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BASIC_LIMITS),
                ("IoInfo", _IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            return
        info = _EXTENDED_LIMITS()
        info.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(info), ctypes.sizeof(info)  # 9 = ExtendedLimitInformation
        ):
            return
        _job_handle = handle
    except (OSError, AttributeError):  # pragma: no cover - 非 Windows / 受限环境
        _job_handle = None


def _assign_to_job(pid: int) -> None:
    if not _job_handle:
        return
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE
        hproc = kernel32.OpenProcess(0x0100 | 0x0001, False, pid)
        if not hproc:
            return
        try:
            kernel32.AssignProcessToJobObject(_job_handle, hproc)
        finally:
            kernel32.CloseHandle(hproc)
    except (OSError, AttributeError):  # pragma: no cover
        pass



class Service:
    """一个被托管的子进程（后端/前端）。"""

    def __init__(self, name: str, logname: str):
        self.name = name
        self.log_path = os.path.join(LOG_DIR, logname)
        self.proc: subprocess.Popen | None = None
        self.restarts = 0

    def spawn(self, cmd, cwd, shell=False):
        os.makedirs(LOG_DIR, exist_ok=True)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        self.proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            shell=shell,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=_win_flags,
        )
        _assign_to_job(self.proc.pid)
        threading.Thread(
            target=_pump, args=(self.name, self.proc.stdout, self.log_path), daemon=True
        ).start()

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def request_stop(self, wait: float = 8.0) -> None:
        """先请子进程自己优雅退出，别一上来就 taskkill。

        Windows 上 `taskkill /F` 是 TerminateProcess，进程没有机会执行
        lifespan 收尾：SQLite 的 WAL 不 checkpoint、连接池不 dispose、
        日志里连"应用已优雅退出"都不会有——事后排查容易误判成崩溃。
        子进程用 CREATE_NEW_PROCESS_GROUP 启动，因此可以只向它自己的
        进程组发 CTRL_BREAK_EVENT，uvicorn 会走正常的 shutdown 流程。
        """
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            if _IS_WINDOWS:
                os.kill(self.proc.pid, signal.CTRL_BREAK_EVENT)
            else:
                self.proc.terminate()
        except (AttributeError, OSError):
            return
        try:
            self.proc.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            pass

    def kill_tree(self):
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            if _IS_WINDOWS:
                # /T 连带子进程；npm.cmd → node → esbuild 一层套一层，必须整棵树清
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        except OSError:
            pass


backend = Service("backend", "backend.out.log")
frontend = Service("frontend", "frontend.out.log")


def _pump(name, pipe, log_path):
    """把子进程输出双写到控制台和日志文件。"""
    try:
        with open(log_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"\n===== {name} 启动于 {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
            f.flush()
            for line in iter(pipe.readline, ""):
                f.write(line)
                f.flush()
                try:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                except (OSError, ValueError):
                    pass  # 控制台已关闭，日志继续写
    except (OSError, ValueError):
        pass
    finally:
        try:
            pipe.close()
        except OSError:
            pass


def _tail(path: str, lines: int = 40) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError:
        return "(日志文件尚不存在)"


def _port_busy(port: int) -> bool:
    """端口是否已有服务在监听。

    用 connect 而不是 bind 判断：Windows 上 bind + SO_REUSEADDR 在端口已被
    socket 占用时仍可能成功，导致"端口明明被占却检测不出"，预检形同虚设。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _pids_on_port(port: int) -> list[str]:
    """Windows 下查端口占用者 PID，方便告诉用户"是谁占着"。"""
    if not _IS_WINDOWS:
        return []
    try:
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, errors="replace"
        ).stdout
    except OSError:
        return []
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3] == "LISTENING":
            pids.add(parts[4])
    return sorted(pids)


def _preflight() -> bool:
    """启动前预检：端口、前端依赖。返回 False 表示不该继续。"""
    ok = True
    for port, label in ((BACKEND_PORT, "后端"), (FRONTEND_PORT, "前端")):
        if _port_busy(port):
            ok = False
            pids = _pids_on_port(port)
            print(f"[FAIL] {label}端口 {port} 已被占用" + (f"（PID {', '.join(pids)}）" if pids else ""))
            if pids:
                print(f"       处置: taskkill /F /T /PID {pids[0]}")
            print("       上一次异常关闭留下的孤儿进程最常见，清理后重试。")

    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.isdir(node_modules):
        ok = False
        print("=" * 56)
        print("  [FAIL] 前端依赖未安装")
        print(f"  请运行: cd {FRONTEND_DIR} && npm install")
        print("=" * 56)
    return ok


def _wait_health(timeout: int = 60) -> bool:
    """等后端健康检查通过；期间若后端进程已死则立刻返回，不空等。"""
    print("等待后端启动...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not backend.alive():
            print(f"[FAIL] 后端进程已退出（退出码 {backend.proc.returncode}），启动失败")
            return False
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    print("  [OK] 后端已就绪")
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    print("[FAIL] 后端启动超时")
    return False


def _backend_cmd() -> list[str]:
    cmd = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
    ]
    if RELOAD:
        # 只监控业务代码目录：避免 .venv / logs / *.db 变更引发无谓重启
        cmd += ["--reload", "--reload-dir", "app"]
    return cmd


def _start_backend():
    backend.spawn(_backend_cmd(), BACKEND_DIR)


def _start_frontend():
    frontend.spawn(["npm", "run", "dev"], FRONTEND_DIR, shell=_IS_WINDOWS)


def _stop_all():
    """停止全部服务：先请各自优雅退出，超时再整棵树强杀（幂等，可被多次调用）。"""
    global _stop_done
    if _stop_done:
        return
    _stop_done = True
    _stopping.set()
    # 前端先停（避免它继续往正在关闭的后端打请求），后端最后停
    for svc in (frontend, backend):
        svc.request_stop()
    for svc in (frontend, backend):
        svc.kill_tree()


def _exit_handler(signum, _frame):
    """Ctrl+C / 停止按钮 / 终端关闭：先请求优雅退出，再把残留的进程树清掉。

    这个钩子只在"被叫停"时触发（SIGINT = 控制台 Ctrl+C 事件），
    出现它说明是有人/某个工具主动停了服务，而不是程序自己崩了。
    """
    label = "SIGINT（Ctrl+C / 停止按钮）" if signum == signal.SIGINT else f"信号 {signum}"
    print(f"\n收到 {label}，正在停止前后端（等待优雅退出，最多约 8 秒）...")
    _stop_all()
    raise SystemExit(0)


def _report_and_hold(reason: str):
    """异常退出时打印取证信息；交互式终端下停住，别让窗口一闪而过。"""
    global _logged_exit
    if _logged_exit:
        return
    _logged_exit = True

    print("\n" + "=" * 56)
    print(f"  [失败] {reason}")
    print("=" * 56)
    for svc in (backend, frontend):
        code = svc.proc.returncode if svc.proc else "未启动"
        print(f"  {svc.name}: 退出码={code}  累计重启={svc.restarts}")
    print(f"\n---- 后端日志尾部 ({backend.log_path}) ----")
    print(_tail(backend.log_path))
    print(f"---- 前端日志尾部 ({frontend.log_path}) ----")
    print(_tail(frontend.log_path, 20))
    print("=" * 56)
    print("  完整日志: backend/logs/app.log（应用日志）")
    print("            backend/logs/crash.log（原生崩溃栈）")
    print("=" * 56)

    if sys.stdin and sys.stdin.isatty():
        try:
            input("按回车键退出...")
        except (EOFError, KeyboardInterrupt):
            pass


atexit.register(_stop_all)
for _sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(_sig, _exit_handler)
    except (AttributeError, ValueError):  # pragma: no cover - 非主线程/平台不支持
        pass


def main() -> int:
    print("=" * 56)
    print("  智慧校园AI服务平台 - 启动中")
    print("=" * 56)
    print(f"  后端: http://localhost:{BACKEND_PORT}  (热重载: {'开' if RELOAD else '关'})")
    print(f"  前端: http://localhost:{FRONTEND_PORT}")
    print(f"  日志: {LOG_DIR}")
    print("  按 Ctrl+C 停止所有服务")
    print("=" * 56)

    if not _preflight():
        _report_and_hold("启动前预检未通过")
        return 1

    _install_job_object()
    _start_backend()
    if not _wait_health():
        _stop_all()
        _report_and_hold("后端启动失败")
        return 1

    try:
        _start_frontend()
    except OSError as exc:
        _report_and_hold(f"前端启动失败: {exc}")
        return 1

    # 监督循环：谁死了就查谁，能重启就重启，重启到上限才整体退出
    while not _stopping.is_set():
        for svc in (backend, frontend):
            if svc.alive():
                continue
            code = svc.proc.returncode if svc.proc else None
            if code in (0, -15) or _stopping.is_set():
                continue
            svc.restarts += 1
            if svc.restarts > MAX_RESTARTS:
                _stop_all()
                _report_and_hold(
                    f"{svc.name} 连续异常退出（最后一次退出码 {code}），已达重启上限 {MAX_RESTARTS}"
                )
                return 1
            delay = min(2 ** (svc.restarts - 1), 30)
            print(f"\n[WARN] {svc.name} 意外退出（退出码 {code}），{delay}s 后第 "
                  f"{svc.restarts}/{MAX_RESTARTS} 次重启")
            time.sleep(delay)
            try:
                if svc is backend:
                    _start_backend()
                else:
                    _start_frontend()
            except OSError as exc:
                _report_and_hold(f"{svc.name} 重启失败: {exc}")
                return 1
        time.sleep(0.5)

    return 0


if __name__ == "__main__":
    sys.exit(main())
