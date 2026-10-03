"""应用入口：只做组装（中间件/静态资源/生命周期/路由注册），业务细节下沉各模块。"""
import importlib
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

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
from app.tasks.periodic import start_periodic_tasks, stop_periodic_tasks

# 结构化 JSON 日志（可观测性 p4_1）：级别由 LOG_LEVEL 环境变量控制（默认 INFO）
setup_logging()
logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """启动时执行数据库迁移（alembic upgrade head），保证 schema 与代码版本一致。

    schema 的唯一事实源是 alembic/versions 下的迁移脚本；应用不再调用 create_all。
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(cfg, "head")


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
    # 可观测性：Sentry 初始化（如有配置）
    init_sentry_if_configured()
    # 迁移：先保证表结构就绪
    run_migrations()
    # 初始化种子数据（幂等）
    importlib.import_module("app.seed")
    # 启动后台周期任务，退出时统一回收
    tasks = start_periodic_tasks()
    yield
    await stop_periodic_tasks(tasks)


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