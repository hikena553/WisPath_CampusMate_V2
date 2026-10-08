"""家校沟通接口：联系人 / 沟通台账 / 只读分享链接（家长无账号，凭 token 只读）。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.guardian import (
    ContactLogCreate,
    ContactLogOut,
    GuardianCreate,
    GuardianOut,
    GuardianUpdate,
    ShareLinkOut,
    SharedLogView,
)
from app.services import guardian_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guardians", tags=["guardians"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


def _assert_student_visible(db: Session, user: User, student_id: int) -> None:
    if user.role == UserRole.ADMIN:
        return
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该学生")


# ── 公开：家长只读页（无鉴权，凭 token） ───────────────────────


@router.get("/share/{token}", response_model=SharedLogView)
def view_shared_log(token: str, db: Session = Depends(get_db)):
    """家长只读访问：7 天有效、可撤销；危机类记录不会生成链接。"""
    data, err = guardian_service.resolve_shared_log(db, token)
    if err:
        detail = {
            "not_found": "链接不存在或已失效",
            "revoked": "链接已被撤销",
            "expired": "链接已过期",
        }.get(err, "链接不可用")
        raise HTTPException(status_code=404 if err == "not_found" else 410, detail=detail)
    return data


# ── 联系人 ────────────────────────────────────────────────────


@router.get("", response_model=list[GuardianOut])
def list_guardians(
    student_id: int = Query(...),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, student_id)
    return guardian_service.list_guardians(db, student_id)


@router.post("", response_model=GuardianOut)
def create_guardian(
    payload: GuardianCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, payload.student_id)
    item = guardian_service.create_guardian(
        db,
        student_id=payload.student_id,
        name=payload.name,
        relation=payload.relation,
        phone=payload.phone,
        is_primary=payload.is_primary,
        remark=payload.remark,
        actor_id=user.id,
    )
    return guardian_service.serialize_guardian(item, guardian_service.name_of(db, payload.student_id))


@router.patch("/{guardian_id}", response_model=GuardianOut)
def update_guardian(
    guardian_id: int,
    payload: GuardianUpdate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    item = guardian_service.get_guardian(db, guardian_id)
    if not item:
        raise HTTPException(status_code=404, detail="联系人不存在")
    _assert_student_visible(db, user, item.student_id)
    guardian_service.update_guardian(db, item, payload.model_dump(exclude_unset=True), actor_id=user.id)
    return guardian_service.serialize_guardian(item, guardian_service.name_of(db, item.student_id))


@router.delete("/{guardian_id}")
def delete_guardian(
    guardian_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    item = guardian_service.get_guardian(db, guardian_id)
    if not item:
        raise HTTPException(status_code=404, detail="联系人不存在")
    _assert_student_visible(db, user, item.student_id)
    guardian_service.soft_delete_guardian(db, item, actor_id=user.id)
    return {"message": "已删除"}


# ── 沟通台账 ──────────────────────────────────────────────────


@router.get("/logs", response_model=list[ContactLogOut])
def list_logs(
    student_id: int | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
    return guardian_service.list_logs(db, user.id, student_id=student_id)


@router.post("/logs", response_model=ContactLogOut)
def create_log(
    payload: ContactLogCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, payload.student_id)
    if payload.guardian_id is not None:
        guardian = guardian_service.get_guardian(db, payload.guardian_id)
        if not guardian or guardian.student_id != payload.student_id:
            raise HTTPException(status_code=400, detail="联系人与学生不匹配")
    log = guardian_service.create_log(
        db,
        teacher_id=user.id,
        student_id=payload.student_id,
        content_summary=payload.content_summary,
        guardian_id=payload.guardian_id,
        scene=payload.scene,
        channel=payload.channel,
        send_sms_flag=payload.send_sms,
    )
    return guardian_service.serialize_log(log, guardian_service.name_of(db, payload.student_id))


@router.delete("/logs/{log_id}")
def delete_log(
    log_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    log = guardian_service.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="沟通记录不存在")
    if user.role != UserRole.ADMIN and log.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能删除本人的沟通记录")
    guardian_service.soft_delete_log(db, log, actor_id=user.id)
    return {"message": "已删除"}


# ── 分享链接 ──────────────────────────────────────────────────


@router.post("/logs/{log_id}/share-link", response_model=ShareLinkOut)
def create_share_link(
    log_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    log = guardian_service.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="沟通记录不存在")
    if user.role != UserRole.ADMIN and log.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能为本人创建的记录生成链接")
    try:
        link = guardian_service.create_share_link(db, log, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return guardian_service.serialize_link(link)


@router.post("/share-links/{link_id}/revoke", response_model=ShareLinkOut)
def revoke_share_link(
    link_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    link = guardian_service.get_share_link(db, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="链接不存在")
    log = guardian_service.get_log(db, link.log_id)
    if log and user.role != UserRole.ADMIN and log.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权撤销该链接")
    guardian_service.revoke_share_link(db, link, actor_id=user.id)
    return guardian_service.serialize_link(link)


@router.get("/logs/{log_id}/share-link", response_model=ShareLinkOut | None)
def get_log_share_link(
    log_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    log = guardian_service.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="沟通记录不存在")
    links = guardian_service.list_links_for_logs(db, [log_id])
    return links.get(log_id)