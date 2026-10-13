"""学生求助接口：学生提交 / 查看自己的求助；辅导员受理并回复。"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.help_request import (
    HelpRequestCreate,
    HelpRequestOut,
    HelpRequestOverview,
    HelpRequestReply,
)
from app.services import help_request_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/help-requests", tags=["help-requests"])

_student_only = require_role(UserRole.STUDENT)
_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


@router.post("", response_model=HelpRequestOut)
def create_request(
    payload: HelpRequestCreate,
    user: User = Depends(_student_only),
    db: Session = Depends(get_db),
):
    """学生提交求助（可匿名）。"""
    record = help_request_service.create_request(
        db,
        student_id=user.id,
        category=payload.category,
        content=payload.content,
        anonymous=payload.anonymous,
    )
    return help_request_service.serialize(db, record, reveal=True)


@router.get("/mine", response_model=list[HelpRequestOut])
def list_mine(user: User = Depends(_student_only), db: Session = Depends(get_db)):
    """学生查看自己的求助与辅导员回复。"""
    return help_request_service.list_mine(db, user.id)


@router.get("/overview", response_model=HelpRequestOverview)
def get_overview(user: User = Depends(_teacher_only), db: Session = Depends(get_db)):
    """辅导员端求助受理概览。"""
    return help_request_service.overview_for_teacher(db, user.id)


@router.get("", response_model=list[HelpRequestOut])
def list_for_teacher(
    status: str | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """辅导员查看名下学生的求助。"""
    return help_request_service.list_for_teacher(db, user.id, status=status)


@router.put("/{request_id}/reply", response_model=HelpRequestOut)
def reply_request(
    request_id: int,
    payload: HelpRequestReply,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """辅导员受理并回复求助。"""
    record = help_request_service.reply(
        db,
        teacher_id=user.id,
        is_admin=user.role == UserRole.ADMIN,
        request_id=request_id,
        reply=payload.reply,
        status=payload.status,
    )
    return help_request_service.serialize(db, record, reveal=not record.anonymous)