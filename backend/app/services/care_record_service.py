"""教师侧写记录服务：关怀记录 / 谈心谈话 / 评语的唯一入口。"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.care_record import CareRecord, CareRecordType
from app.models.user import User


def _record_type(value: str | CareRecordType | None) -> CareRecordType:
    if isinstance(value, CareRecordType):
        return value
    try:
        return CareRecordType(value) if value else CareRecordType.CARE
    except ValueError:
        return CareRecordType.CARE


def _serialize(record: CareRecord, student_name: str = "", teacher_name: str = "") -> dict:
    return {
        "id": record.id,
        "student_id": record.student_id,
        "student_name": student_name,
        "teacher_id": record.teacher_id,
        "teacher_name": teacher_name,
        "record_type": record.record_type.value if record.record_type else "care",
        "content": record.content,
        "is_private": record.is_private,
        "task_id": record.task_id,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def _names(db: Session, records: list[CareRecord]) -> tuple[dict[int, str], dict[int, str]]:
    ids = {r.student_id for r in records} | {r.teacher_id for r in records}
    if not ids:
        return {}, {}
    rows = db.query(User.id, User.name).filter(User.id.in_(ids)).all()
    mapping = {row[0]: row[1] for row in rows}
    return mapping, mapping


def create_record(
    db: Session,
    *,
    teacher_id: int,
    student_id: int,
    content: str,
    record_type: str | CareRecordType = CareRecordType.CARE,
    is_private: bool = True,
    task_id: int | None = None,
) -> CareRecord:
    record = CareRecord(
        student_id=student_id,
        teacher_id=teacher_id,
        record_type=_record_type(record_type),
        content=content,
        is_private=is_private,
        task_id=task_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_record(db: Session, record_id: int) -> CareRecord | None:
    return (
        db.query(CareRecord)
        .filter(CareRecord.id == record_id, CareRecord.is_deleted.is_(False))
        .first()
    )


def list_records(
    db: Session,
    *,
    student_id: int | None = None,
    teacher_id: int | None = None,
    record_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    query = db.query(CareRecord).filter(CareRecord.is_deleted.is_(False))
    if student_id is not None:
        query = query.filter(CareRecord.student_id == student_id)
    if teacher_id is not None:
        query = query.filter(CareRecord.teacher_id == teacher_id)
    if record_type:
        query = query.filter(CareRecord.record_type == _record_type(record_type))

    total = query.count()
    records = query.order_by(CareRecord.created_at.desc(), CareRecord.id.desc()).offset(offset).limit(limit).all()
    student_names, teacher_names = _names(db, records)
    return [
        _serialize(r, student_names.get(r.student_id, ""), teacher_names.get(r.teacher_id, ""))
        for r in records
    ], total


def update_record(db: Session, record: CareRecord, payload: dict) -> CareRecord:
    if payload.get("content") is not None:
        record.content = payload["content"]
    if payload.get("is_private") is not None:
        record.is_private = payload["is_private"]
    db.commit()
    db.refresh(record)
    return record


def soft_delete(db: Session, record: CareRecord) -> None:
    """软删除：保留审计痕迹，不物理删除。"""
    record.is_deleted = True
    record.updated_at = datetime.now()
    db.commit()


def serialize(record: CareRecord, student_name: str = "", teacher_name: str = "") -> dict:
    return _serialize(record, student_name, teacher_name)


def serialize_full(db: Session, record: CareRecord) -> dict:
    """单条序列化并补齐学生 / 教师姓名，供创建、修改接口直接回显。"""
    student_names, teacher_names = _names(db, [record])
    return _serialize(
        record,
        student_names.get(record.student_id, ""),
        teacher_names.get(record.teacher_id, ""),
    )


def workload_stats(db: Session, teacher_id: int) -> dict:
    """教师工作量统计：以侧写记录为唯一数据源。"""
    rows = (
        db.query(CareRecord.record_type)
        .filter(CareRecord.teacher_id == teacher_id, CareRecord.is_deleted.is_(False))
        .all()
    )
    counts = {"care": 0, "talk": 0, "comment": 0}
    for (record_type,) in rows:
        key = record_type.value if hasattr(record_type, "value") else str(record_type)
        if key in counts:
            counts[key] += 1
    counts["total"] = sum(counts.values())
    return counts
