"""教师侧写记录接口：关怀记录 / 谈心谈话 / 评语，并作为工作量统计数据源。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.care_record import (
    CareRecordCreate,
    CareRecordOut,
    CareRecordUpdate,
    WorkloadStats,
)
from app.services import care_record_service, teacher_task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/care-records", tags=["care-records"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


def _assert_student_visible(db: Session, user: User, student_id: int) -> None:
    """教师只能操作自己名下学生的记录；管理员不受限。"""
    if user.role == UserRole.ADMIN:
        return
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该学生档案")


@router.get("/workload", response_model=WorkloadStats)
def get_workload(user: User = Depends(_teacher_only), db: Session = Depends(get_db)):
    """教师工作量统计（成长看板 / 首页工作台使用）。"""
    return care_record_service.workload_stats(db, user.id)


@router.get("", response_model=list[CareRecordOut])
def list_records(
    student_id: int | None = Query(default=None),
    record_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
        items, _ = care_record_service.list_records(
            db, student_id=student_id, record_type=record_type, limit=limit, offset=offset
        )
    else:
        # 未指定学生时只返回本人撰写的记录，避免越权浏览
        items, _ = care_record_service.list_records(
            db, teacher_id=user.id, record_type=record_type, limit=limit, offset=offset
        )
    return items


@router.post("", response_model=CareRecordOut)
def create_record(
    payload: CareRecordCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, payload.student_id)
    record = care_record_service.create_record(
        db,
        teacher_id=user.id,
        student_id=payload.student_id,
        content=payload.content,
        record_type=payload.record_type,
        is_private=payload.is_private,
        task_id=payload.task_id,
    )
    # 闭环：由任务触发的记录，把任务推进到"已关怀"
    if payload.task_id is not None:
        task = teacher_task_service.get_task(db, payload.task_id, user.id)
        if task and task.status.value in ("pending", "contacted"):
            try:
                teacher_task_service.update_task(db, task, {"status": "cared"})
            except ValueError:
                logger.warning("任务 %s 状态推进失败", payload.task_id)
    return care_record_service.serialize_full(db, record)


@router.patch("/{record_id}", response_model=CareRecordOut)
def update_record(
    record_id: int,
    payload: CareRecordUpdate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    record = care_record_service.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if user.role != UserRole.ADMIN and record.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能修改本人撰写的记录")
    care_record_service.update_record(db, record, payload.model_dump(exclude_unset=True))
    return care_record_service.serialize_full(db, record)


@router.delete("/{record_id}")
def delete_record(
    record_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    record = care_record_service.get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if user.role != UserRole.ADMIN and record.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能删除本人撰写的记录")
    care_record_service.soft_delete(db, record)
    return {"message": "已删除"}
