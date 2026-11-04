"""教师端 AI 文案起草接口：填写类弹窗统一的「AI 帮我写」入口。"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import require_role
from app.models.user import User, UserRole
from app.services import teacher_ai_draft_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teacher-ai", tags=["teacher-ai"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


class AiDraftIn(BaseModel):
    scene: str = Field(default="", max_length=40)
    brief: str = Field(default="", max_length=500)
    points: list[str] = Field(default_factory=list, max_length=10)
    reference: str = Field(default="", max_length=1200)
    max_length: int = Field(default=500, ge=20, le=2000)


class AiDraftOut(BaseModel):
    text: str
    source: str = "ai"


@router.post("/draft", response_model=AiDraftOut)
async def draft(payload: AiDraftIn, user: User = Depends(_teacher_only)):
    """AI 帮写：模型不可用（未配置 / 网络异常）时回退本地参考草稿，不阻塞填写。"""
    try:
        text = await teacher_ai_draft_service.ai_draft(
            scene=payload.scene,
            brief=payload.brief,
            points=payload.points,
            reference=payload.reference,
            max_length=payload.max_length,
        )
        return AiDraftOut(text=text, source="ai")
    except Exception:
        logger.warning("教师 AI 帮写失败，使用本地参考草稿", exc_info=True)
        fallback = teacher_ai_draft_service.fallback_text(
            brief=payload.brief,
            points=payload.points,
            reference=payload.reference,
            max_length=payload.max_length,
        )
        return AiDraftOut(text=fallback, source="rule")
