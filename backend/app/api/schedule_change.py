"""排课调整申请 API：教师发起调课 / 增课，管理员审批，审批通过后落到正式课表。

权限口径
--------
- **发起 / 我的 / 撤回**：仅教师本人（``applicant_id == me``）；
- **待审 / 审批**：教师可审批**本人发起**的申请（自查自批没有意义，所以
  教师的待审队列只含「我提交的且待审」用于跟踪状态），
  真正的审批权在管理员；教师若兼任教务，用管理员账号审批；
- **全部台账**：管理员。

为什么教师端也要有「我的申请」而不是直接看课表
--------------------------------------------
申请是异步的——老师点完提交就去上课了，回来要能立刻知道「批了没有 / 为什么被驳」。
所以发起入口之外必须有一条留痕列表，这也是 ``/my`` 存在的理由。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.academic import Course
from app.models.schedule_change import (
    ScheduleChangeKind,
    ScheduleChangeRequest,
    ScheduleChangeStatus,
)
from app.models.user import User, UserRole
from app.schemas.schedule_change import (
    ScheduleChangeCreate,
    ScheduleChangeOut,
    ScheduleChangeReview,
)
from app.services import schedule_change_service as svc
from app.services.realtime import hub as realtime_hub

router = APIRouter(prefix="/api/schedule-change", tags=["排课调整"])

_teacher = require_role(UserRole.TEACHER)
_reviewer = require_role(UserRole.TEACHER, UserRole.ADMIN)


def _to_out(db: Session, r: ScheduleChangeRequest, *, with_conflicts: bool = False) -> ScheduleChangeOut:
    conflicts: list[str] = []
    if with_conflicts and r.status == ScheduleChangeStatus.PENDING:
        common = dict(
            semester=r.semester,
            day_of_week=r.day_of_week,
            start_period=r.start_period,
            end_period=r.end_period,
            week_start=r.week_start,
            week_end=r.week_end,
            class_group_id=r.class_group_id,
            teacher_id=r.teacher_id,
            teacher_name=r.teacher_name,
            location=r.location,
        )
        # 两类冲突都提示：正式课表已占用（阻断）+ 其它待审申请占用（提示，先到先审）
        conflicts = svc.detect_conflicts(db, exclude_course_id=r.course_id, **common)
        conflicts += svc.detect_pending_conflicts(db, exclude_request_id=r.id, **common)
    return ScheduleChangeOut(
        id=r.id,
        kind=r.kind_value,
        kind_label=svc.KIND_LABEL.get(r.kind, r.kind_value),
        status=r.status_value,
        status_label=svc.STATUS_LABEL.get(r.status, r.status_value),
        applicant_id=r.applicant_id,
        applicant_name=r.applicant_name,
        course_id=r.course_id,
        origin_day_of_week=r.origin_day_of_week,
        origin_start_period=r.origin_start_period,
        origin_end_period=r.origin_end_period,
        origin_location=r.origin_location,
        origin_teacher=r.origin_teacher,
        origin_week_start=r.origin_week_start,
        origin_week_end=r.origin_week_end,
        origin_week_no=r.origin_week_no,
        class_group_id=r.class_group_id,
        class_name=r.class_name,
        course_name=r.course_name,
        teacher_id=r.teacher_id,
        teacher_name=r.teacher_name,
        location=r.location,
        day_of_week=r.day_of_week,
        start_period=r.start_period,
        end_period=r.end_period,
        week_start=r.week_start,
        week_end=r.week_end,
        semester=r.semester,
        credit=r.credit,
        reason=r.reason or "",
        approver_name=r.approver_name or "",
        reject_reason=r.reject_reason or "",
        reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else "",
        applied_course_id=r.applied_course_id,
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
        conflicts=conflicts,
    )


def _admin_ids(db: Session) -> list[int]:
    rows = db.query(User.id).filter(User.role == UserRole.ADMIN).all()
    return [r[0] for r in rows]


def _notify_admins(db: Session, req: ScheduleChangeRequest) -> None:
    """新申请 → 通知管理员；同时实时推给在线管理员，审批页徽标立刻 +1。"""
    label = svc.KIND_LABEL.get(req.kind, "排课调整")
    from app.models.notification import NotificationType
    from app.services.notification_service import send_notification

    for admin_id in _admin_ids(db):
        send_notification(
            db,
            admin_id,
            title=f"{label}申请：{req.course_name}",
            content=(
                f"{req.applicant_name} 提交{label}申请：{req.class_name}《{req.course_name}》"
                f" → {svc.weekday_label(req.day_of_week)} 第{req.start_period}-{req.end_period}节"
                + (f"，理由：{req.reason}" if req.reason else "")
            ),
            notification_type=NotificationType.APPROVAL,
            link="/admin/courses",
            related_id=req.id,
            sender_id=req.applicant_id,
        )
        realtime_hub.publish(admin_id, ["admin-schedule-change", "admin-approval"])


@router.get("/my", response_model=list[ScheduleChangeOut])
def list_my(
    status: str | None = Query(None),
    user: User = Depends(_teacher),
    db: Session = Depends(get_db),
):
    """教师：我提交的调课 / 增课申请（按提交时间倒序）。"""
    q = db.query(ScheduleChangeRequest).filter(ScheduleChangeRequest.applicant_id == user.id)
    if status:
        q = q.filter(ScheduleChangeRequest.status == status)
    rows = q.order_by(ScheduleChangeRequest.created_at.desc()).all()
    return [_to_out(db, r) for r in rows]


@router.post("/create", response_model=ScheduleChangeOut)
def create(
    payload: ScheduleChangeCreate,
    user: User = Depends(_teacher),
    db: Session = Depends(get_db),
):
    """教师：发起调课（swap）或增课（add）申请。"""
    try:
        req = svc.create_request(db, user, payload)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.commit()
    db.refresh(req)
    try:
        _notify_admins(db, req)
    except Exception:  # 通知失败不影响申请本身
        pass
    return _to_out(db, req)


@router.delete("/{req_id}")
def cancel(req_id: int, user: User = Depends(_teacher), db: Session = Depends(get_db)):
    """教师：撤回自己还没被处理的申请。

    已被审批的不能撤回——那已经改变了课表，撤回等于单方面篡改事实；
    要改回来请重新发起一次申请。
    """
    req = (
        db.query(ScheduleChangeRequest)
        .filter(ScheduleChangeRequest.id == req_id, ScheduleChangeRequest.applicant_id == user.id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req.status != ScheduleChangeStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有待审批的申请可以撤回")
    req.status = ScheduleChangeStatus.CANCELLED
    req.reviewed_at = datetime.now()
    db.commit()
    for admin_id in _admin_ids(db):
        realtime_hub.publish(admin_id, ["admin-schedule-change"])
    return {"message": "已撤回"}


@router.get("/pending", response_model=list[ScheduleChangeOut])
def pending(
    kind: str | None = Query(None, description="swap / add"),
    semester: str | None = Query(None),
    user: User = Depends(_reviewer),
    db: Session = Depends(get_db),
):
    """审批队列：管理员看全部待审；教师看「我自己提交的待审」（用来自查进度）。"""
    q = db.query(ScheduleChangeRequest).filter(
        ScheduleChangeRequest.status == ScheduleChangeStatus.PENDING
    )
    if user.role != UserRole.ADMIN:
        q = q.filter(ScheduleChangeRequest.applicant_id == user.id)
    if kind in ("swap", "add"):
        q = q.filter(ScheduleChangeRequest.kind == ScheduleChangeKind(kind))
    if semester:
        q = q.filter(ScheduleChangeRequest.semester == semester)
    rows = q.order_by(ScheduleChangeRequest.created_at.desc()).all()
    # 审批时要看到冲突风险，所以这里带上 conflicts
    return [_to_out(db, r, with_conflicts=True) for r in rows]


@router.get("/all", response_model=list[ScheduleChangeOut])
def list_all(
    status: str | None = Query(None),
    kind: str | None = Query(None),
    semester: str | None = Query(None),
    user: User = Depends(_reviewer),
    db: Session = Depends(get_db),
):
    """台账：管理员看全部；教师看自己提交的（已通过 / 已驳回留痕）。"""
    q = db.query(ScheduleChangeRequest)
    if user.role != UserRole.ADMIN:
        q = q.filter(ScheduleChangeRequest.applicant_id == user.id)
    if status:
        q = q.filter(ScheduleChangeRequest.status == status)
    if kind in ("swap", "add"):
        q = q.filter(ScheduleChangeRequest.kind == ScheduleChangeKind(kind))
    if semester:
        q = q.filter(ScheduleChangeRequest.semester == semester)
    rows = q.order_by(ScheduleChangeRequest.created_at.desc()).limit(500).all()
    return [_to_out(db, r) for r in rows]


@router.post("/{req_id}/review")
def review(
    req_id: int,
    payload: ScheduleChangeReview,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员：审批调课 / 增课申请，通过后立即写回正式课表。

    审批权只给管理员：调课影响的是全班级的课表与教室占用，
    教师自审会让「冲突检测」失去意义。
    """
    if payload.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")
    req = db.query(ScheduleChangeRequest).filter(ScheduleChangeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req.status != ScheduleChangeStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"该申请已是「{svc.STATUS_LABEL.get(req.status, req.status_value)}」，不能重复审批")

    label = svc.KIND_LABEL.get(req.kind, "排课调整")
    if payload.action == "reject":
        req.status = ScheduleChangeStatus.REJECTED
        req.reject_reason = (payload.reject_reason or "").strip()
        req.approver_id = user.id
        req.approver_name = user.name
        req.reviewed_at = datetime.now()
        db.commit()
        from app.models.notification import NotificationType
        from app.services.notification_service import send_notification

        send_notification(
            db,
            req.applicant_id,
            title=f"{label}申请被驳回",
            content=(
                f"你提交的{label}申请（{req.class_name}《{req.course_name}》）未通过"
                + (f"，原因：{req.reject_reason}" if req.reject_reason else "")
            ),
            notification_type=NotificationType.APPROVAL,
            link="/teacher/schedule",
            related_id=req.id,
            sender_id=user.id,
        )
        realtime_hub.publish(req.applicant_id, ["teacher-schedule", "teacher-approval"])
        return {"message": "已驳回"}

    # ---- 通过：落地前再查一次冲突（提交后可能有人先占了同一时段）----
    common = dict(
        semester=req.semester,
        day_of_week=req.day_of_week,
        start_period=req.start_period,
        end_period=req.end_period,
        week_start=req.week_start,
        week_end=req.week_end,
        class_group_id=req.class_group_id,
        teacher_id=req.teacher_id,
        teacher_name=req.teacher_name,
        location=req.location,
    )
    conflicts = svc.detect_conflicts(db, exclude_course_id=req.course_id, **common)
    if conflicts:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="排课冲突，无法通过：" + "；".join(conflicts),
        )
    # 与其它待审申请的重叠：只阻断「同班级/同教师/同教室」的重复占用会被前面那条拦掉，
    # 这里剩下的都是其它班级互不干扰的情况，不阻断，仅记录在审批留痕里。
    pending_tips = svc.detect_pending_conflicts(db, exclude_request_id=req.id, **common)

    req.status = ScheduleChangeStatus.APPROVED
    req.approver_id = user.id
    req.approver_name = user.name
    req.reviewed_at = datetime.now()
    course_id = svc.apply_approved(db, req)
    req.applied_course_id = course_id
    db.commit()

    # 同批次还有其他待审申请占着同一时段：审批时已提示，这里在返回里带一句，
    # 让审批人知道「还有一条要单独决定」，而不是通过完就以为万事大吉。
    review_note = "；".join(pending_tips) if pending_tips else ""

    from app.models.notification import NotificationType
    from app.services.notification_service import send_notification

    when = f"{svc.weekday_label(req.day_of_week)} 第{req.start_period}-{req.end_period}节"
    send_notification(
        db,
        req.applicant_id,
        title=f"{label}申请已通过",
        content=f"{req.class_name}《{req.course_name}》已调整为 {when}" + (f"，地点 {req.location}" if req.location else ""),
        notification_type=NotificationType.APPROVAL,
        link="/teacher/schedule",
        related_id=req.id,
        sender_id=user.id,
    )
    # 学生被动数据已变（课表直查 courses），这里补一次主动告知
    try:
        course = db.query(Course).filter(Course.id == course_id).first() if course_id else None
        svc.notify_students(db, req, course)
    except Exception:
        import logging

        logging.getLogger(__name__).warning("调课通知学生失败 req=%s", req.id, exc_info=True)
    realtime_hub.publish(req.applicant_id, ["teacher-schedule", "teacher-approval"])
    return {"message": "已通过", "course_id": course_id, "note": review_note}
