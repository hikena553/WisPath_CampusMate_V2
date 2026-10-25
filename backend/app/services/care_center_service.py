"""人文关怀中心服务：关怀日历 / 家访记录 / 正向激励的唯一入口。

自动生成口径（本月）：
- 学业预警：名下有「未处理且中等及以上」危机预警的学生；
- 困难学生：近 30 天内非驳回请假达阈值的频繁请假学生；
- 生日：因数据模型未存出生日期，仅支持手动添加（已在规划风险中说明）。
"""
import calendar
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.care_center import (
    CareEvent,
    CareEventType,
    FollowUpStatus,
    HomeVisitMethod,
    HomeVisitRecord,
    PraiseRecord,
    PraiseType,
)
from app.models.care_record import CareRecord
from app.models.crisis import AIDialogSummary
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.notification import NotificationType
from app.models.user import User, UserRole
from app.services.notification_service import send_notification
from app.utils.enum_helpers import safe_enum_val

FREQUENT_LEAVE_THRESHOLD = 3
FREQUENT_LEAVE_WINDOW_DAYS = 30

EVENT_TYPE_LABELS = {
    "birthday": "生日关怀",
    "difficulty": "困难学生",
    "academic": "学业预警",
    "other": "其他事项",
}
VISIT_METHOD_LABELS = {
    "home": "实地家访",
    "phone": "电话沟通",
    "video": "视频沟通",
    "school": "校内约谈",
    "other": "其他方式",
}


def _event_type(value: str | CareEventType | None) -> CareEventType:
    if isinstance(value, CareEventType):
        return value
    try:
        return CareEventType(value) if value else CareEventType.OTHER
    except ValueError:
        return CareEventType.OTHER


def _visit_method(value: str | HomeVisitMethod | None) -> HomeVisitMethod:
    if isinstance(value, HomeVisitMethod):
        return value
    try:
        return HomeVisitMethod(value) if value else HomeVisitMethod.PHONE
    except ValueError:
        return HomeVisitMethod.PHONE


def _praise_type(value: str | PraiseType | None) -> PraiseType:
    if isinstance(value, PraiseType):
        return value
    try:
        return PraiseType(value) if value else PraiseType.PRAISE
    except ValueError:
        return PraiseType.PRAISE


def _student_names(db: Session, ids: set[int]) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = db.query(User.id, User.name).filter(User.id.in_(ids)).all()
    return {row[0]: row[1] for row in rows}


def _my_student_ids(db: Session, teacher_id: int) -> list[int]:
    return [
        s.id
        for s in db.query(User).filter(
            User.role == UserRole.STUDENT, User.tutor_id == teacher_id
        ).all()
    ]


def _name_of(db: Session, student_id: int | None) -> str:
    if not student_id:
        return ""
    row = db.query(User.name).filter(User.id == student_id).first()
    return row[0] if row else ""


def _month_range(month: str | None) -> tuple[str, date, date]:
    if month:
        try:
            start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
        except ValueError:
            start = date.today().replace(day=1)
            month = start.strftime("%Y-%m")
    else:
        start = date.today().replace(day=1)
        month = start.strftime("%Y-%m")
    last_day = calendar.monthrange(start.year, start.month)[1]
    return month, start, date(start.year, start.month, last_day)


# ── 关怀日历事件 ──────────────────────────────────────────────


def _serialize_event(event: CareEvent, student_name: str = "") -> dict:
    return {
        "id": event.id,
        "teacher_id": event.teacher_id,
        "student_id": event.student_id,
        "student_name": student_name,
        "event_type": event.event_type.value if event.event_type else "other",
        "event_date": event.event_date,
        "title": event.title,
        "note": event.note,
        "auto_generated": bool(event.auto_generated),
        "created_at": event.created_at.isoformat() if event.created_at else "",
    }


def create_event(
    db: Session,
    *,
    teacher_id: int,
    title: str,
    event_date: date,
    event_type: str | CareEventType = CareEventType.OTHER,
    note: str | None = None,
    student_id: int | None = None,
    auto_generated: bool = False,
) -> CareEvent:
    event = CareEvent(
        teacher_id=teacher_id,
        student_id=student_id,
        event_type=_event_type(event_type),
        event_date=event_date,
        title=title,
        note=note,
        auto_generated=auto_generated,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, teacher_id: int, month: str | None = None, student_id: int | None = None) -> list[dict]:
    _, start, end = _month_range(month)
    query = db.query(CareEvent).filter(
        CareEvent.teacher_id == teacher_id,
        CareEvent.event_date >= start,
        CareEvent.event_date <= end,
    )
    if student_id is not None:
        query = query.filter(CareEvent.student_id == student_id)
    events = query.order_by(CareEvent.event_date.asc(), CareEvent.id.asc()).all()
    names = _student_names(db, {e.student_id for e in events})
    return [_serialize_event(e, names.get(e.student_id or -1, "")) for e in events]


def delete_event(db: Session, teacher_id: int, event_id: int) -> bool:
    event = (
        db.query(CareEvent)
        .filter(CareEvent.id == event_id, CareEvent.teacher_id == teacher_id)
        .first()
    )
    if not event:
        return False
    db.delete(event)
    db.commit()
    return True


def generate_events(db: Session, teacher_id: int, month: str | None = None) -> int:
    """按本月自动生成关怀事项（幂等：同教师 + 同学生 + 同类型 + 同日只生成一次）。"""
    month, start, end = _month_range(month)
    student_ids = _my_student_ids(db, teacher_id)
    if not student_ids:
        return 0

    today = date.today()
    event_day = today if start <= today <= end else start
    created = 0

    def _exists(student_id: int, etype: CareEventType, day: date) -> bool:
        return (
            db.query(CareEvent)
            .filter(
                CareEvent.teacher_id == teacher_id,
                CareEvent.student_id == student_id,
                CareEvent.event_type == etype,
                CareEvent.event_date == day,
                CareEvent.auto_generated.is_(True),
            )
            .first()
            is not None
        )

    # ① 学业预警：未处理且中等及以上
    crisis_rows = (
        db.query(AIDialogSummary)
        .filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.resolved.is_(False),
        )
        .all()
    )
    seen_academic: set[int] = set()
    for row in crisis_rows:
        level = safe_enum_val(row.level)
        if level not in ("moderate", "severe") or row.student_id in seen_academic:
            continue
        seen_academic.add(row.student_id)
        if _exists(row.student_id, CareEventType.ACADEMIC, event_day):
            continue
        student = db.query(User).filter(User.id == row.student_id).first()
        create_event(
            db,
            teacher_id=teacher_id,
            student_id=row.student_id,
            title=f"学业/心理预警跟进：{student.name if student else '学生'}",
            event_type=CareEventType.ACADEMIC,
            event_date=event_day,
            note="存在未处理的危机预警，建议本周内安排谈心",
            auto_generated=True,
        )
        created += 1

    # ② 困难学生：近 30 天频繁请假
    window_start = datetime.now() - timedelta(days=FREQUENT_LEAVE_WINDOW_DAYS)
    leave_rows = (
        db.query(LeaveRequest.student_id)
        .filter(
            LeaveRequest.student_id.in_(student_ids),
            LeaveRequest.created_at >= window_start,
            LeaveRequest.status != LeaveStatus.REJECTED,
        )
        .all()
    )
    counts: dict[int, int] = {}
    for (sid,) in leave_rows:
        counts[sid] = counts.get(sid, 0) + 1
    for sid, count in counts.items():
        if count < FREQUENT_LEAVE_THRESHOLD:
            continue
        if _exists(sid, CareEventType.DIFFICULTY, event_day):
            continue
        student = db.query(User).filter(User.id == sid).first()
        create_event(
            db,
            teacher_id=teacher_id,
            student_id=sid,
            title=f"困难学生关注：{student.name if student else '学生'}",
            event_type=CareEventType.DIFFICULTY,
            event_date=event_day,
            note=f"近{FREQUENT_LEAVE_WINDOW_DAYS}天请假 {count} 次，建议了解家庭与学业状况",
            auto_generated=True,
        )
        created += 1

    return created


# ── 家访记录 ──────────────────────────────────────────────────


def _serialize_visit(record: HomeVisitRecord, student_name: str = "") -> dict:
    return {
        "id": record.id,
        "student_id": record.student_id,
        "student_name": student_name,
        "teacher_id": record.teacher_id,
        "visit_date": record.visit_date,
        "method": record.method.value if record.method else "phone",
        "content": record.content,
        "follow_up": record.follow_up,
        "follow_up_status": record.follow_up_status.value if record.follow_up_status else "pending",
        "follow_up_done_at": record.follow_up_done_at.isoformat() if record.follow_up_done_at else "",
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def _follow_up_status(value: str | FollowUpStatus | None) -> FollowUpStatus | None:
    if value is None:
        return None
    if isinstance(value, FollowUpStatus):
        return value
    try:
        return FollowUpStatus(value)
    except ValueError:
        return None


def _notify_student(db: Session, student_id: int | None, title: str, content: str, related_id: int) -> None:
    """给关联学生发一条普通级站内通知；失败不阻塞主流程。"""
    if not student_id:
        return
    try:
        send_notification(
            db,
            user_id=student_id,
            title=title,
            content=content,
            notification_type=NotificationType.SYSTEM,
            link="/student/care",
            related_id=related_id,
        )
    except Exception:  # noqa: BLE001 通知为旁路，失败不影响主流程
        db.rollback()


def create_visit(
    db: Session,
    *,
    teacher_id: int,
    student_id: int,
    visit_date: date,
    content: str,
    method: str | HomeVisitMethod = HomeVisitMethod.PHONE,
    follow_up: str | None = None,
    sync_to_guardian: bool = False,
) -> HomeVisitRecord:
    record = HomeVisitRecord(
        student_id=student_id,
        teacher_id=teacher_id,
        visit_date=visit_date,
        method=_visit_method(method),
        content=content,
        follow_up=follow_up,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if sync_to_guardian:
        sync_visit_to_guardian(db, record)

    _notify_student(
        db,
        student_id,
        "老师记录了对你的关怀",
        f"{visit_date} 的家访已记录，记得查看老师的关心与后续安排。",
        record.id,
    )
    return record


def sync_visit_to_guardian(db: Session, record: HomeVisitRecord) -> None:
    """把家访同步进家校沟通台账（scene=care / channel=note）；失败不阻塞主流程。"""
    from app.services import guardian_service

    try:
        guardian_service.create_log(
            db,
            teacher_id=record.teacher_id,
            student_id=record.student_id,
            content_summary=f"家访（{record.visit_date}）：{record.content}",
            scene="care",
            channel="note",
        )
    except Exception:  # noqa: BLE001 台账同步为旁路，失败不影响家访主流程
        db.rollback()


def update_visit(
    db: Session,
    actor_id: int,
    visit_id: int,
    payload: dict,
    *,
    allow_any: bool = False,
) -> HomeVisitRecord | None:
    """更新家访记录：内容 / 后续计划 / 回访状态。

    回访状态置 done 时写 follow_up_done_at，置回 pending 时清空。
    allow_any=True 供管理员跨教师修改；否则校验归属（只能改本人记录）。
    """
    query = db.query(HomeVisitRecord).filter(
        HomeVisitRecord.id == visit_id,
        HomeVisitRecord.is_deleted.is_(False),
    )
    if not allow_any:
        query = query.filter(HomeVisitRecord.teacher_id == actor_id)
    record = query.first()
    if not record:
        return None

    if payload.get("content") is not None:
        record.content = payload["content"]
    if "follow_up" in payload:
        record.follow_up = payload["follow_up"]

    status = _follow_up_status(payload.get("follow_up_status"))
    if status is not None:
        record.follow_up_status = status
        record.follow_up_done_at = datetime.now() if status == FollowUpStatus.DONE else None

    db.commit()
    db.refresh(record)
    return record


def list_visits(
    db: Session, teacher_id: int, *, student_id: int | None = None, limit: int = 100
) -> list[dict]:
    query = db.query(HomeVisitRecord).filter(
        HomeVisitRecord.teacher_id == teacher_id,
        HomeVisitRecord.is_deleted.is_(False),
    )
    if student_id is not None:
        query = query.filter(HomeVisitRecord.student_id == student_id)
    records = query.order_by(HomeVisitRecord.visit_date.desc(), HomeVisitRecord.id.desc()).limit(limit).all()
    names = _student_names(db, {r.student_id for r in records})
    return [_serialize_visit(r, names.get(r.student_id, "")) for r in records]


def get_visit(db: Session, teacher_id: int, visit_id: int) -> HomeVisitRecord | None:
    return (
        db.query(HomeVisitRecord)
        .filter(
            HomeVisitRecord.id == visit_id,
            HomeVisitRecord.teacher_id == teacher_id,
            HomeVisitRecord.is_deleted.is_(False),
        )
        .first()
    )


def soft_delete_visit(db: Session, record: HomeVisitRecord) -> None:
    record.is_deleted = True
    db.commit()


# ── 正向激励 ──────────────────────────────────────────────────


def _serialize_praise(record: PraiseRecord, student_name: str = "") -> dict:
    return {
        "id": record.id,
        "student_id": record.student_id,
        "student_name": student_name,
        "teacher_id": record.teacher_id,
        "praise_type": record.praise_type.value if record.praise_type else "praise",
        "badge_name": record.badge_name,
        "reason": record.reason,
        "occurred_on": record.occurred_on,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def create_praise(
    db: Session,
    *,
    teacher_id: int,
    student_id: int,
    reason: str,
    praise_type: str | PraiseType = PraiseType.PRAISE,
    badge_name: str | None = None,
    occurred_on: date | None = None,
) -> PraiseRecord:
    record = PraiseRecord(
        student_id=student_id,
        teacher_id=teacher_id,
        praise_type=_praise_type(praise_type),
        badge_name=badge_name,
        reason=reason,
        occurred_on=occurred_on or date.today(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    label = record.badge_name or "正向激励"
    _notify_student(
        db,
        student_id,
        "你收到了一条正向激励",
        f"老师为你送上「{label}」：{reason}",
        record.id,
    )
    return record


def list_praises(
    db: Session, teacher_id: int, *, student_id: int | None = None, limit: int = 100
) -> list[dict]:
    query = db.query(PraiseRecord).filter(
        PraiseRecord.teacher_id == teacher_id,
        PraiseRecord.is_deleted.is_(False),
    )
    if student_id is not None:
        query = query.filter(PraiseRecord.student_id == student_id)
    records = query.order_by(PraiseRecord.occurred_on.desc(), PraiseRecord.id.desc()).limit(limit).all()
    names = _student_names(db, {r.student_id for r in records})
    return [_serialize_praise(r, names.get(r.student_id, "")) for r in records]


def get_praise(db: Session, teacher_id: int, praise_id: int) -> PraiseRecord | None:
    return (
        db.query(PraiseRecord)
        .filter(
            PraiseRecord.id == praise_id,
            PraiseRecord.teacher_id == teacher_id,
            PraiseRecord.is_deleted.is_(False),
        )
        .first()
    )


def soft_delete_praise(db: Session, record: PraiseRecord) -> None:
    record.is_deleted = True
    db.commit()


# ── 概览 ──────────────────────────────────────────────────────


def overview(db: Session, teacher_id: int, month: str | None = None) -> dict:
    month, start, end = _month_range(month)
    event_count = (
        db.query(CareEvent)
        .filter(
            CareEvent.teacher_id == teacher_id,
            CareEvent.event_date >= start,
            CareEvent.event_date <= end,
        )
        .count()
    )
    visit_count = (
        db.query(HomeVisitRecord)
        .filter(
            HomeVisitRecord.teacher_id == teacher_id,
            HomeVisitRecord.is_deleted.is_(False),
            HomeVisitRecord.visit_date >= start,
            HomeVisitRecord.visit_date <= end,
        )
        .count()
    )
    praise_count = (
        db.query(PraiseRecord)
        .filter(
            PraiseRecord.teacher_id == teacher_id,
            PraiseRecord.is_deleted.is_(False),
            PraiseRecord.occurred_on >= start,
            PraiseRecord.occurred_on <= end,
        )
        .count()
    )
    # 待回访家访数（本月，状态 pending）：语义修正，原实现误等于事项数
    pending_visits = (
        db.query(HomeVisitRecord)
        .filter(
            HomeVisitRecord.teacher_id == teacher_id,
            HomeVisitRecord.is_deleted.is_(False),
            HomeVisitRecord.visit_date >= start,
            HomeVisitRecord.visit_date <= end,
            HomeVisitRecord.follow_up_status == FollowUpStatus.PENDING,
        )
        .count()
    )
    # 已回访家访数（本月，状态 done）
    closed_visits = (
        db.query(HomeVisitRecord)
        .filter(
            HomeVisitRecord.teacher_id == teacher_id,
            HomeVisitRecord.is_deleted.is_(False),
            HomeVisitRecord.visit_date >= start,
            HomeVisitRecord.visit_date <= end,
            HomeVisitRecord.follow_up_status == FollowUpStatus.DONE,
        )
        .count()
    )
    # 未来（含今天）的关怀事项数
    upcoming_events = (
        db.query(CareEvent)
        .filter(
            CareEvent.teacher_id == teacher_id,
            CareEvent.event_date >= date.today(),
        )
        .count()
    )
    return {
        "month": month,
        "event_count": event_count,
        "visit_count": visit_count,
        "praise_count": praise_count,
        "pending_events": pending_visits,
        "upcoming_events": upcoming_events,
        "closed_visit_count": closed_visits,
    }


def list_student_care(db: Session, student_id: int) -> dict:
    """学生端「我的关怀」只读数据：激励 + 非私密关怀记录 + 家访 + 汇总计数。"""
    praise_rows = (
        db.query(PraiseRecord)
        .filter(PraiseRecord.student_id == student_id, PraiseRecord.is_deleted.is_(False))
        .order_by(PraiseRecord.occurred_on.desc(), PraiseRecord.id.desc())
        .all()
    )
    record_rows = (
        db.query(CareRecord)
        .filter(
            CareRecord.student_id == student_id,
            CareRecord.is_deleted.is_(False),
            CareRecord.is_private.is_(False),
        )
        .order_by(CareRecord.created_at.desc(), CareRecord.id.desc())
        .all()
    )
    visit_rows = (
        db.query(HomeVisitRecord)
        .filter(HomeVisitRecord.student_id == student_id, HomeVisitRecord.is_deleted.is_(False))
        .order_by(HomeVisitRecord.visit_date.desc(), HomeVisitRecord.id.desc())
        .all()
    )

    tids = {r.teacher_id for r in praise_rows + record_rows + visit_rows}
    names = _student_names(db, tids)

    praises = [
        {
            "id": r.id,
            "praise_type": r.praise_type.value if r.praise_type else "praise",
            "badge_name": r.badge_name,
            "reason": r.reason,
            "occurred_on": r.occurred_on,
            "teacher_name": names.get(r.teacher_id, ""),
        }
        for r in praise_rows
    ]
    records = [
        {
            "id": r.id,
            "record_type": r.record_type.value if r.record_type else "care",
            "content": r.content,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "teacher_name": names.get(r.teacher_id, ""),
        }
        for r in record_rows
    ]
    visits = [
        {
            "id": r.id,
            "visit_date": r.visit_date,
            "method": r.method.value if r.method else "phone",
            "content": r.content,
            "follow_up": r.follow_up,
            "follow_up_status": r.follow_up_status.value if r.follow_up_status else "pending",
            "teacher_name": names.get(r.teacher_id, ""),
        }
        for r in visit_rows
    ]
    return {
        "praises": praises,
        "records": records,
        "visits": visits,
        "summary": {"praises": len(praises), "visits": len(visits), "records": len(records)},
    }


def serialize_event(db: Session, event: CareEvent) -> dict:
    return _serialize_event(event, _name_of(db, event.student_id))


def serialize_visit(db: Session, record: HomeVisitRecord) -> dict:
    return _serialize_visit(record, _name_of(db, record.student_id))


def serialize_praise(db: Session, record: PraiseRecord) -> dict:
    return _serialize_praise(record, _name_of(db, record.student_id))