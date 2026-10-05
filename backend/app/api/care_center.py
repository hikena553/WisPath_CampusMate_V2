"""人文关怀中心接口：关怀日历 / 家访记录 / 正向激励（匿名求助复用既有反馈通道）。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.care_center import (
    CareCenterOverview,
    CareEventCreate,
    CareEventOut,
    HomeVisitCreate,
    HomeVisitOut,
    PraiseCreate,
    PraiseOut,
)
from app.services import care_center_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/care-center", tags=["care-center"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


def _assert_student_visible(db: Session, user: User, student_id: int) -> None:
    """教师只能操作名下学生的关怀数据；管理员不受限。"""
    if user.role == UserRole.ADMIN:
        return
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该学生")


@router.get("/overview", response_model=CareCenterOverview)
def get_overview(
    month: str | None = Query(default=None, description="YYYY-MM，默认当月"),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    return care_center_service.overview(db, user.id, month)


# ── 关怀日历 ──────────────────────────────────────────────────


@router.get("/events", response_model=list[CareEventOut])
def list_events(
    month: str | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    return care_center_service.list_events(db, user.id, month)


@router.post("/events", response_model=CareEventOut)
def create_event(
    payload: CareEventCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    if payload.student_id is not None:
        _assert_student_visible(db, user, payload.student_id)
    event = care_center_service.create_event(
        db,
        teacher_id=user.id,
        title=payload.title,
        event_date=payload.event_date,
        event_type=payload.event_type,
        note=payload.note,
        student_id=payload.student_id,
    )
    return care_center_service.serialize_event(db, event)


@router.post("/events/generate")
def generate_events(
    month: str | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """按本月自动生成关怀事项（幂等，重复触发不重复生成）。"""
    created = care_center_service.generate_events(db, user.id, month)
    return {"created": created, "message": f"已生成 {created} 条关怀事项"}


@router.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    if not care_center_service.delete_event(db, user.id, event_id):
        raise HTTPException(status_code=404, detail="关怀事项不存在")
    return {"message": "已删除"}


# ── 家访记录 ──────────────────────────────────────────────────


@router.get("/visits", response_model=list[HomeVisitOut])
def list_visits(
    student_id: int | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
    return care_center_service.list_visits(db, user.id, student_id=student_id)


@router.post("/visits", response_model=HomeVisitOut)
def create_visit(
    payload: HomeVisitCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, payload.student_id)
    record = care_center_service.create_visit(
        db,
        teacher_id=user.id,
        student_id=payload.student_id,
        visit_date=payload.visit_date,
        content=payload.content,
        method=payload.method,
        follow_up=payload.follow_up,
    )
    return care_center_service.serialize_visit(db, record)


@router.delete("/visits/{visit_id}")
def delete_visit(
    visit_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    record = care_center_service.get_visit(db, user.id, visit_id)
    if not record:
        raise HTTPException(status_code=404, detail="家访记录不存在")
    care_center_service.soft_delete_visit(db, record)
    return {"message": "已删除"}


# ── 正向激励 ──────────────────────────────────────────────────


@router.get("/praises", response_model=list[PraiseOut])
def list_praises(
    student_id: int | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
    return care_center_service.list_praises(db, user.id, student_id=student_id)


@router.post("/praises", response_model=PraiseOut)
def create_praise(
    payload: PraiseCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, payload.student_id)
    record = care_center_service.create_praise(
        db,
        teacher_id=user.id,
        student_id=payload.student_id,
        reason=payload.reason,
        praise_type=payload.praise_type,
        badge_name=payload.badge_name,
        occurred_on=payload.occurred_on,
    )
    return care_center_service.serialize_praise(db, record)


@router.delete("/praises/{praise_id}")
def delete_praise(
    praise_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    record = care_center_service.get_praise(db, user.id, praise_id)
    if not record:
        raise HTTPException(status_code=404, detail="激励记录不存在")
    care_center_service.soft_delete_praise(db, record)
    return {"message": "已删除"}