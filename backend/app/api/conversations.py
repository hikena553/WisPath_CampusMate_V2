from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage, ConversationType, ProjectTemplate, PROJECT_STAGES
from app.utils.enum_helpers import safe_enum_val

router = APIRouter(prefix="/api/agent", tags=["conversations"])

PROJECT_GREETINGS = {
    "competition": "你好！欢迎开始「{title}」学科竞赛项目 🏆\n\n我是绵小城，会全程协助你从赛前准备到答辩展示。请告诉我你现在处于哪个阶段，或者需要我帮你做些什么？",
    "thesis": "你好！欢迎开始「{title}」毕业论文项目 📖\n\n我会协助你从选题开题到答辩的全流程。目前你有什么初步想法吗？",
    "practice": "你好！欢迎开始「{title}」社会实践项目 🌟\n\n我会协助你完成方案申报到总结评优的全过程。请告诉我你的计划？",
    "certificate": "你好！欢迎开始「{title}」证书考取项目 📚\n\n我会陪你一起备考，从考情分析到考前冲刺。你打算报考哪个考试？",
    "student_work": "你好！欢迎开始「{title}」学生工作项目 ✨\n\n我会协助你完成活动策划到复盘总结。目前有什么想法吗？",
    "custom": "你好！欢迎开始「{title}」项目 🚀\n\n我会全程协助你推进这个项目。请告诉我你的目标和计划？",
}


@router.get("/conversations")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 清理15天前的旧会话
    cutoff = datetime.now(timezone.utc) - timedelta(days=15)
    old = db.query(Conversation).filter(
        Conversation.user_id == user.id,
        Conversation.updated_at < cutoff,
    ).all()
    for c in old:
        db.query(ConversationMessage).filter(ConversationMessage.conversation_id == c.id).delete()
        db.delete(c)
    db.commit()

    convos = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).order_by(Conversation.updated_at.desc()).limit(100).all()
    return [{
        "id": c.id,
        "title": c.title,
        "type": safe_enum_val(c.type),
        "project_template": c.project_template,
        "project_stage": c.project_stage,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    } for c in convos]


@router.post("/conversations")
def create_conversation(body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ctype = body.get("type", "normal")
    template = body.get("project_template")
    title = body.get("title", "")
    if not title:
        title = {"competition": "学科竞赛", "thesis": "毕业论文", "practice": "社会实践",
                 "certificate": "证书考取", "student_work": "学生工作", "custom": "自定义项目"}.get(template, "新对话")
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
        greeting = PROJECT_GREETINGS.get(template, PROJECT_GREETINGS["custom"]).format(title=title)
        msg = ConversationMessage(conversation_id=conv.id, role="assistant", content=greeting)
        db.add(msg)
        db.commit()

    return {
        "id": conv.id,
        "title": conv.title,
        "type": safe_enum_val(conv.type),
        "project_template": conv.project_template,
        "project_stage": conv.project_stage,
        "is_active": conv.is_active,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


@router.put("/conversations/{conv_id}")
def update_conversation(conv_id: int, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(404, "对话不存在")
    if "title" in body:
        conv.title = body["title"]
    if "project_stage" in body:
        conv.project_stage = body["project_stage"]
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "ok"}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(404, "对话不存在")
    db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv_id).delete()
    db.delete(conv)
    db.commit()
    return {"message": "deleted"}


@router.get("/conversations/{conv_id}/messages")
def get_messages(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(404, "对话不存在")
    msgs = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conv_id
    ).order_by(ConversationMessage.timestamp).all()
    return [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "timestamp": m.timestamp.isoformat(),
    } for m in msgs]


@router.post("/conversations/{conv_id}/messages")
def add_message(conv_id: int, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(404, "对话不存在")
    msg = ConversationMessage(
        conversation_id=conv_id,
        role=body["role"],
        content=body["content"],
    )
    db.add(msg)
    if conv.title == "新对话" and body.get("user_message"):
        title = body["user_message"][:20] + ("…" if len(body["user_message"]) > 20 else "")
        conv.title = title
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "timestamp": msg.timestamp.isoformat(),
    }
