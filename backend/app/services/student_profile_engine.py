import json
import logging
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.academic import Grade
from app.models.growth import GrowthRecord
from app.models.crisis import AIDialogSummary
from app.models.leave import LeaveRequest
from app.models.conversation import Conversation
from app.models.profile import StudentProfileSnapshot, ConversationSummary
from app.services.scoring import calc_radar_score, get_risk_indicators, get_trajectory, get_record_type_counts
from app.services.llm_service import _get_client, _get_llm_config
from app.utils.enum_helpers import safe_enum_val

logger = logging.getLogger(__name__)


def _detect_behavioral_patterns(db, student_id: int, now=None) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    today = date.today()

    leave_count = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == student_id,
        LeaveRequest.created_at >= now - timedelta(days=90),
    ).count()
    leave_frequency = "high" if leave_count >= 5 else "medium" if leave_count >= 2 else "low"

    crises = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).limit(5).all()
    if len(crises) >= 2:
        risk_values = {"normal": 0, "mild": 1, "moderate": 2, "severe": 3}
        levels = [risk_values.get(c.level.value, 0) for c in crises[:3]]
        crisis_trend = "worsening" if levels == sorted(levels, reverse=True) else "improving" if levels == sorted(levels) else "stable"
    else:
        crisis_trend = "stable"

    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    semesters = defaultdict(list)
    for g in grades:
        semesters[g.semester].append(g.gpa)
    sem_avgs = [(s, sum(gpas)/len(gpas)) for s, gpas in semesters.items()]
    sem_avgs.sort(key=lambda x: x[0])
    if len(sem_avgs) >= 2:
        diff = sem_avgs[-1][1] - sem_avgs[-2][1]
        grade_trajectory = "declining" if diff < -0.2 else "improving" if diff > 0.2 else "stable"
    else:
        grade_trajectory = "stable"

    convs_90d = db.query(Conversation).filter(
        Conversation.user_id == student_id,
        Conversation.created_at >= now - timedelta(days=90),
    ).count()
    engagement_level = "high" if convs_90d > 20 else "medium" if convs_90d > 5 else "low"

    last_conv = db.query(Conversation).filter(
        Conversation.user_id == student_id
    ).order_by(Conversation.updated_at.desc()).first()
    inactive_days = (now - last_conv.updated_at).days if last_conv else 999

    return {
        "leave_frequency": leave_frequency,
        "crisis_trend": crisis_trend,
        "grade_trajectory": grade_trajectory,
        "engagement_level": engagement_level,
        "inactive_days": inactive_days,
    }


def _compute_dimension_scores(db, student_id: int, user=None) -> dict:
    if not user:
        user = db.query(User).filter(User.id == student_id).first()
    if not user:
        return {"academic": 0, "psychological_risk": 0, "engagement": 0, "growth": 0, "overall_risk": 0}

    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == student_id).all()
    skills_data = user.skills_json or {"skills": [], "interests": []}
    raw_skills = skills_data.get("skills", [])
    skills = [s["name"] if isinstance(s, dict) else s for s in raw_skills]
    interests = skills_data.get("interests", [])

    type_counts = get_record_type_counts(records)
    n_records = len(records)
    n_skills = len(skills)
    n_interests = len(interests)

    academic = min(100, type_counts.get("honor", 0) * 15 + type_counts.get("paper", 0) * 30 + n_records * 3)
    growth = min(100, n_records * 10 + n_skills * 8 + type_counts.get("practice", 0) * 10)
    engagement = min(100, n_interests * 15 + type_counts.get("practice", 0) * 15)

    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    if grades:
        gpas = [g.gpa for g in grades if g.gpa]
        if gpas:
            academic = min(100, academic + (sum(gpas) / len(gpas)) * 15)

    recent_crises = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).limit(3).all()
    risk_values = {"normal": 0, "mild": 25, "moderate": 60, "severe": 90}
    psych_risk = 0
    for c in recent_crises:
        psych_risk = max(psych_risk, risk_values.get(safe_enum_val(c.level) or "normal", 0))
    if recent_crises and not recent_crises[0].resolved:
        psych_risk = min(100, psych_risk + 15)

    overall_risk = min(100, (100 - academic) * 0.3 + psych_risk * 0.4 + (100 - engagement) * 0.2 + (100 - growth) * 0.1)

    return {
        "academic": round(academic, 1),
        "psychological_risk": round(psych_risk, 1),
        "engagement": round(engagement, 1),
        "growth": round(growth, 1),
        "overall_risk": round(overall_risk, 1),
    }


async def _batch_generate_insights(db, students_batch: list[tuple[int, dict, dict]], max_retries=1):
    if not students_batch:
        return {}
    try:
        lines = []
        for sid, scores, patterns in students_batch:
            lines.append(
                f"学生ID={sid}：学业={scores['academic']}，心理风险={scores['psychological_risk']}，"
                f"参与度={scores['engagement']}，请假频率={patterns['leave_frequency']}，"
                f"危机趋势={patterns['crisis_trend']}，成绩轨迹={patterns['grade_trajectory']}"
            )
        prompt = f"""你是一名校园学生数据分析师。基于以下学生数据，为每位学生生成1-2条关键洞察（中文）。

每条洞察包含：
- dimension: academic/psychology/behavior/engagement/growth
- type: warning/praise/observation/escalation
- content: 具体描述（20-40字）

学生数据：
{chr(10).join(lines)}

以JSON数组格式返回，每个元素包含 student_id 和 insights 数组：
[{{"student_id": 1, "insights": [{{"dimension": "academic", "type": "warning", "content": "..."}}]}}]
只返回JSON，不要其他文字。"""
        config = _get_llm_config()
        resp = await _get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "[]"
        cleaned = content.strip().strip("```json").strip("```").strip()
        results = json.loads(cleaned)
        if isinstance(results, dict) and "insights" in results:
            results = [results]
        return {r["student_id"]: r.get("insights", []) for r in results}
    except Exception:
        logger.exception("批量洞察生成失败")
        return {}


async def refresh_single_profile(db: Session, student_id: int) -> StudentProfileSnapshot | None:
    user = db.query(User).filter(User.id == student_id).first()
    if not user:
        return None
    scores = _compute_dimension_scores(db, student_id, user)
    patterns = _detect_behavioral_patterns(db, student_id)
    insights = await _batch_generate_insights(db, [(student_id, scores, patterns)])
    snapshot = StudentProfileSnapshot(
        student_id=student_id,
        snapshot_date=date.today(),
        academic_score=scores["academic"],
        psychological_risk=scores["psychological_risk"],
        engagement_score=scores["engagement"],
        growth_score=scores["growth"],
        overall_risk=scores["overall_risk"],
        behavioral_patterns=patterns,
        key_insights=insights.get(student_id, []),
    )
    db.add(snapshot)
    db.commit()
    return snapshot


async def refresh_all_profiles():
    db = SessionLocal()
    try:
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        batch_size = 5
        for i in range(0, len(students), batch_size):
            batch = students[i:i + batch_size]
            batch_data = []
            for s in batch:
                scores = _compute_dimension_scores(db, s.id, s)
                patterns = _detect_behavioral_patterns(db, s.id)
                batch_data.append((s.id, scores, patterns))
            insights_map = await _batch_generate_insights(db, batch_data)
            for s in batch:
                scores = _compute_dimension_scores(db, s.id, s)
                patterns = _detect_behavioral_patterns(db, s.id)
                snapshot = StudentProfileSnapshot(
                    student_id=s.id,
                    snapshot_date=date.today(),
                    academic_score=scores["academic"],
                    psychological_risk=scores["psychological_risk"],
                    engagement_score=scores["engagement"],
                    growth_score=scores["growth"],
                    overall_risk=scores["overall_risk"],
                    behavioral_patterns=patterns,
                    key_insights=insights_map.get(s.id, []),
                )
                db.add(snapshot)
            db.commit()
            logger.info("已刷新学生画像 %d-%d / %d", i + 1, min(i + batch_size, len(students)), len(students))
    finally:
        db.close()


def get_latest_profile(db: Session, student_id: int) -> StudentProfileSnapshot | None:
    return db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).first()


def get_profile_history(db: Session, student_id: int, limit: int = 30):
    return db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).limit(limit).all()
