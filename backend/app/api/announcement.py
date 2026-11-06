import logging
import os
import uuid
from pathlib import Path
from datetime import datetime, date, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as safunc, select, or_

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.academic import ClassGroup
from app.models.announcement import TeacherAnnouncement, AnnouncementRead, UrgencyLevel, TeacherSchedule
from app.models.notification import NotificationType
from app.schemas.announcement import (
    AnnouncementOut,
    AnnouncementReachItem,
    AnnouncementReachOut,
    UnreadCountOut,
    ScheduleOut,
    ScheduleCreate,
    ScheduleUpdate,
    TeacherClassOption,
)
from app.services.notification_service import send_batch_notifications
from app.utils.enum_helpers import safe_enum_val

logger = logging.getLogger(__name__)

router = APIRouter(tags=["announcement"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "announcements"


def _class_names(db: Session, ids: set[int]) -> dict[int, str]:
    """批量取班级名：班级字典表很小，但公告列表可能有多条，避免 N+1。"""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = db.query(ClassGroup.id, ClassGroup.name).filter(ClassGroup.id.in_(ids)).all()
    return {r[0]: r[1] for r in rows}


def _resolve_class_scope(db: Session, teacher_id: int, class_group_id: int | None) -> int | None:
    """校验并归一化发布目标班级。

    - None / 0 → None（发给名下全体学生）
    - 指定班级 → 必须是「该教师名下学生实际所属」的班级，否则 400。
      这一步不只是校验，也防止教师把公告定向投递到与自己无关的班级。
    """
    if not class_group_id:
        return None
    owned = db.query(User.class_group_id).filter(
        User.role == UserRole.STUDENT,
        User.tutor_id == teacher_id,
        User.class_group_id == class_group_id,
    ).first()
    if not owned:
        raise HTTPException(400, "所选班级下没有你的学生，请重新选择")
    return class_group_id


def _target_student_ids(db: Session, teacher_id: int, class_group_id: int | None) -> list[int]:
    """按发布范围计算收件人：不指定班级 = 名下全体学生。"""
    q = db.query(User.id).filter(
        User.role == UserRole.STUDENT,
        User.tutor_id == teacher_id,
    )
    if class_group_id:
        q = q.filter(User.class_group_id == class_group_id)
    return [row[0] for row in q.all()]


@router.get("/api/teacher/announcement-classes", response_model=list[TeacherClassOption])
def list_announcement_classes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布公告时可选的目标班级：只列该教师名下有学生的班级，并带上人数。

    教师通常带多个班的课，但「名下学生」是按 tutor_id 绑定的；这里用实际绑定关系
    反查班级，避免把全校班级都塞进下拉框。
    """
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    rows = (
        db.query(User.class_group_id, safunc.count(User.id))
        .filter(
            User.role == UserRole.STUDENT,
            User.tutor_id == user.id,
            User.class_group_id.isnot(None),
        )
        .group_by(User.class_group_id)
        .all()
    )
    if not rows:
        return []
    names = _class_names(db, {r[0] for r in rows})
    options = [
        TeacherClassOption(id=cid, name=names.get(cid, f"班级{cid}"), student_count=count)
        for cid, count in rows
    ]
    options.sort(key=lambda o: o.name)
    return options


@router.get("/api/teacher/announcements", response_model=list[AnnouncementOut])
def list_teacher_announcements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    items = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.teacher_id == user.id
    ).order_by(TeacherAnnouncement.created_at.desc()).limit(10).all()
    names = _class_names(db, {a.class_group_id for a in items})
    result = []
    for a in items:
        result.append(AnnouncementOut(
            id=a.id, teacher_id=a.teacher_id, teacher_name=user.name,
            title=a.title, content=a.content, urgency=safe_enum_val(a.urgency),
            attachment_url=a.attachment_url,
            class_group_id=a.class_group_id,
            class_name=names.get(a.class_group_id or 0, ""),
            created_at=a.created_at,
        ))
    return result


@router.post("/api/teacher/announcements", response_model=AnnouncementOut)
async def create_announcement(
    title: str = Form(...),
    content: str = Form(...),
    urgency: str = Form("normal"),
    class_group_id: int | None = Form(None),
    file: UploadFile | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    if urgency not in ("normal", "important", "urgent"):
        urgency = "normal"
    # 发布目标班级：None/0 = 名下全体学生；指定时必须是自己名下有学生的班级
    target_class = _resolve_class_scope(db, user.id, class_group_id)
    attachment_url = None
    if file:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = Path(file.filename).suffix.lower() if file.filename else ""
        save_name = f"{uuid.uuid4().hex}{ext}"
        save_path = UPLOAD_DIR / save_name
        content_bytes = await file.read()
        with open(save_path, "wb") as f:
            f.write(content_bytes)
        attachment_url = f"/api/files/announcements/{save_name}"
    item = TeacherAnnouncement(
        teacher_id=user.id, title=title, content=content,
        urgency=UrgencyLevel(urgency), attachment_url=attachment_url,
        class_group_id=target_class,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # 打通「公告 → 站内通知」链路：发布后即时给目标学生推送通知，
    # 学生端消息中心「通知」可直接看到，避免公告只躺在公告页无人知。
    student_ids = _target_student_ids(db, user.id, target_class)
    if student_ids:
        try:
            urgency_label = {"normal": "普通", "important": "重要", "urgent": "紧急"}.get(urgency, "普通")
            scope_label = ""
            if target_class:
                cname = _class_names(db, {target_class}).get(target_class)
                if cname:
                    scope_label = f"·{cname}"
            send_batch_notifications(
                db,
                student_ids,
                title=f"[{urgency_label}公告{scope_label}] {title}",
                content=content[:200],
                notification_type=NotificationType.ANNOUNCEMENT,
                # 原指旧「工作台」公告子页（已下线）：学生端公告由首页横幅 / 校园资讯承接
                link="/student",
                related_id=item.id,
                sender_id=user.id,
                # 紧急程度 → 提醒级别：学生端据此分级提醒（紧急强提醒 / 重要横幅 / 普通红点）
                level=UrgencyLevel(urgency),
            )
        except Exception:
            logger.exception("公告发布后推送站内通知失败 announcement_id=%s", item.id)

    names = _class_names(db, {item.class_group_id})
    return AnnouncementOut(
        id=item.id, teacher_id=item.teacher_id, teacher_name=user.name,
        title=item.title, content=item.content,
        urgency=safe_enum_val(item.urgency),
        attachment_url=item.attachment_url,
        class_group_id=item.class_group_id,
        class_name=names.get(item.class_group_id or 0, ""),
        created_at=item.created_at,
    )


@router.get("/api/teacher/announcements/reach", response_model=AnnouncementReachOut)
def announcement_reach(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """公告触达回执：基于 AnnouncementRead 真实统计「已读 / 应读 / 触达率」。

    此前页面里的触达率是按紧急程度估算的假数据，这里改为真实口径：
    应读 = 名下学生数；已读 = announcement_reads 中该公告的去重学生数。
    """
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    items = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.teacher_id == user.id
    ).order_by(TeacherAnnouncement.created_at.desc()).limit(10).all()

    # 应读人数按每条公告自己的投递范围算：定向班级公告只应被该班学生读到，
    # 用「名下学生总数」做分母会把班级公告的触达率压得极低（甚至永远到不了 100%）。
    total_students = db.query(safunc.count(User.id)).filter(
        User.role == UserRole.STUDENT,
        User.tutor_id == user.id,
    ).scalar() or 0

    out_items: list[AnnouncementReachItem] = []
    for a in items:
        if a.class_group_id:
            expect = db.query(safunc.count(User.id)).filter(
                User.role == UserRole.STUDENT,
                User.tutor_id == user.id,
                User.class_group_id == a.class_group_id,
            ).scalar() or 0
        else:
            expect = total_students
        read = db.query(safunc.count(safunc.distinct(AnnouncementRead.student_id))).filter(
            AnnouncementRead.announcement_id == a.id
        ).scalar() or 0
        rate = round(read / expect * 100) if expect else 0
        out_items.append(AnnouncementReachItem(
            announcement_id=a.id,
            title=a.title,
            urgency=safe_enum_val(a.urgency),
            total=int(expect),
            read=int(read),
            rate=int(min(rate, 100)),
        ))
    # 汇总按「各公告自己的应读」求和，避免把不同范围的公告混算导致 >100%
    sum_total = sum(i.total for i in out_items)
    sum_read = sum(i.read for i in out_items)
    return AnnouncementReachOut(
        items=out_items,
        total=sum_total,
        read=sum_read,
        rate=round(sum_read / sum_total * 100) if sum_total else 0,
    )


@router.post("/api/teacher/announcements/remind")
def remind_unread_announcements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对最近公告中仍未读的学生补发站内提醒（真实写入通知，不是前端假提示）。"""
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    items = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.teacher_id == user.id
    ).order_by(TeacherAnnouncement.created_at.desc()).limit(10).all()
    if not items:
        return {"ok": True, "reminded": 0}

    # 每条公告只提醒它自己范围内的学生：定向到某班的公告不该打扰其他班
    scope_cache: dict[int | None, list[int]] = {}

    def scope_of(cid: int | None) -> list[int]:
        if cid not in scope_cache:
            scope_cache[cid] = _target_student_ids(db, user.id, cid)
        return scope_cache[cid]

    reminded = 0
    for a in items:
        target_ids = scope_of(a.class_group_id)
        if not target_ids:
            continue
        read_ids = {
            row[0] for row in db.query(AnnouncementRead.student_id).filter(
                AnnouncementRead.announcement_id == a.id
            ).all()
        }
        unread_ids = [sid for sid in target_ids if sid not in read_ids]
        if not unread_ids:
            continue
        try:
            send_batch_notifications(
                db,
                unread_ids,
                title=f"【提醒】{a.title}",
                content=(a.content or "")[:200],
                notification_type=NotificationType.ANNOUNCEMENT,
                link="/student",
                related_id=a.id,
                sender_id=user.id,
                level=a.urgency,
            )
            reminded += len(unread_ids)
        except Exception:
            logger.exception("补发公告提醒失败 announcement_id=%s", a.id)
    return {"ok": True, "reminded": reminded}


@router.delete("/api/teacher/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    item = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.id == announcement_id,
        TeacherAnnouncement.teacher_id == user.id,
    ).first()
    if not item:
        raise HTTPException(404, "公告不存在")
    db.query(AnnouncementRead).filter(AnnouncementRead.announcement_id == announcement_id).delete()
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/api/student/announcements", response_model=list[AnnouncementOut])
def list_student_announcements(
    unread_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(403)
    if not user.tutor_id:
        return []
    tutor = db.query(User).filter(User.id == user.tutor_id).first()
    tutor_name = tutor.name if tutor else ""
    query = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.teacher_id == user.tutor_id
    )
    # 定向公告只给目标班学生看：class_group_id 为空的（全体公告）所有人可见；
    # 有班级的必须匹配学生自己所在班，否则该公告只是发给了别的班。
    if user.class_group_id:
        query = query.filter(
            or_(
                TeacherAnnouncement.class_group_id.is_(None),
                TeacherAnnouncement.class_group_id == user.class_group_id,
            )
        )
    else:
        query = query.filter(TeacherAnnouncement.class_group_id.is_(None))
    if unread_only:
        read_ids = select(AnnouncementRead.announcement_id).where(
            AnnouncementRead.student_id == user.id
        )
        query = query.filter(~TeacherAnnouncement.id.in_(read_ids))
    items = query.order_by(TeacherAnnouncement.created_at.desc()).all()
    names = _class_names(db, {a.class_group_id for a in items})
    result = []
    for a in items:
        result.append(AnnouncementOut(
            id=a.id, teacher_id=a.teacher_id, teacher_name=tutor_name,
            title=a.title, content=a.content,
            urgency=safe_enum_val(a.urgency),
            attachment_url=a.attachment_url,
            class_group_id=a.class_group_id,
            class_name=names.get(a.class_group_id or 0, ""),
            created_at=a.created_at,
        ))
    return result


@router.get("/api/student/announcements/unread-count", response_model=UnreadCountOut)
def unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(403)
    if not user.tutor_id:
        return UnreadCountOut(count=0)
    read_ids = select(AnnouncementRead.announcement_id).where(
        AnnouncementRead.student_id == user.id
    )
    # 与列表一致：只统计发给全体或自己所在班的公告，否则红点会多于列表条数
    if user.class_group_id:
        scope_filter = or_(
            TeacherAnnouncement.class_group_id.is_(None),
            TeacherAnnouncement.class_group_id == user.class_group_id,
        )
    else:
        scope_filter = TeacherAnnouncement.class_group_id.is_(None)
    count = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.teacher_id == user.tutor_id,
        scope_filter,
        ~TeacherAnnouncement.id.in_(read_ids),
    ).count()
    return UnreadCountOut(count=count)


@router.post("/api/student/announcements/{announcement_id}/read")
def mark_read(
    announcement_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(403)
    # 只能标记「确实发给自己」的公告：否则会把别的班公告也计入该生的已读，
    # 让教师端触达率虚高。范围口径与列表/未读数保持一致。
    ann = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.id == announcement_id,
        TeacherAnnouncement.teacher_id == user.tutor_id,
    ).first()
    if not ann:
        raise HTTPException(404, "公告不存在")
    if ann.class_group_id and ann.class_group_id != user.class_group_id:
        raise HTTPException(403, "无权查看该公告")
    existing = db.query(AnnouncementRead).filter(
        AnnouncementRead.student_id == user.id,
        AnnouncementRead.announcement_id == announcement_id,
    ).first()
    if not existing:
        db.add(AnnouncementRead(student_id=user.id, announcement_id=announcement_id))
        db.commit()
    return {"ok": True}


# ── Teacher Schedule endpoints ──

def _schedule_out(i: TeacherSchedule) -> ScheduleOut:
    return ScheduleOut(
        id=i.id, date=str(i.date), content=i.content,
        urgency=safe_enum_val(i.urgency),
        completed=bool(i.completed),
        completed_at=i.completed_at,
    )


def _schedule_sort_key(i: TeacherSchedule, today: date) -> tuple:
    """排序规则与完成状态完全解耦，保证勾选完成前后卡片位置稳定：
    - 紧急任务（无论是否完成）置顶，同一优先级内按日期升序；
    - 按日期升序自然把逾期（日期较早）的任务排到前面。
    """
    urgent = safe_enum_val(i.urgency) == "urgent"
    return (
        0 if urgent else 1,
        i.date,
    )


@router.get("/api/teacher/schedules/overdue", response_model=list[ScheduleOut])
def list_overdue_schedules(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """逾期未完成任务提醒：所有已过期且未完成的任务，紧急优先、按日期升序。"""
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    today = date.today()
    items = db.query(TeacherSchedule).filter(
        TeacherSchedule.teacher_id == user.id,
        TeacherSchedule.date < today,
        TeacherSchedule.completed.is_(False),
    ).all()
    items.sort(key=lambda i: (0 if safe_enum_val(i.urgency) == "urgent" else 1, i.date))
    return [_schedule_out(i) for i in items]


@router.get("/api/teacher/schedules", response_model=list[ScheduleOut])
def list_schedules(
    year: int = Query(...),
    month: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    items = db.query(TeacherSchedule).filter(
        TeacherSchedule.teacher_id == user.id,
        safunc.extract("year", TeacherSchedule.date) == year,
        safunc.extract("month", TeacherSchedule.date) == month,
    ).all()
    today = date.today()
    items.sort(key=lambda i: _schedule_sort_key(i, today))
    return [_schedule_out(i) for i in items]


@router.post("/api/teacher/schedules", response_model=ScheduleOut)
def create_schedule(
    body: ScheduleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    try:
        d = date.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(400, "日期格式错误")
    urgency = body.urgency if body.urgency in ("normal", "important", "urgent") else "normal"
    item = TeacherSchedule(teacher_id=user.id, date=d, content=body.content, urgency=UrgencyLevel(urgency))
    db.add(item)
    db.commit()
    db.refresh(item)
    return _schedule_out(item)


@router.patch("/api/teacher/schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule_status(
    schedule_id: int,
    body: ScheduleUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """标记任务完成/取消完成。完成时记录 completed_at，取消完成时清空。"""
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    item = db.query(TeacherSchedule).filter(
        TeacherSchedule.id == schedule_id,
        TeacherSchedule.teacher_id == user.id,
    ).first()
    if not item:
        raise HTTPException(404, "日程不存在")
    item.completed = body.completed
    item.completed_at = datetime.now(timezone.utc) if body.completed else None
    db.commit()
    db.refresh(item)
    return _schedule_out(item)


@router.delete("/api/teacher/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    item = db.query(TeacherSchedule).filter(
        TeacherSchedule.id == schedule_id,
        TeacherSchedule.teacher_id == user.id,
    ).first()
    if not item:
        raise HTTPException(404, "日程不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}
