"""学生求助服务：学生提交 / 学生查看自己的求助 / 辅导员受理回复，唯一入口。"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.help_request import HelpRequest, HelpRequestStatus
from app.models.user import User, UserRole

_DT_FMT = "%Y-%m-%d %H:%M:%S"

CATEGORY_LABELS = {
    "academic": "学业困扰",
    "life": "生活困难",
    "mental": "心理情绪",
    "relation": "人际关系",
    "other": "其他",
}
_CATEGORIES = set(CATEGORY_LABELS)

# 辅导员回复可收敛到的状态（不允许回退到待受理）
_REPLY_TARGETS = {HelpRequestStatus.PROCESSING, HelpRequestStatus.RESOLVED}


def _fmt(dt: Optional[datetime]) -> str:
    return dt.strftime(_DT_FMT) if dt else ""


def _category(value: str | None) -> str:
    return value if value in _CATEGORIES else "other"


def _name_of(db: Session, user_id: int | None) -> str:
    if not user_id:
        return ""
    row = db.query(User.name).filter(User.id == user_id).first()
    return row[0] if row else ""


def _my_student_ids(db: Session, teacher_id: int) -> list[int]:
    return [
        s.id
        for s in db.query(User).filter(
            User.role == UserRole.STUDENT, User.tutor_id == teacher_id
        ).all()
    ]


def serialize(db: Session, r: HelpRequest, *, reveal: bool) -> dict:
    """reveal=False（匿名求助对辅导员）时隐去学生姓名。"""
    return {
        "id": r.id,
        "student_id": r.student_id,
        "student_name": _name_of(db, r.student_id) if reveal else "",
        "anonymous": bool(r.anonymous),
        "category": r.category or "other",
        "content": r.content,
        "status": r.status.value if r.status else "pending",
        "teacher_id": r.teacher_id,
        "teacher_name": _name_of(db, r.teacher_id),
        "reply": r.reply,
        "replied_at": _fmt(r.replied_at),
        "created_at": _fmt(r.created_at),
    }


def create_request(
    db: Session,
    *,
    student_id: int,
    category: str,
    content: str,
    anonymous: bool = False,
) -> HelpRequest:
    record = HelpRequest(
        student_id=student_id,
        category=_category(category),
        content=content,
        anonymous=anonymous,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_mine(db: Session, student_id: int, limit: int = 100) -> list[dict]:
    records = (
        db.query(HelpRequest)
        .filter(HelpRequest.student_id == student_id, HelpRequest.is_deleted.is_(False))
        .order_by(desc(HelpRequest.created_at), desc(HelpRequest.id))
        .limit(limit)
        .all()
    )
    return [serialize(db, r, reveal=True) for r in records]


def list_for_teacher(
    db: Session, teacher_id: int, *, status: str | None = None, limit: int = 200
) -> list[dict]:
    """辅导员查看自己名下学生的求助；匿名求助隐去姓名。"""
    student_ids = _my_student_ids(db, teacher_id)
    if not student_ids:
        return []
    query = db.query(HelpRequest).filter(
        HelpRequest.student_id.in_(student_ids),
        HelpRequest.is_deleted.is_(False),
    )
    if status in {s.value for s in HelpRequestStatus}:
        query = query.filter(HelpRequest.status == HelpRequestStatus(status))
    records = (
        query.order_by(desc(HelpRequest.created_at), desc(HelpRequest.id)).limit(limit).all()
    )
    return [serialize(db, r, reveal=not r.anonymous) for r in records]


def overview_for_teacher(db: Session, teacher_id: int) -> dict:
    student_ids = _my_student_ids(db, teacher_id)
    if not student_ids:
        return {"pending": 0, "processing": 0, "resolved": 0, "total": 0}
    rows = (
        db.query(HelpRequest.status)
        .filter(
            HelpRequest.student_id.in_(student_ids),
            HelpRequest.is_deleted.is_(False),
        )
        .all()
    )
    counts = {"pending": 0, "processing": 0, "resolved": 0}
    for (st,) in rows:
        key = st.value if st else "pending"
        counts[key] = counts.get(key, 0) + 1
    return {**counts, "total": len(rows)}


def reply(
    db: Session,
    *,
    teacher_id: int,
    is_admin: bool,
    request_id: int,
    reply: str,
    status: str,
) -> HelpRequest:
    record = db.query(HelpRequest).filter(HelpRequest.id == request_id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=404, detail="求助不存在")

    if not is_admin:
        student = db.query(User).filter(User.id == record.student_id).first()
        if not student or student.tutor_id != teacher_id:
            raise HTTPException(status_code=403, detail="无权受理该求助")

    record.reply = reply
    record.status = (
        HelpRequestStatus(status) if status in {s.value for s in _REPLY_TARGETS}
        else HelpRequestStatus.RESOLVED
    )
    record.teacher_id = teacher_id
    record.replied_at = datetime.now()

    db.commit()
    db.refresh(record)
    return record