"""统一审批门面（OA 门面）：聚合多类申请的待审、统一审核、数据统计。
教师审核自己学生（tutor_id）的申请，管理员审核全部。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.service import ServiceTicket, TicketStatus
from app.models.material import MaterialArchive, MaterialStatus
from app.models.notification import NotificationType
from app.services import approval_service

router = APIRouter(prefix="/api/approval", tags=["统一审批"])

APPROVAL_KINDS = {"leave", "ticket", "material"}
STATUS_ACTIVE = ("pending", "approved", "rejected")


class ReviewRequest(BaseModel):
    action: str  # approve / reject
    reject_reason: str | None = None


# 数据级可见性收敛（本人所带学生）统一由 service 实现，api 层只做装配。
# 保留 (user, db) 的既有调用签名，避免改动 api 内多处调用点。
def _scoped_student_ids(user: User, db: Session) -> list[int] | None:
    return approval_service.scoped_student_ids(db, user)


def _leave_items(user: User, db: Session, status: str | None, student_id: int | None = None):
    q = db.query(LeaveRequest)
    if user.role != UserRole.ADMIN:
        ids = _scoped_student_ids(user, db)
        q = q.filter(LeaveRequest.student_id.in_(ids)) if ids else q.filter(False)
    if status:
        q = q.filter(LeaveRequest.status == status)
    if student_id is not None:
        q = q.filter(LeaveRequest.student_id == student_id)
    items = []
    for r in q.order_by(LeaveRequest.created_at.desc()).all():
        st = r.student_id
        name = db.query(User).filter(User.id == st).first()
        items.append({
            "kind": "leave",
            "id": r.id,
            "title": f"请假申请（{r.leave_type.value if hasattr(r.leave_type, 'value') else r.leave_type}）" if getattr(r, "leave_type", None) else "请假申请",
            "applicant_id": r.student_id,
            "applicant_name": name.name if name else "",
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "detail": r.reason or "",
        })
    return items


def _ticket_items(user: User, db: Session, status: str | None, student_id: int | None = None):
    q = db.query(ServiceTicket)
    if user.role != UserRole.ADMIN:
        ids = _scoped_student_ids(user, db)
        q = q.filter(ServiceTicket.applicant_id.in_(ids)) if ids else q.filter(False)
    if status:
        q = q.filter(ServiceTicket.status == status)
    if student_id is not None:
        q = q.filter(ServiceTicket.applicant_id == student_id)
    items = []
    for t in q.order_by(ServiceTicket.created_at.desc()).all():
        name = db.query(User).filter(User.id == t.applicant_id).first()
        items.append({
            "kind": "ticket",
            "id": t.id,
            "title": t.title,
            "applicant_id": t.applicant_id,
            "applicant_name": name.name if name else t.applicant_name,
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "detail": t.content or "",
        })
    return items


def _material_items(user: User, db: Session, status: str | None, student_id: int | None = None):
    q = db.query(MaterialArchive)
    if user.role != UserRole.ADMIN:
        ids = _scoped_student_ids(user, db)
        q = q.filter(MaterialArchive.student_id.in_(ids)) if ids else q.filter(False)
    if status:
        q = q.filter(MaterialArchive.status == status)
    if student_id is not None:
        q = q.filter(MaterialArchive.student_id == student_id)
    items = []
    for m in q.order_by(MaterialArchive.created_at.desc()).all():
        name = db.query(User).filter(User.id == m.student_id).first()
        items.append({
            "kind": "material",
            "id": m.id,
            "title": f"材料档案：{m.title}",
            "applicant_id": m.student_id,
            "applicant_name": name.name if name else "",
            "status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "created_at": m.created_at.isoformat() if m.created_at else "",
            "detail": m.remark or "",
        })
    return items


@router.get("/pending")
def pending_list(
    status: str | None = Query(None),
    kind: str | None = Query(None),
    student_id: int | None = Query(None, description="按学生过滤，闭环用"),
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """教师/管理员：聚合待处理（或按状态/类型筛选）的申请列表。"""
    if kind and kind not in APPROVAL_KINDS:
        raise HTTPException(400, f"不支持的申请类型: {kind}")
    if status and status not in STATUS_ACTIVE:
        status = None
    result = []
    if kind in (None, "leave"):
        result += _leave_items(user, db, status, student_id)
    if kind in (None, "ticket"):
        result += _ticket_items(user, db, status, student_id)
    if kind in (None, "material"):
        result += _material_items(user, db, status, student_id)
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result


@router.post("/{kind}/{item_id}/review")
def review_item(
    kind: str,
    item_id: int,
    req: ReviewRequest,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """统一审核：approve / reject。审核后站内通知申请人。"""
    if kind not in APPROVAL_KINDS:
        raise HTTPException(400, "不支持的申请类型")
    if req.action not in ("approve", "reject"):
        raise HTTPException(400, "action 必须为 approve 或 reject")

    title = "审批结果"
    applicant_id: int | None = None
    reject_reason = req.reject_reason or ""

    if kind == "leave":
        rec = db.query(LeaveRequest).filter(LeaveRequest.id == item_id).first()
        if not rec:
            raise HTTPException(404, "请假申请不存在")
        if user.role != UserRole.ADMIN:
            student = db.query(User).filter(User.id == rec.student_id).first()
            if not student or student.tutor_id != user.id:
                raise HTTPException(403, "无权审批该请假")
        setattr(rec, "status", LeaveStatus.APPROVED if req.action == "approve" else LeaveStatus.REJECTED)
        rec.tutor_id = user.id
        if req.action == "reject":
            rec.reject_reason = reject_reason
        applicant_id = rec.student_id
        title = "请假审批结果"
        content = f"你的请假申请已{'通过' if req.action == 'approve' else '未通过'}" + (f"，原因：{reject_reason}" if req.action == "reject" else "")
        ntype = NotificationType.LEAVE

    elif kind == "ticket":
        rec = db.query(ServiceTicket).filter(ServiceTicket.id == item_id).first()
        if not rec:
            raise HTTPException(404, "工单不存在")
        rec.status = TicketStatus.APPROVED if req.action == "approve" else TicketStatus.REJECTED
        rec.approver_id = user.id
        applicant_id = rec.applicant_id
        title = "工单审批结果"
        content = f"你的工单「{rec.title}」审批结果：{'已通过' if req.action == 'approve' else '未通过'}"
        ntype = NotificationType.APPROVAL

    else:  # material
        rec = db.query(MaterialArchive).filter(MaterialArchive.id == item_id).first()
        if not rec:
            raise HTTPException(404, "材料档案不存在")
        if user.role != UserRole.ADMIN:
            student = db.query(User).filter(User.id == rec.student_id).first()
            if not student or student.tutor_id != user.id:
                raise HTTPException(403, "无权审核该材料")
        rec.status = MaterialStatus.APPROVED if req.action == "approve" else MaterialStatus.REJECTED
        rec.reject_reason = reject_reason if req.action == "reject" else None
        rec.reviewer_id = user.id
        applicant_id = rec.student_id
        title = "材料档案归档结果"
        content = f"你的材料「{rec.title}」已{'通过审核归档' if req.action == 'approve' else '未通过审核'}" + (f"，原因：{reject_reason}" if req.action == "reject" else "")
        ntype = NotificationType.APPROVAL

    from app.services.notification_service import send_notification
    send_notification(
        db, applicant_id, title=title, content=content,
        notification_type=ntype, link="/student/workbench",
        related_id=item_id, sender_id=user.id, sms_template=f"{title}短信",
    )
    return {"message": f"已{req.action}"}


@router.get("/stats")
def approval_stats(
    days: int = Query(30, ge=1, le=3650),
    student_id: int | None = Query(None, description="按学生过滤，闭环用"),
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """数据统计（薄路由）：口径与聚合全部在 services/approval_service.py。

    返回：总量/待处理/通过/驳回（全量口径，兼容旧字段）+ 近 N 天口径
    （submitted 提交 / approved_window 通过 / rejected_window 驳回）+ accepted（已受理），
    供审批页流程条（提交 → 受理 → 审批 → 归档）动态展示。
    """
    return approval_service.stats(db, user, days=days, student_id=student_id)