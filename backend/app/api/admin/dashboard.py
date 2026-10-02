from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.models.crisis import AIDialogSummary
from app.models.academic import College
from app.models.knowledge import KnowledgeItem
from app.models.document import Document
from app.models.conversation import Conversation, ConversationMessage

router = APIRouter(tags=["admin"])

# ========== 仪表盘统计 ==========

@router.get("/dashboard")
def dashboard_stats(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    teacher_count = db.query(User).filter(User.role == UserRole.TEACHER).count()
    student_count = db.query(User).filter(User.role == UserRole.STUDENT).count()
    college_count = db.query(College).count()
    knowledge_count = db.query(KnowledgeItem).count()
    document_count = db.query(Document).count()

    student_gender_rows = db.query(User.gender, func.count(User.id)).filter(
        User.role == UserRole.STUDENT, User.gender.isnot(None)
    ).group_by(User.gender).all()
    student_gender_stats = {g or "未知": c for g, c in student_gender_rows}

    teacher_gender_rows = db.query(User.gender, func.count(User.id)).filter(
        User.role == UserRole.TEACHER, User.gender.isnot(None)
    ).group_by(User.gender).all()
    teacher_gender_stats = {g or "未知": c for g, c in teacher_gender_rows}

    conversation_count = db.query(Conversation).count()
    message_count = db.query(ConversationMessage).count()

    college_rows = db.query(User.college, func.count(User.id)).filter(
        User.role == UserRole.STUDENT, User.college.isnot(None)
    ).group_by(User.college).all()
    college_stats = [{"college": c, "count": n} for c, n in college_rows]

    teacher_college_rows = db.query(User.college, func.count(User.id)).filter(
        User.role == UserRole.TEACHER, User.college.isnot(None)
    ).group_by(User.college).all()
    teacher_college_stats = [{"college": c, "count": n} for c, n in teacher_college_rows]

    crisis_sub = db.query(
        AIDialogSummary.student_id,
        AIDialogSummary.level,
        func.row_number().over(
            partition_by=AIDialogSummary.student_id,
            order_by=AIDialogSummary.created_at.desc()
        ).label("rn")
    ).subquery()

    crisis_counts = db.query(crisis_sub.c.level, func.count(crisis_sub.c.student_id)).filter(
        crisis_sub.c.rn == 1
    ).group_by(crisis_sub.c.level).all()
    crisis_stats = [{"level": level.value, "count": n} for level, n in crisis_counts]

    no_crisis = student_count - sum(n for _, n in crisis_counts)
    if no_crisis > 0:
        crisis_stats.append({"level": "none", "count": no_crisis})

    return {
        "teacher_count": teacher_count,
        "student_count": student_count,
        "college_count": college_count,
        "knowledge_count": knowledge_count,
        "document_count": document_count,
        "student_gender_stats": student_gender_stats,
        "teacher_gender_stats": teacher_gender_stats,
        "conversation_count": conversation_count,
        "message_count": message_count,
        "college_stats": college_stats,
        "teacher_college_stats": teacher_college_stats,
        "crisis_stats": crisis_stats,
    }
