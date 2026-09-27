"""反馈模块业务逻辑：列表/详情/提交/回复，屏蔽 ORM 细节，供 API 层调用。"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.feedback import Feedback, FeedbackType, FeedbackStatus
from app.models.user import User, UserRole
from app.schemas.feedback import FeedbackCreate, FeedbackOut, FeedbackReply

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt(dt: Optional[datetime]) -> str:
    return dt.strftime(_DT_FMT) if dt else ""


def _to_out(f: Feedback, user_name: Optional[str], replier_name: Optional[str]) -> FeedbackOut:
    return FeedbackOut(
        id=f.id,
        user_id=f.user_id,
        user_name=user_name,
        type=f.type.value if f.type else "other",
        title=f.title,
        content=f.content,
        contact=f.contact,
        status=f.status.value if f.status else "pending",
        reply=f.reply,
        replied_by=f.replied_by,
        replier_name=replier_name,
        replied_at=_fmt(f.replied_at),
        created_at=_fmt(f.created_at),
    )


def _resolve_names(db: Session, f: Feedback) -> tuple[Optional[str], Optional[str]]:
    user = db.query(User).filter(User.id == f.user_id).first()
    replier = db.query(User).filter(User.id == f.replied_by).first() if f.replied_by else None
    return (user.name if user else None, replier.name if replier else None)


def create_feedback(db: Session, current_user: User, data: FeedbackCreate) -> FeedbackOut:
    feedback = Feedback(
        user_id=current_user.id,
        type=FeedbackType(data.type) if data.type in [t.value for t in FeedbackType] else FeedbackType.OTHER,
        title=data.title,
        content=data.content,
        contact=data.contact,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return _to_out(feedback, current_user.name, None)


def list_feedbacks(
    db: Session,
    current_user: User,
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> list[FeedbackOut]:
    query = db.query(Feedback)

    # 非管理员只能看自己的反馈
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Feedback.user_id == current_user.id)

    if status:
        query = query.filter(Feedback.status == status)
    if type:
        query = query.filter(Feedback.type == type)

    feedbacks = (
        query.order_by(desc(Feedback.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for f in feedbacks:
        user_name, replier_name = _resolve_names(db, f)
        result.append(_to_out(f, user_name, replier_name))
    return result


def get_feedback_detail(db: Session, current_user: User, feedback_id: int) -> FeedbackOut:
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    # 非管理员只能看自己的反馈
    if current_user.role != UserRole.ADMIN and feedback.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问")

    user_name, replier_name = _resolve_names(db, feedback)
    return _to_out(feedback, user_name, replier_name)


def reply_feedback(db: Session, current_user: User, feedback_id: int, data: FeedbackReply) -> FeedbackOut:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可回复")

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    feedback.reply = data.reply
    feedback.status = (
        FeedbackStatus(data.status)
        if data.status in [s.value for s in FeedbackStatus]
        else FeedbackStatus.RESOLVED
    )
    feedback.replied_by = current_user.id
    feedback.replied_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(feedback)

    user_name = db.query(User).filter(User.id == feedback.user_id).first().name
    return _to_out(feedback, user_name, current_user.name)