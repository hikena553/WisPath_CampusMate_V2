"""应用入口：只做组装（中间件/静态资源/生命周期/路由注册），业务细节下沉各模块。"""
import importlib
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
from app.tasks.periodic import start_periodic_tasks, stop_periodic_tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# 统一注册业务路由
include_all_routers(app)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}