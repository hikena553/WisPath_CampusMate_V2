from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage, ConversationType, ProjectTemplate, PROJECT_STAGES
from app.models.setting import SystemSetting
from app.utils.enum_helpers import safe_enum_val

router = APIRouter(prefix="/api/agent", tags=["conversations"])

PROJECT_GREETINGS = {
    "competition": "你好！欢迎开始「{title}」学科竞赛项目 🏆\n\n我是{agent_name}，会全程协助你从赛前准备到答辩展示。请告诉我你现在处于哪个阶段，或者需要我帮你做些什么？",
    "thesis": "你好！欢迎开始「{title}」毕业论文项目 📖\n\n我会协助你从选题开题到答辩的全流程。目前你有什么初步想法吗？",
    "practice": "你好！欢迎开始「{title}」社会实践项目 🌟\n\n我会协助你完成方案申报到总结评优的全过程。请告诉我你的计划？",
    "certificate": "你好！欢迎开始「{title}」证书考取项目 📚\n\n我会陪你一起备考，从考情分析到考前冲刺。你打算报考哪个考试？",
    "student_work": "你好！欢迎开始「{title}」学生工作项目 ✨\n\n我会协助你完成活动策划到复盘总结。目前有什么想法吗？",
    "custom": "你好！欢迎开始「{title}」项目 🚀\n\n我会全程协助你推进这个项目。请告诉我你的目标和计划？",
}

# 项目类型 → 默认标题（同时用于服务端关键词匹配的中文标签）
PROJECT_TITLES = {
    "competition": "学科竞赛",
    "thesis": "毕业论文",
    "practice": "社会实践",
    "certificate": "证书考取",
    "student_work": "学生工作",
    "custom": "自定义项目",
}

RETENTION_DAYS = 15
DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100
TITLE_MAX_LEN = 200
BATCH_ACTIONS = {"delete", "restore", "pin", "unpin", "archive", "unarchive"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(c: Conversation) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "type": safe_enum_val(c.type),
        "project_template": c.project_template,
        "project_stage": c.project_stage,
        "is_active": c.is_active,
        "pinned": c.pinned_at is not None,
        "archived": c.archived_at is not None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _purge_expired(db: Session, user_id: int) -> None:
    """清理 15 天前的旧会话（保留既有保留策略，仅从列表接口中抽出）"""
    cutoff = _now() - timedelta(days=RETENTION_DAYS)
    old = db.query(Conversation).filter(
        Conversation.user_id == user_id,
        Conversation.updated_at < cutoff,
    ).all()
    for c in old:
        db.query(ConversationMessage).filter(ConversationMessage.conversation_id == c.id).delete()
        db.delete(c)
    db.commit()


def _get_owned(db: Session, user: User, conv_id: int, *, allow_deleted: bool = False) -> Conversation:
    query = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id,
    )
    if not allow_deleted:
        query = query.filter(Conversation.deleted_at.is_(None))
    conv = query.first()
    if not conv:
        raise HTTPException(404, "对话不存在")
    return conv


def _clean_title(raw) -> str:
    title = (raw or "").strip()
    if not title:
        raise HTTPException(400, "标题不能为空")
    if len(title) > TITLE_MAX_LEN:
        raise HTTPException(400, f"标题不能超过 {TITLE_MAX_LEN} 个字符")
    return title


def _validate_stage(conv: Conversation, stage) -> str:
    allowed = PROJECT_STAGES.get(conv.project_template or "", [])
    if not allowed:
        raise HTTPException(400, "该对话不是阶段性项目，无法设置阶段")
    if stage not in allowed:
        raise HTTPException(400, f"阶段无效，可选：{'、'.join(allowed)}")
    return stage


@router.get("/conversations")
def list_conversations(
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    q: str | None = Query(None, description="按标题 / 项目阶段 / 项目类型搜索"),
    archived: bool = Query(False, description="true 查看已归档，false 查看进行中"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _purge_expired(db, user.id)

    query = db.query(Conversation).filter(
        Conversation.user_id == user.id,
        Conversation.deleted_at.is_(None),
    )
    if archived:
        query = query.filter(Conversation.archived_at.isnot(None))
    else:
        query = query.filter(Conversation.archived_at.is_(None))

    keyword = (q or "").strip().lower()
    if keyword:
        conditions = [
            func.lower(Conversation.title).contains(keyword, autoescape=True),
            func.lower(func.coalesce(Conversation.project_stage, "")).contains(keyword, autoescape=True),
        ]
        # 中文项目类型名（如「学科竞赛」）与英文 key（如 competition）同样可命中
        matched_templates = [
            key for key, label in PROJECT_TITLES.items()
            if keyword in label.lower() or keyword in key.lower()
        ]
        if matched_templates:
            conditions.append(Conversation.project_template.in_(matched_templates))
        query = query.filter(or_(*conditions))

    total = query.count()
    items = (
        query.order_by(
            Conversation.pinned_at.is_(None),
            Conversation.pinned_at.desc(),
            Conversation.updated_at.desc(),
            Conversation.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [_serialize(c) for c in items],
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(items) < total,
        "archived": archived,
    }


@router.post("/conversations")
def create_conversation(body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ctype = body.get("type", "normal")
    if ctype not in {t.value for t in ConversationType}:
        raise HTTPException(400, f"对话类型无效：{ctype}")
    template = body.get("project_template")
    if template and template not in {t.value for t in ProjectTemplate}:
        raise HTTPException(400, f"项目类型无效：{template}")

    raw_title = (body.get("title") or "").strip()
    if raw_title:
        title = _clean_title(raw_title)
    else:
        title = PROJECT_TITLES.get(template, "新对话")
    stages = PROJECT_STAGES.get(template, [])
    conv = Conversation(
        user_id=user.id,
        title=title,
        type=ConversationType(ctype),
        project_template=template,
        project_stage=stages[0] if stages else None,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    # 为项目对话自动添加欢迎语
    if ctype == "project" and template:
        agent_name = (
            db.query(SystemSetting).filter(SystemSetting.key == "agent_name").first()
        )
        agent_name = (agent_name.value if agent_name else "") or settings.AGENT_NAME
        greeting = PROJECT_GREETINGS.get(template, PROJECT_GREETINGS["custom"]).format(
            title=title, agent_name=agent_name
        )
        msg = ConversationMessage(conversation_id=conv.id, role="assistant", content=greeting)
        db.add(msg)
        db.commit()

    return _serialize(conv)


@router.put("/conversations/{conv_id}")
def update_conversation(conv_id: int, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = _get_owned(db, user, conv_id)

    changed = False
    if "title" in body:
        conv.title = _clean_title(body.get("title"))
        changed = True
    if "project_stage" in body:
        conv.project_stage = _validate_stage(conv, body.get("project_stage"))
        changed = True
    if "pinned" in body:
        conv.pinned_at = _now() if body["pinned"] else None
        changed = True
    if "archived" in body:
        conv.archived_at = _now() if body["archived"] else None
        changed = True

    if not changed:
        raise HTTPException(400, "没有需要更新的字段")

    conv.updated_at = _now()
    db.commit()
    db.refresh(conv)
    return _serialize(conv)


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """软删除：置 deleted_at，用户可在提示条里撤销；物理清理仍交给 15 天保留策略"""
    conv = _get_owned(db, user, conv_id)
    conv.deleted_at = _now()
    db.commit()
    return {"message": "deleted", "id": conv.id, "soft": True}


@router.post("/conversations/{conv_id}/restore")
def restore_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """撤销删除"""
    conv = _get_owned(db, user, conv_id, allow_deleted=True)
    if conv.deleted_at is None:
        return {"message": "not_deleted", "conversation": _serialize(conv)}
    conv.deleted_at = None
    db.commit()
    db.refresh(conv)
    return {"message": "restored", "conversation": _serialize(conv)}


@router.post("/conversations/batch")
def batch_conversations(body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """批量置顶 / 归档 / 删除 / 恢复：单事务提交，避免逐条请求造成半完成状态"""
    action = (body.get("action") or "").strip()
    if action not in BATCH_ACTIONS:
        raise HTTPException(400, f"批量操作无效：{action or '(空)'}")

    raw_ids = body.get("ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise HTTPException(400, "请选择要操作的对话")
    try:
        ids = [int(i) for i in raw_ids]
    except (TypeError, ValueError):
        raise HTTPException(400, "对话 ID 必须是整数")

    convs = db.query(Conversation).filter(
        Conversation.id.in_(ids),
        Conversation.user_id == user.id,
    ).all()

    now = _now()
    for c in convs:
        if action == "delete":
            c.deleted_at = now
        elif action == "restore":
            c.deleted_at = None
        elif action == "pin":
            c.pinned_at = now
        elif action == "unpin":
            c.pinned_at = None
        elif action == "archive":
            c.archived_at = now
        elif action == "unarchive":
            c.archived_at = None
    db.commit()

    return {
        "message": action,
        "updated": len(convs),
        "ids": [c.id for c in convs],
        "requested": len(ids),
    }


@router.get("/conversations/{conv_id}/messages")
def get_messages(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = _get_owned(db, user, conv_id, allow_deleted=True)
    msgs = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conv.id
    ).order_by(ConversationMessage.timestamp).all()
    return [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "timestamp": m.timestamp.isoformat(),
    } for m in msgs]


@router.post("/conversations/{conv_id}/messages")
def add_message(conv_id: int, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """兼容保留：正常对话由 agent_service 落库，该接口仅作为前端兜底写入"""
    conv = _get_owned(db, user, conv_id)
    role = body.get("role")
    if role not in {"user", "assistant"}:
        raise HTTPException(400, "role 只能是 user 或 assistant")
    content = body.get("content")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(400, "消息内容不能为空")

    msg = ConversationMessage(
        conversation_id=conv.id,
        role=role,
        content=content,
    )
    db.add(msg)
    if conv.title == "新对话" and body.get("user_message"):
        clean = str(body["user_message"]).replace("\n", " ").replace("\r", "").strip()
        if clean:
            conv.title = clean[:20] + ("…" if len(clean) > 20 else "")
    conv.updated_at = _now()
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "timestamp": msg.timestamp.isoformat(),
        "title": conv.title,
    }