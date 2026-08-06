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
from app.services.scoring import calc_radar_score
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
    total_students: int = 0
    alert_count: int = 0
    pending_leave_count: int = 0
    severe_alert_count: int = 0
    resolved_alert_count: int = 0

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
    return DashboardOut(
        total_students=total,
        alert_count=alert_count,
        pending_leave_count=pending_leave,
        severe_alert_count=severe_count,
        resolved_alert_count=resolved_count,
    )


@router.get("/students", response_model=list[StudentOut])
def list_students(
    search: str | None = None,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            User.name.like(like) | User.username.like(like) | User.college.like(like)
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


class ContactSuggestionOut(BaseModel):
    student_id: int
    student_name: str
    reason: str
    priority: str


@router.get("/suggest-contacts", response_model=list[ContactSuggestionOut])
async def suggest_contacts(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):

    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
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

    prompt = f"""你是校园管理助手。请从以下学生名单中，分析并推荐3位最应该主动联系的学生。

学生信息：
{students_text}

分析维度：
1. 长时间未联系的学生（优先级高）
2. 有危机预警的学生（优先级高）
3. 近期请假较多的学生（需关注）
4. 有成长成果但未沟通的学生（鼓励）

要求：
1. 从列表中选出3位学生
2. 每位学生给出具体理由（至少20字）
3. 标注优先级：high/medium/low
4. 只返回JSON数组，不要其他内容

格式：[{{"student_id": 1, "student_name": "姓名", "reason": "具体理由...", "priority": "high"}}]"""

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
        # fallback: 返回前3个学生
        return [
            {"student_id": s["id"], "student_name": s["name"], "reason": "AI分析暂不可用，建议手动查看", "priority": "medium"}
            for s in student_infos[:3]
        ]
