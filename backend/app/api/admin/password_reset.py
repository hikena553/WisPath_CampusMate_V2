"""管理端 · 密码重置申请审核。

学生 / 教师在登录页提交「忘记密码」身份核验后，系统自动给全部管理员发站内消息；
管理员在此审核：通过则把密码重置为学校统一初始密码，拒绝则记录原因并通知申请人。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import hash_password
from app.models.announcement import UrgencyLevel
from app.models.notification import NotificationType
from app.models.password_reset import PasswordResetRequest, PasswordResetStatus
from app.models.user import User, UserRole
from app.services.import_export_service import DEFAULT_PASSWORD
from app.services.notification_service import send_notification

router = APIRouter(tags=["admin"])


def _serialize(item: PasswordResetRequest) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "username": item.username,
        "name": item.name,
        "contact": item.contact,
        "reason": item.reason,
        "status": item.status.value,
        "admin_note": item.admin_note,
        "created_at": item.created_at,
        "handled_at": item.handled_at,
    }


@router.get("/password-reset-requests")
def list_password_reset_requests(
    status: str | None = Query(None, description="pending / reset / rejected"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(PasswordResetRequest)
    if status:
        try:
            query = query.filter(PasswordResetRequest.status == PasswordResetStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="状态参数不正确")
    total = query.count()
    rows = (
        query.order_by(PasswordResetRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pending = (
        db.query(PasswordResetRequest)
        .filter(PasswordResetRequest.status == PasswordResetStatus.PENDING)
        .count()
    )
    return {
        "items": [_serialize(r) for r in rows],
        "total": total,
        "pending": pending,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/password-reset-requests/{request_id}/approve")
def approve_password_reset(
    request_id: int,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    item = db.query(PasswordResetRequest).filter(PasswordResetRequest.id == request_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="申请不存在")
    if item.status != PasswordResetStatus.PENDING:
        raise HTTPException(status_code=400, detail="该申请已处理")

    target = db.query(User).filter(User.id == item.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="申请人账号不存在")

    target.password_hash = hash_password(DEFAULT_PASSWORD)
    target.password_changed = False
    item.status = PasswordResetStatus.RESET
    item.handled_by = admin.id
    item.handled_at = datetime.now()

    send_notification(
        db,
        target.id,
        title="密码已重置",
        content=f"管理员已通过你的密码重置申请，账号密码已恢复为初始密码 {DEFAULT_PASSWORD}，请登录后立即修改。",
        notification_type=NotificationType.SYSTEM,
        link="/login",
        related_id=item.id,
        sender_id=admin.id,
        level=UrgencyLevel.IMPORTANT,
    )
    db.commit()
    return {
        "message": f"已将 {target.name} 的密码重置为初始密码",
        "initial_password": DEFAULT_PASSWORD,
    }


@router.post("/password-reset-requests/{request_id}/reject")
def reject_password_reset(
    request_id: int,
    note: str | None = Query(None, max_length=200),
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    item = db.query(PasswordResetRequest).filter(PasswordResetRequest.id == request_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="申请不存在")
    if item.status != PasswordResetStatus.PENDING:
        raise HTTPException(status_code=400, detail="该申请已处理")

    item.status = PasswordResetStatus.REJECTED
    item.admin_note = (note or "身份信息核验未通过").strip()[:200]
    item.handled_by = admin.id
    item.handled_at = datetime.now()

    target = db.query(User).filter(User.id == item.user_id).first()
    if target:
        send_notification(
            db,
            target.id,
            title="密码重置申请未通过",
            content=f"你的密码重置申请未通过：{item.admin_note}。如有疑问请联系辅导员或管理员。",
            notification_type=NotificationType.SYSTEM,
            link="/login",
            related_id=item.id,
            sender_id=admin.id,
            level=UrgencyLevel.IMPORTANT,
        )
    db.commit()
    return {"message": "已驳回该申请"}
