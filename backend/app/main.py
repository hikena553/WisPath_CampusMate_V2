from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.database import engine, Base
from app.api.auth import router as auth_router
from app.api.agent import router as agent_router
from app.api.campus import router as campus_router
from app.api.growth import router as growth_router
from app.api.academic import router as academic_router
from app.api.service import router as service_router
from app.api.leave import router as leave_router
from app.api.crisis import router as crisis_router
from app.api.teacher import router as teacher_router
from app.api.upload import router as upload_router
from app.api.conversations import router as conversations_router
from app.api.messages import router as messages_router
from app.api.announcement import router as announcement_router
from app.api.admin import router as admin_router
from app.api.organization import router as organization_router
from app.api.notification import router as notification_router
from app.api.feedback import router as feedback_router
from app.api.setting import router as setting_router
from app.api.grade_analysis import router as grade_analysis_router
from app.api.profile import router as profile_router

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Base.metadata.create_all(bind=engine)  # Alembic manages schema now
    import importlib
    importlib.import_module("app.seed")
    yield


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

app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(campus_router)
app.include_router(growth_router)
app.include_router(academic_router)
app.include_router(service_router)
app.include_router(leave_router)
app.include_router(crisis_router)
app.include_router(teacher_router)
app.include_router(conversations_router)
app.include_router(upload_router)
app.include_router(messages_router)
app.include_router(announcement_router)
app.include_router(admin_router)
app.include_router(organization_router)
app.include_router(notification_router)
app.include_router(feedback_router)
app.include_router(setting_router)
app.include_router(grade_analysis_router)
app.include_router(profile_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
