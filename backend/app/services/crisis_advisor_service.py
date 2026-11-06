"""AI 处置推荐：针对单条心理预警生成结构化处置建议（scheme/steps/rationale/taboo）。

设计要点：
- 只喂脱敏事实清单（预警摘要/等级/趋势/画像风险/既往干预/家校沟通史），禁止编造；
- severe 强制附「24 小时内面谈」要求；
- 模型不可用时回退规则化建议，保证接口永远有内容（与态势研判 insight 同一降级模式）。
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.crisis import AIDialogSummary, InterventionType
from app.models.user import User
from app.services.crisis_service import get_crisis_trend
from app.services.student_insight_service import get_insight

logger = logging.getLogger(__name__)

_LEVEL_NAMES = {"severe": "高危", "moderate": "中度", "mild": "轻度", "normal": "正常"}


def _facts(db: Session, alert: AIDialogSummary) -> str:
    """把该生相关事实压成事实清单，模型只在此范围内研判。"""
    student = db.query(User).filter(User.id == alert.student_id).first()
    history = (
        db.query(AIDialogSummary)
        .filter(AIDialogSummary.student_id == alert.student_id)
        .order_by(AIDialogSummary.created_at.desc())
        .limit(10)
        .all()
    )
    past_interventions = [
        f"{h.created_at.strftime('%m-%d') if h.created_at else '?'} {h.intervention_type.value if h.intervention_type else '未登记'}"
        + ("（已闭环）" if h.resolved else "（未闭环）")
        for h in history
        if h.intervention_type is not None and h.id != alert.id
    ]
    level_counts: dict[str, int] = {}
    for h in history:
        key = h.level.value if hasattr(h.level, "value") else str(h.level)
        level_counts[key] = level_counts.get(key, 0) + 1

    return (
        f"学生：{student.name if student else '未知'}（历史预警 {len(history)} 条，其中高危 {level_counts.get('severe', 0)}、中度 {level_counts.get('moderate', 0)}）\n"
        f"本条预警：等级 {_LEVEL_NAMES.get(alert.level.value if hasattr(alert.level, 'value') else str(alert.level), str(alert.level))}，"
        f"触发信号：{(alert.keywords_matched or '').replace(',', '、') or '未记录'}\n"
        f"脱敏摘要：{(alert.summary or '')[:150]}\n"
        f"近 5 次预警趋势：{get_crisis_trend(db, alert.student_id)}（worsening=恶化/improving=好转/stable=平稳）\n"
        f"既往干预：{'；'.join(past_interventions[:5]) or '无'}\n"
    )


def _rule_advice(alert: AIDialogSummary, trend: str) -> dict:
    level = alert.level.value if hasattr(alert.level, "value") else str(alert.level)
    if level == "severe":
        return {
            "scheme": "转介心理咨询",
            "steps": [
                "24 小时内完成一次面对面谈话，确认当前安全状态",
                "联系学校心理中心进行专业评估与转介",
                "告知监护人，约定共同关注方案",
            ],
            "rationale": "高危预警按规程须当日面谈并转介专业评估；趋势为 " + trend,
            "taboo": ["避免追问细节或评判", "不独自承诺保密", "避免刺激性话题"],
        }
    if level == "moderate":
        return {
            "scheme": "谈话",
            "steps": [
                "48 小时内安排一次谈心谈话，了解近况与压力源",
                "设置 7 天内随访，观察情绪变化",
                "必要时联系心理中心咨询",
            ],
            "rationale": "中度预警需在两日内建立联系并持续随访；趋势为 " + trend,
            "taboo": ["避免追问学业压力", "多倾听少建议"],
        }
    return {
        "scheme": "谈话",
        "steps": [
            "本周内安排一次轻松场合的交流",
            "保持每周观察，登记情绪台账变化",
        ],
        "rationale": "轻度预警以观察和日常关怀为主；趋势为 " + trend,
        "taboo": ["避免过度关注造成压力"],
    }


_ADVICE_PROMPT_TEMPLATE = (
    "你是高校辅导员的心理危机处置助手。只依据下面的事实清单，为这条预警给出处置建议。\n\n"
    "{facts}\n"
    "要求：\n"
    "1. 只能使用事实清单中的信息，不得编造；\n"
    "2. scheme 从「谈话 / 转介心理咨询 / 约谈家长 / 建议休养观察」中选一个；\n"
    "3. steps 给 2~4 步当日可执行动作，每步不超过 25 字；\n"
    "4. rationale 60 字以内说明推荐理由；\n"
    "5. taboo 给 2~3 条沟通禁忌，每条不超过 15 字；\n"
    "6. 语气专业克制，不做医学诊断；\n"
    "7. 只输出 JSON：{{\"scheme\": \"…\", \"steps\": [\"…\"], \"rationale\": \"…\", \"taboo\": [\"…\"]}}"
)


def _parse_advice(text: str) -> dict | None:
    raw = (text or "").strip()
    left, right = raw.find("{"), raw.rfind("}")
    if left == -1 or right <= left:
        return None
    try:
        obj = json.loads(raw[left:right + 1])
    except Exception:
        return None
    scheme = str(obj.get("scheme") or "").strip()
    steps = [str(s).strip() for s in (obj.get("steps") or []) if str(s).strip()][:4]
    rationale = str(obj.get("rationale") or "").strip()[:200]
    taboo = [str(t).strip() for t in (obj.get("taboo") or []) if str(t).strip()][:3]
    if not scheme or not steps or not rationale:
        return None
    return {"scheme": scheme, "steps": steps, "rationale": rationale, "taboo": taboo}


async def get_advice(db: Session, alert: AIDialogSummary) -> dict:
    """单条预警处置建议：LLM 研判 → 失败回退规则化。severe 强制附 24h 面谈。"""
    trend = get_crisis_trend(db, alert.student_id)
    fallback = _rule_advice(alert, trend)
    level = alert.level.value if hasattr(alert.level, "value") else str(alert.level)
    if level == "severe" and not any("24 小时" in s for s in fallback["steps"]):
        fallback["steps"].insert(0, "24 小时内完成面对面谈话")

    # 画像风险证据（失败不阻塞）
    try:
        insight = await get_insight(db, alert.student_id, days=30)
        insight_line = f"画像风险：{insight.get('profile', {}).get('risk_level', '未知')}"
    except Exception:
        insight_line = ""

    facts = _facts(db, alert) + (insight_line + "\n" if insight_line else "")
    try:
        from app.services.llm_service import complete
        text = await complete(
            _ADVICE_PROMPT_TEMPLATE.format(facts=facts), temperature=0.3, max_tokens=500
        )
        parsed = _parse_advice(text)
        if not parsed:
            return {**fallback, "source": "rule", "generated_at": datetime.now(timezone.utc).isoformat()}
        if level == "severe" and not any("24 小时" in s for s in parsed["steps"]):
            parsed["steps"].insert(0, "24 小时内完成面对面谈话")
        parsed["source"] = "ai"
        parsed["generated_at"] = datetime.now(timezone.utc).isoformat()
        return parsed
    except Exception:
        logger.warning("处置建议生成失败，使用规则化建议 alert=%s", alert.id, exc_info=True)
        return {**fallback, "source": "rule", "generated_at": datetime.now(timezone.utc).isoformat()}
