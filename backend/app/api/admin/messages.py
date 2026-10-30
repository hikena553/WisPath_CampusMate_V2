"""管理端 · 顶栏消息中心。

聚合管理员待办：学生 / 教师忘记密码后提交的重置申请、用户提交的待处理反馈。
顶栏消息组件轮询此接口，红点数量即待处理事项总数；点击消息跳转到对应管理页处理。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.feedback import Feedback, FeedbackStatus
from app.models.password_reset import PasswordResetRequest, PasswordResetStatus
from app.models.user import User, UserRole

router = APIRouter(tags=["admin"])

# 每类消息最多返回条数：消息面板只用于快速处理最新事项，历史待办过多时以红点总数提示
_MAX_ITEMS_PER_KIND = 20


def _feedback_preview(content: str | None) -> str:
    text = " ".join((content or "").split())
    return text if len(text) <= 80 else f"{text[:80]}…"


@router.get("/messages")
def admin_messages(
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """顶栏消息：待处理密码重置申请 + 待处理反馈。"""
    # -------- 密码重置申请 --------
    reset_query = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.status == PasswordResetStatus.PENDING
    )
    reset_total = reset_query.count()
    resets = (
        reset_query.order_by(PasswordResetRequest.created_at.desc())
        .limit(_MAX_ITEMS_PER_KIND)
        .all()
    )

    applicant_map: dict[int, User] = {}
    if resets:
        for user in db.query(User).filter(User.id.in_([r.user_id for r in resets])).all():
            applicant_map[user.id] = user

    items: list[dict] = []
    for r in resets:
        applicant = applicant_map.get(r.user_id)
        # 申请人角色决定跳转到学生管理还是教师管理
        is_student = applicant is None or applicant.role == UserRole.STUDENT
        page = "/admin/students" if is_student else "/admin/teachers"
        page_name = "学生管理" if is_student else "教师管理"
        reason = (r.reason or "").strip()
        items.append({
            "id": f"password-reset-{r.id}",
            "kind": "password_reset",
            "level": "important",
            "title": f"{r.name}（{r.username}）申请重置密码",
            "content": f"{reason + ' · ' if reason else ''}联系方式 {r.contact}，请前往{page_name}重置",
            "link": f"{page}?focus={r.username}",
            "created_at": r.created_at,
        })

    # -------- 待处理反馈 --------
    feedback_query = db.query(Feedback).filter(Feedback.status == FeedbackStatus.PENDING)
    feedback_total = feedback_query.count()
    feedbacks = (
        feedback_query.order_by(Feedback.created_at.desc())
        .limit(_MAX_ITEMS_PER_KIND)
        .all()
    )

    submitter_map: dict[int, User] = {}
    if feedbacks:
        for user in db.query(User).filter(User.id.in_([f.user_id for f in feedbacks])).all():
            submitter_map[user.id] = user

    for f in feedbacks:
        submitter = submitter_map.get(f.user_id)
        items.append({
            "id": f"feedback-{f.id}",
            "kind": "feedback",
            "level": "normal",
            "title": f"用户反馈：{f.title}",
            "content": f"{submitter.name if submitter else '匿名用户'}：{_feedback_preview(f.content)}",
            "link": f"/admin/feedbacks?focus={f.id}",
            "created_at": f.created_at,
        })

    return {
        "items": items,
        # 红点数量：两类待办的真实总数（列表最多各展示 20 条）
        "unread": reset_total + feedback_total,
        "counts": {"password_reset": reset_total, "feedback": feedback_total},
    }
