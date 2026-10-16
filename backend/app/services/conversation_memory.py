import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationMessage
from app.models.profile import ConversationSummary
from app.services.llm_service import _get_client, _get_llm_config
from app.services.prompts import build_conversation_summary_prompt

logger = logging.getLogger(__name__)


async def summarize_conversation(db: Session, conversation_id: int) -> ConversationSummary | None:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return None
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id
    ).order_by(ConversationMessage.timestamp.asc()).all()
    if not messages:
        return None

    message_text = "\n".join(
        f"{m.role}: {m.content[:200]}" for m in messages if m.content
    )
    prompt = build_conversation_summary_prompt(message_text)
    try:
        config = _get_llm_config()
        resp = await _get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        result = json.loads(content)
        summary = ConversationSummary(
            conversation_id=conversation_id,
            student_id=conv.user_id,
            summary=result.get("summary", ""),
            key_insights=result.get("key_insights", {}),
            topics=result.get("topics", []),
            sentiment=result.get("sentiment", "neutral"),
            message_count=len(messages),
        )
        db.add(summary)
        db.commit()
        return summary
    except Exception:
        logger.exception("对话摘要生成失败")
        return None


def get_relevant_memories(db: Session, student_id: int, current_message: str, limit: int = 3) -> str:
    summaries = db.query(ConversationSummary).filter(
        ConversationSummary.student_id == student_id
    ).order_by(ConversationSummary.created_at.desc()).limit(limit).all()
    if not summaries:
        return ""
    parts = []
    for s in summaries:
        insights = s.key_insights or {}
        concerns = insights.get("concerns", [])
        skills = insights.get("skills", [])
        interests = insights.get("interests", [])
        extras = []
        if concerns:
            extras.append(f"关注点：{', '.join(concerns[:3])}")
        if skills:
            extras.append(f"技能：{', '.join(skills[:3])}")
        if interests:
            extras.append(f"兴趣：{', '.join(interests[:3])}")
        extra = "；".join(extras)
        if extra:
            parts.append(f"[{s.created_at.strftime('%m-%d')}] {s.summary}（{extra}）")
        else:
            parts.append(f"[{s.created_at.strftime('%m-%d')}] {s.summary}")
    return "；".join(parts) if parts else ""


async def summarize_conversation_by_student(db: Session, student_id: int, conversation_id: int) -> ConversationSummary | None:
    return await summarize_conversation(db, conversation_id)
