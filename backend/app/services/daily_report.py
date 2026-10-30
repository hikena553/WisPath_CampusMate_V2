"""AI 今日报告：把心情、任务、已实现积累与实时天气合成一份带运势的今日简报。

设计要点：
- **事实由服务端计算**（天气/心情/任务/成长），LLM 只负责措辞与重点标注，不允许编造；
- **永远有内容**：LLM 未配置 / 超时 / 返回不合法时退回规则文案；
- 天气按城市缓存 30 分钟、报告按「学生 + 日期 + 事实指纹」缓存 10 分钟，避免重复开销；
- 文本标注约定：``==重点==`` 渲染为黄色描色，``__留意__`` 渲染为虚线下划线（前端统一解析）。
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.emotion import EmotionRecord
from app.models.growth import GrowthRecord, StudentProject
from app.models.plan import PlanCheckin, PlanTask, StudyPlan, TaskStatus
from app.models.user import User
from app.services.llm_service import complete
from app.services.plan_streak import compute_streak, local_today
from app.services.proactive_engine import evaluate_student
from app.services.prompts import build_daily_report_prompt

try:
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo("Asia/Shanghai")
except Exception:  # pragma: no cover - 无 tzdata 时退化为固定 UTC+8
    _TZ = timezone(timedelta(hours=8), "Asia/Shanghai")

logger = logging.getLogger(__name__)

# 校园所在地（绵阳）：天气按城市取，学生端无需授权定位
CAMPUS = {"city": "绵阳", "lat": 31.4677, "lon": 104.6796}
WEATHER_TTL = 30 * 60
REPORT_TTL = 10 * 60

_weather_cache: dict[str, tuple[float, dict]] = {}
_report_cache: dict[str, tuple[float, dict]] = {}

# 情绪 → 展示文案（与前端 MOODS 的取值保持一致）
MOOD_META = {
    "happy": ("开心", "😄", 5, "#f0a04b"),
    "surprised": ("惊喜", "🤩", 4, "#e8845b"),
    "neutral": ("平静", "😌", 3, "#6f9fc4"),
    "sad": ("难过", "😔", 2, "#7c8db5"),
    "fearful": ("担忧", "😟", 2, "#8b7fb0"),
    "angry": ("生气", "😠", 1, "#d96557"),
    "disgusted": ("烦躁", "😖", 1, "#b98a6b"),
}

# WMO 天气代码 → (中文描述, emoji)
WEATHER_CODES = {
    0: ("晴", "☀️"), 1: ("大部晴朗", "🌤️"), 2: ("多云", "⛅"), 3: ("阴", "☁️"),
    45: ("有雾", "🌫️"), 48: ("雾凇", "🌫️"),
    51: ("小毛毛雨", "🌦️"), 53: ("毛毛雨", "🌦️"), 55: ("浓毛毛雨", "🌧️"),
    61: ("小雨", "🌧️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    66: ("冻雨", "🌧️"), 67: ("强冻雨", "🌧️"),
    71: ("小雪", "🌨️"), 73: ("中雪", "🌨️"), 75: ("大雪", "🌨️"), 77: ("雪粒", "🌨️"),
    80: ("阵雨", "🌦️"), 81: ("强阵雨", "🌧️"), 82: ("暴雨", "⛈️"),
    85: ("阵雪", "🌨️"), 86: ("强阵雪", "🌨️"),
    95: ("雷阵雨", "⛈️"), 96: ("雷雨伴冰雹", "⛈️"), 99: ("强雷雨冰雹", "⛈️"),
}

LUCKY_COLORS = ["雾霾蓝", "奶油黄", "薄荷绿", "藕荷紫", "珊瑚橙", "象牙白"]
LUCKY_TIMES = ["上午 9:00-11:00", "午后 14:00-16:00", "傍晚 19:00-21:00", "睡前 22:00-23:00"]
LUCKY_WORDS = ["稳", "静", "进", "定", "轻", "韧"]


def _local(dt: datetime) -> datetime:
    """DB 里存的是 naive UTC，统一转成本地时间再判断「今天/昨晚」。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ)


def _recent_mood(db: Session, user: User) -> dict:
    """今日心情优先；今天没记录则沿用昨晚（昨天 18:00 之后）的一条。"""
    today = local_today()
    rows = (
        db.query(EmotionRecord)
        .filter(EmotionRecord.user_id == user.id)
        .order_by(EmotionRecord.created_at.desc())
        .limit(30)
        .all()
    )
    today_mood = None
    last_night = None
    for r in rows:
        local = _local(r.created_at)
        if local.date() == today:
            today_mood = (r, local)
            break
        if local.date() == today - timedelta(days=1) and local.hour >= 18 and last_night is None:
            last_night = (r, local)
        if local.date() < today - timedelta(days=1):
            break

    picked, source = (today_mood, "today") if today_mood else (last_night, "last_night")
    if not picked:
        return {"from": "none", "label": "", "emoji": "🫧", "score": 3, "at": "", "color": "#9db4c8"}
    r, local = picked
    label, emoji, score, color = MOOD_META.get(r.emotion, (r.emotion, "🙂", 3, "#9db4c8"))
    return {
        "from": source,
        "emotion": r.emotion,
        "label": label,
        "emoji": emoji,
        "score": score,
        "at": local.strftime("%m-%d %H:%M") if source == "last_night" else local.strftime("%H:%M"),
        "color": color,
    }


async def get_weather() -> dict | None:
    """实时天气（Open-Meteo，免 Key）。网络不可用时返回 None，报告照常生成。"""
    key = CAMPUS["city"]
    now = time.time()
    hit = _weather_cache.get(key)
    if hit and now - hit[0] < WEATHER_TTL:
        return hit[1]

    params = {
        "latitude": CAMPUS["lat"],
        "longitude": CAMPUS["lon"],
        "current": "temperature_2m,weather_code,apparent_temperature",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Asia/Shanghai",
        "forecast_days": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
        cur = data.get("current") or {}
        daily = data.get("daily") or {}
        code = int(cur.get("weather_code", -1))
        desc, emoji = WEATHER_CODES.get(code, ("天气多变", "🌡️"))
        report = {
            "city": CAMPUS["city"],
            "temp": round(float(cur.get("temperature_2m", 0))),
            "feels": round(float(cur.get("apparent_temperature", 0))),
            "desc": desc,
            "emoji": emoji,
            "high": round(float((daily.get("temperature_2m_max") or [0])[0])),
            "low": round(float((daily.get("temperature_2m_min") or [0])[0])),
            "rain": int((daily.get("precipitation_probability_max") or [0])[0] or 0),
        }
        _weather_cache[key] = (now, report)
        return report
    except Exception as e:
        logger.info("[今日报告] 天气获取失败，降级跳过: %s", e)
        return None


def _yesterday_review(db: Session, user: User, today, pending: list[PlanTask]) -> dict:
    """昨日回顾所需事实：打卡/时长/做过的事/心情，以及昨天到期但没做完的任务。"""
    yesterday = today - timedelta(days=1)
    checkins = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.student_id == user.id, PlanCheckin.check_date == yesterday)
        .all()
    )
    titles: list[str] = []
    task_ids = [c.task_id for c in checkins if c.task_id]
    if task_ids:
        for t in db.query(PlanTask).filter(PlanTask.id.in_(task_ids)).all():
            if t.title and t.title not in titles:
                titles.append(t.title)

    mood = None
    rows = (
        db.query(EmotionRecord)
        .filter(EmotionRecord.user_id == user.id)
        .order_by(EmotionRecord.created_at.desc())
        .limit(20)
        .all()
    )
    for r in rows:
        local = _local(r.created_at)
        if local.date() == yesterday:
            label, emoji, *_ = MOOD_META.get(r.emotion, (r.emotion, "🙂", 3, "#9db4c8"))
            mood = {"label": label, "emoji": emoji, "at": local.strftime("%H:%M")}
            break
        if local.date() < yesterday:
            break

    unfinished = [t for t in pending if t.due_date == yesterday]
    return {
        "checkin_count": len(checkins),
        "minutes": sum(c.minutes or 0 for c in checkins),
        "task_titles": titles[:3],
        "mood": mood,
        "unfinished_count": len(unfinished),
        "unfinished_titles": [t.title for t in unfinished][:2],
    }


def collect_facts(db: Session, user: User) -> dict:
    """采集报告所需事实：心情、昨日回顾、今日/遗留任务、已实现的积累。"""
    today = local_today()
    plan_ids = [p.id for p in db.query(StudyPlan).filter(StudyPlan.student_id == user.id).all()]
    pending = (
        db.query(PlanTask)
        .filter(PlanTask.plan_id.in_(plan_ids), PlanTask.status != TaskStatus.DONE)
        .all()
        if plan_ids else []
    )
    due_today = [t for t in pending if t.due_date == today]
    overdue = sorted(
        [t for t in pending if t.due_date and t.due_date < today],
        key=lambda t: t.due_date,
    )
    done_total = (
        db.query(PlanTask)
        .filter(PlanTask.plan_id.in_(plan_ids), PlanTask.status == TaskStatus.DONE)
        .count()
        if plan_ids else 0
    )

    checkins_today = db.query(PlanCheckin).filter(
        PlanCheckin.student_id == user.id, PlanCheckin.check_date == today
    ).all()
    streak = compute_streak(db, user.id, today)

    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == user.id).all()
    projects = db.query(StudentProject).filter(StudentProject.student_id == user.id).count()
    latest_record = max(records, key=lambda r: r.date) if records else None

    return {
        "date": today.isoformat(),
        "mood": _recent_mood(db, user),
        "yesterday": _yesterday_review(db, user, today, pending),
        "tasks": {
            "due_today_count": len(due_today),
            "due_today_titles": [t.title for t in due_today][:3],
            "overdue_count": len(overdue),
            "overdue_titles": [t.title for t in overdue][:3],
            "overdue_days": (today - overdue[0].due_date).days if overdue else 0,
        },
        "progress": {
            "checkin_today": len(checkins_today),
            "minutes_today": sum(c.minutes or 0 for c in checkins_today),
            "streak": streak["current"],
            "streak_best": streak["longest"],
            "done_total": done_total,
            "records": len(records),
            "projects": projects,
            "latest_record": latest_record.title if latest_record else None,
            "latest_record_date": latest_record.date.isoformat() if latest_record else None,
        },
    }


def _fingerprint(facts: dict, weather: dict | None) -> str:
    t = facts["tasks"]
    p = facts["progress"]
    y = facts["yesterday"]
    return (
        f"{facts['date']}|{facts['mood'].get('emotion')}|{facts['mood'].get('from')}"
        f"|{t['due_today_count']}|{t['overdue_count']}|{p['checkin_today']}|{p['records']}"
        f"|{y['checkin_count']}|{y['unfinished_count']}"
        f"|{(weather or {}).get('temp')}|{(weather or {}).get('desc')}"
    )


def _fortune(facts: dict, weather: dict | None, user: User) -> dict:
    """规则运势：分数由真实状态决定，吉利色彩/时段按「学生 + 日期」稳定抽样。"""
    today = facts["date"]
    p = facts["progress"]
    t = facts["tasks"]
    score = 62 + {5: 14, 4: 10, 3: 6, 2: 2, 1: 0}.get(facts["mood"].get("score", 3), 4)
    score += 6 if p["checkin_today"] else 0
    score += -min(12, t["overdue_count"] * 4) if t["overdue_count"] else 4
    if weather:
        score += 3 if weather["rain"] < 40 else -3
    score = max(52, min(96, score))
    if score >= 90:
        level = "上上签"
    elif score >= 80:
        level = "上签"
    elif score >= 70:
        level = "中签"
    elif score >= 60:
        level = "平签"
    else:
        level = "缓行签"

    summaries = {
        "上上签": "顺得很，把最难的那件事放到状态最好的时段。",
        "上签": "节奏不错，先做一件小事把状态推起来。",
        "中签": "稳着来，专注一小段就会顺，不用赶。",
        "平签": "别急着铺开，先清掉一件一直拖着的事。",
        "缓行签": "今天适合减量，完成一件算一件。",
    }
    rng = random.Random(f"{user.id}-{today}")
    return {
        "level": level,
        "score": score,
        "keyword": rng.choice(LUCKY_WORDS),
        "summary": summaries.get(level, ""),
        "lucky_color": rng.choice(LUCKY_COLORS),
        "lucky_time": rng.choice(LUCKY_TIMES),
    }


def _review_items(facts: dict) -> list[str]:
    """昨日回顾：只写昨天真实发生的事（打卡、时长、心情、没做完的任务）。"""
    y = facts["yesterday"]
    items: list[str] = []
    if y["checkin_count"]:
        text = f"昨天完成 =={y['checkin_count']} 个任务==、投入 {y['minutes']} 分钟"
        if y["task_titles"]:
            text += f"，其中做了「{y['task_titles'][0]}」"
        if y["mood"]:
            text += f"；心情是「{y['mood']['label']}」{y['mood']['emoji']}"
        text += "，这个节奏今天可以接着用。"
        items.append(text)
    elif y["mood"]:
        items.append(
            f"昨天没有打卡记录，心情是「{y['mood']['label']}」{y['mood']['emoji']}，"
            "__今天先补一个最小目标__ 把节奏接回来。"
        )
    else:
        items.append("昨天没有打卡也没有心情记录，__今天从一件 25 分钟的小事开始__，先把连续性接上。")

    if y["unfinished_count"]:
        items.append(
            f"昨天还有 __{y['unfinished_count']} 项没做完__（如「{y['unfinished_titles'][0]}」），"
            "今天优先补 1 项，==不要一次全部重开==。"
        )
    else:
        items.append("昨天到期的任务没有堆积，==今天可以顺着计划往前走==，不用回头补课。")
    return items


def _today_schedule(facts: dict, weather: dict | None, fortune: dict) -> list[str]:
    """今日学习安排：给出带具体时间点的可执行计划，而不是泛泛而谈。"""
    t = facts["tasks"]
    y = facts["yesterday"]
    items: list[str] = []
    if t["overdue_count"]:
        items.append(
            f"09:00-10:00 先清 1 项遗留任务「{t['overdue_titles'][0]}」，"
            "用 2 个 25 分钟专注块收口"
        )
    elif t["due_today_count"]:
        items.append(
            f"09:30-10:30 先推进今天到期的「{t['due_today_titles'][0]}」，==完成前不开新任务=="
        )
    elif y["unfinished_count"]:
        items.append(
            f"09:30-10:30 把昨天没做完的「{y['unfinished_titles'][0]}」补上，避免越积越多"
        )
    else:
        items.append("10:00-10:30 提前推进明天最重的一项，==把节奏往前挪半天==")

    slot = fortune.get("lucky_time") or "午后"
    items.append(f"=={slot} 安排 1 个 50 分钟深度块==，只做今天最需要专注的一件事，中途不看消息")

    if weather and weather["rain"] >= 40:
        items.append(
            f"降水概率 {weather['rain']}%，出门带伞、户外安排换到室内；"
            "20:30-20:45 花 15 分钟复盘并记一条成长记录"
        )
    else:
        items.append("午间留 20 分钟到户外走一走；20:30-20:45 花 15 分钟复盘，记一条成长记录")
    return items


def _rule_sections(facts: dict, weather: dict | None, fortune: dict) -> list[dict]:
    """规则文案（LLM 不可用时的兜底），与 LLM 版共用同一套标注语法。"""
    mood = facts["mood"]
    t = facts["tasks"]
    p = facts["progress"]

    if mood["from"] == "today":
        mood_items = [
            f"今天 {mood['at']} 记录的心情是「{mood['label']}」{mood['emoji']}，"
            "==就按这个节奏来==，别硬逼自己超频。"
        ]
    elif mood["from"] == "last_night":
        mood_items = [
            f"今天还没记录心情，沿用昨晚（{mood['at']}）的「{mood['label']}」{mood['emoji']}；"
            "__如果今天感觉变了，记得重新点一下心情__，建议会跟着变。"
        ]
    else:
        mood_items = ["还没有心情记录，__点一下「此刻的心情」__，AI 才能按你的状态给建议。"]

    task_items = []
    if t["overdue_count"]:
        task_items.append(
            f"有 __{t['overdue_count']} 项遗留任务__ 还没清，最久的一项是「{t['overdue_titles'][0]}」，"
            f"已经拖了 {t['overdue_days']} 天，==今天先清 1 项就够==。"
        )
    if t["due_today_count"]:
        task_items.append(
            f"今天到期 =={t['due_today_count']} 项==，先啃「{t['due_today_titles'][0]}」，"
            "做完再开新的，避免同时开太多线程。"
        )
    if not task_items:
        task_items.append("今天没有到期任务，==适合提前推进明天的 1 项==，把节奏往前挪半天。")

    progress_items = []
    if p["checkin_today"]:
        progress_items.append(
            f"今天已打卡 =={p['checkin_today']} 次==、投入 {p['minutes_today']} 分钟；"
            f"连续打卡 {p['streak']} 天，__最长纪录 {p['streak_best']} 天__。"
        )
    elif p["streak"]:
        progress_items.append(
            f"连续打卡已经到 __{p['streak']} 天__，==今天补一次就能接上==，别让纪录断在今天。"
        )
    else:
        progress_items.append("今天还没有打卡，==从最小的一项任务开始==，先让连击从 0 变成 1。")
    if p["records"] or p["projects"]:
        progress_items.append(
            f"成长档案里已经沉淀 {p['records']} 条记录、{p['projects']} 段项目"
            + (f"，最近一条是「{p['latest_record']}」" if p["latest_record"] else "")
            + "，这些都是你自己的底牌。"
        )

    if weather:
        advice = "适合安排 20 分钟户外走动" if weather["rain"] < 40 else "==记得带伞==，通勤多留 10 分钟"
        weather_items = [
            f"{weather['city']} {weather['temp']}℃ {weather['desc']}{weather['emoji']}，"
            f"{weather['low']}~{weather['high']}℃，降水概率 {weather['rain']}%，{advice}。"
        ]
    else:
        weather_items = ["__天气数据暂时取不到__，出门前看一眼窗外或天气 App 再定行程。"]

    return [
        {"key": "review", "title": "昨日回顾", "items": _review_items(facts)[:2]},
        {"key": "today", "title": "今日学习安排", "items": _today_schedule(facts, weather, fortune)[:3]},
        {"key": "task", "title": "任务焦点", "items": task_items[:2]},
        {"key": "mood", "title": "心情状态", "items": mood_items[:2]},
        {"key": "weather", "title": "天气与安排", "items": weather_items[:2]},
        {"key": "achievement", "title": "已实现", "items": progress_items[:2]},
    ]


def _facts_text(facts: dict, weather: dict | None, fortune: dict) -> str:
    mood = facts["mood"]
    t = facts["tasks"]
    p = facts["progress"]
    y = facts["yesterday"]
    mood_line = (
        f"今日心情：{mood['label']}（来源：今日记录 {mood['at']}）" if mood["from"] == "today"
        else f"今日心情：沿用昨晚 {mood['at']} 的「{mood['label']}」" if mood["from"] == "last_night"
        else "今日心情：无记录"
    )
    yesterday_line = (
        f"昨日完成：打卡 {y['checkin_count']} 次、投入 {y['minutes']} 分钟"
        + (f"，做过「{'、'.join(y['task_titles'])}」" if y["task_titles"] else "")
        + (f"；昨日心情「{y['mood']['label']}」" if y["mood"] else "；昨日无心情记录")
        + (f"；昨日到期未完成 {y['unfinished_count']} 项（{'、'.join(y['unfinished_titles'])}）"
           if y["unfinished_count"] else "；昨日到期任务没有堆积")
    )
    weather_line = (
        f"天气：{weather['city']} {weather['temp']}℃ {weather['desc']}，"
        f"{weather['low']}~{weather['high']}℃，降水概率 {weather['rain']}%"
        if weather else "天气：数据不可用"
    )
    return "\n".join([
        f"日期：{facts['date']}",
        mood_line,
        yesterday_line,
        f"今日到期任务：{t['due_today_count']} 项（{'、'.join(t['due_today_titles']) or '无'}）",
        f"遗留逾期任务：{t['overdue_count']} 项（{'、'.join(t['overdue_titles']) or '无'}）",
        weather_line,
        f"今日打卡：{p['checkin_today']} 次，{p['minutes_today']} 分钟；连续 {p['streak']} 天，最长 {p['streak_best']} 天",
        f"已实现：完成任务 {p['done_total']} 项，成长记录 {p['records']} 条，项目 {p['projects']} 段"
        + (f"，最近一条成长记录：{p['latest_record']}" if p["latest_record"] else ""),
        f"系统给出的运势基调：{fortune['level']}（{fortune['score']} 分），"
        f"关键词「{fortune['keyword']}」，黄金时段 {fortune['lucky_time']}",
    ])


def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(cleaned[start:end + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


SECTION_KEYS = ("review", "today", "task", "mood", "weather", "achievement")
ITEM_LIMITS = {"review": 2, "today": 3}


def _merge_sections(rule_sections: list[dict], llm_sections: list[dict]) -> list[dict]:
    """LLM 段落覆盖规则段落，但缺少的段落（如昨日回顾/今日安排）保留规则版，保证结构完整。"""
    merged = {s["key"]: s for s in rule_sections}
    for sec in llm_sections:
        merged[sec["key"]] = sec
    return [merged[key] for key in SECTION_KEYS if key in merged]


async def _llm_sections(facts: dict, weather: dict | None, fortune: dict, user: User) -> dict | None:
    """让 LLM 重写报告与运势文案；失败返回 None，调用方保留规则文案。"""
    try:
        prompt = build_daily_report_prompt(
            student_name=user.name or "同学",
            facts=_facts_text(facts, weather, fortune),
        )
        text = await complete(prompt, temperature=0.7, max_tokens=900)
        data = _parse_json(text)
        if not data:
            return None

        sections = []
        for sec in data.get("sections") or []:
            if not isinstance(sec, dict) or sec.get("key") not in SECTION_KEYS:
                continue
            items = [str(i).strip() for i in (sec.get("items") or []) if str(i).strip()]
            if not items:
                continue
            sections.append({
                "key": sec["key"],
                "title": str(sec.get("title") or "").strip() or sec["key"],
                "items": items[:ITEM_LIMITS.get(sec["key"], 2)],
            })
        if len(sections) < 2:
            return None

        fortune_patch = {}
        f = data.get("fortune") or {}
        if isinstance(f, dict):
            keyword = str(f.get("keyword") or "").strip()[:6]
            summary = str(f.get("summary") or "").strip()[:60]
            if keyword:
                fortune_patch["keyword"] = keyword
            if summary:
                fortune_patch["summary"] = summary
        return {"sections": sections, "fortune": fortune_patch}
    except Exception as e:
        logger.info("[今日报告] LLM 生成失败，降级为规则文案: %s", e)
        return None


# 这些主动发现动作只是「告知」，不能变成学习任务：
# 请假审批、上课提醒、里程碑通报、久未互动关怀……
# 旧实现把所有 actions 一律当建议，导致「请假申请审批中」被一键写进 study_plans。
# 用黑名单而不是白名单：以后新增的学习类信号默认可以进建议，不会被漏掉。
NOTICE_TRIGGERS = {
    "leave_pending", "leave_result",
    "class_soon", "class_today",
    "notification", "escalation", "crisis_escalation",
    "milestone_reached", "prolonged_inactivity", "growth_record_gap",
}


def _suggestions(db: Session, user: User, facts: dict, fortune: dict) -> list[dict]:
    """可一键加入学习计划的建议：优先复用主动发现动作，没有时按遗留任务兜底。"""
    slots = ["上午 09:00-10:00", f"黄金时段 {fortune.get('lucky_time', '')}".strip(), "晚上 20:30-21:00"]

    def with_slot(items: list[dict]) -> list[dict]:
        return [
            {**item, "when": slots[min(i, len(slots) - 1)]}
            for i, item in enumerate(items[:3])
        ]

    actions = evaluate_student(db, user, target_role="student")
    # 只取「能落成学习任务」的动作；通知类（请假/上课/里程碑/关怀）留在消息中心
    actions = [a for a in actions if a.trigger not in NOTICE_TRIGGERS]
    if actions:
        picked = sorted(actions, key=lambda a: a.priority, reverse=True)[:3]
        return with_slot([
            {"trigger": a.trigger, "kind": "plan", "priority": a.priority, "title": a.title, "content": a.content}
            for a in picked
        ])

    t = facts["tasks"]
    p = facts["progress"]
    out = []
    if t["overdue_count"]:
        out.append({
            "trigger": "daily_overdue",
            "priority": 3,
            "title": f"清理逾期任务：{t['overdue_titles'][0]}",
            "content": f"有 {t['overdue_count']} 项遗留任务，先拆成 3 个 25 分钟的小块集中清理。",
        })
    if not p["checkin_today"]:
        out.append({
            "trigger": "daily_checkin",
            "priority": 2,
            "title": "今天先打卡一次，把连击接上",
            "content": "挑一个 25 分钟能完成的小任务，完成后在今日任务里勾选打卡。",
        })
    return with_slot(out)


async def build_daily_report(db: Session, user: User) -> dict:
    facts = collect_facts(db, user)
    weather = await get_weather()
    cache_key = f"{user.id}-{_fingerprint(facts, weather)}"
    hit = _report_cache.get(cache_key)
    if hit and time.time() - hit[0] < REPORT_TTL:
        return hit[1]

    fortune = _fortune(facts, weather, user)
    sections = _rule_sections(facts, weather, fortune)
    llm = await _llm_sections(facts, weather, fortune, user)
    if llm:
        sections = _merge_sections(sections, llm["sections"])
        fortune.update(llm["fortune"])

    hour = datetime.now(_TZ).hour
    greeting = "早上好" if hour < 11 else "中午好" if hour < 14 else "下午好" if hour < 18 else "晚上好"
    report = {
        "date": facts["date"],
        "greeting": f"{greeting}，{user.name or '同学'}",
        "weather": weather,
        "mood": facts["mood"],
        "fortune": fortune,
        "sections": sections,
        "suggestions": _suggestions(db, user, facts, fortune),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _report_cache[cache_key] = (time.time(), report)
    return report


def clear_cache() -> None:
    """清空天气与报告缓存（测试或配置变更时使用）。"""
    _weather_cache.clear()
    _report_cache.clear()
