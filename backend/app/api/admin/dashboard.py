from datetime import datetime, timedelta, timezone

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

# 平均响应延迟统计窗口与采样上限（避免大表全量扫描）
RESPONSE_WINDOW_DAYS = 7
RESPONSE_SAMPLE_LIMIT = 4000
# 单次「提问 → 回复」间隔超过该秒数视为中断（用户中途离开等），不计入均值
RESPONSE_MAX_INTERVAL_SECONDS = 300


def _avg_response_time(db: Session, days: int = RESPONSE_WINDOW_DAYS) -> float:
    """智能体平均响应延迟（秒）。

    取近 N 天内的会话消息，按会话分组、时间排序，统计「用户提问(user) →
    紧邻的 AI 回复(assistant)」时间差的均值。跨会话、AI 主动问候（无前置
    提问）不计入；间隔异常（<=0 或 > RESPONSE_MAX_INTERVAL_SECONDS）剔除。
    为控制开销只采样最近 RESPONSE_SAMPLE_LIMIT 条消息。
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
    rows = (
        db.query(
            ConversationMessage.conversation_id,
            ConversationMessage.role,
            ConversationMessage.timestamp,
            ConversationMessage.id,
        )
        .filter(ConversationMessage.timestamp >= since)
        .order_by(
            ConversationMessage.timestamp.desc(),
            ConversationMessage.id.desc(),
        )
        .limit(RESPONSE_SAMPLE_LIMIT)
        .all()
    )

    # 采样结果是「最近 N 条」，需按会话内时间正序重排后才能正确配对相邻消息
    rows.sort(key=lambda r: (r[0], r[2] or datetime.min, r[3]))

    deltas: list[float] = []
    prev_conv: int | None = None
    prev_role: str | None = None
    prev_ts: datetime | None = None
    for conv_id, role, ts, _msg_id in rows:
        if (
            conv_id == prev_conv
            and prev_role == "user"
            and role == "assistant"
            and ts is not None
            and prev_ts is not None
        ):
            delta = (ts - prev_ts).total_seconds()
            if 0 < delta <= RESPONSE_MAX_INTERVAL_SECONDS:
                deltas.append(delta)
        prev_conv, prev_role, prev_ts = conv_id, role, ts

    if not deltas:
        return 0.0
    return round(sum(deltas) / len(deltas), 2)


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
        "avg_response_time": _avg_response_time(db),
    }
