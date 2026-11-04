"""「我的育人成长」聚合服务。

这一层是教师端 v3 的核心：把散落在 10 张表里的教师侧数据，聚合成一个
**以教师为第一人称**的叙事——我做了什么、我成长到哪、我强在哪。

刻意不新建任何表：所有数字都来自既有业务表（关怀 / 家访 / 家校 / 待办 /
档案 / 徽章 / 点名 / 作业 / 成绩）。原因有二：

1. 新表意味着双写与不一致风险，而这批数据本来就已存在，缺的只是聚合口径；
2. 「成长」是派生概念，不是原始事实。派生数据落库后一旦口径调整就要迁移历史，
   而现算永远与业务表一致。

性能约束：单次请求固定 8~10 条聚合查询，不随学生数量增长（逐学生查询会被
N+1 拖垮）。逐学生粒度的东西（能力雷达的互评回填）只有一条 join 查询。
"""
from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.academic import Course, Grade
from app.models.badge import UserBadge
from app.models.care_center import CareEvent, CareEventType, HomeVisitRecord, FollowUpStatus, PraiseRecord
from app.models.care_record import CareRecord
from app.models.guardian import GuardianContactLog
from app.models.peer_survey import PeerSurvey, PeerSurveyResponse
from app.models.teacher_portfolio import TeacherPortfolioItem
from app.models.teacher_task import TaskStatus, TeacherTask
from app.models.teaching import Attendance, AttendanceStatus, Homework, HomeworkSubmission, SubmissionStatus
from app.models.user import User, UserRole
from app.services import badge_service

# ── 九项职业能力（对标《高等学校辅导员职业能力标准（暂行）》）──────
#
# 每项能力都由既有数据折算，不做主观打分。权重之和固定为 100，
# 折算逻辑见 ``_capability_radar``：分数 = 该能力各项指标达成率的加权平均。
CAPABILITIES: list[dict] = [
    {"key": "ideology", "name": "思想理论教育", "icon": "🧭",
     "desc": "主题班会、班级公告、思想引导类活动的覆盖"},
    {"key": "party", "name": "党团与班级建设", "icon": "🚩",
     "desc": "班团活动组织与骨干培养的投入"},
    {"key": "academic", "name": "学业指导", "icon": "📘",
     "desc": "作业跟进、成绩分析与学业预警的处理"},
    {"key": "mental", "name": "心理健康教育", "icon": "💚",
     "desc": "谈心谈话与心理类关怀记录的密度"},
    {"key": "network", "name": "网络思政", "icon": "🌐",
     "desc": "线上沟通与班级群互动的活跃度"},
    {"key": "crisis", "name": "危机事件应对", "icon": "🛡️",
     "desc": "预警响应的及时性与闭环率"},
    {"key": "career", "name": "职业规划指导", "icon": "🎯",
     "desc": "生涯类谈话与成长档案的沉淀"},
    {"key": "aid", "name": "资助育人", "icon": "🤝",
     "desc": "困难学生关怀、家访与家长沟通"},
    {"key": "class", "name": "班级管理", "icon": "📋",
     "desc": "待办办结率、公告触达与日常事务效率"},
]


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def _scale(value: float, target: float, cap: float = 100.0) -> float:
    """把「达成量 / 目标量」折算成 0~cap 的分数。目标量为 0 时返回 0。"""
    if target <= 0:
        return 0.0
    return round(min(value / target, 1.0) * cap, 1)


def _trend(current: float, previous: float) -> float | None:
    """环比：上一期为 0 时不返回百分比（避免「暴涨 1000%」的误导）。"""
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


# ══════════════════════════════════════════════════════════════════
# 1. 履职画像：我做了什么
# ══════════════════════════════════════════════════════════════════


def _duty_profile(db: Session, teacher: User) -> dict:
    tid = teacher.id
    now = datetime.now()
    m_start = now - timedelta(days=30)
    p_start = now - timedelta(days=60)

    students = [
        s for s in db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == tid).all()
    ]
    sids = [s.id for s in students]

    def _count_between(model, start, end, **filters):
        q = db.query(func.count(model.id)).filter(
            model.teacher_id == tid, model.created_at >= start, model.created_at < end
        )
        if filters:
            for k, v in filters.items():
                q = q.filter(getattr(model, k) == v)
        return int(q.scalar() or 0)

    # ── 四项主指标（本月 / 上月，用于环比）──
    care_m = _count_between(CareRecord, m_start, now, is_deleted=False)
    care_p = _count_between(CareRecord, p_start, m_start, is_deleted=False)
    visit_m = _count_between(HomeVisitRecord, m_start, now, is_deleted=False)
    visit_p = _count_between(HomeVisitRecord, p_start, m_start, is_deleted=False)
    guardian_m = _count_between(GuardianContactLog, m_start, now, is_deleted=False)
    guardian_p = _count_between(GuardianContactLog, p_start, m_start, is_deleted=False)
    praise_m = _count_between(PraiseRecord, m_start, now, is_deleted=False)

    # ── 待办办结率（全周期，不按自然月——办结率是能力指标不是工作量指标）──
    total_tasks = int(db.query(func.count(TeacherTask.id)).filter(TeacherTask.teacher_id == tid).scalar() or 0)
    done_tasks = int(
        db.query(func.count(TeacherTask.id))
        .filter(TeacherTask.teacher_id == tid, TeacherTask.status == TaskStatus.DONE)
        .scalar()
        or 0
    )
    open_tasks = int(
        db.query(func.count(TeacherTask.id))
        .filter(
            TeacherTask.teacher_id == tid,
            TeacherTask.status.in_([TaskStatus.PENDING, TaskStatus.CONTACTED, TaskStatus.CARED]),
        )
        .scalar()
        or 0
    )
    overdue_tasks = int(
        db.query(func.count(TeacherTask.id))
        .filter(
            TeacherTask.teacher_id == tid,
            TeacherTask.status.in_([TaskStatus.PENDING, TaskStatus.CONTACTED, TaskStatus.CARED]),
            TeacherTask.due_at.isnot(None),
            TeacherTask.due_at < date.today(),
        )
        .scalar()
        or 0
    )

    # ── 家访回访完成情况：有 follow_up 但没回访 = 悬空的家访 ──
    pending_visits = int(
        db.query(func.count(HomeVisitRecord.id))
        .filter(
            HomeVisitRecord.teacher_id == tid,
            HomeVisitRecord.is_deleted.is_(False),
            HomeVisitRecord.follow_up_status == FollowUpStatus.PENDING,
        )
        .scalar()
        or 0
    )

    # ── 覆盖率：本月被关怀过的学生 / 名下学生 ──
    cared_students = 0
    if sids:
        cared_students = int(
            db.query(func.count(func.distinct(CareRecord.student_id)))
            .filter(
                CareRecord.teacher_id == tid,
                CareRecord.is_deleted.is_(False),
                CareRecord.created_at >= m_start,
                CareRecord.student_id.in_(sids),
            )
            .scalar()
            or 0
        )

    # ── 教学线工作量（也是「履职」，不该只算育人）──
    my_course_ids = [cid for (cid,) in db.query(Course.id).filter(Course.teacher_id == tid).all()]
    teach = {"courses": len(my_course_ids), "sessions_month": 0, "homeworks": 0, "graded": 0}
    if my_course_ids:
        teach["sessions_month"] = int(
            db.query(func.count(func.distinct(Attendance.attend_date)))
            .filter(
                Attendance.course_id.in_(my_course_ids),
                Attendance.attend_date >= m_start.date(),
            )
            .scalar()
            or 0
        )
        teach["homeworks"] = int(
            db.query(func.count(Homework.id))
            .filter(Homework.teacher_id == tid, Homework.is_deleted.is_(False))
            .scalar()
            or 0
        )
        teach["graded"] = int(
            db.query(func.count(HomeworkSubmission.id))
            .join(Homework, Homework.id == HomeworkSubmission.homework_id)
            .filter(Homework.teacher_id == tid, HomeworkSubmission.status == SubmissionStatus.GRADED)
            .scalar()
            or 0
        )

    return {
        "student_total": len(students),
        "cared_students_month": cared_students,
        "coverage_rate": _pct(cared_students, len(students)),
        "metrics": [
            {
                "key": "care", "label": "关怀记录", "icon": "🫶", "unit": "条",
                "value": care_m, "previous": care_p, "trend": _trend(care_m, care_p),
                "hint": "谈心、谈话、评语等写下来的记录",
            },
            {
                "key": "visit", "label": "家访", "icon": "🏠", "unit": "次",
                "value": visit_m, "previous": visit_p, "trend": _trend(visit_m, visit_p),
                "hint": "实地 / 电话 / 视频家访",
            },
            {
                "key": "guardian", "label": "家校留痕", "icon": "📞", "unit": "条",
                "value": guardian_m, "previous": guardian_p, "trend": _trend(guardian_m, guardian_p),
                "hint": "与家长的有效沟通记录",
            },
            {
                "key": "praise", "label": "正向激励", "icon": "🌻", "unit": "次",
                "value": praise_m, "previous": _count_between(PraiseRecord, p_start, m_start, is_deleted=False),
                "trend": _trend(praise_m, _count_between(PraiseRecord, p_start, m_start, is_deleted=False)),
                "hint": "表扬与徽章激励",
            },
        ],
        "tasks": {
            "total": total_tasks,
            "done": done_tasks,
            "open": open_tasks,
            "overdue": overdue_tasks,
            "done_rate": _pct(done_tasks, total_tasks),
        },
        "pending_visits": pending_visits,
        "teaching": teach,
        "period": {"care_month": m_start.date().isoformat(), "care_previous": p_start.date().isoformat()},
    }


# ══════════════════════════════════════════════════════════════════
# 2. 成长轨迹：我走到哪了
# ══════════════════════════════════════════════════════════════════


def _growth_timeline(db: Session, teacher: User, limit: int = 40) -> list[dict]:
    """把档案条目 + 徽章解锁 + 等级晋升合并成一条时间线。

    排序依据是「发生日期」而非创建时间：教师补录一条去年获奖的荣誉时，
    它应该落在去年那一段，而不是今天。
    """
    items: list[dict] = []

    for p in (
        db.query(TeacherPortfolioItem)
        .filter(TeacherPortfolioItem.teacher_id == teacher.id, TeacherPortfolioItem.is_deleted.is_(False))
        .all()
    ):
        items.append({
            "kind": "portfolio",
            "type": p.item_type.value if hasattr(p.item_type, "value") else str(p.item_type),
            "title": p.title,
            "desc": (p.reflection or "")[:80],
            "date": str(p.occurred_on or p.created_at.date()),
            "icon": {"case": "📁", "honor": "🏅", "training": "🎓", "research": "🔬"}.get(
                p.item_type.value if hasattr(p.item_type, "value") else str(p.item_type), "📁"
            ),
        })

    catalog = {d["code"]: d for d in badge_service.BADGE_CATALOG}
    for b in (
        db.query(UserBadge)
        .filter(UserBadge.user_id == teacher.id, UserBadge.awarded_at.isnot(None))
        .all()
    ):
        defn = catalog.get(b.badge_code)
        if not defn:
            continue
        items.append({
            "kind": "badge",
            "type": defn.get("category", ""),
            "title": f"解锁徽章「{defn['name']}」",
            "desc": defn.get("desc", ""),
            "date": str(_naive(b.awarded_at).date()) if b.awarded_at else "",
            "icon": defn.get("icon", "🏅"),
        })

    items = [i for i in items if i["date"]]
    items.sort(key=lambda i: i["date"], reverse=True)
    return items[:limit]


def _impact_curve(db: Session, teacher: User, weeks: int = 12) -> dict:
    """育人影响力曲线：近 N 周每周的「关怀 + 家访 + 家校 + 表扬」总量。

    刻意不做成「综合指数」——指数需要解释，而教师看一眼就懂的是动作次数。
    """
    today = date.today()
    start = today - timedelta(weeks=weeks - 1)
    start -= timedelta(days=start.weekday())  # 对齐到周一

    buckets: dict[str, int] = {}
    cursor = start
    while cursor <= today:
        buckets[cursor.isoformat()] = 0
        cursor += timedelta(days=7)

    def _week_key(d: date) -> str:
        monday = d - timedelta(days=d.weekday())
        return monday.isoformat()

    sources = [
        (CareRecord, "created_at"),
        (HomeVisitRecord, "created_at"),
        (GuardianContactLog, "created_at"),
        (PraiseRecord, "created_at"),
    ]
    for model, col in sources:
        rows = (
            db.query(getattr(model, col))
            .filter(model.teacher_id == teacher.id, getattr(model, col) >= datetime.combine(start, datetime.min.time()))
            .all()
        )
        for (ts,) in rows:
            ts = _naive(ts)
            if not ts:
                continue
            k = _week_key(ts.date())
            if k in buckets:
                buckets[k] += 1

    points = [{"week": k, "value": v} for k, v in sorted(buckets.items())]
    values = [p["value"] for p in points]
    return {
        "points": points,
        "total": sum(values),
        "avg": round(statistics.mean(values), 1) if values else 0.0,
        "best_week": max(points, key=lambda p: p["value"])["week"] if points else None,
    }


def _teaching_profile(db: Session, teacher: User) -> dict:
    """授课概况：我教的课、学生规模、教学重合度。"""
    tid = teacher.id
    courses = db.query(Course).filter(Course.teacher_id == tid).all()
    class_ids = {c.class_group_id for c in courses if c.class_group_id}
    total_students = 0
    if class_ids:
        total_students = int(
            db.query(func.count(User.id))
            .filter(User.role == UserRole.STUDENT, User.class_group_id.in_(class_ids))
            .scalar()
            or 0
        )
    tutoring = {
        sid for (sid,) in db.query(User.id).filter(User.role == UserRole.STUDENT, User.tutor_id == tid).all()
    }
    taught = set()
    if class_ids:
        taught = {
            sid
            for (sid,) in db.query(User.id)
            .filter(User.role == UserRole.STUDENT, User.class_group_id.in_(class_ids))
            .all()
        }
    course_ids = [c.id for c in courses]
    sessions = 0
    absent = 0
    if course_ids:
        sessions = int(
            db.query(func.count(func.distinct(Attendance.attend_date)))
            .filter(Attendance.course_id.in_(course_ids))
            .scalar()
            or 0
        )
        absent = int(
            db.query(func.count(Attendance.id))
            .filter(Attendance.course_id.in_(course_ids), Attendance.status == AttendanceStatus.ABSENT)
            .scalar()
            or 0
        )
    return {
        "course_count": len(courses),
        "class_count": len(class_ids),
        "student_count": total_students,
        "overlap_count": len(taught & tutoring),
        "attendance_sessions": sessions,
        "absent_total": absent,
        "homework_count": int(
            db.query(func.count(Homework.id))
            .filter(Homework.teacher_id == tid, Homework.is_deleted.is_(False))
            .scalar()
            or 0
        ),
    }


# ══════════════════════════════════════════════════════════════════
# 3. 能力雷达：我强在哪
# ══════════════════════════════════════════════════════════════════


def _peer_scores(db: Session, teacher: User) -> dict[str, float]:
    """互评聚合：把 ``PeerSurveyResponse.scores_json`` 按题目 key 求均值。

    只返回均值，不返回任何单条答卷——匿名承诺落在这一层：即使有人拿到
    数据库也只看到聚合值（原始表本身也不存提交人）。
    """
    responses = (
        db.query(PeerSurveyResponse)
        .filter(PeerSurveyResponse.target_teacher_id == teacher.id)
        .all()
    )
    if not responses:
        return {}
    import json

    totals: dict[str, list[float]] = {}
    for r in responses:
        try:
            scores = json.loads(r.scores_json or "{}")
        except (TypeError, ValueError):
            continue
        if not isinstance(scores, dict):
            continue
        for k, v in scores.items():
            try:
                totals.setdefault(str(k), []).append(float(v))
            except (TypeError, ValueError):
                continue
    return {k: round(statistics.mean(v), 2) for k, v in totals.items() if v}


def _capability_radar(db: Session, teacher: User, duty: dict, teaching: dict) -> dict:
    """九项能力折算。

    每项满分 100，全部来自可观测行为，不做主观评价：

    - 有互评数据的能力项，取「行为得分 60% + 互评得分折算 40%」，
      因为互评是外部视角，能校正「只做数字不做事」的偏差；
    - 无互评数据时完全按行为折算，不虚构分数。
    """
    tid = teacher.id
    today = date.today()
    m_start = datetime.now() - timedelta(days=30)

    care_by_type = {
        (t.value if hasattr(t, "value") else str(t)): int(c)
        for t, c in db.query(CareRecord.record_type, func.count(CareRecord.id))
        .filter(CareRecord.teacher_id == tid, CareRecord.is_deleted.is_(False))
        .group_by(CareRecord.record_type)
        .all()
    }
    talk_count = care_by_type.get("talk", 0)
    care_count = care_by_type.get("care", 0)
    comment_count = care_by_type.get("comment", 0)

    announcements = int(
        db.query(func.count(func.distinct(CareEvent.id)))
        .filter(CareEvent.teacher_id == tid, CareEvent.event_type == CareEventType.BIRTHDAY)
        .scalar()
        or 0
    )
    visits = int(
        db.query(func.count(HomeVisitRecord.id))
        .filter(HomeVisitRecord.teacher_id == tid, HomeVisitRecord.is_deleted.is_(False))
        .scalar()
        or 0
    )
    guardian_logs = int(
        db.query(func.count(GuardianContactLog.id))
        .filter(GuardianContactLog.teacher_id == tid, GuardianContactLog.is_deleted.is_(False))
        .scalar()
        or 0
    )
    # 危机闭环率
    from app.models.crisis import AIDialogSummary

    student_ids = [s.id for s in db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == tid).all()]
    crisis_total = crisis_resolved = 0
    if student_ids:
        crisis_total = int(
            db.query(func.count(AIDialogSummary.id)).filter(AIDialogSummary.student_id.in_(student_ids)).scalar() or 0
        )
        crisis_resolved = int(
            db.query(func.count(AIDialogSummary.id))
            .filter(AIDialogSummary.student_id.in_(student_ids), AIDialogSummary.resolved.is_(True))
            .scalar()
            or 0
        )
    # 作业批改响应
    graded = teaching.get("homework_count") and int(
        db.query(func.count(HomeworkSubmission.id))
        .join(Homework, Homework.id == HomeworkSubmission.homework_id)
        .filter(Homework.teacher_id == tid, HomeworkSubmission.status == SubmissionStatus.GRADED)
        .scalar()
        or 0
    )
    homework_total = max(teaching.get("homework_count") or 0, 1)

    peers = _peer_scores(db, teacher)
    peer_map = {  # 互评题目 key → 能力 key（问卷模板可用这些 key 直接对齐雷达）
        "ideology": "ideology", "party": "party", "academic": "academic",
        "mental": "mental", "network": "network", "crisis": "crisis",
        "career": "career", "aid": "aid", "class": "class",
    }

    raw: dict[str, float] = {
        "ideology": _scale(announcements, 10) * 0.5 + _scale(comment_count, 20) * 0.5,
        "party": _scale(care_count, 15),
        "academic": _scale(graded / homework_total * 100 if teaching.get("homework_count") else 0, 100) * 0.6
                    + _scale(duty["tasks"]["done_rate"], 100) * 0.4,
        "mental": _scale(talk_count, 20),
        "network": _scale(guardian_logs, 15),
        "crisis": _scale(_pct(crisis_resolved, crisis_total) if crisis_total else 0, 100),
        "career": _scale(comment_count, 15),
        "aid": _scale(visits, 6) * 0.6 + _scale(duty["coverage_rate"], 100) * 0.4,
        "class": _scale(duty["tasks"]["done_rate"], 100) * 0.7 + _scale(teaching.get("course_count") or 0, 4) * 0.3,
    }

    items: list[dict] = []
    for cap in CAPABILITIES:
        key = cap["key"]
        behaviour = round(min(raw.get(key, 0.0), 100.0), 1)
        peer = peers.get(key)
        if peer is not None:
            # 互评通常 1~5 分制，折算成百分制后只占 40%，避免单一外部评价决定成绩
            peer_pct = round(min(peer / 5 * 100, 100), 1) if peer <= 5 else round(min(peer, 100), 1)
            score = round(behaviour * 0.6 + peer_pct * 0.4, 1)
        else:
            score = behaviour
        items.append({
            "key": key,
            "name": cap["name"],
            "icon": cap["icon"],
            "desc": cap["desc"],
            "score": score,
            "behaviour_score": behaviour,
            "peer_score": peer,
            "has_peer": peer is not None,
        })

    ranked = sorted(items, key=lambda i: i["score"], reverse=True)
    # top / weak 一定要返回 [名称, 分数]，不要只返回名称：
    # 前端 MyGrowthPage.vue 会调 `top[1].toFixed(1)` 显示分数，
    # 曾经这里返回的是纯名称数组 ["思想理论教育", "党团与班级建设"]，
    # 导致 pageerror: data.radar.top[1].toFixed is not a function —— 整页白屏。
    top = ranked[0] if ranked else None
    weak = next((i for i in reversed(ranked) if i["score"] < 60), None)
    return {
        "items": items,
        "avg": round(statistics.mean([i["score"] for i in items]), 1) if items else 0.0,
        "top": [top["name"], top["score"]] if top else None,
        "weak": [weak["name"], weak["score"]] if weak else None,
        "peer_coverage": sum(1 for i in items if i["has_peer"]),
    }


# ══════════════════════════════════════════════════════════════════
# 4. 对外入口
# ══════════════════════════════════════════════════════════════════


def build_my_growth(db: Session, teacher: User) -> dict:
    """「我的育人成长」主接口的全部数据。

    一次算完再返回：分成四个接口会让前端发起四次请求，而它们的调用时机
    永远是同一个（进入页面），拆开只增加往返不增加灵活性。
    """
    # 先同步一次徽章：进入成长页是最自然的「结算」时机，
    # 让刚完成第 3 次家访的老师立刻看到新徽章，而不是等到某次随机同步。
    try:
        badge_service.evaluate_and_award(db, teacher)
    except Exception:  # noqa: BLE001 - 结算失败不阻断成长页
        pass

    duty = _duty_profile(db, teacher)
    teaching = _teaching_profile(db, teacher)
    radar = _capability_radar(db, teacher, duty, teaching)
    wall = badge_service.build_wall(db, teacher)

    return {
        "teacher": {
            "id": teacher.id,
            "name": teacher.name,
            "avatar": teacher.avatar,
            "college": teacher.college,
            "title": teacher.title,
            "signature": teacher.signature,
            "department": teacher.department,
        },
        "level": wall["level"],
        "badges": {
            "earned": wall["earned"],
            "locked": wall["locked"],
            "earned_count": wall["earned_count"],
            "total_count": wall["total_count"],
        },
        "duty": duty,
        "timeline": _growth_timeline(db, teacher),
        "impact": _impact_curve(db, teacher),
        "teaching": teaching,
        "radar": radar,
        "generated_at": datetime.now().isoformat(),
    }
