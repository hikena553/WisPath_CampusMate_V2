"""应用入口：只做组装（中间件/静态资源/生命周期/路由注册），业务细节下沉各模块。"""
import faulthandler
import importlib
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# ---------- 第三方包兜底 ----------
# 若当前 Python 环境未安装 jieba（依赖缺失导致启动即报错），
# 自动将项目自带的 vendor_packages 目录加入导入路径，确保服务可正常启动。
_VENDOR_PACKAGES_DIR = Path(__file__).resolve().parent.parent / "vendor_packages"

try:
    import jieba  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    if _VENDOR_PACKAGES_DIR.is_dir():
        sys.path.insert(0, str(_VENDOR_PACKAGES_DIR))
        import jieba  # noqa: F401

from app.api.registry import include_all_routers
from app.core.config import settings
from app.core.database import engine
from app.core.logging_setup import setup_logging
from app.core.middleware import (
    CsrfProtectionMiddleware,
    RequestLogMiddleware,
)
from app.core.schema_guard import repair_missing_columns
from app.tasks.periodic import start_periodic_tasks, stop_periodic_tasks

# 结构化 JSON 日志（可观测性 p4_1）：级别由 LOG_LEVEL 环境变量控制（默认 INFO）
setup_logging()
logger = logging.getLogger(__name__)

# faulthandler 需要持有文件句柄直到进程结束，因此放在模块级
_crash_stream = None


def enable_crash_diagnostics() -> None:
    """崩溃取证（稳定性 p4_2）：把"进程突然没了"变成可定位的记录。

    - faulthandler：段错误 / 原生库崩溃（如 sqlite、lxml、SSL）会直接把
      所有线程的调用栈写进 logs/crash.log，而不是静默退出；
    - sys.excepthook / threading.excepthook：主线程与后台线程的未捕获异常
      统一走 logger（同时落盘），避免只打一行 stderr 就被窗口关掉；
    - 顺带在启动/退出打点，事后能区分"崩溃"和"被人关掉"。
    """
    global _crash_stream
    crash_path = Path(__file__).resolve().parent.parent / "logs" / "crash.log"
    try:
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        _crash_stream = open(crash_path, "a", encoding="utf-8", buffering=1)
        faulthandler.enable(file=_crash_stream, all_threads=True)
    except OSError:  # pragma: no cover - 目录不可写时降级
        logger.warning("crash.log 不可写，faulthandler 未启用")

    def _log_uncaught(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("主线程未捕获异常，进程即将退出", exc_info=(exc_type, exc_value, exc_tb))

    def _log_thread_exception(args):
        name = args.thread.name if args.thread else "unknown"
        logger.error(
            "后台线程 %s 未捕获异常（进程继续存活但该任务已死）",
            name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _log_uncaught
    threading.excepthook = _log_thread_exception


def _with_retry(fn, *, label: str, attempts: int = 3, delay: float = 1.5):
    """启动阶段的可重试执行：SQLite 写入撞车（database is locked）不再直接崩进程。"""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except OperationalError as exc:
            if attempt >= attempts:
                raise
            logger.warning(
                "%s 第 %d/%d 次失败（数据库繁忙），%.1fs 后重试: %s",
                label, attempt, attempts, delay, exc,
            )
            time.sleep(delay)



def run_migrations() -> None:
    """启动时执行数据库迁移（alembic upgrade head），保证 schema 与代码版本一致。

    schema 的唯一事实源是 alembic/versions 下的迁移脚本；应用不再调用 create_all。

    账号边界：迁移走 MIGRATION_DATABASE_URL（campus_ddl，有 DDL 权限），
    运行时走 DATABASE_URL（campus_rw，只有 DML 权限）。分离后即使应用被注入也改不了
    表结构；代价是「谁能改表」必须显式配置，不能再靠应用自己顺手做掉。

    AUTO_MIGRATE=false 时整体跳过：多副本部署下 N 个进程同时 upgrade 会抢同一把
    DDL 锁，且某个副本迁移失败就直接起不来（而不是等流水线回滚）。
    """
    if not settings.AUTO_MIGRATE:
        logger.info(
            "AUTO_MIGRATE=false：跳过启动期迁移。"
            "请由发布流水线以 DDL 账号执行 alembic upgrade head（见 docs/数据库规范.md §9）"
        )
        return

    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    logger.info(
        "执行数据库迁移 head（连接账号：%s）",
        "独立迁移账号" if settings.uses_separate_migration_account else "与运行时同账号",
    )
    command.upgrade(cfg, "head")
    # alembic/env.py 会调用 logging.config.fileConfig(alembic.ini)：根 logger 的 handler
    # 与 level 会被 ini 里的配置整体替换（WARNING + 文本格式 + stderr），
    # 导致启动后本应用的结构化 JSON 日志静默失效（INFO 访问日志、排查信息全部丢失）。
    # disable_existing_loggers=False 只保护已有 logger 对象，挡不住根 logger 被覆盖，
    # 因此迁移结束后必须重新装配日志。
    setup_logging()


def init_sentry_if_configured() -> None:
    """Sentry 预留口子（可观测性 p4_1）：配置了 SENTRY_DSN 且已安装 sentry-sdk 才启用。

    未配置 DSN 或未安装 SDK 时静默跳过，不引入强依赖、不影响启动。
    """
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, traces_sample_rate=1.0)
        logger.info("Sentry 已启用（SENTRY_DSN 已配置）")
    except ImportError:  # pragma: no cover - 依赖缺失兜底
        logger.warning("SENTRY_DSN 已配置但未安装 sentry-sdk，跳过 Sentry 初始化")

# 第三方 HTTP 客户端降噪：httpx/openai 每发一次请求都会在 INFO 打一条
#   httpx: HTTP Request: GET https://... "HTTP/1.1 200 OK"
# 首页/教务/arXiv/RSS 抓取一轮就会刷几十行，把业务日志淹没。这里只对这些
# 依赖库压到 WARNING（真实错误仍会打印），项目自身 logger 保持 INFO 不变。
# 需要排查 HTTP 细节时，临时改为 logging.INFO 即可。
for _noisy_logger in ("httpx", "httpcore", "hpack", "openai", "urllib3"):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 崩溃取证：必须最早启用，才能覆盖迁移/种子阶段的意外退出
    enable_crash_diagnostics()
    logger.info("应用启动中 pid=%s cwd=%s", os.getpid(), Path.cwd())
    # 可观测性：Sentry 初始化（如有配置）
    init_sentry_if_configured()
    # 迁移：先保证表结构就绪（SQLite 并发写入撞车时自动重试，避免启动即崩）
    _with_retry(run_migrations, label="数据库迁移")
    # schema 对账：alembic 版本号已是 head 但真实表少列（备份恢复/手工 stamp）时，
    # 运行期会 `no such column` 整片 500 且迁移永远修不到，这里启动即补齐并告警
    try:
        repair_missing_columns()
    except Exception as exc:  # noqa: BLE001 - 自愈失败只告警，不阻断启动
        logger.error("schema 对账异常（不影响启动）: %s", exc)
    # 初始化种子数据（幂等）
    _with_retry(lambda: importlib.import_module("app.seed"), label="种子数据初始化")
    # 启动后台周期任务，退出时统一回收
    tasks = start_periodic_tasks()
    logger.info("应用启动完成，后台周期任务 %d 个", len(tasks))
    try:
        yield
    finally:
        await stop_periodic_tasks(tasks)
        logger.info("应用已优雅退出 pid=%s", os.getpid())


app = FastAPI(title="智慧校园AI服务平台", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSRF 纵深防护：携带认证 Cookie 的写请求必须带 X-Requested-With 头
# （后注册先执行，置于最外层，先于业务逻辑）
app.add_middleware(CsrfProtectionMiddleware)

# 请求访问日志：置于最外层，耗时统计覆盖全部下游中间件与业务处理
app.add_middleware(RequestLogMiddleware)

# 上传文件不再静态挂载（S4）：统一走 /api/files 鉴权下载接口，
# 旧 /uploads 路径由 files 路由中的兼容路由（同样鉴权）承接。
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)

# 统一注册业务路由
include_all_routers(app)


@app.get("/api/health")
def health_check():
    """健康检查探活（可观测性 p4_1）：返回服务状态/版本/数据库连通性/时间戳。

    - 数据库探活执行 SELECT 1，失败不抛异常：status 降级为 degraded，
      database 字段标记 error，便于容器探针与外部监控区分处理。
    """
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": app.version,
        "database": "ok" if db_ok else "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }