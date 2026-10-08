"""学情数据底座接口：事件查询与聚合（供其它模块与教师端学情诊断使用）。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.services import learning_event_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learning-events", tags=["learning-events"])

_staff_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


def _assert_visible(db: Session, user: User, actor_id: int) -> None:
    if user.role == UserRole.ADMIN:
        return
    student = db.query(User).filter(User.id == actor_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该学生学情数据")


@router.get("/aggregate")
def aggregate_events(
    actor_id: int = Query(...),
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    """按学生聚合学情事件（谓语分布 / 对象分布 / 最近时间线）。"""
    _assert_visible(db, user, actor_id)
    return learning_event_service.aggregate(db, actor_id, days=days)


@router.get("")
def list_events(
    actor_id: int | None = Query(default=None),
    verb: str | None = Query(default=None),
    object_type: str | None = Query(default=None),
    days: int | None = Query(default=None, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    if actor_id is not None:
        _assert_visible(db, user, actor_id)
        return learning_event_service.query(
            db,
            actor_id=actor_id,
            verb=verb,
            object_type=object_type,
            days=days,
            limit=limit,
            offset=offset,
        )

    # 未指定学生：教师只看名下学生，管理员看全部（限制条数）
    query = db.query(User.id).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    ids = [row[0] for row in query.all()]
    if not ids:
        return []

    from app.models.learning_event import LearningEvent

    stmt = db.query(LearningEvent).filter(LearningEvent.actor_id.in_(ids))
    if verb:
        stmt = stmt.filter(LearningEvent.verb == verb)
    if object_type:
        stmt = stmt.filter(LearningEvent.object_type == object_type)
    rows = (
        stmt.order_by(LearningEvent.occurred_at.desc(), LearningEvent.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [learning_event_service.serialize(r) for r in rows]