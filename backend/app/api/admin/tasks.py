"""管理端任务下发：管理员把任务指派给教师，自动进入该教师的日程任务清单。"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.notification import NotificationType
from app.models.teacher_task import TaskSourceType
from app.models.user import User, UserRole
from app.schemas.teacher_task import AdminTaskCreate, TeacherTaskOut
from app.services import notification_service, teacher_task_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-tasks"])

_admin_only = require_role(UserRole.ADMIN)


@router.post("/tasks", response_model=TeacherTaskOut)
def dispatch_task(
    payload: AdminTaskCreate,
    user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    """向指定教师下发任务：写入该教师的待办任务，并推送站内通知。"""
    teacher = db.query(User).filter(User.id == payload.teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    if teacher.role != UserRole.TEACHER:
        raise HTTPException(status_code=400, detail="只能向教师账号下发任务")

    task = teacher_task_service.create_task(
        db,
        teacher_id=teacher.id,
        title=payload.title,
        detail=payload.detail,
        student_id=payload.student_id,
        due_at=payload.due_at,
        remind_at=payload.remind_at,
        priority=payload.priority,
        source_type=TaskSourceType.ADMIN,
    )

    # 下发即通知，教师在消息中心立刻看到（失败不影响任务创建）
    try:
        notification_service.send_notification(
            db,
            teacher.id,
            title="管理员下发任务",
            content=payload.title,
            notification_type=NotificationType.SYSTEM,
            link="/teacher/tasks",
            related_id=task.id,
            sender_id=user.id,
        )
    except Exception:
        logger.exception("下发任务后推送通知失败 task_id=%s", task.id)

    return teacher_task_service.serialize_one(db, task)