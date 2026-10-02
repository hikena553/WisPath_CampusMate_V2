"""应用入口：只做组装（中间件/静态资源/生命周期/路由注册），业务细节下沉各模块。"""
import importlib
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.core.middleware import CsrfProtectionMiddleware, EnforcePasswordChangeMiddleware
from app.tasks.periodic import start_periodic_tasks, stop_periodic_tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
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

# 强制首登改密：未修改初始密码的用户仅可访问认证/改密白名单接口
app.add_middleware(EnforcePasswordChangeMiddleware)

# CSRF 纵深防护：携带认证 Cookie 的写请求必须带 X-Requested-With 头
# （后注册先执行，置于最外层，先于改密拦截与业务逻辑）
app.add_middleware(CsrfProtectionMiddleware)

# 上传文件不再静态挂载（S4）：统一走 /api/files 鉴权下载接口，
# 旧 /uploads 路径由 files 路由中的兼容路由（同样鉴权）承接。
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)

# 统一注册业务路由
include_all_routers(app)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}