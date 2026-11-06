import json
import logging
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
    CrisisInsightOut,
    CrisisKeywordOut,
    CrisisLevelDistOut,
    CrisisSlaItemOut,
    CrisisSlaOut,
    CrisisStageOut,
    CrisisTrendPointOut,
)
from app.services.llm_service import _get_llm_config, complete
from app.services.prompts import build_crisis_summary_prompt, build_semantic_risk_prompt, build_short_term_triage_prompt
from app.utils.enum_helpers import safe_enum_val

logger = logging.getLogger(__name__)

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


# ============================ 智能分析（态势研判） ============================


def _insight_facts(data: CrisisAnalyticsOut, days: int) -> str:
    """把聚合指标压成一份事实清单，模型只在此范围内做研判，避免编造。"""
    recent7 = sum(p.count for p in data.trend[-7:])
    close_rate = round(data.stage.closed / data.total * 100) if data.total else 0
    top_kw = "、".join(f"{k.word}({k.count})" for k in data.keywords[:6]) or "无"
    return (
        f"趋势区间：近 {days} 天\n"
        f"预警总数（全量口径，不是近 {days} 天）{data.total}，未闭环 {data.unresolved}，其中高危未闭环 {data.high_risk}\n"
        f"等级分布：高危 {data.level_dist.severe}，中度 {data.level_dist.moderate}，"
        f"轻度 {data.level_dist.mild}，正常 {data.level_dist.normal}\n"
        f"处置阶段：发现 {data.stage.found}，已干预 {data.stage.intervened}，"
        f"随访中 {data.stage.following}，已闭环 {data.stage.closed}（闭环率 {close_rate}%）\n"
        f"处置时限：超过 24 小时未办结 {data.sla.overdue} 条，12~24 小时临期 {data.sla.due_soon} 条\n"
        f"近 7 天新增预警 {recent7} 条\n"
        f"高频敏感词：{top_kw}"
    )


def _insight_prompt(data: CrisisAnalyticsOut, days: int) -> str:
    return (
        "你是高校辅导员心理预警工作台的研判助手。请只依据下面的统计结果，"
        "输出一段态势研判和今天就能执行的处置建议。\n\n"
        f"{_insight_facts(data, days)}\n\n"
        "要求：\n"
        "1. 只能使用上面的数字与词条，不得编造学生姓名、事件或数据；"
        f"描述预警总数时用全量口径，只有趋势可以写「近 {days} 天」；\n"
        "2. summary 为 60~100 字的态势判断，点出风险集中点与当前处置压力"
        "（如高危未闭环、超时积压、近期趋势），并给出总体判断；\n"
        "3. advice 给 2~3 条当日可执行的处置建议，每条不超过 30 字，按优先级排序；\n"
        "4. 语气专业克制，不做医学诊断，不夸大风险；\n"
        "5. 只输出 JSON，不要代码块与解释："
        '{"summary": "…", "advice": ["…", "…"]}'
    )


def _parse_insight(text: str) -> tuple[str, list[str]] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    left, right = raw.find("{"), raw.rfind("}")
    if left != -1 and right > left:
        raw = raw[left:right + 1]
    try:
        obj = json.loads(raw)
    except Exception:
        return None
    summary = str(obj.get("summary") or "").strip()
    advice = [str(item).strip() for item in (obj.get("advice") or []) if str(item).strip()]
    if len(summary) < 8 or not advice:
        return None
    return summary[:240], advice[:3]


def _rule_insight(data: CrisisAnalyticsOut, days: int) -> CrisisInsightOut:
    """模型不可用时的规则化研判：保证「智能分析」始终有可读结论。"""
    now = datetime.now(timezone.utc).isoformat()
    if data.total <= 0:
        return CrisisInsightOut(
            summary="暂未发现预警记录，整体风险平稳，保持日常观察即可。",
            advice=[
                "留意近期情绪波动较大的学生，发现异常及时登记预警。",
                "对已闭环学生保持每周一次的回访，确认状态稳定。",
            ],
            source="rule",
            generated_at=now,
        )

    parts = [f"当前共 {data.total} 条预警，未闭环 {data.unresolved} 条"]
    if data.high_risk:
        parts.append(f"高危未闭环 {data.high_risk} 条")
    if data.sla.overdue:
        parts.append(f"超 24 小时未办结 {data.sla.overdue} 条")
    if data.sla.due_soon:
        parts.append(f"临期 {data.sla.due_soon} 条")
    summary = "，".join(parts) + "。"
    top_kw = data.keywords[:3]
    if top_kw:
        summary += f"高频信号集中在「{'、'.join(k.word for k in top_kw)}」。"

    advice: list[str] = []
    if data.high_risk:
        advice.append(f"优先面谈 {data.high_risk} 名高危学生，今日完成干预登记。")
    if data.sla.overdue:
        advice.append(f"{data.sla.overdue} 条预警已超 24 小时，今日补齐处置记录。")
    if data.sla.due_soon:
        advice.append(f"{data.sla.due_soon} 条预警将在 12~24 小时到期，提前安排跟进。")
    if len(advice) < 2 and data.unresolved:
        rest = max(data.unresolved - data.high_risk, 0)
        if rest:
            advice.append(f"其余 {rest} 条未闭环预警分批安排谈话，避免积压。")
    if len(advice) < 2:
        advice.append("保持与班级心理委员的联系，持续收集新的情绪信号。")

    return CrisisInsightOut(
        summary=summary[:240],
        advice=advice[:3],
        source="rule",
        generated_at=now,
    )


async def insight(db: Session, teacher_id: int | None, days: int = 30) -> CrisisInsightOut:
    """处置态势智能分析：聚合指标 → 模型研判；失败或未配置时回退规则化结论。"""
    days = max(1, min(int(days or 30), 365))
    data = analytics(db, teacher_id=teacher_id, days=days)
    fallback = _rule_insight(data, days)
    if data.total <= 0:
        return fallback
    try:
        text = await complete(_insight_prompt(data, days), temperature=0.3, max_tokens=700)
        parsed = _parse_insight(text)
        if not parsed:
            return fallback
        summary, advice = parsed
        return CrisisInsightOut(
            summary=summary,
            advice=advice,
            source="ai",
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception:
        logger.warning("危机智能分析生成失败，使用规则化研判", exc_info=True)
        return fallback


# ============================ 双轨降噪：硬词直通 + 短时情绪分流 ============================

# 极端行为信号词：命中即旁路一切降噪，直接进预警工作台并实时推送（fail-open）。
# 注意：只收「行为/手段类」词；"不想活/想死"这类情绪化表达交给 LLM 短时研判分流，
# 避免随口抱怨全部触发硬词直通造成狼来了效应。
EXTREME_KEYWORDS = [
    "自杀", "自残", "割腕", "跳楼", "轻生", "了结", "安眠药", "遗书",
]
# 计划/方式暗示词：与极端词同现时等级升至 severe
_PLAN_HINT_WORDS = ["计划", "准备", "遗书", "告别", "明天", "今晚", "已经买", "攒了"]

SETTING_EXTREME_KEYWORDS = "crisis_extreme_keywords"
TRIAGE_SOURCE_HARD_GATE = "hard_gate"
TRIAGE_SOURCE_LLM = "llm"
TRIAGE_SOURCE_FREQUENCY = "frequency"

# 同一学生同词去重窗口（小时内不重复落库）
_DEDUPE_HOURS = 2
# 频次升级：近 7 天情绪台账 ≥ N 条或同词 ≥ M 次，强制生成 mild 预警
_LEDGER_ESCALATION_COUNT = 5
_SAME_KEYWORD_ESCALATION_COUNT = 3


def get_extreme_keywords(db: Session | None = None) -> list[str]:
    """极端行为信号词：管理员可经 SystemSetting 覆盖，未配置时回退内置词库。"""
    if db is not None:
        try:
            from app.models.setting import SystemSetting
            row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_EXTREME_KEYWORDS).first()
            if row and row.value:
                custom = [k.strip() for k in re.split(r"[,，、;；\s]+", str(row.value)) if k.strip()]
                if custom:
                    return custom
        except Exception:
            pass
    return list(EXTREME_KEYWORDS)


def detect_extreme_keywords(text: str, db: Session | None = None) -> list[str]:
    return [kw for kw in get_extreme_keywords(db) if kw in text]


def _recent_signal_counts(db: Session, student_id: int) -> tuple[int, int]:
    """近 24h 信号窗口：历史预警条数 + 负面情绪台账条数。"""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    alert_count = (
        db.query(AIDialogSummary)
        .filter(AIDialogSummary.student_id == student_id, AIDialogSummary.created_at >= since)
        .count()
    )
    from app.models.emotion import EmotionRecord
    emo_count = (
        db.query(EmotionRecord)
        .filter(
            EmotionRecord.user_id == student_id,
            EmotionRecord.source == "ai_dialog",
            EmotionRecord.created_at >= since,
        )
        .count()
    )
    return alert_count, emo_count


async def judge_short_term_risk(
    db: Session,
    student_id: int,
    user_message: str,
    ai_reply: str,
    keywords: list[str],
) -> tuple[str, str]:
    """24h 窗口短时情绪研判。失败时 fail-open 判 mid（轻度预警，不进台账）。"""
    alert_count, emo_count = _recent_signal_counts(db, student_id)
    try:
        from app.services.llm_service import _get_client as get_client
        prompt = build_short_term_triage_prompt(
            user_message=user_message,
            ai_reply=ai_reply,
            keywords=keywords,
            recent_alert_count=alert_count,
            recent_negative_emotions=emo_count,
        )
        config = _get_llm_config()
        resp = await get_client().chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        obj = json.loads(resp.choices[0].message.content or "{}")
        risk = str(obj.get("acute_risk") or "").strip().lower()
        reason = str(obj.get("reason") or "").strip()[:200]
        if risk in ("none", "low", "mid", "high"):
            return risk, reason or "模型未给出理由"
        return "mid", "研判结果异常，保守处理"
    except Exception:
        logger.warning("短时情绪研判失败，按轻度预警保守处理 student=%s", student_id, exc_info=True)
        return "mid", "研判服务不可用，按轻度预警保守处理"


def _write_ledger_record(db: Session, student_id: int, note: str, keywords: list[str]) -> None:
    """轻度情绪走情绪台账（emotion_records），教师画像侧可见，不进预警工作台。"""
    from app.models.emotion import EmotionRecord
    note = (note or "")[:200]
    db.add(EmotionRecord(
        user_id=student_id,
        emotion="negative",
        confidence=0.6,
        source="ai_dialog",
        note=note or f"对话中出现情绪信号：{', '.join(keywords[:3])}",
    ))


def _notify_crisis_alert(db: Session, student_id: int, level: str, summary: str) -> None:
    """分级实时推送：moderate/severe 落库后推送给辅导员（SSE 域事件 + 站内通知）。

    SSE 通知教师端即时刷新；站内 Notification 保证离线补偿；失败不阻塞预警主流程。
    """
    if level not in ("moderate", "severe"):
        return
    try:
        from app.services.realtime import hub as realtime_hub
        from app.services import notification_service
        from app.models.user import User, UserRole
        from app.models.notification import NotificationType, UrgencyLevel

        student = db.query(User).filter(User.id == student_id).first()
        receiver_ids: set[int] = set()
        if student is not None and student.tutor_id:
            receiver_ids.add(student.tutor_id)
        receiver_ids.update(
            uid for (uid,) in db.query(User.id).filter(User.role == UserRole.ADMIN).all()
        )
        level_name = {"moderate": "中度", "severe": "高危"}.get(level, level)
        title = f"心理预警（{level_name}）"
        content = (summary or "学生出现心理风险信号")[:120]
        link = "/teacher/crisis"
        urgency = UrgencyLevel.URGENT if level == "severe" else UrgencyLevel.IMPORTANT
        for uid in receiver_ids:
            try:
                notification_service.send_notification(
                    db,
                    user_id=uid,
                    title=title,
                    content=content,
                    notification_type=NotificationType.SYSTEM,
                    link=link,
                    level=urgency,
                )
            except Exception:
                logger.warning("危机站内通知发送失败 receiver=%s", uid, exc_info=True)
            try:
                realtime_hub.publish(uid, ["teacher-crisis", "teacher-dashboard"])
            except Exception:
                logger.warning("危机 SSE 推送失败 receiver=%s", uid, exc_info=True)
    except Exception:
        logger.warning("危机实时推送流程异常 student=%s", student_id, exc_info=True)


def _frequency_escalation(db: Session, student_id: int, keywords: list[str]) -> bool:
    """频次升级兜底：近 7 天情绪台账 ≥5 条或同词预警 ≥3 次 → 返回 True。"""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    from app.models.emotion import EmotionRecord
    ledger_count = (
        db.query(EmotionRecord)
        .filter(
            EmotionRecord.user_id == student_id,
            EmotionRecord.source == "ai_dialog",
            EmotionRecord.created_at >= since,
        )
        .count()
    )
    if ledger_count >= _LEDGER_ESCALATION_COUNT:
        return True
    for kw in keywords:
        same_kw = (
            db.query(AIDialogSummary)
            .filter(
                AIDialogSummary.student_id == student_id,
                AIDialogSummary.keywords_matched.contains(kw),
                AIDialogSummary.created_at >= since,
            )
            .count()
        )
        if same_kw >= _SAME_KEYWORD_ESCALATION_COUNT:
            return True
    return False


def _dedupe_recent(db: Session, student_id: int, keywords: list[str]) -> AIDialogSummary | None:
    """2 小时内同词命中只更新首条，避免刷屏。"""
    since = datetime.now(timezone.utc) - timedelta(hours=_DEDUPE_HOURS)
    if not keywords:
        return None
    rows = (
        db.query(AIDialogSummary)
        .filter(
            AIDialogSummary.student_id == student_id,
            AIDialogSummary.created_at >= since,
        )
        .order_by(AIDialogSummary.created_at.desc())
        .all()
    )
    for row in rows:
        matched = (row.keywords_matched or "").split(",")
        if any(kw in matched for kw in keywords):
            return row
    return None


async def triage_crisis_signal(
    db: Session,
    student_id: int,
    user_message: str,
    ai_reply: str,
    keywords: list[str],
    source: str = TRIAGE_SOURCE_LLM,
) -> dict:
    """双轨降噪主入口：硬词直通 → LLM 短时研判 → 分流（预警工作台 / 情绪台账）。

    返回 {"outcome": "alert" | "ledger" | "deduped", "level": str|None, "reason": str}
    """
    if not keywords:
        return {"outcome": "ledger", "level": None, "reason": "无命中关键词"}

    # 1. 硬词直通闸：旁路一切降噪，fail-open
    extreme = detect_extreme_keywords(user_message, db)
    if extreme:
        plan_hint = any(w in user_message for w in _PLAN_HINT_WORDS)
        level = "severe" if plan_hint else "moderate"
        existing = _dedupe_recent(db, student_id, keywords)
        if existing is not None:
            existing.level = CrisisLevel(level) if level in ("severe", "moderate") else existing.level
            db.commit()
            return {"outcome": "deduped", "level": level, "reason": "硬词命中，2h 内去重"}
        result = await generate_crisis_summary(user_message, ai_reply, keywords) or {}
        record = AIDialogSummary(
            student_id=student_id,
            summary=result.get("summary") or f"命中极端行为信号词：{', '.join(extreme)}",
            level=CrisisLevel(level),
            keywords_matched=",".join(keywords),
            raw_snippet=user_message[:200],
            triage_status=AIDialogSummary.TRIAGE_ALERT,
            triage_source=TRIAGE_SOURCE_HARD_GATE,
            judge_reason=f"硬词直通：{', '.join(extreme)}" + ("；含计划/方式暗示" if plan_hint else ""),
        )
        db.add(record)
        db.commit()
        _notify_crisis_alert(db, student_id, level, record.summary)
        return {"outcome": "alert", "level": level, "reason": "硬词直通"}

    # 2. 同词 2h 去重
    existing = _dedupe_recent(db, student_id, keywords)
    if existing is not None:
        return {"outcome": "deduped", "level": safe_enum_val(existing.level), "reason": "短时去重"}

    # 3. LLM 短时情绪研判
    acute_risk, reason = await judge_short_term_risk(db, student_id, user_message, ai_reply, keywords)

    # 4. 分流
    if acute_risk in ("none", "low"):
        _write_ledger_record(db, student_id, reason or f"命中：{', '.join(keywords[:3])}", keywords)
        # 频次升级兜底：台账高频也生成 mild 预警
        if _frequency_escalation(db, student_id, keywords):
            record = AIDialogSummary(
                student_id=student_id,
                summary=f"近 7 天情绪信号频次升高，建议关注：{reason or ', '.join(keywords[:3])}"[:180],
                level=CrisisLevel.MILD,
                keywords_matched=",".join(keywords),
                raw_snippet=user_message[:200],
                triage_status=AIDialogSummary.TRIAGE_ALERT,
                triage_source=TRIAGE_SOURCE_FREQUENCY,
                judge_reason="频次升级：轻度情绪记录多次累积",
            )
            db.add(record)
            db.commit()
            return {"outcome": "alert", "level": "mild", "reason": "频次升级"}
        db.commit()
        return {"outcome": "ledger", "level": None, "reason": reason}

    # mid → mild 预警；high → moderate 预警
    level = "moderate" if acute_risk == "high" else "mild"
    result = await generate_crisis_summary(user_message, ai_reply, keywords) or {}
    record = AIDialogSummary(
        student_id=student_id,
        summary=result.get("summary") or f"短时情绪研判：{reason}"[:180],
        level=CrisisLevel(level),
        keywords_matched=",".join(keywords),
        raw_snippet=user_message[:200],
        triage_status=AIDialogSummary.TRIAGE_ALERT,
        triage_source=source,
        judge_reason=reason,
    )
    db.add(record)
    db.commit()
    _notify_crisis_alert(db, student_id, level, record.summary)
    return {"outcome": "alert", "level": level, "reason": reason}
