"""失物招领工具 handlers：记录序列化、检索（含模糊匹配）、登记。"""

from sqlalchemy.orm import Session

from app.models.lost_found import ItemStatus, ItemType, LostFoundItem
from app.models.user import User
from app.utils.enum_helpers import safe_enum_str




# ============ 失物招领工具 ============

_LOST_FOUND_TYPE_NAMES = {"lost": "寻物启事", "found": "招领信息"}
_LOST_FOUND_STATUS_NAMES = {"open": "待处理", "claimed": "已认领", "closed": "已关闭"}


def _serialize_lost_found_item(db: Session, item: LostFoundItem, score: float | None = None) -> dict:
    """把失物招领记录序列化为便于 LLM 阅读的字典。"""
    owner = db.query(User).filter(User.id == item.user_id).first()
    contact = (item.contact or "").strip()
    if not contact and owner:
        contact = (owner.phone or "").strip() or owner.username
    type_val = safe_enum_str(item.type, "")
    status_val = safe_enum_str(item.status, "")
    data = {
        "id": item.id,
        "type": _LOST_FOUND_TYPE_NAMES.get(type_val, type_val),
        "title": item.title,
        "description": (item.description or "")[:150],
        "location": item.location or "未填写",
        "contact": contact or "未提供",
        "publisher": owner.name if owner else "未知",
        "status": _LOST_FOUND_STATUS_NAMES.get(status_val, status_val),
        "image_url": item.image_url or "",
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else "",
    }
    if score is not None:
        data["match_score"] = score
    return data


def _search_lost_found(db: Session, args: dict, user: User) -> dict:
    keyword = (args.get("keyword") or "").strip()
    if not keyword:
        return {"success": False, "message": "缺少必要参数：keyword（物品关键词）"}

    item_type = (args.get("item_type") or "all").strip().lower()
    if item_type not in ("lost", "found", "all"):
        item_type = "all"
    try:
        limit = int(args.get("limit") or 5)
    except (TypeError, ValueError):
        limit = 5

    from app.services.lost_found_service import search_lost_found_items
    result = search_lost_found_items(db, keyword, item_type, limit)
    matches = result["matches"]

    if matches:
        items = [_serialize_lost_found_item(db, it, sc) for it, sc in matches]
        return {
            "success": True, "found": True, "keyword": keyword, "count": len(items),
            "matched": items, "candidates": [],
            "message": (
                f"失物招领处检索到 {len(items)} 条与「{keyword}」相关的记录。"
                "请判断哪条最可能是学生的物品，并把发布者、地点、联系方式告诉学生。"
                "已有记录时不要重复登记。"
            ),
        }

    candidates = [_serialize_lost_found_item(db, it) for it in result["candidates"]]
    if candidates:
        msg = (
            f"失物招领处没有与「{keyword}」直接匹配的记录。以下是最新 {len(candidates)} 条待处理记录，"
            "请先判断其中是否其实就有学生描述的物品；确认没有后再调用 create_lost_found 帮学生登记。"
        )
    else:
        msg = f"失物招领处没有与「{keyword}」相关的记录，也没有其他待处理记录，可以直接调用 create_lost_found 帮学生登记。"
    return {
        "success": True, "found": False, "keyword": keyword, "count": 0,
        "matched": [], "candidates": candidates, "scanned": result["scanned"],
        "message": msg,
    }


def _create_lost_found(db: Session, args: dict, user: User) -> dict:
    item_type = (args.get("type") or "lost").strip().lower()
    if item_type not in ("lost", "found"):
        return {"success": False, "message": "type 必须为 lost（寻物启事）或 found（招领信息）"}
    title = (args.get("title") or "").strip()
    if not title:
        return {"success": False, "message": "缺少必要参数：title（物品名称）"}

    contact = (args.get("contact") or "").strip() or (user.phone or "").strip() or user.username
    item = LostFoundItem(
        user_id=user.id,
        type=ItemType(item_type),
        title=title[:100],
        description=(args.get("description") or "")[:2000],
        location=(args.get("location") or "")[:200],
        contact=contact[:200],
        image_url=(args.get("image_url") or "").strip() or None,
        status=ItemStatus.OPEN,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    kind = _LOST_FOUND_TYPE_NAMES[item_type]
    where = f"，地点：{item.location}" if item.location else ""
    return {
        "success": True, "item_id": item.id, "type": item_type, "title": item.title,
        "message": (
            f"✅ 已在失物招领处发布{kind}：{item.title}{where}（编号 {item.id}），"
            f"联系方式 {item.contact}。请告知学生已登记完成，并提醒可随时补充物品特征或地点。"
        ),
    }
