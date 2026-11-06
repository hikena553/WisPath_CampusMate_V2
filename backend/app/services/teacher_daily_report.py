"""教师端 AI 日报：把「昨天做了什么、今天该做什么、哪些学生要关注」合成一页简报。

和学生端 ``daily_report.py`` 同一套设计口径，但事实来源换成辅导员的工作面：

- **事实由服务端算**（任务办结/逾期、未闭环心理预警、待批请假、学生成长信号、今日安排），
  LLM 只负责措辞与重点标注，不允许编造；
- **永远有内容**：LLM 未配置 / 超时 / 返回不合法时退回规则文案；
- 报告按「教师 + 日期 + 事实指纹」缓存 10 分钟，避免列表刷新时重复调用 LLM；
- 文本标注约定：``==重点==`` 渲染为黄色描色，``__留意__`` 渲染为虚线下划线（前端统一解析）。

除四段正文外，本模块还输出两类可直接操作的数据：
``actions``（带跳转链接/一键完成的任务条）与 ``suggestions``（AI 建议动作）。
一键完成只在服务端判定为「低风险」的任务上开放，高危预警与请假审批一律走跳转。
"""
from __future__ import annotations

import logging
import random
import re
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.growth import GrowthRecord
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.teacher_task import TaskPriority, TaskSourceType, TaskStatus, TeacherTask
from app.models.user import User, UserRole
from app.services.daily_report import LUCKY_COLORS, LUCKY_TIMES, LUCKY_WORDS, get_weather
from app.services.llm_service import complete
from app.services.plan_streak import local_today
from app.services.prompts import build_teacher_daily_report_prompt

try:
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo("Asia/Shanghai")
except Exception:  # pragma: no cover - 无 tzdata 时退化为固定 UTC+8
    _TZ = timezone(timedelta(hours=8), "Asia/Shanghai")

logger = logging.getLogger(__name__)

REPORT_TTL = 10 * 60
_report_cache: dict[str, tuple[float, dict]] = {}

# 段序固定，LLM 缺哪段就用规则版补回去
SECTION_KEYS = ["review", "today", "student", "plan"]
SECTION_TITLES = {
    "review": "昨日复盘",
    "today": "今日梳理",
    "student": "学生成长关注",
    "plan": "明日规划",
}
ITEM_LIMITS = {"review": 3, "today": 3, "student": 3, "plan": 2}

# 预警等级 → (展示名, 权重)；normal 不算需要关注的学生
ALERT_LEVELS = {
    CrisisLevel.SEVERE: ("高危", 3),
    CrisisLevel.MODERATE: ("中度", 2),
    CrisisLevel.MILD: ("轻度", 1),
}

# 成长记录类型 → 展示名（用于「学生成长关注」的正面信号）
GROWTH_LABELS = {
    "honor": "荣誉",
    "competition": "竞赛",
    "practice": "实践",
    "paper": "论文",
    "achievement": "成果",
}

# 任务来源 → 一键完成时的安全性说明用的标签
SOURCE_LABELS = {
    TaskSourceType.AI_SUGGEST: "AI 建议",
    TaskSourceType.FOLLOW_UP: "随访提醒",
    TaskSourceType.APPROVAL: "审批待办",
    TaskSourceType.CARE_PLAN: "关怀计划",
    TaskSourceType.ALERT: "预警",
    TaskSourceType.MANUAL: "手动",
    TaskSourceType.ADMIN: "管理员下发",
}

# 请假类型 → 中文（模型里存的是英文枚举值）
LEAVE_TYPE_LABELS = {
    "competition": "竞赛",
    "sick": "病假",
    "personal": "事假",
    "other": "其他",
}


def _local(dt: datetime) -> datetime:
    """DB 存 naive UTC，统一转本地（Asia/Shanghai）再判断「今天/昨天」。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ)


def _local_day_utc_range(day: date) -> tuple[datetime, datetime]:
    """把本地某一天换算成 naive UTC 区间，用于查询 done_at 这类 UTC 时间戳。"""
    start_local = datetime.combine(day, datetime.min.time(), tzinfo=_TZ)
    start = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start, start + timedelta(days=1)


def _md(day: date) -> str:
    return f"{day.month}月{day.day}日"


def _weekday(day: date) -> str:
    return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day.weekday()]


def _is_open(status: TaskStatus) -> bool:
    """未办结 = 还没真正结束的任务（已过期也算没做完）。"""
    return status not in (TaskStatus.DONE, TaskStatus.EXPIRED)


# ==================== 事实采集 ====================

def _my_student_ids(db: Session, teacher: User) -> list[int]:
    rows = db.query(User.id).filter(User.role == UserRole.STUDENT, User.tutor_id == teacher.id).all()
    return [r[0] for r in rows]


def collect_facts(db: Session, teacher: User) -> dict:
    """采集教师今天写日报所需的全部真实事实（只读，不做任何写操作）。"""
    today = local_today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=6)
    today_start, today_end = _local_day_utc_range(today)

    tid = teacher.id
    tasks = db.query(TeacherTask).filter(TeacherTask.teacher_id == tid)

    # ---- 任务：今天要做的 ----
    # MySQL 不支持 NULLS LAST，用「先按 due_at 是否为空排序」把没定截止的沉到最后
    open_tasks = (
        tasks.filter(~TeacherTask.status.in_([TaskStatus.DONE, TaskStatus.EXPIRED]))
        .order_by(TeacherTask.due_at.is_(None), TeacherTask.due_at.asc(), TeacherTask.priority.asc())
        .limit(120)
        .all()
    )
    due_today = [t for t in open_tasks if t.due_at == today]
    overdue = [t for t in open_tasks if t.due_at and t.due_at < today]
    remind_today = [t for t in open_tasks if t.remind_at == today]
    high_open = [t for t in open_tasks if t.priority == TaskPriority.HIGH]

    # ---- 任务：昨天办结的 ----
    done_yesterday = (
        tasks.filter(
            TeacherTask.status == TaskStatus.DONE,
            TeacherTask.done_at.isnot(None),
            TeacherTask.done_at >= _local_day_utc_range(yesterday)[0],
            TeacherTask.done_at < _local_day_utc_range(yesterday)[1],
        )
        .order_by(TeacherTask.done_at.desc())
        .all()
    )
    # 昨天截止但今天还没办结的，就是「昨日遗留」
    left_from_yesterday = [t for t in open_tasks if t.due_at == yesterday]

    created_today = tasks.filter(
        TeacherTask.created_at >= today_start, TeacherTask.created_at < today_end
    ).count()

    student_ids = _my_student_ids(db, teacher)

    # ---- 心理预警：未闭环的才算需要跟进 ----
    alerts: list[AIDialogSummary] = []
    if student_ids:
        alerts = (
            db.query(AIDialogSummary)
            .filter(AIDialogSummary.student_id.in_(student_ids), AIDialogSummary.resolved.is_(False))
            .order_by(AIDialogSummary.created_at.desc())
            .all()
        )
    name_map: dict[int, str] = {}
    if student_ids:
        name_map = {
            u.id: u.name
            for u in db.query(User.id, User.name).filter(User.id.in_(student_ids)).all()
        }
    # 任务里可能挂到非本人名下的学生（如跨班级下发的任务），姓名单独补齐
    extra_ids = {t.student_id for t in open_tasks if t.student_id and t.student_id not in name_map}
    if extra_ids:
        name_map.update({
            u.id: u.name for u in db.query(User.id, User.name).filter(User.id.in_(extra_ids)).all()
        })

    alert_items = []
    for a in alerts:
        meta = ALERT_LEVELS.get(a.level)
        if not meta:
            continue  # normal 等级不进日报，避免虚增焦虑
        alert_items.append({
            "alert_id": a.id,
            "student_id": a.student_id,
            "student_name": name_map.get(a.student_id, "该学生"),
            "level": a.level.value if hasattr(a.level, "value") else str(a.level),
            "level_label": meta[0],
            "weight": meta[1],
            "summary": a.summary or "",
            "created_at": _local(a.created_at).strftime("%m-%d %H:%M"),
        })
    alert_items.sort(key=lambda x: -x["weight"])

    # ---- 请假：待审批 ----
    pending_leaves: list[LeaveRequest] = []
    if student_ids:
        pending_leaves = (
            db.query(LeaveRequest)
            .filter(LeaveRequest.student_id.in_(student_ids), LeaveRequest.status == LeaveStatus.PENDING)
            .order_by(LeaveRequest.created_at.desc())
            .all()
        )

    # ---- 成长：近 7 天新增的荣誉/竞赛等正面信号 ----
    growth_recent: list[GrowthRecord] = []
    if student_ids:
        growth_recent = (
            db.query(GrowthRecord)
            .filter(GrowthRecord.student_id.in_(student_ids), GrowthRecord.date >= week_ago)
            .order_by(GrowthRecord.date.desc())
            .limit(20)
            .all()
        )

    # ---- 学情沉默：近 14 天没有成长/关怀记录、任务也一直挂着的学生（只做提示，不下结论） ----
    activity_cut = today - timedelta(days=14)
    active_ids: set[int] = set()
    if student_ids:
        active_ids |= {
            r[0] for r in db.query(GrowthRecord.student_id)
            .filter(GrowthRecord.student_id.in_(student_ids), GrowthRecord.date >= activity_cut)
            .all()
        }
        active_ids |= {
            r[0] for r in db.query(TeacherTask.student_id)
            .filter(
                TeacherTask.teacher_id == tid,
                TeacherTask.student_id.in_(student_ids),
                TeacherTask.status.in_([TaskStatus.DONE, TaskStatus.CONTACTED, TaskStatus.CARED]),
            )
            .all()
        }
    quiet_students = [
        {"student_id": sid, "name": name_map.get(sid, "该学生")}
        for sid in student_ids
        if sid not in active_ids
    ][:3]

    # ---- 昨日/今日的教师侧其他事实 ----
    leaves_approved_yesterday = 0
    if student_ids:
        leaves_approved_yesterday = (
            db.query(func.count(LeaveRequest.id))
            .filter(
                LeaveRequest.student_id.in_(student_ids),
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.updated_at >= _local_day_utc_range(yesterday)[0],
                LeaveRequest.updated_at < _local_day_utc_range(yesterday)[1],
            )
            .scalar()
            or 0
        )

    return {
        "date": today.isoformat(),
        "yesterday": yesterday.isoformat(),
        "weekday": _weekday(today),
        "teacher_name": teacher.name or "老师",
        "student_total": len(student_ids),
        "tasks": {
            "open": len(open_tasks),
            "due_today": len(due_today),
            "overdue": len(overdue),
            "remind_today": len(remind_today),
            "high": len(high_open),
            "created_today": created_today,
            "done_yesterday": len(done_yesterday),
            "done_yesterday_titles": [t.title for t in done_yesterday[:4]],
            "left_from_yesterday": [t.title for t in left_from_yesterday[:3]],
        },
        "alerts": alert_items[:4],
        "alert_total": len(alert_items),
        "severe_total": len([a for a in alert_items if a["level"] == "severe"]),
        "pending_leaves": [
            {
                "leave_id": l.id,
                "student_id": l.student_id,
                "student_name": name_map.get(l.student_id, "该学生"),
                "leave_type": getattr(l.leave_type, "value", str(l.leave_type)),
                "leave_type_label": LEAVE_TYPE_LABELS.get(
                    getattr(l.leave_type, "value", str(l.leave_type)), "请假"
                ),
                "start_date": l.start_date.isoformat() if l.start_date else None,
            }
            for l in pending_leaves[:3]
        ],
        "leave_total": len(pending_leaves),
        "leaves_approved_yesterday": leaves_approved_yesterday,
        "growth_recent": [
            {
                "student_id": g.student_id,
                "student_name": name_map.get(g.student_id, "该学生"),
                "type": getattr(g.type, "value", str(g.type)),
                "type_label": GROWTH_LABELS.get(getattr(g.type, "value", str(g.type)), "成长"),
                "title": g.title,
                "date": g.date.isoformat() if g.date else None,
            }
            for g in growth_recent[:3]
        ],
        # 供 actions / suggestions 使用（不进 prompt）
        "_due_today": due_today[:5],
        "_overdue": overdue[:5],
        "_remind": remind_today[:5],
        "_name_map": name_map,
        "quiet_students": quiet_students,
    }


def _fingerprint(facts: dict, weather: dict | None) -> str:
    t = facts["tasks"]
    return (
        f"{facts['date']}|{t['open']}|{t['due_today']}|{t['overdue']}|{t['done_yesterday']}"
        f"|{facts['alert_total']}|{facts['severe_total']}|{facts['leave_total']}"
        f"|{len(facts['growth_recent'])}|{(weather or {}).get('temp')}"
    )


# ==================== 运势 ====================

def _fortune(facts: dict, weather: dict | None, teacher: User) -> dict:
    """规则运势：分数由今天真实的工作压力决定，吉利色彩/时段按「教师 + 日期」稳定抽样。

    口径是「今天顺不顺」，所以逾期多、高危预警多会压低分数；办结多会抬高。
    """
    today = facts["date"]
    t = facts["tasks"]
    score = 72
    score += min(10, t["done_yesterday"] * 2)          # 昨天有产出，状态在线
    score -= min(14, t["overdue"] * 3)                 # 逾期越多越费劲
    score -= min(12, facts["severe_total"] * 6)        # 高危预警压节奏
    score += 4 if t["due_today"] <= 3 else -4          # 今天排得动 vs 排满
    if weather:
        score += 2 if weather["rain"] < 40 else -2
    score = max(55, min(96, score))

    if score >= 90:
        level = "上上签"
    elif score >= 80:
        level = "上签"
    elif score >= 70:
        level = "中签"
    elif score >= 62:
        level = "平签"
    else:
        level = "缓行签"

    summaries = {
        "上上签": "今天节奏很顺，把最费神的那件事放到上午先做。",
        "上签": "手里的事排得动，先清掉一件逾期，后面会越来越轻。",
        "中签": "按重要顺序一件件推，不用同时抓太多线。",
        "平签": "今天适合收口不适合铺开，把悬着的跟进做个了结。",
        "缓行签": "今天事偏多，优先保高危学生的跟进，其余可以放宽。",
    }
    rng = random.Random(f"{teacher.id}-{today}")
    return {
        "level": level,
        "score": score,
        "keyword": rng.choice(LUCKY_WORDS),
        "summary": summaries.get(level, ""),
        "lucky_color": rng.choice(LUCKY_COLORS),
        "lucky_time": rng.choice(LUCKY_TIMES),
    }


# ==================== 规则文案 ====================

def _rule_sections(facts: dict) -> list[dict]:
    """不依赖 LLM 的兜底文案：每条都能和数字对上，方便老师核对。"""
    t = facts["tasks"]
    y_md = _md(date.fromisoformat(facts["yesterday"]))
    out: list[dict] = []

    # 昨日复盘
    review: list[str] = []
    if t["done_yesterday"]:
        head = "、".join(t["done_yesterday_titles"][:2])
        review.append(f"昨天办结了 =={t['done_yesterday']} 项== 跟进任务，包括{head}。")
    else:
        review.append("昨天没有办结记录，__今天先补一次完整闭环__，让跟进链条接上。")
    if t["left_from_yesterday"]:
        names = "、".join(t["left_from_yesterday"][:2])
        review.append(f"昨天到期但没做完的还有 {len(t['left_from_yesterday'])} 项：__{names}__，已滚到今天。")
    if facts["leaves_approved_yesterday"]:
        review.append(f"昨天审批了 {facts['leaves_approved_yesterday']} 条请假，流程已发出。")
    out.append({"key": "review", "title": SECTION_TITLES["review"], "items": review[:ITEM_LIMITS["review"]]})

    # 今日梳理
    today_items: list[str] = []
    if facts["severe_total"]:
        s = facts["alerts"][0]
        today_items.append(f"先处理 =={s['level_label']}预警==：{s['summary'][:26]}，建议上午就安排谈话。")
    if t["overdue"]:
        today_items.append(f"有 =={t['overdue']} 项任务已逾期==，挑最久的先清，别让它们一直挂在列表顶部。")
    if t["due_today"]:
        today_items.append(f"今天到期 {t['due_today']} 项，其中高优先级 {t['high']} 项，按顺序推即可。")
    if facts["leave_total"]:
        today_items.append(f"待你审批的请假有 =={facts['leave_total']} 条==，__学生在等结果__。")
    if not today_items:
        today_items.append("今天没有到期任务和待批事项，__适合做一次学生档案梳理__。")
    out.append({"key": "today", "title": SECTION_TITLES["today"], "items": today_items[:ITEM_LIMITS["today"]]})

    # 学生成长关注
    stu: list[str] = []
    mild = [a for a in facts["alerts"] if a["level"] != "severe"]
    if mild:
        names = "、".join(a["student_name"] if a.get("student_name") else "同学" for a in mild[:2])
        stu.append(f"{names} 存在未闭环的心理预警，__建议本周内完成一次面谈跟进__。")
    if facts["growth_recent"]:
        g = facts["growth_recent"][0]
        stu.append(f"亮点：{g['student_name']} 新增{g['type_label']}「{g['title']}」，可以在班会上提一句。")
    if facts["quiet_students"]:
        names = "、".join(s["name"] for s in facts["quiet_students"][:2])
        stu.append(f"{names} 近两周没有新的记录，__属于沉默风险__，顺手关心一下。")
    if not stu:
        stu.append("名下学生近期状态平稳，没有需要立刻介入的信号。")
    out.append({"key": "student", "title": SECTION_TITLES["student"], "items": stu[:ITEM_LIMITS["student"]]})

    # 明日规划
    plan: list[str] = []
    if t["overdue"]:
        plan.append(f"明天第一件事把 =={t['overdue']} 项逾期== 处理掉，能关的关，关不掉的改期重排。")
    if facts["alert_total"]:
        plan.append(f"留 30 分钟给 {facts['alert_total']} 条预警的跟进记录，避免只跟进不留痕。")
    if not plan:
        plan.append("明天按今天的节奏走即可，__,别忘了给两位学生各留一条成长记录__。")
    out.append({"key": "plan", "title": SECTION_TITLES["plan"], "items": plan[:ITEM_LIMITS["plan"]]})

    return out


def _facts_text(facts: dict, weather: dict | None) -> str:
    """喂给 LLM 的纯事实清单，不含任何引导性结论。"""
    t = facts["tasks"]
    lines = [
        f"今天：{facts['date']}（{facts['weekday']}），辅导员：{facts['teacher_name']}，名下学生 {facts['student_total']} 人",
        f"昨天（{facts['yesterday']}）办结任务 {t['done_yesterday']} 项：{'、'.join(t['done_yesterday_titles']) or '无'}",
        f"昨天到期未完成：{len(t['left_from_yesterday'])} 项：{'、'.join(t['left_from_yesterday']) or '无'}",
        f"昨天审批请假：{facts['leaves_approved_yesterday']} 条",
        f"今天到期任务 {t['due_today']} 项，逾期 {t['overdue']} 项，高优先级未办结 {t['high']} 项，今日提醒 {t['remind_today']} 项，未办结合计 {t['open']} 项",
        f"未闭环心理预警 {facts['alert_total']} 条（其中高危 {facts['severe_total']} 条）："
        + ("；".join(f"{a['level_label']}·{a['summary'][:40]}" for a in facts["alerts"]) or "无"),
        f"待审批请假 {facts['leave_total']} 条："
        + ("；".join(
            f"{l['student_name']}·{l['leave_type_label']}·{l['start_date']}" for l in facts["pending_leaves"]
        ) or "无"),
        f"近 7 天成长记录 {len(facts['growth_recent'])} 条："
        + ("；".join(f"{g['student_name']}·{g['type_label']}·{g['title']}" for g in facts["growth_recent"]) or "无"),
        f"近两周无任何记录的学生：{'、'.join(s['name'] for s in facts['quiet_students']) or '无'}",
    ]
    if weather:
        lines.append(f"天气：{weather['city']} {weather['temp']}℃ {weather['desc']}，降水概率 {weather['rain']}%")
    return "\n".join(lines)


# ==================== LLM 改写 ====================

def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    import json

    try:
        data = json.loads(cleaned[start:end + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _merge_sections(rule_sections: list[dict], llm_sections: list[dict]) -> list[dict]:
    """LLM 段落覆盖规则段落，缺少的段落保留规则版，保证四段结构完整。"""
    merged = {s["key"]: s for s in rule_sections}
    for sec in llm_sections:
        merged[sec["key"]] = sec
    return [merged[key] for key in SECTION_KEYS if key in merged]


async def _llm_sections(facts: dict, weather: dict | None, teacher: User) -> dict | None:
    """让 LLM 重写四段正文；失败返回 None，调用方保留规则文案。"""
    try:
        prompt = build_teacher_daily_report_prompt(
            teacher_name=facts["teacher_name"],
            facts=_facts_text(facts, weather),
        )
        text = await complete(prompt, temperature=0.7, max_tokens=800)
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
            key = sec["key"]
            sections.append({
                "key": key,
                "title": str(sec.get("title") or "").strip() or SECTION_TITLES[key],
                "items": items[: ITEM_LIMITS[key]],
            })
        if len(sections) < 2:
            return None

        fortune_patch: dict = {}
        f = data.get("fortune") or {}
        if isinstance(f, dict):
            keyword = str(f.get("keyword") or "").strip()[:6]
            summary = str(f.get("summary") or "").strip()[:60]
            if keyword:
                fortune_patch["keyword"] = keyword
            if summary:
                fortune_patch["summary"] = summary
        return {"sections": sections, "fortune": fortune_patch}
    except Exception as e:  # LLM 未配置 / 超时 / 返回不合法都走这里
        logger.info("[教师日报] LLM 生成失败，降级为规则文案: %s", e)
        return None


# ==================== 可操作数据 ====================

def _task_action(
    task: TeacherTask, *, group: str, kind_label: str, name_map: dict[int, str]
) -> dict:
    """把一条任务转成日报里可跳转、可一键完成的条目。"""
    return {
        "id": f"task-{task.id}",
        "task_id": task.id,
        "kind": "task",
        "group": group,
        "label": kind_label,
        "title": task.title,
        "student_id": task.student_id,
        "student_name": name_map.get(task.student_id, "") if task.student_id else "",
        "priority": task.priority.value if hasattr(task.priority, "value") else str(task.priority),
        "source": task.source_type.value if hasattr(task.source_type, "value") else str(task.source_type),
        "source_label": SOURCE_LABELS.get(task.source_type, "任务"),
        # 一键完成只对低风险任务开放：高危预警生成的、高优先级的都必须老师亲自走一遍
        "can_complete": _can_complete(task),
        "link": f"/teacher/tasks?open-task={task.id}",
    }


def _can_complete(task: TeacherTask) -> bool:
    """低风险判定：非高优先级、未逾期、不来自预警/审批。

    注意这里用 ``due_at`` 自行判断逾期，而不是读 ``task.overdue``：
    后者是 schema 层计算出来的属性，ORM 实体上没有该字段。
    """
    if task.priority == TaskPriority.HIGH:
        return False
    if task.due_at and task.due_at < local_today():
        return False
    if task.source_type in (TaskSourceType.ALERT, TaskSourceType.APPROVAL):
        return False
    return True


def _build_actions(facts: dict, name_map: dict[int, str]) -> list[dict]:
    """今日梳理里的可操作条目：预警 → 请假 → 逾期 → 今日到期。"""
    actions: list[dict] = []

    for a in facts["alerts"][:2]:
        actions.append({
            "id": f"alert-{a['alert_id']}",
            "kind": "alert",
            "group": "alert",
            "label": f"{a['level_label']}预警",
            "title": a["summary"][:40] or "有未闭环的心理预警",
            "student_id": a["student_id"],
            "student_name": a["student_name"],
            "priority": "high",
            "source_label": "心理预警",
            "can_complete": False,
            "link": f"/teacher/crisis?student_id={a['student_id']}&alert_id={a['alert_id']}",
            "action_text": "去跟进",
        })

    for l in facts["pending_leaves"][:2]:
        actions.append({
            "id": f"leave-{l['leave_id']}",
            "kind": "leave",
            "group": "leave",
            "label": "请假审批",
            "title": f"{l['student_name']} 的{l['leave_type_label']}申请待批",
            "student_id": l["student_id"],
            "student_name": l["student_name"],
            "priority": "mid",
            "source_label": "请假",
            "can_complete": False,
            "link": "/teacher/approval",
            "action_text": "去审批",
        })

    for t in facts["_overdue"][:2]:
        item = _task_action(t, group="overdue", kind_label="逾期", name_map=name_map)
        item["action_text"] = "去处理"
        actions.append(item)

    for t in facts["_due_today"][:2]:
        item = _task_action(t, group="due", kind_label="今日到期", name_map=name_map)
        item["action_text"] = "一键完成" if item["can_complete"] else "去处理"
        actions.append(item)


    return actions


def _build_suggestions(facts: dict) -> list[dict]:
    """AI 建议：可以直接转成任务的小动作（前端一键加入今日任务）。"""
    out: list[dict] = []
    if facts["quiet_students"]:
        s = facts["quiet_students"][0]
        out.append({
            "priority": "mid",
            "when": "今天",
            "title": f"关心一下 {s['name']}",
            "content": f"__近两周没有新的记录__，先发一条关心消息，看看是否需要约谈。",
            "student_id": s["student_id"],
            "student_name": s["name"],
            "task_title": f"跟进 {s['name']} 近期状态",
        })
    if facts["severe_total"]:
        out.append({
            "priority": "high",
            "when": "今天上午",
            "title": "把高危预警的跟进记录补全",
            "content": "==高危预警不过夜==，谈话后记得在预警里填写干预方式，否则下一条日报还会提醒。",
            "task_title": "补全高危预警跟进记录",
        })
    if facts["tasks"]["left_from_yesterday"]:
        out.append({
            "priority": "mid",
            "when": "今天",
            "title": "给昨日遗留任务重新定一个截止时间",
            "content": "一直挂着会稀释优先级，__,能明天做的就改期，做不了的关掉__。",
            "task_title": "重排昨日遗留任务的截止时间",
        })
    return out[:3]


# ==================== 主流程 ====================

async def build_teacher_daily_report(db: Session, teacher: User, force_refresh: bool = False) -> dict:
    """构建教师日报；``force_refresh=True`` 跳过 10 分钟缓存（「重新生成」按钮用）。"""
    facts = collect_facts(db, teacher)
    weather = await get_weather()
    cache_key = f"{teacher.id}-{_fingerprint(facts, weather)}"
    if not force_refresh:
        hit = _report_cache.get(cache_key)
        if hit and time.time() - hit[0] < REPORT_TTL:
            return hit[1]

    fortune = _fortune(facts, weather, teacher)
    sections = _rule_sections(facts)
    llm = await _llm_sections(facts, weather, teacher)
    if llm:
        sections = _merge_sections(sections, llm["sections"])
        fortune.update(llm["fortune"])

    hour = _local(datetime.now(timezone.utc)).hour
    greeting = "早上好" if hour < 11 else "中午好" if hour < 14 else "下午好" if hour < 18 else "晚上好"
    report = {
        "date": facts["date"],
        "weekday": facts["weekday"],
        "date_text": f"{_md(date.fromisoformat(facts['date']))} {facts['weekday']}",
        "greeting": f"{greeting}，{facts['teacher_name']}",
        "weather": weather,
        "fortune": fortune,
        "sections": sections,
        "actions": _build_actions(facts, facts["_name_map"]),
        "suggestions": _build_suggestions(facts),
        "summary": {
            "open": facts["tasks"]["open"],
            "due_today": facts["tasks"]["due_today"],
            "overdue": facts["tasks"]["overdue"],
            "high": facts["tasks"]["high"],
            "done_yesterday": facts["tasks"]["done_yesterday"],
            "alert_total": facts["alert_total"],
            "severe_total": facts["severe_total"],
            "leave_total": facts["leave_total"],
            "student_total": facts["student_total"],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _report_cache[cache_key] = (time.time(), report)
    return report


def clear_cache() -> None:
    """清空报告缓存（测试或数据批量变更后使用）。"""
    _report_cache.clear()
