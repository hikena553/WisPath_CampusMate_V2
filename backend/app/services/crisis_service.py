import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

try:
    import jieba
except ModuleNotFoundError:  # pragma: no cover
    # 环境未安装 jieba 时，回退加载项目 vendor_packages 目录内置的同版本副本
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor_packages"))
    import jieba

from app.core.database import SessionLocal
from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.user import User
from app.schemas.crisis import (
    CrisisAnalyticsOut,
    CrisisKeywordOut,
    CrisisLevelDistOut,
    CrisisSlaItemOut,
    CrisisSlaOut,
    CrisisStageOut,
    CrisisTrendPointOut,
)
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


# ============================ 工作台聚合分析 ============================

# 词云停用词：常见虚词/口语词，过滤后保留高信息量关键词
_CRISIS_STOPWORDS = {
    "的", "了", "和", "是", "在", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "有", "就", "不", "都", "也", "很", "吗", "啊", "呢", "吧", "个", "这", "那",
    "等", "与", "及", "或", "从", "去", "为", "之", "对", "到", "中", "上", "下",
    "一个", "没有", "可以", "希望", "觉得", "感觉",
}

# SLA 口径：未闭环且创建超 24 小时计 overdue，12~24 小时计 due_soon
_SLA_OVERDUE_HOURS = 24
_SLA_DUE_SOON_HOURS = 12
# SLA 清单最多返回条数（前端卡片同样只展示 5 条）
_SLA_ITEM_LIMIT = 5


def _crisis_keywords(rows: list[AIDialogSummary], top_n: int) -> list[CrisisKeywordOut]:
    """对预警命中关键词 + 摘要做 jieba 分词统计，返回高频词（词云数据）。

    分词/停用词/相邻双词组合的过滤口径与反馈词云保持一致（feedback_service）：
    允许单字中文，丢弃纯英文单字符、纯数字、纯标点与停用词。
    """
    pieces: list[str] = []
    for row in rows:
        if row.keywords_matched:
            pieces.append(row.keywords_matched)
        if row.summary:
            pieces.append(row.summary)

    full_text = "\n".join(pieces)
    if not full_text.strip():
        return []

    tokens: list[str] = []
    for word in jieba.lcut(full_text):
        w = word.strip()
        if not w:
            continue
        if re.fullmatch(r"[\dA-Za-z]", w):
            continue
        if len(w) < 2 and not re.fullmatch(r"[\u4e00-\u9fa5]", w):
            continue
        if w in _CRISIS_STOPWORDS:
            continue
        if not re.search(r"[\u4e00-\u9fa5a-zA-Z0-9]", w):
            continue
        if re.fullmatch(r"[\d\W_]+", w):
            continue
        tokens.append(w)

    counter: Counter = Counter(tokens)
    for i in range(len(tokens) - 1):
        left, right = tokens[i], tokens[i + 1]
        if len(left) >= 2 and len(right) >= 2:
            counter[left + right] += 1

    return [CrisisKeywordOut(word=w, count=c) for w, c in counter.most_common(top_n)]


def analytics(db: Session, teacher_id: int | None, days: int = 30, top_n: int = 40) -> CrisisAnalyticsOut:
    """心理预警工作台聚合分析。

    teacher_id 为 None 表示管理员（全量口径）；否则仅统计该教师名下学生
    （User.tutor_id == teacher_id），与 API 层 _filter_by_tutor 一致。
    """
    days = max(1, min(int(days or 30), 365))
    top_n = max(1, min(int(top_n or 40), 200))

    if teacher_id is None:
        rows = db.query(AIDialogSummary).all()
    else:
        student_ids = [s.id for s in db.query(User).filter(User.tutor_id == teacher_id).all()]
        rows = (
            db.query(AIDialogSummary).filter(AIDialogSummary.student_id.in_(student_ids)).all()
            if student_ids else []
        )

    level_dist = CrisisLevelDistOut()
    stage = CrisisStageOut(found=len(rows))
    unresolved = 0
    high_risk = 0

    for row in rows:
        level = safe_enum_val(row.level) or CrisisLevel.NORMAL.value
        if level in ("severe", "moderate", "mild"):
            setattr(level_dist, level, getattr(level_dist, level) + 1)
        else:
            level_dist.normal += 1

        if row.intervention_type is not None:
            stage.intervened += 1
        if row.resolved:
            stage.closed += 1
        else:
            unresolved += 1
            if row.follow_up_date is not None:
                stage.following += 1
            if level == CrisisLevel.SEVERE.value:
                high_risk += 1

    # ---- 趋势：以本地日期为锚，近 days 天按 created_at 逐日计数（补齐 0 值，避免折线断点）----
    today = date.today()
    start = today - timedelta(days=days - 1)
    buckets: dict[date, int] = {}
    for row in rows:
        if not row.created_at:
            continue
        d = row.created_at.date()
        if start <= d <= today:
            buckets[d] = buckets.get(d, 0) + 1
    trend = [
        CrisisTrendPointOut(day=(start + timedelta(days=i)).strftime("%m-%d"),
                            count=buckets.get(start + timedelta(days=i), 0))
        for i in range(days)
    ]

    # ---- 时限：未闭环按创建时间计算 SLA 滞留时长 ----
    now = datetime.now(timezone.utc)
    sla_rows: list[tuple[bool, datetime, AIDialogSummary]] = []
    for row in rows:
        if row.resolved or not row.created_at:
            continue
        created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
        hours = (now - created).total_seconds() / 3600
        if hours > _SLA_OVERDUE_HOURS:
            sla_rows.append((True, created, row))
        elif hours >= _SLA_DUE_SOON_HOURS:
            sla_rows.append((False, created, row))

    overdue = sum(1 for is_overdue, _, _ in sla_rows if is_overdue)
    due_soon = len(sla_rows) - overdue

    # 最逾期（创建最早）在前，最多 5 条
    sla_rows.sort(key=lambda item: item[1])
    items: list[CrisisSlaItemOut] = []
    name_map: dict[int, str] = {}
    for _, _, row in sla_rows[:_SLA_ITEM_LIMIT]:
        if row.student_id not in name_map:
            student = db.query(User).filter(User.id == row.student_id).first()
            name_map[row.student_id] = student.name if student else ""
        items.append(CrisisSlaItemOut(
            id=row.id,
            student_name=name_map[row.student_id],
            summary=row.summary or "",
            created_at=row.created_at.isoformat() if row.created_at else "",
        ))

    return CrisisAnalyticsOut(
        level_dist=level_dist,
        stage=stage,
        trend=trend,
        keywords=_crisis_keywords(rows, top_n),
        sla=CrisisSlaOut(overdue=overdue, due_soon=due_soon, items=items),
        total=len(rows),
        unresolved=unresolved,
        high_risk=high_risk,
    )
