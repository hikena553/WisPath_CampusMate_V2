"""教师待办任务接口：闭环的公共待办层。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.teacher_task import TeacherTask
from app.models.user import User, UserRole
from app.schemas.teacher_task import (
    TeacherTaskCreate,
    TeacherTaskOut,
    TeacherTaskSummary,
    TeacherTaskUpdate,
)
from app.services import teacher_task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teacher-tasks", tags=["teacher-tasks"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/summary", response_model=TeacherTaskSummary)
def get_summary(user: User = Depends(_teacher_only), db: Session = Depends(get_db)):
    """首页 KPI：今日待跟进 / 逾期 / 本周完成。"""
    return teacher_task_service.summary(db, user.id)


@router.get("", response_model=list[TeacherTaskOut])
def list_tasks(
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    due: str | None = Query(default=None, description="overdue / today"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    items, _ = teacher_task_service.list_tasks(
        db, user.id, status=status, source_type=source_type, due=due, limit=limit, offset=offset
    )
    return items


@router.post("", response_model=TeacherTaskOut)
def create_task(
    payload: TeacherTaskCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    task = teacher_task_service.create_task(
        db,
        teacher_id=user.id,
        title=payload.title,
        detail=payload.detail,
        student_id=payload.student_id,
        due_at=payload.due_at,
        source_type=payload.source_type,
        source_id=payload.source_id,
    )
    return teacher_task_service.serialize_one(db, task)


@router.patch("/{task_id}", response_model=TeacherTaskOut)
def update_task(
    task_id: int,
    payload: TeacherTaskUpdate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    task = teacher_task_service.get_task(db, task_id, user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    try:
        teacher_task_service.update_task(db, task, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return teacher_task_service.serialize_one(db, task)
