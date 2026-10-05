"""教师待办任务服务：任务层的唯一入口。

所有模块（AI 建议、预警随访、审批待办、关怀计划）都通过本服务建任务，
以保证"同一来源对象不重复建任务"的幂等约束集中在同一处。
"""
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.teacher_task import (
    ALLOWED_TRANSITIONS,
    TaskSourceType,
    TaskStatus,
    TeacherTask,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# 视为"仍需处理"的状态，用于逾期 / 今日统计
_OPEN_STATUSES = (TaskStatus.PENDING, TaskStatus.CONTACTED, TaskStatus.CARED)


def _source_type(value: str | TaskSourceType | None) -> TaskSourceType:
    if isinstance(value, TaskSourceType):
        return value
    try:
        return TaskSourceType(value) if value else TaskSourceType.MANUAL
    except ValueError:
        return TaskSourceType.MANUAL


def _status(value: str | TaskStatus | None) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    try:
        return TaskStatus(value) if value else TaskStatus.PENDING
    except ValueError:
        return TaskStatus.PENDING


def _naive_now() -> datetime:
    """统一使用 naive 本地时间，避免与 naive 字段比较时抛 TypeError。"""
    return datetime.now()


def _serialize(task: TeacherTask, student_name: str = "") -> dict:
    today = date.today()
    overdue = bool(task.due_at and task.due_at < today and task.status in _OPEN_STATUSES)
    return {
        "id": task.id,
        "teacher_id": task.teacher_id,
        "source_type": task.source_type.value if task.source_type else "manual",
        "source_id": task.source_id,
        "student_id": task.student_id,
        "student_name": student_name,
        "title": task.title,
        "detail": task.detail,
        "rule_code": task.rule_code,
        "status": task.status.value if task.status else "pending",
        "due_at": task.due_at,
        "overdue": overdue,
        "done_at": task.done_at.isoformat() if task.done_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else "",
    }


def create_task(
    db: Session,
    *,
    teacher_id: int,
    title: str,
    detail: str | None = None,
    student_id: int | None = None,
    due_at: date | None = None,
    source_type: str | TaskSourceType = TaskSourceType.MANUAL,
    source_id: int | None = None,
    rule_code: str | None = None,
) -> TeacherTask:
    """建任务（幂等）：同一 (source_type, source_id, teacher_id) 已存在时直接返回旧任务。"""
    stype = _source_type(source_type)

    if source_id is not None:
        existing = (
            db.query(TeacherTask)
            .filter(
                TeacherTask.teacher_id == teacher_id,
                TeacherTask.source_type == stype,
                TeacherTask.source_id == source_id,
            )
            .first()
        )
        if existing:
            # 已办结的任务不再被重复触发覆盖
            if existing.status in _OPEN_STATUSES:
                existing.title = title
                existing.detail = detail
                if rule_code is not None:
                    existing.rule_code = rule_code
                if due_at is not None:
                    existing.due_at = due_at
                db.commit()
                db.refresh(existing)
            return existing

    task = TeacherTask(
        teacher_id=teacher_id,
        title=title,
        detail=detail,
        student_id=student_id,
        due_at=due_at,
        source_type=stype,
        source_id=source_id,
        rule_code=rule_code,
    )
    db.add(task)
    try:
        db.commit()
    except IntegrityError:
        # 并发下唯一键兜底：回滚后取已存在记录
        db.rollback()
        return (
            db.query(TeacherTask)
            .filter(
                TeacherTask.teacher_id == teacher_id,
                TeacherTask.source_type == stype,
                TeacherTask.source_id == source_id,
            )
            .first()
        )
    db.refresh(task)
    return task


def bulk_upsert_from_suggestions(db: Session, teacher_id: int, suggestions: list[dict]) -> int:
    """把 AI 推荐联系的学生批量落为跟进任务，返回新建数量。"""
    created = 0
    for item in suggestions:
        student_id = item.get("student_id")
        if student_id is None:
            continue
        before = (
            db.query(TeacherTask)
            .filter(
                TeacherTask.teacher_id == teacher_id,
                TeacherTask.source_type == TaskSourceType.AI_SUGGEST,
                TeacherTask.source_id == student_id,
            )
            .first()
        )
        name = item.get("student_name") or "该学生"
        create_task(
            db,
            teacher_id=teacher_id,
            title=f"跟进联系：{name}",
            detail=item.get("reason"),
            student_id=student_id,
            source_type=TaskSourceType.AI_SUGGEST,
            source_id=student_id,
        )
        if before is None:
            created += 1
    return created


def _student_names(db: Session, tasks: list[TeacherTask]) -> dict[int, str]:
    ids = {t.student_id for t in tasks if t.student_id}
    if not ids:
        return {}
    rows = db.query(User.id, User.name).filter(User.id.in_(ids)).all()
    return {row[0]: row[1] for row in rows}


def list_tasks(
    db: Session,
    teacher_id: int,
    *,
    status: str | None = None,
    source_type: str | None = None,
    due: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    query = db.query(TeacherTask).filter(TeacherTask.teacher_id == teacher_id)

    if status:
        query = query.filter(TeacherTask.status == _status(status))
    if source_type:
        query = query.filter(TeacherTask.source_type == _source_type(source_type))
    if due == "overdue":
        query = query.filter(TeacherTask.due_at < date.today(), TeacherTask.status.in_(_OPEN_STATUSES))
    elif due == "today":
        query = query.filter(TeacherTask.due_at == date.today(), TeacherTask.status.in_(_OPEN_STATUSES))

    total = query.count()
    tasks = (
        query.order_by(TeacherTask.status.asc(), TeacherTask.due_at.asc().nulls_last(), TeacherTask.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    names = _student_names(db, tasks)
    return [_serialize(t, names.get(t.student_id or -1, "")) for t in tasks], total


def get_task(db: Session, task_id: int, teacher_id: int) -> TeacherTask | None:
    return (
        db.query(TeacherTask)
        .filter(TeacherTask.id == task_id, TeacherTask.teacher_id == teacher_id)
        .first()
    )


def serialize_one(db: Session, task: TeacherTask) -> dict:
    names = _student_names(db, [task])
    return _serialize(task, names.get(task.student_id or -1, ""))


def update_task(db: Session, task: TeacherTask, payload: dict) -> TeacherTask:
    """更新任务；状态变更走状态机校验，非法流转抛 ValueError。"""
    new_status = payload.get("status")
    if new_status is not None:
        target = _status(new_status)
        if target != task.status and target not in ALLOWED_TRANSITIONS.get(task.status, set()):
            raise ValueError(f"不允许的状态流转：{task.status.value} → {target.value}")
        task.status = target
        task.done_at = _naive_now() if target == TaskStatus.DONE else None

    if payload.get("title") is not None:
        task.title = payload["title"]
    if "detail" in payload:
        task.detail = payload["detail"]
    if "due_at" in payload:
        task.due_at = payload["due_at"]

    db.commit()
    db.refresh(task)
    return task


def summary(db: Session, teacher_id: int) -> dict:
    """首页 KPI 用的任务概览。"""
    base = db.query(TeacherTask).filter(TeacherTask.teacher_id == teacher_id)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    return {
        "pending": base.filter(TeacherTask.status == TaskStatus.PENDING).count(),
        "overdue": base.filter(
            TeacherTask.due_at < today, TeacherTask.status.in_(_OPEN_STATUSES)
        ).count(),
        "today": base.filter(
            TeacherTask.due_at == today, TeacherTask.status.in_(_OPEN_STATUSES)
        ).count(),
        "done_this_week": base.filter(
            TeacherTask.status == TaskStatus.DONE,
            TeacherTask.done_at >= datetime.combine(week_start, datetime.min.time()),
        ).count(),
        "total": base.count(),
    }
