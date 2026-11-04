"""教师成长档案服务：成长档案的唯一入口（增删改查 + 成长报告聚合）。"""
import json
import logging
import re
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.teacher_portfolio import (
    PortfolioItemType,
    PortfolioVisibility,
    TeacherPortfolioItem,
)
from app.models.user import User

logger = logging.getLogger(__name__)

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
        # occurred_on 可为空：MySQL 不支持 NULLS LAST，改用 is_(None) 升序把空值排到最后
        query.order_by(
            TeacherPortfolioItem.occurred_on.is_(None),
            TeacherPortfolioItem.occurred_on.desc(),
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


def _parse_date(value: object) -> date | None:
    """从模型输出中提取合法日期；无法识别则返回空，交给老师自己补。"""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _fallback_ai_draft(description: str, item_type: PortfolioItemType) -> dict:
    """模型不可用时的本地兜底：只整理老师口述，不编造额外事实。"""
    text = (description or "").strip()
    first = re.split(r"[。！？!?\n]", text, maxsplit=1)[0].strip()
    title = first[:40] or f"{TYPE_LABELS[item_type.value]}记录"
    if len(title) < 6:
        title = f"{TYPE_LABELS[item_type.value]}：{title}"
    reflection = (
        f"{text.rstrip('。')}。回顾这次经历，我梳理了事情背景、处理过程与实际效果，"
        "也记下了可继续沿用的做法和需要改进的地方。"
    )[:1000]
    return {
        "item_type": item_type.value,
        "title": title[:200],
        "occurred_on": None,
        "reflection": reflection,
        "source": "rule",
    }


def _guess_type(text: str) -> PortfolioItemType:
    """兜底时从口述关键词判断档案类型，不依赖前端已选内容。"""
    rules: list[tuple[PortfolioItemType, tuple[str, ...]]] = [
        (PortfolioItemType.TRAINING, ("培训", "研修", "讲座", "学习班", "课程学习")),
        (PortfolioItemType.HONOR, ("获奖", "荣誉", "表彰", "称号", "获评", "一等奖", "二等奖", "三等奖")),
        (PortfolioItemType.RESEARCH, ("研究", "论文", "课题", "调研", "成果")),
    ]
    for item_type, keywords in rules:
        if any(k in text for k in keywords):
            return item_type
    return PortfolioItemType.CASE


async def ai_draft(description: str, item_type: str | PortfolioItemType | None = None) -> dict:
    """AI 帮写：老师口述大体情况 → 自动填充类型、标题、日期与反思，供其确认。"""
    desc = (description or "").strip()[:500]
    default_type = _item_type(item_type) if item_type else _guess_type(desc)
    fallback = _fallback_ai_draft(desc, default_type)

    prompt = (
        "你是高校辅导员的育人档案整理助手。请根据老师的口述，整理成一条可直接入库的育人档案。\n"
        "档案类型：case=工作案例，honor=荣誉表彰，training=培训研修，research=工作研究成果。\n"
        f"老师口述：{desc}\n"
        "要求：\n"
        "1. title 不超过 40 字，概括这件事或成果，具体、不空泛；\n"
        "2. item_type 根据口述内容从四类中选最贴切的一类；\n"
        "3. occurred_on 尽量从口述中提取日期，格式 YYYY-MM-DD，无法确定则为 null；\n"
        "4. reflection 用第一人称写 120–300 字，包含背景、做法、效果与反思，"
        "保留口述中的具体细节，不得编造未提到的人名、数据或结果；\n"
        "5. 只输出 JSON，不要解释。格式："
        '{"item_type":"case","title":"标题","occurred_on":"2026-11-01","reflection":"反思正文"}'
    )
    try:
        from app.services.llm_service import _parse_json_loose, complete

        raw = await complete(prompt, temperature=0.4, max_tokens=800)
        data = _parse_json_loose(raw) or {}
        title = str(data.get("title") or "").strip()[:200]
        reflection = str(data.get("reflection") or "").strip()[:1000]
        if not title or len(reflection) < 20:
            raise ValueError("模型未返回完整的档案内容")
        raw_type = data.get("item_type")
        valid_type = raw_type if isinstance(raw_type, str) and raw_type in TYPE_LABELS else None
        return {
            "item_type": valid_type or default_type.value,
            "title": title,
            "occurred_on": _parse_date(data.get("occurred_on")),
            "reflection": reflection,
            "source": "ai",
        }
    except Exception:
        # 未配置模型 / 网络异常 / 输出不合法：静默降级，保证按钮永远有结果
        logger.warning("育人档案 AI 帮写失败，使用本地兜底", exc_info=True)
        return fallback