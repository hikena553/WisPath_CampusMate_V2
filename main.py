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
    python main.py                # 正常启动（前端 HTTP）
    HTTPS=1 python main.py        # 前端 HTTPS：手机访问时麦克风/语音录制才可用
    RELOAD=1 python main.py       # 带后端热重载
    MAX_RESTARTS=0 python main.py # 崩溃不自动重启，便于看第一次的错误现场

HTTPS=1 首次启动会在 frontend/certs/ 生成本地 CA 与服务端证书（已 gitignore），
并额外开一个只提供证书下载的 HTTP 端口（默认 5174）。手机先装证书：
Android 打开 http://<局域网IP>:5174/dev-ca.crt；iOS 打开
http://<局域网IP>:5174/dev-ca.mobileconfig 并在
“设置→通用→关于本机→证书信任设置”开启完全信任，之后访问
https://<局域网IP>:5173 才能调用麦克风。
"""
import atexit
import base64
import ipaddress
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
LOG_DIR = os.path.join(BACKEND_DIR, "logs")

BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
RELOAD = os.getenv("RELOAD", "0") == "1"
MAX_RESTARTS = int(os.getenv("MAX_RESTARTS", "5"))
HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/api/health"
# HTTPS=1：前端以 HTTPS 启动，手机通过局域网访问时才能调用麦克风（语音消息）。
HTTPS = os.getenv("HTTPS", "0") == "1"
FRONTEND_CERT_DIR = os.path.join(FRONTEND_DIR, "certs")
CA_HTTP_PORT = int(os.getenv("CA_HTTP_PORT", "5174"))
_ca_http_server = None

_IS_WINDOWS = sys.platform == "win32"
_win_flags = subprocess.CREATE_NEW_PROCESS_GROUP if _IS_WINDOWS else 0

_stopping = threading.Event()
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



def _enable_ansi() -> None:
    """让父控制台渲染 ANSI 颜色码。

    本启动器用 subprocess.PIPE 接管子进程 stdout，子进程 isatty() 恒为 False，
    uvicorn / vite 因此把日志降级成纯文本（这就是"错误日志全是白色"的原因）。
    修法分两步：子进程强制输出颜色（--use-colors / FORCE_COLOR=1），父进程这边
    再把 Windows 控制台的 VT 处理打开，否则父进程 print 出来的就是 `←[31m` 乱码。
    """
    if not _IS_WINDOWS:
        return
    try:
        import colorama

        colorama.just_fix_windows_console()
        return
    except (ImportError, OSError, AttributeError):
        pass
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except (OSError, AttributeError):  # pragma: no cover - 老控制台/重定向场景
        pass


def _local_ipv4_addresses() -> list[str]:
    """本机所有非回环 IPv4（手机通过哪个地址访问，证书里就要覆盖哪个 IP）。"""
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip and not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass
    return sorted(ips)


def _ensure_dev_certs() -> bool:
    """生成一次本地 CA + 服务端证书（HTTPS=1 时用）。

    手机浏览器只在 HTTPS/localhost 下开放 getUserMedia；局域网 IP 用 HTTP 会被
    浏览器直接禁用麦克风。Android 装 dev-ca.crt、iOS 装 dev-ca.mobileconfig 后，
    https://<局域网IP>:5173 就是受信任的安全上下文，按住说话才能工作。
    """
    ca_key_path = os.path.join(FRONTEND_CERT_DIR, "dev-ca.key")
    ca_crt_path = os.path.join(FRONTEND_CERT_DIR, "dev-ca.crt")
    srv_key_path = os.path.join(FRONTEND_CERT_DIR, "dev-server.key")
    srv_crt_path = os.path.join(FRONTEND_CERT_DIR, "dev-server.crt")
    mobileconfig_path = os.path.join(FRONTEND_CERT_DIR, "dev-ca.mobileconfig")
    required_ips = set(_local_ipv4_addresses()) | {"127.0.0.1"}

    def cert_still_valid() -> bool:
        if not all(os.path.isfile(p) for p in (srv_key_path, srv_crt_path, ca_crt_path, mobileconfig_path)):
            return False
        try:
            from cryptography import x509

            cert = x509.load_pem_x509_certificate(open(srv_crt_path, "rb").read())
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            ips = {str(v) for v in san.get_values_for_type(x509.IPAddress)}
            dns = set(san.get_values_for_type(x509.DNSName))
            try:
                expires = cert.not_valid_after_utc
            except AttributeError:  # cryptography < 42
                expires = cert.not_valid_after.replace(tzinfo=timezone.utc)
            return expires > datetime.now(timezone.utc) + timedelta(days=7) and "localhost" in dns and required_ips <= ips
        except Exception:
            return False

    if cert_still_valid():
        return True

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    except ImportError:
        print("[WARN] 当前 Python 环境未安装 cryptography，无法生成 HTTPS 开发证书")
        return False

    try:
        os.makedirs(FRONTEND_CERT_DIR, exist_ok=True)
        now = datetime.now(timezone.utc)

        def read_bytes(path: str) -> bytes:
            with open(path, "rb") as f:
                return f.read()

        # 复用已有 CA：局域网 IP 变化时只重签服务端证书，避免手机反复安装根证书
        ca_key = None
        ca_cert = None
        if os.path.isfile(ca_key_path) and os.path.isfile(ca_crt_path):
            try:
                ca_key = serialization.load_pem_private_key(read_bytes(ca_key_path), password=None)
                ca_cert = x509.load_pem_x509_certificate(read_bytes(ca_crt_path))
                try:
                    ca_expires = ca_cert.not_valid_after_utc
                except AttributeError:  # cryptography < 42
                    ca_expires = ca_cert.not_valid_after.replace(tzinfo=timezone.utc)
                if ca_expires < now + timedelta(days=30) or ca_key.public_key().public_numbers() != ca_cert.public_key().public_numbers():
                    ca_key = ca_cert = None
            except Exception:
                ca_key = ca_cert = None

        if ca_key is not None and ca_cert is not None:
            ca_name = ca_cert.subject
        else:
            ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            ca_name = x509.Name([
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WisPath CampusMate"),
                x509.NameAttribute(NameOID.COMMON_NAME, "WisPath CampusMate Dev CA"),
            ])
            ca_cert = (
                x509.CertificateBuilder()
                .subject_name(ca_name)
                .issuer_name(ca_name)
                .public_key(ca_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(days=1))
                .not_valid_after(now + timedelta(days=3650))
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=False,
                        content_commitment=False,
                        key_encipherment=False,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=True,
                        crl_sign=True,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
                .sign(ca_key, hashes.SHA256())
            )
            with open(ca_key_path, "wb") as f:
                f.write(ca_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            with open(ca_crt_path, "wb") as f:
                f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

        srv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        san = x509.SubjectAlternativeName(
            [x509.DNSName("localhost")]
            + [x509.IPAddress(ipaddress.ip_address(ip)) for ip in sorted(required_ips)]
        )
        srv_cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
            .issuer_name(ca_name)
            .public_key(srv_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=825))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(san, critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(ca_key, hashes.SHA256())
        )

        pem = serialization.Encoding.PEM
        no_enc = serialization.NoEncryption()
        with open(srv_key_path, "wb") as f:
            f.write(srv_key.private_bytes(pem, serialization.PrivateFormat.PKCS8, no_enc))
        with open(srv_crt_path, "wb") as f:
            f.write(srv_cert.public_bytes(pem))

        # iOS 只能通过描述文件安装根证书；PayloadContent 必须是 DER 的 base64
        ca_der = base64.b64encode(ca_cert.public_bytes(serialization.Encoding.DER)).decode()
        profile_uuid = str(uuid.uuid4()).upper()
        payload_uuid = str(uuid.uuid4()).upper()
        with open(mobileconfig_path, "w", encoding="utf-8") as f:
            f.write(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0">\n<dict>\n'
                "  <key>PayloadContent</key>\n  <array>\n    <dict>\n"
                "      <key>PayloadCertificateFileName</key><string>dev-ca.crt</string>\n"
                f"      <key>PayloadContent</key><data>{ca_der}</data>\n"
                "      <key>PayloadDescription</key><string>WisPath CampusMate 本地开发 HTTPS 根证书（仅用于开发调试）</string>\n"
                "      <key>PayloadDisplayName</key><string>WisPath CampusMate Dev CA</string>\n"
                "      <key>PayloadIdentifier</key><string>com.wispath.campusmate.devca</string>\n"
                "      <key>PayloadType</key><string>com.apple.security.root</string>\n"
                f"      <key>PayloadUUID</key><string>{payload_uuid}</string>\n"
                "      <key>PayloadVersion</key><integer>1</integer>\n"
                "    </dict>\n  </array>\n"
                "  <key>PayloadDisplayName</key><string>WisPath CampusMate Dev CA</string>\n"
                "  <key>PayloadIdentifier</key><string>com.wispath.campusmate.devca.profile</string>\n"
                "  <key>PayloadRemovalDisallowed</key><false/>\n"
                "  <key>PayloadType</key><string>Configuration</string>\n"
                f"  <key>PayloadUUID</key><string>{profile_uuid}</string>\n"
                "  <key>PayloadVersion</key><integer>1</integer>\n"
                "</dict>\n</plist>\n"
            )
        return True
    except Exception as exc:  # noqa: BLE001 - 证书生成失败时退回 HTTP，不能挡住启动
        print(f"[WARN] 生成 HTTPS 开发证书失败: {exc}")
        return False


def _start_ca_http_server() -> None:
    """HTTPS 模式下提供一个纯 HTTP 的证书下载口。

    手机首次访问时 HTTPS 证书还没被信任，直接从 HTTPS 页面下载描述文件会被浏览器
    拦截；单独开一个只暴露两个公开证书文件的 HTTP 端口，安装流程最省事。
    """
    global _ca_http_server
    if not HTTPS or _ca_http_server is not None:
        return
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    files = {
        "/dev-ca.crt": ("dev-ca.crt", "application/x-x509-ca-cert"),
        "/dev-ca.mobileconfig": ("dev-ca.mobileconfig", "application/x-apple-aspen-config"),
    }

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 约定
            item = files.get(self.path.split("?", 1)[0])
            full = os.path.join(FRONTEND_CERT_DIR, item[0]) if item else ""
            if not item or not os.path.isfile(full):
                self.send_error(404)
                return
            with open(full, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", item[1])
            self.send_header("Content-Disposition", f'attachment; filename="{item[0]}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    try:
        server = ThreadingHTTPServer(("0.0.0.0", CA_HTTP_PORT), _Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _ca_http_server = server
    except OSError as exc:
        print(f"[WARN] 证书下载端口 {CA_HTTP_PORT} 启动失败: {exc}")


def _stop_ca_http_server() -> None:
    global _ca_http_server
    if _ca_http_server is not None:
        _ca_http_server.shutdown()
        _ca_http_server.server_close()
        _ca_http_server = None


class Service:
    """一个被托管的子进程（后端/前端）。"""

    def __init__(self, name: str, logname: str):
        self.name = name
        self.log_path = os.path.join(LOG_DIR, logname)
        self.proc: subprocess.Popen | None = None
        self.restarts = 0

    def spawn(self, cmd, cwd, shell=False, extra_env=None):
        os.makedirs(LOG_DIR, exist_ok=True)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        if extra_env:
            env.update(extra_env)
        # stdout 是管道，子进程（vite/uvicorn/node）会误判为"非终端"而关闭颜色
        env["FORCE_COLOR"] = "1"
        env["CLICOLOR_FORCE"] = "1"
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


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _pump(name, pipe, log_path):
    """把子进程输出双写到控制台和日志文件（控制台带色，文件去色便于 grep）。"""
    try:
        with open(log_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"\n===== {name} 启动于 {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
            f.flush()
            for line in iter(pipe.readline, ""):
                f.write(_ANSI_RE.sub("", line))
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
        # stdout 被重定向到管道时 uvicorn 默认按 isatty() 关闭颜色，
        # ERROR/INFO 一律白字，500 堆栈在满屏白字里根本跳不出来
        "--use-colors",
    ]
    if RELOAD:
        # 只监控业务代码目录：避免 .venv / logs / *.db 变更引发无谓重启
        cmd += ["--reload", "--reload-dir", "app"]
    return cmd


def _start_backend():
    backend.spawn(_backend_cmd(), BACKEND_DIR)


def _start_frontend():
    extra_env = {"VITE_HTTPS": "1"} if HTTPS else None
    frontend.spawn(["npm", "run", "dev"], FRONTEND_DIR, shell=_IS_WINDOWS, extra_env=extra_env)


def _stop_all():
    _stopping.set()
    _stop_ca_http_server()
    for svc in (frontend, backend):
        svc.kill_tree()


def _exit_handler(signum, _frame):
    """Ctrl+C / SIGTERM / 关窗口：先把子进程树清干净再退。"""
    print(f"\n收到信号 {signum}，正在停止所有服务...")
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
    global HTTPS
    _enable_ansi()
    if HTTPS and not _ensure_dev_certs():
        HTTPS = False
    scheme = "https" if HTTPS else "http"
    print("=" * 56)
    print("  智慧校园AI服务平台 - 启动中")
    print("=" * 56)
    print(f"  后端: http://localhost:{BACKEND_PORT}  (热重载: {'开' if RELOAD else '关'})")
    print(f"  前端: {scheme}://localhost:{FRONTEND_PORT}")
    if HTTPS:
        _start_ca_http_server()
        ips = _local_ipv4_addresses()
        host = ips[0] if ips else "<局域网IP>"
        print(f"  手机访问: {scheme}://{host}:{FRONTEND_PORT}/")
        print("    1) 先装开发证书（用手机浏览器直接打开下面的 HTTP 地址）:")
        print(f"       Android: http://{host}:{CA_HTTP_PORT}/dev-ca.crt")
        print(f"       iOS:     http://{host}:{CA_HTTP_PORT}/dev-ca.mobileconfig")
        print("       iOS 装完还需到 设置→通用→关于本机→证书信任设置 开启完全信任")
        print("    2) 证书装好后访问上面的 HTTPS 地址，按住说话即可")
    else:
        _ips = _local_ipv4_addresses()
        _host = _ips[0] if _ips else "<局域网IP>"
        print(f"  手机访问: http://{_host}:{FRONTEND_PORT}/  （只能浏览；浏览器在 HTTP 下禁用麦克风）")
        print("       手机要用语音通话/录音：改为 HTTPS=1 python main.py 启动")
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
