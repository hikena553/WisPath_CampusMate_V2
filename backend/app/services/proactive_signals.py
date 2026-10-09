"""学生主动触达信号采集层。

统一为 proactive_engine 提供「真实业务信号」，取代旧版「必须有画像快照」的前提：
- 画像/风险：StudentProfileSnapshot（最近两条，用于成长档位对比）；
- 成绩：grades 表（学期均绩轨迹、最新学期不及格课程）；
- 课表：courses 表（今日课程、下一节课，节次映射为真实时间）；
- 考试：exams 表（7 天内临考）；
- 待办：plan_tasks（逾期未完成）；
- 请假：leave_requests（待审批 / 近 7 天审批结果）；
- 成长档案：growth_records（条数 / 距上次记录天数）；
- 互动活跃度：conversations（最近对话时间），无对话时回退画像 behavioral_patterns。

设计约束：
1. `full=False` 只采集画像 + 成绩（教师视角遍历全体学生时避免放大成 N×8 次查询）；
2. 每个数据源独立兜底——任何一张表出问题都不该让主动触达接口 500，
   取数失败时该维度留空（触发器自然不命中），并记 warning 日志。
"""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.academic import Course, Exam, Grade
from app.models.conversation import Conversation
from app.models.growth import GrowthRecord
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.plan import PlanTask, StudyPlan, TaskStatus
from app.models.profile import StudentProfileSnapshot
from app.models.user import User
from app.utils.enum_helpers import safe_enum_val

logger = logging.getLogger(__name__)

# 节次 -> 上课时间（与前端课程表 periodTimes 保持一致）
PERIOD_TIMES: dict[int, str] = {
    1: "08:30", 2: "09:20", 3: "10:25", 4: "11:15",
    5: "14:10", 6: "15:00", 7: "16:05", 8: "16:55",
    9: "18:30", 10: "19:20", 11: "20:10", 12: "21:00",
}

EXAM_WINDOW_DAYS = 7          # 临考窗口
RECENT_LEAVE_DAYS = 7         # 请假审批结果回溯窗口
GROWTH_GAP_DAYS = 30          # 成长档案断档阈值（与引擎展示口径一致）

# 成绩/均绩轨迹判定容差
GPA_DROP_DELTA = 0.3
GPA_RISE_DELTA = 0.3


@dataclass
class CourseInfo:
    """今日课程（节次已映射为真实时间，供引擎直接展示）"""

    name: str
    location: str
    start_period: int
    end_period: int
    start_time: str
    start_minutes: int


@dataclass
class StudentSignals:
    """一名学生的主动触达信号快照（默认空，取数失败即保持空）"""

    # ── 画像 / 风险 ──
    has_snapshot: bool = False
    risk_score: float | None = None
    academic_score: float | None = None
    engagement_score: float | None = None
    growth_score: float | None = None
    prev_growth_score: float | None = None
    overall_risk: float | None = None

    # ── 成绩 ──
    grade_trajectory: str | None = None          # declining / stable / improving
    latest_gpa: float | None = None
    prev_gpa: float | None = None
    failing_courses: list[dict[str, Any]] = field(default_factory=list)

    # ── 考试 ──
    upcoming_exams: list[dict[str, Any]] = field(default_factory=list)

    # ── 课程 ──
    next_course: CourseInfo | None = None
    next_course_minutes_left: int | None = None
    today_courses: list[CourseInfo] = field(default_factory=list)
    now_minutes: int = 0

    # ── 待办 ──
    overdue_tasks: list[dict[str, Any]] = field(default_factory=list)

    # ── 请假 ──
    pending_leaves: int = 0
    recent_leave_results: list[dict[str, Any]] = field(default_factory=list)

    # ── 成长档案 ──
    record_count: int = 0
    days_since_record: int | None = None

    # ── 互动活跃度 ──
    inactive_days: int | None = None


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

def _to_minutes(t: time | None) -> int | None:
    if t is None:
        return None
    return t.hour * 60 + t.minute


def _period_start_minutes(period: int) -> int:
    """把节次映射为「距零点分钟数」，未知节次回退到第 1 节。"""
    hhmm = PERIOD_TIMES.get(period) or PERIOD_TIMES[1]
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _as_naive_local(dt: datetime | None) -> datetime | None:
    """把可能带时区的历史时间归一到本地 naive 时间，避免相减报错/错算。"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 2)


# ═══════════════════════════════════════════════════════════
# 各数据源采集
# ═══════════════════════════════════════════════════════════

def _load_profile(db: Session, student: User, sig: StudentSignals) -> tuple[Any, Any]:
    """画像快照（最近两条）。返回 (behavioral_patterns.inactive_days, .grade_trajectory)。"""
    snaps = (
        db.query(StudentProfileSnapshot)
        .filter(StudentProfileSnapshot.student_id == student.id)
        .order_by(StudentProfileSnapshot.snapshot_date.desc(), StudentProfileSnapshot.id.desc())
        .limit(2)
        .all()
    )
    if not snaps:
        return None, None

    latest = snaps[0]
    sig.has_snapshot = True
    sig.risk_score = latest.psychological_risk
    sig.academic_score = latest.academic_score
    sig.engagement_score = latest.engagement_score
    sig.growth_score = latest.growth_score
    sig.overall_risk = latest.overall_risk
    if len(snaps) > 1:
        sig.prev_growth_score = snaps[1].growth_score

    bp = latest.behavioral_patterns or {}
    return bp.get("inactive_days"), bp.get("grade_trajectory")


def _load_grades(db: Session, student: User, sig: StudentSignals) -> None:
    """学期均绩轨迹 + 最新学期不及格课程。"""
    grades = db.query(Grade).filter(Grade.student_id == student.id).all()
    if not grades:
        return

    by_semester: dict[str, list[Grade]] = {}
    for g in grades:
        by_semester.setdefault(g.semester or "", []).append(g)

    semesters = sorted(by_semester.keys(), reverse=True)
    latest_sem = semesters[0]
    sig.latest_gpa = _avg([g.gpa for g in by_semester[latest_sem] if g.gpa is not None])

    if len(semesters) > 1:
        prev_sem = semesters[1]
        sig.prev_gpa = _avg([g.gpa for g in by_semester[prev_sem] if g.gpa is not None])
        if sig.latest_gpa is not None and sig.prev_gpa is not None:
            if sig.latest_gpa < sig.prev_gpa - GPA_DROP_DELTA:
                sig.grade_trajectory = "declining"
            elif sig.latest_gpa > sig.prev_gpa + GPA_RISE_DELTA:
                sig.grade_trajectory = "improving"
            else:
                sig.grade_trajectory = "stable"

    sig.failing_courses = [
        {"course_name": g.course_name, "score": g.score}
        for g in by_semester[latest_sem]
        if g.score is not None and g.score < 60
    ]


def _load_exams(db: Session, student: User, sig: StudentSignals) -> None:
    today = date.today()
    exams = (
        db.query(Exam)
        .filter(
            Exam.student_id == student.id,
            Exam.exam_date >= today,
            Exam.exam_date <= today + timedelta(days=EXAM_WINDOW_DAYS),
        )
        .order_by(Exam.exam_date.asc(), Exam.start_time.asc())
        .all()
    )
    for e in exams:
        sig.upcoming_exams.append({
            "course_name": e.course_name,
            "exam_date": e.exam_date,
            "days_left": (e.exam_date - today).days,
            "start_time": e.start_time.strftime("%H:%M") if e.start_time else "",
            "location": e.location or "",
        })


def _load_courses(db: Session, student: User, sig: StudentSignals) -> None:
    """今日课程 + 下一节课（依赖班级关联，节次映射为真实时间）。"""
    now = datetime.now()
    sig.now_minutes = now.hour * 60 + now.minute

    if not student.class_group_id:
        return

    courses = (
        db.query(Course)
        .filter(
            Course.class_group_id == student.class_group_id,
            Course.day_of_week == now.isoweekday(),
        )
        .order_by(Course.start_period.asc())
        .all()
    )

    for c in courses:
        sig.today_courses.append(CourseInfo(
            name=c.name,
            location=c.location or "",
            start_period=c.start_period,
            end_period=c.end_period,
            start_time=PERIOD_TIMES.get(c.start_period, ""),
            start_minutes=_period_start_minutes(c.start_period),
        ))

    for info in sig.today_courses:
        if info.start_minutes > sig.now_minutes:
            sig.next_course = info
            sig.next_course_minutes_left = info.start_minutes - sig.now_minutes
            break


def _load_todos(db: Session, student: User, sig: StudentSignals) -> None:
    """逾期未完成的学习计划任务。"""
    today = date.today()
    rows = (
        db.query(PlanTask)
        .join(StudyPlan, StudyPlan.id == PlanTask.plan_id)
        .filter(
            StudyPlan.student_id == student.id,
            PlanTask.status != TaskStatus.DONE,
            PlanTask.due_date.isnot(None),
            PlanTask.due_date < today,
        )
        .order_by(PlanTask.due_date.asc())
        .all()
    )
    for t in rows:
        sig.overdue_tasks.append({
            "title": t.title,
            "due_date": t.due_date,
            "days_overdue": (today - t.due_date).days if t.due_date else 0,
        })


def _load_leaves(db: Session, student: User, sig: StudentSignals) -> None:
    """待审批数量 + 近 7 天审批结果。"""
    pending = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.student_id == student.id,
            LeaveRequest.status == LeaveStatus.PENDING,
        )
        .count()
    )
    sig.pending_leaves = pending

    cutoff = datetime.now() - timedelta(days=RECENT_LEAVE_DAYS)
    results = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.student_id == student.id,
            LeaveRequest.status.in_([LeaveStatus.APPROVED, LeaveStatus.REJECTED]),
            LeaveRequest.updated_at >= cutoff,
        )
        .order_by(LeaveRequest.updated_at.desc())
        .all()
    )
    for lv in results:
        sig.recent_leave_results.append({
            "start_date": str(lv.start_date),
            "end_date": str(lv.end_date),
            "status": safe_enum_val(lv.status),
            "reject_reason": lv.reject_reason or "",
        })


def _load_growth(db: Session, student: User, sig: StudentSignals) -> None:
    """成长档案条数 + 距上次记录天数。"""
    records = (
        db.query(GrowthRecord)
        .filter(GrowthRecord.student_id == student.id)
        .all()
    )
    sig.record_count = len(records)
    if records:
        latest = max(r.date for r in records if r.date is not None) if any(r.date for r in records) else None
        if latest is not None:
            sig.days_since_record = (date.today() - latest).days


def _load_activity(db: Session, student: User, sig: StudentSignals, snapshot_inactive: Any) -> None:
    """最近一次对话时间推算久未互动天数，无对话时回退画像值。"""
    last_conv = (
        db.query(Conversation)
        .filter(Conversation.user_id == student.id)
        .order_by(Conversation.updated_at.desc())
        .first()
    )
    last = _as_naive_local(last_conv.updated_at) if last_conv else None
    if last is not None:
        sig.inactive_days = max(0, (datetime.now() - last).days)
        return

    if snapshot_inactive is not None:
        try:
            sig.inactive_days = int(snapshot_inactive)
        except (TypeError, ValueError):
            logger.warning("画像 inactive_days 非法，已忽略: %r", snapshot_inactive)


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

def gather_signals(db: Session, student: User, full: bool = True) -> StudentSignals:
    """采集一名学生的主动触达信号。

    full=True：采集全部维度（学生视角 / 全量评估）；
    full=False：只采集画像 + 成绩（教师视角遍历时保持轻量）。

    每个数据源独立兜底，单表异常不影响其余信号。
    """
    sig = StudentSignals()

    snapshot_inactive: Any = None
    snapshot_trajectory: Any = None
    try:
        snapshot_inactive, snapshot_trajectory = _load_profile(db, student, sig)
    except Exception:
        logger.warning("主动信号-画像 取数失败 student=%s", student.id, exc_info=True)

    try:
        _load_grades(db, student, sig)
    except Exception:
        logger.warning("主动信号-成绩 取数失败 student=%s", student.id, exc_info=True)

    # 无真实成绩轨迹时，回退画像里的历史判定（兼容旧数据 / 单元测试口径）
    if sig.grade_trajectory is None and snapshot_trajectory:
        sig.grade_trajectory = snapshot_trajectory

    if not full:
        return sig

    for name, loader in (
        ("考试", _load_exams),
        ("课表", _load_courses),
        ("待办", _load_todos),
        ("请假", _load_leaves),
        ("成长档案", _load_growth),
    ):
        try:
            loader(db, student, sig)
        except Exception:
            logger.warning("主动信号-%s 取数失败 student=%s", name, student.id, exc_info=True)

    try:
        _load_activity(db, student, sig, snapshot_inactive)
    except Exception:
        logger.warning("主动信号-活跃度 取数失败 student=%s", student.id, exc_info=True)

    return sig