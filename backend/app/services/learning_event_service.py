"""学情数据底座服务：LearningEvent 的单点写入与查询。

写入原则（规划硬约束）：
- 只写不判：不做任何业务判断；
- 旁路：写失败不得影响主流程 —— 传入 db 时只入队不提交（随调用方事务落库，失败仅记日志），
  未传入 db 时使用独立会话并在内部提交，异常吞掉并记日志。
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.learning_event import LearningEvent

logger = logging.getLogger(__name__)


def _dump(payload) -> str | None:
    if payload is None:
        return None
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return json.dumps({"_raw": str(payload)}, ensure_ascii=False)


def _load(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"value": data}
    except (TypeError, ValueError):
        return {}


def emit(
    db: Session | None = None,
    *,
    actor_id: int,
    verb: str,
    object_type: str = "",
    object_id: int | None = None,
    result: dict | None = None,
    context: dict | None = None,
) -> None:
    """写入一条学情事件（旁路，绝不抛出）。"""
    event = LearningEvent(
        actor_id=actor_id,
        verb=verb,
        object_type=object_type or "",
        object_id=object_id,
        result_json=_dump(result),
        context_json=_dump(context),
        occurred_at=datetime.now(),
    )
    if db is not None:
        # 复用调用方会话：随其事务落库；失败只记日志，绝不中断主流程
        try:
            db.add(event)
        except Exception:
            logger.warning("学情事件入队失败 verb=%s actor=%s", verb, actor_id, exc_info=True)
        return

    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        session.add(event)
        session.commit()
    except Exception:
        session.rollback()
        logger.warning("学情事件写入失败 verb=%s actor=%s", verb, actor_id, exc_info=True)
    finally:
        session.close()


def query(
    db: Session,
    *,
    actor_id: int | None = None,
    verb: str | None = None,
    object_type: str | None = None,
    days: int | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    stmt = select(LearningEvent)
    if actor_id is not None:
        stmt = stmt.where(LearningEvent.actor_id == actor_id)
    if verb:
        stmt = stmt.where(LearningEvent.verb == verb)
    if object_type:
        stmt = stmt.where(LearningEvent.object_type == object_type)
    if days:
        stmt = stmt.where(LearningEvent.occurred_at >= datetime.now() - timedelta(days=days))

    stmt = stmt.order_by(LearningEvent.occurred_at.desc(), LearningEvent.id.desc()).offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [_serialize(r) for r in rows]


def _serialize(event: LearningEvent) -> dict:
    return {
        "id": event.id,
        "actor_id": event.actor_id,
        "verb": event.verb,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "result": _load(event.result_json),
        "context": _load(event.context_json),
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else "",
    }


def serialize(event: LearningEvent) -> dict:
    return _serialize(event)


def aggregate(db: Session, actor_id: int, days: int = 30) -> dict:
    """按学生聚合学情事件：谓语分布 / 对象分布 / 时间线（供画像与预警规则使用）。"""
    since = datetime.now() - timedelta(days=days)
    base = [LearningEvent.actor_id == actor_id, LearningEvent.occurred_at >= since]

    verb_rows = db.execute(
        select(LearningEvent.verb, func.count(LearningEvent.id))
        .where(*base)
        .group_by(LearningEvent.verb)
        .order_by(func.count(LearningEvent.id).desc())
    ).all()
    object_rows = db.execute(
        select(LearningEvent.object_type, func.count(LearningEvent.id))
        .where(*base)
        .group_by(LearningEvent.object_type)
        .order_by(func.count(LearningEvent.id).desc())
    ).all()
    total = db.execute(select(func.count(LearningEvent.id)).where(*base)).scalar() or 0

    recent = db.execute(
        select(LearningEvent)
        .where(*base)
        .order_by(LearningEvent.occurred_at.desc(), LearningEvent.id.desc())
        .limit(20)
    ).scalars().all()

    return {
        "actor_id": actor_id,
        "days": days,
        "total": int(total),
        "by_verb": [{"verb": v, "count": c} for v, c in verb_rows],
        "by_object": [{"object_type": o, "count": c} for o, c in object_rows],
        "recent": [_serialize(r) for r in recent],
    }


def count_by_verb(db: Session, actor_id: int, verb: str, days: int = 7) -> int:
    """某个谓语在窗口内的次数（预警规则用）。"""
    since = datetime.now() - timedelta(days=days)
    return int(
        db.execute(
            select(func.count(LearningEvent.id)).where(
                LearningEvent.actor_id == actor_id,
                LearningEvent.verb == verb,
                LearningEvent.occurred_at >= since,
            )
        ).scalar()
        or 0
    )


def distinct_actors(db: Session, days: int = 7) -> list[int]:
    """窗口内有学情事件的学生 id（预警扫描范围，避免全表扫描）。"""
    since = datetime.now() - timedelta(days=days)
    rows = db.execute(
        select(LearningEvent.actor_id).where(LearningEvent.occurred_at >= since).distinct()
    ).all()
    return [r[0] for r in rows]