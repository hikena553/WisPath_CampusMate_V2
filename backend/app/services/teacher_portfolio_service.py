"""教师成长档案服务：成长档案的唯一入口（增删改查 + 成长报告聚合）。"""
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.teacher_portfolio import (
    PortfolioItemType,
    PortfolioVisibility,
    TeacherPortfolioItem,
)
from app.models.user import User

TYPE_LABELS: dict[str, str] = {
    "case": "工作案例",
    "honor": "荣誉表彰",
    "training": "培训研修",
    "research": "工作研究成果",
}


def _item_type(value: str | PortfolioItemType | None) -> PortfolioItemType:
    if isinstance(value, PortfolioItemType):
        return value
    try:
        return PortfolioItemType(value) if value else PortfolioItemType.CASE
    except ValueError:
        return PortfolioItemType.CASE


def _visibility(value: str | PortfolioVisibility | None) -> PortfolioVisibility:
    if isinstance(value, PortfolioVisibility):
        return value
    try:
        return PortfolioVisibility(value) if value else PortfolioVisibility.PRIVATE
    except ValueError:
        return PortfolioVisibility.PRIVATE


def _dump_evidence(evidence: list[dict] | None) -> str | None:
    if not evidence:
        return None
    return json.dumps(evidence, ensure_ascii=False)


def _load_evidence(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def _serialize(item: TeacherPortfolioItem) -> dict:
    return {
        "id": item.id,
        "teacher_id": item.teacher_id,
        "item_type": item.item_type.value if item.item_type else "case",
        "title": item.title,
        "evidence": _load_evidence(item.evidence_json),
        "reflection": item.reflection,
        "occurred_on": item.occurred_on,
        "visibility": item.visibility.value if item.visibility else "private",
        "reviewer_id": item.reviewer_id,
        "review_comment": item.review_comment,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }


def create_item(
    db: Session,
    *,
    teacher_id: int,
    title: str,
    item_type: str | PortfolioItemType = PortfolioItemType.CASE,
    evidence: list[dict] | None = None,
    reflection: str | None = None,
    occurred_on=None,
    visibility: str | PortfolioVisibility = PortfolioVisibility.PRIVATE,
) -> TeacherPortfolioItem:
    item = TeacherPortfolioItem(
        teacher_id=teacher_id,
        item_type=_item_type(item_type),
        title=title,
        evidence_json=_dump_evidence(evidence),
        reflection=reflection,
        occurred_on=occurred_on,
        visibility=_visibility(visibility),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, item_id: int) -> TeacherPortfolioItem | None:
    return (
        db.query(TeacherPortfolioItem)
        .filter(
            TeacherPortfolioItem.id == item_id,
            TeacherPortfolioItem.is_deleted.is_(False),
        )
        .first()
    )


def list_items(
    db: Session,
    teacher_id: int,
    *,
    item_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    query = db.query(TeacherPortfolioItem).filter(
        TeacherPortfolioItem.teacher_id == teacher_id,
        TeacherPortfolioItem.is_deleted.is_(False),
    )
    if item_type:
        query = query.filter(TeacherPortfolioItem.item_type == _item_type(item_type))

    total = query.count()
    items = (
        query.order_by(
            TeacherPortfolioItem.occurred_on.desc().nulls_last(),
            TeacherPortfolioItem.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize(i) for i in items], total


def update_item(db: Session, item: TeacherPortfolioItem, payload: dict) -> TeacherPortfolioItem:
    if payload.get("item_type") is not None:
        item.item_type = _item_type(payload["item_type"])
    if payload.get("title") is not None:
        item.title = payload["title"]
    if "evidence" in payload:
        item.evidence_json = _dump_evidence(payload["evidence"])
    if "reflection" in payload:
        item.reflection = payload["reflection"]
    if "occurred_on" in payload:
        item.occurred_on = payload["occurred_on"]
    if payload.get("visibility") is not None:
        item.visibility = _visibility(payload["visibility"])
    db.commit()
    db.refresh(item)
    return item


def soft_delete(db: Session, item: TeacherPortfolioItem) -> None:
    item.is_deleted = True
    item.updated_at = datetime.now()
    db.commit()


def report(db: Session, teacher_id: int) -> dict:
    """成长报告数据：按类型聚合 + 时间线明细。"""
    items, total = list_items(db, teacher_id)
    counts: dict[str, int] = {key: 0 for key in TYPE_LABELS}
    for it in items:
        key = it["item_type"]
        counts[key] = counts.get(key, 0) + 1

    teacher = db.query(User).filter(User.id == teacher_id).first()
    return {
        "teacher_id": teacher_id,
        "teacher_name": teacher.name if teacher else "",
        "total": total,
        "by_type": [
            {"type": key, "label": label, "count": counts.get(key, 0)}
            for key, label in TYPE_LABELS.items()
        ],
        "items": items,
        "generated_at": datetime.now().isoformat(),
    }


def serialize(item: TeacherPortfolioItem) -> dict:
    return _serialize(item)