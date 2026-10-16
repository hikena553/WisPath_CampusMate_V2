import json
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.user import User
from app.services.llm_service import _get_llm_config
from app.services.prompts import build_crisis_summary_prompt, build_semantic_risk_prompt
from app.utils.enum_helpers import safe_enum_val

CRISIS_KEYWORDS = [
    "失眠", "睡不着", "焦虑", "抑郁", "压力大", "不想活", "自杀",
    "自残", "想死", "没意思", "活着累", "撑不住", "崩溃", "绝望",
    "不想上学", "害怕", "心慌", "难受", "想哭",
]

# 设置表中的配置键名
SETTING_CRISIS_KEYWORDS = "crisis_keywords"
SETTING_NOTIFY_COUNSELOR = "auto_notify_counselor"


def get_crisis_keywords(db: Session | None = None) -> list[str]:
    """获取生效的危机预警敏感词：优先读取设置表中的管理员配置，未配置时回退内置默认词库。"""
    if db is not None:
        try:
            from app.models.setting import SystemSetting
            row = (
                db.query(SystemSetting)
                .filter(SystemSetting.key == SETTING_CRISIS_KEYWORDS)
                .first()
            )
            if row and row.value:
                custom = [k.strip() for k in re.split(r"[,，、;；\s]+", str(row.value)) if k.strip()]
                if custom:
                    return custom
        except Exception:
            pass
    return list(CRISIS_KEYWORDS)


def detect_crisis_keywords(text: str, db: Session | None = None) -> list[str]:
    matched = []
    for kw in get_crisis_keywords(db):
        if kw in text:
            matched.append(kw)
    return matched


async def generate_crisis_summary(user_message: str, ai_reply: str, keywords: list[str]) -> dict | None:
    if not keywords:
        return None
    try:
        from app.services.llm_service import _get_client as get_client
        prompt = build_crisis_summary_prompt(
            user_message=user_message, ai_reply=ai_reply, keywords=keywords
        )

        config = _get_llm_config()
        resp = await get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        result = json.loads(content)
        return result
    except Exception:
        return {
            "summary": f"学生消息中包含敏感关键词：{', '.join(keywords)}",
            "level": "mild",
        }


async def save_crisis_summary(db: Session, student_id: int, user_message: str, ai_reply: str, keywords: list[str]):
    if not keywords:
        return
    result = await generate_crisis_summary(user_message, ai_reply, keywords)
    if not result:
        return
    summary = AIDialogSummary(
        student_id=student_id,
        summary=result.get("summary", ""),
        level=result.get("level", "mild"),
        keywords_matched=",".join(keywords),
        raw_snippet=user_message[:200],
    )
    db.add(summary)
    db.commit()


async def analyze_semantic_risk(user_message: str, context: list[dict] | None = None) -> dict | None:
    from app.services.llm_service import _get_client as get_client
    prompt = build_semantic_risk_prompt(user_message)
    try:
        config = _get_llm_config()
        resp = await get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception:
        return None


def get_crisis_trend(db: Session, student_id: int) -> str:
    crises = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).limit(5).all()
    if len(crises) < 2:
        return "stable"
    risk_values = {"normal": 0, "mild": 1, "moderate": 2, "severe": 3}
    levels = [risk_values.get(safe_enum_val(c.level) or "normal", 0) for c in crises]
    if levels == sorted(levels, reverse=True):
        return "worsening"
    if levels == sorted(levels):
        return "improving"
    return "stable"
