from datetime import date, timedelta, datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.growth import GrowthRecord
from app.models.user import User, UserRole
from app.models.profile import StudentProfileSnapshot
from app.utils.enum_helpers import safe_enum_val


TYPE_LABELS = {"honor": "荣誉", "competition": "竞赛", "practice": "实践", "paper": "论文", "achievement": "成果"}


def get_record_type_counts(records: list) -> dict[str, int]:
    """从成长记录列表中统计各类型数量"""
    type_counts = defaultdict(int)
    for r in records:
        type_counts[safe_enum_val(r.type)] += 1
    return dict(type_counts)


def _compute_dimension_scores(records: list, skills: list, interests: list) -> dict:
    type_counts = get_record_type_counts(records)

    n_records = len(records)
    n_skills = len(skills)
    n_interests = len(interests)

    return {
        "score_practice": min(100, n_records * 10 + n_skills * 8 + type_counts.get("practice", 0) * 10),
        "score_innovation": min(100, type_counts.get("competition", 0) * 25 + type_counts.get("achievement", 0) * 30),
        "score_academic": min(100, type_counts.get("honor", 0) * 15 + type_counts.get("paper", 0) * 30 + n_records * 3),
        "score_social": min(100, n_interests * 15 + type_counts.get("practice", 0) * 15),
        "score_character": min(100, (n_records + n_skills) * 8),
    }


def calc_radar_score(db: Session, student_id: int, user: User | None = None) -> float:
    if not user:
        user = db.query(User).filter(User.id == student_id).first()
    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == student_id).all()
    skills_data = user.skills_json or {"skills": [], "interests": []}
    raw_skills = skills_data.get("skills", [])
    skills = [s["name"] if isinstance(s, dict) else s for s in raw_skills]
    interests = skills_data.get("interests", [])

    scores = _compute_dimension_scores(records, skills, interests)
    total = sum(scores.values()) / 5
    return round(total, 1)


def get_radar_dimensions(db: Session, student_id: int, user: User | None = None) -> list[dict]:
    """返回各维度分数，供雷达图使用"""
    if not user:
        user = db.query(User).filter(User.id == student_id).first()
    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == student_id).all()
    skills_data = user.skills_json or {"skills": [], "interests": []}
    raw_skills = skills_data.get("skills", [])
    skills = [s["name"] if isinstance(s, dict) else s for s in raw_skills]
    interests = skills_data.get("interests", [])

    scores = _compute_dimension_scores(records, skills, interests)
    return [
        {"name": "学术素养", "value": scores["score_academic"]},
        {"name": "创新能力", "value": scores["score_innovation"]},
        {"name": "实践能力", "value": scores["score_practice"]},
        {"name": "社交素养", "value": scores["score_social"]},
        {"name": "综合素质", "value": scores["score_character"]},
    ]


def get_cohort_percentile(db: Session, student_id: int, college: str | None = None) -> dict:
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        return {}

    college = college or student.college
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if college:
        query = query.filter(User.college == college)
    cohort_ids = [u.id for u in query.all()]
    if not cohort_ids or student_id not in cohort_ids:
        return {}

    latest_snapshot = db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).first()
    if not latest_snapshot:
        return {"overall": 50, "academic": 50, "practice": 50}

    scores = ["academic_score", "psychological_risk", "engagement_score", "growth_score", "overall_risk"]
    result = {}
    for s in scores:
        all_scores = [
            r[0] for r in db.query(getattr(StudentProfileSnapshot, s))
            .filter(
                StudentProfileSnapshot.student_id.in_(cohort_ids),
                StudentProfileSnapshot.snapshot_date == latest_snapshot.snapshot_date
            ).all()
        ]
        if not all_scores:
            continue
        student_val = getattr(latest_snapshot, s)
        below = sum(1 for v in all_scores if v <= student_val)
        result[s.replace("_score", "").replace("_risk", "_risk")] = round(below / len(all_scores) * 100, 1)
    return result


def get_trajectory(db: Session, student_id: int, weeks: int = 12) -> dict:
    cutoff = date.today() - timedelta(weeks=weeks)
    snapshots = db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id,
        StudentProfileSnapshot.snapshot_date >= cutoff
    ).order_by(StudentProfileSnapshot.snapshot_date.asc()).all()

    if len(snapshots) < 2:
        return {"academic": 0, "psychological_risk": 0, "engagement": 0, "growth": 0, "overall_risk": 0}

    first = snapshots[0]
    last = snapshots[-1]
    return {
        "academic": round(last.academic_score - first.academic_score, 1),
        "psychological_risk": round(last.psychological_risk - first.psychological_risk, 1),
        "engagement": round(last.engagement_score - first.engagement_score, 1),
        "growth": round(last.growth_score - first.growth_score, 1),
        "overall_risk": round(last.overall_risk - first.overall_risk, 1),
    }


def get_risk_indicators(db: Session, student_id: int) -> list[dict]:
    from app.models.academic import Grade
    from app.models.growth import GrowthRecord
    from app.models.crisis import AIDialogSummary
    from app.models.leave import LeaveRequest
    from app.models.conversation import Conversation

    indicators = []
    now = datetime.now(timezone.utc)
    today = date.today()

    grades = db.query(Grade).filter(Grade.student_id == student_id).order_by(Grade.semester.desc()).all()
    if grades:
        semesters = {}
        for g in grades:
            semesters.setdefault(g.semester, []).append(g.gpa)
        sem_avgs = [(s, sum(gpas)/len(gpas)) for s, gpas in semesters.items()]
        if len(sem_avgs) >= 2:
            latest_avg = sem_avgs[0][1]
            prev_avg = sem_avgs[1][1]
            if latest_avg < prev_avg - 0.3:
                indicators.append({
                    "dimension": "academic", "severity": "high",
                    "detail": f"GPA 从 {prev_avg:.2f} 降至 {latest_avg:.2f}",
                })

    leaves_90d = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == student_id,
        LeaveRequest.created_at >= now - timedelta(days=90),
    ).count()
    if leaves_90d >= 5:
        indicators.append({
            "dimension": "behavior", "severity": "medium",
            "detail": f"近 90 天请假 {leaves_90d} 次，频率偏高",
        })

    latest_crisis = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).first()
    if latest_crisis and latest_crisis.level.value in ("severe", "moderate") and not latest_crisis.resolved:
        indicators.append({
            "dimension": "psychology", "severity": "high",
            "detail": f"未解决的 {latest_crisis.level.value} 级危机预警",
        })

    last_conv = db.query(Conversation).filter(
        Conversation.user_id == student_id
    ).order_by(Conversation.updated_at.desc()).first()
    if last_conv:
        inactive = (now - last_conv.updated_at).days
        if inactive > 14:
            indicators.append({
                "dimension": "engagement", "severity": "medium",
                "detail": f"已 {inactive} 天无对话交互",
            })

    growth_90d = db.query(GrowthRecord).filter(
        GrowthRecord.student_id == student_id,
        GrowthRecord.date >= today - timedelta(days=90),
    ).count()
    if growth_90d == 0:
        indicators.append({
            "dimension": "growth", "severity": "low",
            "detail": "近 90 天无新增成长记录",
        })

    return indicators
