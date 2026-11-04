import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.growth import GrowthRecord, StudentProject
from app.models.crisis import AIDialogSummary
from app.models.leave import LeaveRequest
from app.models.academic import Grade
from app.models.message import Message
from app.services.llm_service import _get_client, _get_llm_config
from app.services.prompts import build_teacher_outreach_prompt
from app.services.scoring import calc_radar_score
from app.services import teacher_task_service
from app.core.security import hash_password
from app.utils.enum_helpers import safe_enum_val, safe_enum_str
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


class StudentOut(BaseModel):
    id: int
    name: str
    college: str | None = None
    username: str
    avatar: str | None = None
    skills_json: dict | None = None
    growth_count: int = 0
    score: float = 0
    leave_count: int = 0
    crisis_level: str | None = None
    latest_crisis_summary: str | None = None
    latest_crisis_time: str | None = None
    tutor_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class StudentResumeOut(BaseModel):
    id: int
    name: str
    college: str | None = None
    username: str
    avatar: str | None = None
    skills_json: dict | None = None
    growth_records: list = []
    projects: list = []

    model_config = ConfigDict(from_attributes=True)


class StudentDetailOut(BaseModel):
    id: int
    name: str
    college: str | None = None
    username: str
    avatar: str | None = None
    skills_json: dict | None = None
    growth_records: list = []
    projects: list = []
    crisis_alerts: list = []
    leave_requests: list = []

    model_config = ConfigDict(from_attributes=True)


class DashboardOut(BaseModel):
    # ── 学生维度（既有口径，保持不变：首页班级图表依赖它）──
    total_students: int = 0
    alert_count: int = 0
    pending_leave_count: int = 0
    severe_alert_count: int = 0
    resolved_alert_count: int = 0

    # ── 我的维度（v3 新增）──
    #
    # 为什么非要加这一组：原来 5 个指标的主语全是「学生」，教师打开首页看到的是
    # 「我的人在怎样」，看不到「我今天该做什么、我这周做了多少」。有了这组，
    # 首页第一屏才有资格说「我的工作台」。
    my_open_tasks: int = 0
    my_overdue_tasks: int = 0
    my_due_today: int = 0
    my_care_month: int = 0
    my_visits_month: int = 0
    my_guardian_month: int = 0
    my_done_rate: float = 0
    #: 本月被关怀过的学生占名下学生的比例
    my_coverage_rate: float = 0

    # ── 教学维度（v3 新增，需要 courses.teacher_id）──
    my_course_count: int = 0
    today_course_count: int = 0
    current_week: int | None = None
    semester: str | None = None
    #: 未交作业的待提醒学生数（跨全部作业累计）
    my_pending_submissions: int = 0

    model_config = ConfigDict(from_attributes=True)


def _calc_student_score(db: Session, student_id: int, user: User | None = None) -> float:
    return calc_radar_score(db, student_id, user)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard_stats(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    students = query.all()
    student_ids = [s.id for s in students]
    total = len(student_ids)
    if student_ids:
        alert_count = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids)
        ).count()
        severe_count = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.level == "severe"
        ).count()
        resolved_count = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.resolved == True
        ).count()
        pending_leave = db.query(LeaveRequest).filter(
            LeaveRequest.student_id.in_(student_ids),
            LeaveRequest.status == "pending"
        ).count()
    else:
        alert_count = 0
        severe_count = 0
        resolved_count = 0
        pending_leave = 0

    # ── 「我的」指标 ────────────────────────────────────────────────
    #
    # 全部从既有表现算，不做缓存：数据量都在「一个教师的」量级（几十到几千行），
    # 上缓存反而引入不一致风险。若日后慢，再按 teacher_id 加短 TTL 缓存。
    from datetime import date as _date, datetime as _dt, timedelta as _td

    from app.models.care_center import HomeVisitRecord
    from app.models.care_record import CareRecord
    from app.models.guardian import GuardianContactLog
    from app.models.teacher_task import TaskStatus, TeacherTask
    from app.models.teaching import Homework, HomeworkSubmission, SubmissionStatus

    today = _date.today()
    month_start = _dt.now() - _td(days=30)

    open_statuses = [TaskStatus.PENDING, TaskStatus.CONTACTED, TaskStatus.CARED]
    my_open = db.query(func.count(TeacherTask.id)).filter(
        TeacherTask.teacher_id == user.id, TeacherTask.status.in_(open_statuses)
    ).scalar() or 0
    my_overdue = db.query(func.count(TeacherTask.id)).filter(
        TeacherTask.teacher_id == user.id,
        TeacherTask.status.in_(open_statuses),
        TeacherTask.due_at.isnot(None),
        TeacherTask.due_at < today,
    ).scalar() or 0
    my_due_today = db.query(func.count(TeacherTask.id)).filter(
        TeacherTask.teacher_id == user.id,
        TeacherTask.status.in_(open_statuses),
        TeacherTask.due_at == today,
    ).scalar() or 0
    my_done = db.query(func.count(TeacherTask.id)).filter(
        TeacherTask.teacher_id == user.id, TeacherTask.status == TaskStatus.DONE
    ).scalar() or 0
    my_total = db.query(func.count(TeacherTask.id)).filter(TeacherTask.teacher_id == user.id).scalar() or 0

    my_care = db.query(func.count(CareRecord.id)).filter(
        CareRecord.teacher_id == user.id, CareRecord.is_deleted.is_(False),
        CareRecord.created_at >= month_start,
    ).scalar() or 0
    my_visits = db.query(func.count(HomeVisitRecord.id)).filter(
        HomeVisitRecord.teacher_id == user.id, HomeVisitRecord.is_deleted.is_(False),
        HomeVisitRecord.created_at >= month_start,
    ).scalar() or 0
    my_guardian = db.query(func.count(GuardianContactLog.id)).filter(
        GuardianContactLog.teacher_id == user.id, GuardianContactLog.is_deleted.is_(False),
        GuardianContactLog.created_at >= month_start,
    ).scalar() or 0

    cared_students = 0
    if student_ids:
        cared_students = db.query(func.count(func.distinct(CareRecord.student_id))).filter(
            CareRecord.teacher_id == user.id,
            CareRecord.is_deleted.is_(False),
            CareRecord.created_at >= month_start,
            CareRecord.student_id.in_(student_ids),
        ).scalar() or 0

    # ── 教学指标：只算「我任教的课」，与「我带的班」严格区分 ──
    from app.models.academic import Course
    from app.services.teaching_scope import default_semester

    sem = default_semester(db)
    course_q = db.query(Course).filter(Course.teacher_id == user.id)
    if sem:
        course_q = course_q.filter(Course.semester == sem)
    my_courses = course_q.all()
    today_courses = [c for c in my_courses if c.day_of_week == today.isoweekday()]

    my_pending_subs = 0
    course_ids = [c.id for c in my_courses]
    if course_ids:
        my_pending_subs = db.query(func.count(HomeworkSubmission.id)).join(
            Homework, Homework.id == HomeworkSubmission.homework_id
        ).filter(
            Homework.teacher_id == user.id,
            Homework.is_deleted.is_(False),
            HomeworkSubmission.status == SubmissionStatus.PENDING,
        ).scalar() or 0

    # 教学周与「最新学期」的口径和「我的教学」页保持一致，避免首页与课表页
    # 对「第 N 周」给出两个不同答案
    from app.api.teaching import _week_of_semester

    week, _ = _week_of_semester(sem)
    return DashboardOut(
        total_students=total,
        alert_count=alert_count,
        pending_leave_count=pending_leave,
        severe_alert_count=severe_count,
        resolved_alert_count=resolved_count,
        my_open_tasks=int(my_open),
        my_overdue_tasks=int(my_overdue),
        my_due_today=int(my_due_today),
        my_care_month=int(my_care),
        my_visits_month=int(my_visits),
        my_guardian_month=int(my_guardian),
        my_done_rate=round(my_done / my_total * 100, 1) if my_total else 0.0,
        my_coverage_rate=round(cared_students / total * 100, 1) if total else 0.0,
        my_course_count=len(my_courses),
        today_course_count=len(today_courses),
        current_week=week,
        semester=sem,
        my_pending_submissions=int(my_pending_subs),
    )


@router.get("/students", response_model=list[StudentOut])
def list_students(
    search: str | None = None,
    class_group_id: int | None = None,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    # 按班级取名单：供通讯录「组织架构 → 班级」下钻使用。
    # 班级属于公开的组织信息，此时不套用「仅本人名下辅导员关系」的过滤，
    # 否则教师只能看到自己带的学生，班级下钻会永远为空。
    if class_group_id:
        query = query.filter(User.class_group_id == class_group_id)
    elif user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    if search:
        from app.services.knowledge_service import _escape_like
        safe = _escape_like(search)
        like = f"%{safe}%"
        query = query.filter(
            User.name.like(like, escape="\\") | User.username.like(like, escape="\\") | User.college.like(like, escape="\\")
        )
    students = query.all()
    student_ids = [s.id for s in students]

    # 批量查询：每个学生的成长记录数量（1次查询代替N次）
    growth_count_rows = db.query(
        GrowthRecord.student_id, func.count(GrowthRecord.id)
    ).filter(GrowthRecord.student_id.in_(student_ids)
    ).group_by(GrowthRecord.student_id).all()
    growth_counts = {r[0]: r[1] for r in growth_count_rows}

    # 批量查询：每个学生的请假次数（1次查询代替N次）
    leave_count_rows = db.query(
        LeaveRequest.student_id, func.count(LeaveRequest.id)
    ).filter(LeaveRequest.student_id.in_(student_ids)
    ).group_by(LeaveRequest.student_id).all()
    leave_counts = {r[0]: r[1] for r in leave_count_rows}

    # 每个学生最近的危机记录（逐个学生查询；N通常小于50）
    result = []
    for s in students:
        growth_count = growth_counts.get(s.id, 0)
        leave_count = leave_counts.get(s.id, 0)
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == s.id
        ).order_by(AIDialogSummary.created_at.desc()).first()
        score = _calc_student_score(db, s.id, s)
        result.append(StudentOut(
            id=s.id,
            name=s.name,
            college=s.college,
            username=s.username,
            avatar=s.avatar,
            skills_json=s.skills_json,
            growth_count=growth_count,
            score=score,
            leave_count=leave_count,
            crisis_level=safe_enum_val(latest_crisis.level) if latest_crisis else None,
            latest_crisis_summary=latest_crisis.summary if latest_crisis else None,
            latest_crisis_time=latest_crisis.created_at.isoformat() if latest_crisis and latest_crisis.created_at else None,
            tutor_id=s.tutor_id,
        ))
    return result


@router.get("/students/{student_id}", response_model=StudentDetailOut | StudentResumeOut)
def get_student_detail(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    is_tutor = user.role == UserRole.ADMIN or student.tutor_id == user.id

    growth_records = db.query(GrowthRecord).filter(
        GrowthRecord.student_id == student_id
    ).order_by(GrowthRecord.date.desc()).all()

    projects = db.query(StudentProject).filter(
        StudentProject.student_id == student_id
    ).order_by(StudentProject.start_date.desc()).all()

    def format_record(r):
        return {
            "id": r.id,
            "type": safe_enum_val(r.type),
            "title": r.title,
            "description": r.description,
            "date": str(r.date),
            "attachment_url": r.attachment_url,
            "honor_level": r.honor_level,
            "organizer": r.organizer,
            "competition_level": r.competition_level,
            "practice_type": r.practice_type,
            "practice_certificate": r.practice_certificate,
            "paper_type": r.paper_type,
            "paper_name": r.paper_name,
            "first_author": r.first_author,
            "second_author": r.second_author,
            "third_author": r.third_author,
            "achievement_type": r.achievement_type,
            "achievement_name": r.achievement_name,
        }

    def format_project(p):
        return {
            "id": p.id,
            "project_name": p.project_name,
            "start_date": str(p.start_date),
            "end_date": str(p.end_date) if p.end_date else None,
            "is_team": p.is_team,
            "team_members": p.team_members,
            "attachment_url": p.attachment_url,
        }

    # 非导师教师：简历视图（仅显示成长记录）
    if not is_tutor:
        return StudentResumeOut(
            id=student.id,
            name=student.name,
            college=student.college,
            username=student.username,
            avatar=student.avatar,
            skills_json=student.skills_json,
            growth_records=[format_record(r) for r in growth_records],
            projects=[format_project(p) for p in projects],
        )

    # 导师或管理员：完整详情视图
    crisis_alerts = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).all()

    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == student_id
    ).order_by(LeaveRequest.created_at.desc()).all()

    def format_alert(a):
        return {
            "id": a.id,
            "summary": a.summary,
            "level": safe_enum_val(a.level),
            "keywords_matched": a.keywords_matched,
            "resolved": a.resolved,
            "created_at": a.created_at.isoformat() if a.created_at else "",
        }

    def format_leave(l):
        return {
            "id": l.id,
            "start_date": str(l.start_date),
            "end_date": str(l.end_date),
            "reason": l.reason,
            "leave_type": safe_enum_val(l.leave_type),
            "status": safe_enum_val(l.status),
            "reject_reason": l.reject_reason,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }

    return StudentDetailOut(
        id=student.id,
        name=student.name,
        college=student.college,
        username=student.username,
        avatar=student.avatar,
        skills_json=student.skills_json,
        growth_records=[format_record(r) for r in growth_records],
        projects=[format_project(p) for p in projects],
        crisis_alerts=[format_alert(a) for a in crisis_alerts],
        leave_requests=[format_leave(l) for l in leaves],
    )


@router.get("/growth-stats")
def growth_stats(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    student_ids = [s.id for s in query.all()]
    if not student_ids:
        return {"honor": 0, "competition": 0, "practice": 0, "paper": 0, "achievement": 0}
    stats = db.query(
        GrowthRecord.type,
        func.count(GrowthRecord.id)
    ).filter(GrowthRecord.student_id.in_(student_ids)).group_by(GrowthRecord.type).all()
    result = {s[0].value: s[1] for s in stats}
    for t in ["honor", "competition", "practice", "paper", "achievement"]:
        result.setdefault(t, 0)
    return result


@router.get("/class-evaluation")
def class_evaluation(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    students = query.all()
    student_ids = [s.id for s in students]
    total = len(student_ids)
    if total == 0:
        return {
            "total_students": 0, "avg_gpa": 0, "avg_score": 0,
            "growth": {"honor": 0, "competition": 0, "practice": 0, "paper": 0, "achievement": 0},
            "crisis": {"severe": 0, "moderate": 0, "mild": 0, "resolved": 0},
            "pending_leaves": 0,
        }

    # 平均GPA
    grades = db.query(Grade).filter(Grade.student_id.in_(student_ids)).all()
    total_credit = sum(g.credit for g in grades)
    avg_gpa = round(sum(g.gpa * g.credit for g in grades) / total_credit, 2) if total_credit > 0 else 0

    # 平均分
    total_score = 0
    for s in student_ids:
        total_score += _calc_student_score(db, s)
    avg_score = round(total_score / total, 1)

    # 成长记录
    if student_ids:
        growth = db.query(
            GrowthRecord.type,
            func.count(GrowthRecord.id)
        ).filter(GrowthRecord.student_id.in_(student_ids)
        ).group_by(GrowthRecord.type).all()
    else:
        growth = []
    growth_data = {r[0].value: r[1] for r in growth}
    for t in ["honor", "competition", "practice", "paper", "achievement"]:
        growth_data.setdefault(t, 0)

    # 按级别统计危机
    if student_ids:
        crisis_severe = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.level == "severe",
        ).count()
        crisis_moderate = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.level == "moderate",
        ).count()
        crisis_mild = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.level == "mild",
        ).count()
        crisis_resolved = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.resolved == True,
        ).count()
        pending_leaves = db.query(LeaveRequest).filter(
            LeaveRequest.student_id.in_(student_ids),
            LeaveRequest.status == "pending",
        ).count()
    else:
        crisis_severe = crisis_moderate = crisis_mild = crisis_resolved = pending_leaves = 0

    return {
        "total_students": total,
        "avg_gpa": avg_gpa,
        "avg_score": avg_score,
        "growth": growth_data,
        "crisis": {
            "severe": crisis_severe,
            "moderate": crisis_moderate,
            "mild": crisis_mild,
            "resolved": crisis_resolved,
        },
        "pending_leaves": pending_leaves,
    }


class ClassStatsOut(BaseModel):
    total_students: int = 0
    gender_stats: dict = {}
    crisis_stats: dict = {}
    grade_stats: dict = {}
    political_stats: dict = {}
    hometown_stats: dict = {}
    crisis_trend: list = []


@router.get("/class-stats", response_model=ClassStatsOut)
def class_stats(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    students = query.all()
    student_ids = [s.id for s in students]
    total = len(student_ids)
    
    if total == 0:
        return ClassStatsOut()
    
    # 性别统计
    gender_counts = {}
    for s in students:
        gender = s.gender or "未知"
        gender_counts[gender] = gender_counts.get(gender, 0) + 1
    
    # 危机统计
    crisis_counts = {"severe": 0, "moderate": 0, "mild": 0, "resolved": 0}
    if student_ids:
        crisis_data = db.query(
            AIDialogSummary.level,
            func.count(AIDialogSummary.id)
        ).filter(AIDialogSummary.student_id.in_(student_ids)
        ).group_by(AIDialogSummary.level).all()
        for level, count in crisis_data:
            if level in crisis_counts:
                crisis_counts[level] = count
        
        resolved_count = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.resolved == True
        ).count()
        crisis_counts["resolved"] = resolved_count
    
    # 成绩分布统计
    grade_stats = {"excellent": 0, "good": 0, "medium": 0, "pass": 0, "fail": 0}
    if student_ids:
        grades = db.query(Grade).filter(Grade.student_id.in_(student_ids)).all()
        for g in grades:
            if g.score >= 90:
                grade_stats["excellent"] += 1
            elif g.score >= 80:
                grade_stats["good"] += 1
            elif g.score >= 70:
                grade_stats["medium"] += 1
            elif g.score >= 60:
                grade_stats["pass"] += 1
            else:
                grade_stats["fail"] += 1
    
    # 政治面貌统计
    political_counts = {}
    for s in students:
        status = s.political_status or "未知"
        political_counts[status] = political_counts.get(status, 0) + 1
    
    # 生源地统计（取前10个省份）
    hometown_counts = {}
    for s in students:
        hometown = s.hometown or "未知"
        hometown_counts[hometown] = hometown_counts.get(hometown, 0) + 1
    hometown_sorted = dict(sorted(hometown_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    # 预警趋势统计（按月统计最近6个月）
    crisis_trend = []
    if student_ids:
        from datetime import datetime, timedelta
        from sqlalchemy import func as safunc, extract
        
        now = datetime.now()
        for i in range(5, -1, -1):
            month_date = now - timedelta(days=30 * i)
            year = month_date.year
            month = month_date.month
            count = db.query(AIDialogSummary).filter(
                AIDialogSummary.student_id.in_(student_ids),
                extract('year', AIDialogSummary.created_at) == year,
                extract('month', AIDialogSummary.created_at) == month
            ).count()
            crisis_trend.append({"month": f"{year}-{month:02d}", "count": count})
    
    return ClassStatsOut(
        total_students=total,
        gender_stats=gender_counts,
        crisis_stats=crisis_counts,
        grade_stats=grade_stats,
        political_stats=political_counts,
        hometown_stats=hometown_sorted,
        crisis_trend=crisis_trend,
    )


class ContactSuggestionOut(BaseModel):
    student_id: int
    student_name: str
    reason: str
    priority: str


@router.get("/suggest-contacts", response_model=list[ContactSuggestionOut])
async def suggest_contacts(
    student_id: int | None = Query(None, description="聚焦单个学生，闭环用"),
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):

    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    if student_id is not None:
        query = query.filter(User.id == student_id)
    students = query.all()
    if not students:
        return []

    student_ids = [s.id for s in students]

    last_msg_sub = db.query(
        Message.receiver_id, Message.sender_id, Message.created_at,
        func.row_number().over(
            order_by=Message.created_at.desc()
        ).label("rn")
    ).filter(
        ((Message.sender_id == user.id) & (Message.receiver_id.in_(student_ids))) |
        ((Message.sender_id.in_(student_ids)) & (Message.receiver_id == user.id))
    ).subquery()

    latest_crisis_sub = db.query(
        AIDialogSummary.student_id, AIDialogSummary.level, AIDialogSummary.summary, AIDialogSummary.created_at,
        func.row_number().over(
            partition_by=AIDialogSummary.student_id,
            order_by=AIDialogSummary.created_at.desc()
        ).label("rn")
    ).filter(AIDialogSummary.student_id.in_(student_ids)).subquery()

    growth_count_rows = db.query(
        GrowthRecord.student_id, func.count(GrowthRecord.id)
    ).filter(GrowthRecord.student_id.in_(student_ids)
    ).group_by(GrowthRecord.student_id).all()

    leave_count_rows = db.query(
        LeaveRequest.student_id, func.count(LeaveRequest.id)
    ).filter(LeaveRequest.student_id.in_(student_ids)
    ).group_by(LeaveRequest.student_id).all()

    last_msgs = {r.receiver_id if r.receiver_id != user.id else r.sender_id: r.created_at
                 for r in db.query(last_msg_sub).filter(last_msg_sub.c.rn == 1).all()}
    latest_crises = {c.student_id: c for c in db.query(latest_crisis_sub).filter(latest_crisis_sub.c.rn == 1).all()}
    growth_counts = dict(growth_count_rows)
    leave_counts = dict(leave_count_rows)

    student_infos = []
    for s in students:
        last_contact_dt = last_msgs.get(s.id)
        last_contact = last_contact_dt.isoformat() if last_contact_dt else "从未联系"
        latest_crisis = latest_crises.get(s.id)
        growth_count = growth_counts.get(s.id, 0)
        leave_count = leave_counts.get(s.id, 0)

        student_infos.append({
            "id": s.id,
            "name": s.name,
            "college": s.college or "未分配",
            "last_contact": last_contact,
            "crisis_level": latest_crisis.level if latest_crisis else None,
            "growth_count": growth_count,
            "leave_count": leave_count,
        })

    # 构造 prompt 发送给 AI
    students_text = "\n".join([
        f"- {info['name']}（{info['college']}）：最近联系={info['last_contact']}，危机等级={info['crisis_level'] or '无'}，成果数={info['growth_count']}，请假数={info['leave_count']}，ID={info['id']}"
        for info in student_infos
    ])

    focus_one = student_id is not None
    prompt = build_teacher_outreach_prompt(
        students_text=students_text,
        focus_student_id=student_id if focus_one else None,
    )

    try:
        config = _get_llm_config()
        resp = await _get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        content = resp.choices[0].message.content or ""
        # 清理 markdown 代码块
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", content).strip().rstrip("`")
        result = json.loads(cleaned)
        return result
    except Exception as e:
        logger.error("[AI推荐联系] 错误: %s", e)
        # fallback: 聚焦模式返回该生，否则返回前3个学生
        return [
            {"student_id": s["id"], "student_name": s["name"], "reason": "AI分析暂不可用，建议手动查看", "priority": "medium"}
            for s in (student_infos if focus_one else student_infos[:3])
        ]


class ContactSuggestionPersistItem(BaseModel):
    student_id: int
    student_name: str = ""
    reason: str | None = None


class ContactSuggestionPersistRequest(BaseModel):
    items: list[ContactSuggestionPersistItem]


class ContactSuggestionPersistResult(BaseModel):
    created: int = 0
    total: int = 0


@router.post("/suggest-contacts/persist", response_model=ContactSuggestionPersistResult)
def persist_contact_suggestions(
    body: ContactSuggestionPersistRequest,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """把 AI 推荐联系的学生落为跟进任务（幂等，重复调用不重复建）。"""
    created = teacher_task_service.bulk_upsert_from_suggestions(
        db, user.id, [item.model_dump() for item in body.items]
    )
    return ContactSuggestionPersistResult(created=created, total=len(body.items))


class StudentImportItem(BaseModel):
    username: str
    name: str
    college: str | None = None
    gender: str | None = None
    class_name: str | None = None


class StudentImportRequest(BaseModel):
    students: list[StudentImportItem]


class StudentImportResult(BaseModel):
    created: int = 0
    skipped: list[str] = []


@router.post("/students/import", response_model=StudentImportResult)
def import_students(
    body: StudentImportRequest,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """批量导入学生账号：默认密码 123456，跳过已存在的学号。"""
    existing = {row[0] for row in db.query(User.username).all()}
    created = 0
    skipped: list[str] = []
    for item in body.students:
        username = (item.username or "").strip()
        name = (item.name or "").strip()
        if not username or not name:
            skipped.append(username or "(空学号)")
            continue
        if username in existing:
            skipped.append(username)
            continue
        db.add(User(
            username=username,
            password_hash=hash_password("123456"),
            name=name,
            role=UserRole.STUDENT,
            college=item.college,
            gender=item.gender,
            class_name=item.class_name,
            tutor_id=user.id if user.role == UserRole.TEACHER else None,
        ))
        existing.add(username)
        created += 1
    db.commit()
    return StudentImportResult(created=created, skipped=skipped)


# ===== 模块 13 · AI 学情助手 =====


class InsightToTaskIn(BaseModel):
    advice: str
    risk_level: str = "low"


def _assert_my_student(db: Session, user: User, student_id: int) -> User:
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if user.role != UserRole.ADMIN and student.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该学生")
    return student


@router.get("/students/{student_id}/insight")
async def student_insight(
    student_id: int,
    days: int = Query(default=30, ge=1, le=180),
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """学情诊断：可溯源画像（证据清单）+ AI 辅导建议（失败自动降级）。"""
    from app.services import student_insight_service

    _assert_my_student(db, user, student_id)
    return await student_insight_service.get_insight(db, student_id, days=days)


@router.post("/students/{student_id}/insight/task")
def student_insight_to_task(
    student_id: int,
    payload: InsightToTaskIn,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """把学情建议一键转为跟进任务（画像 → 执行 闭环）。"""
    from app.services import student_insight_service

    _assert_my_student(db, user, student_id)
    task = student_insight_service.to_task(
        db,
        teacher_id=user.id,
        student_id=student_id,
        advice=payload.advice,
        risk_level=payload.risk_level,
    )
    return teacher_task_service.serialize_one(db, task)
