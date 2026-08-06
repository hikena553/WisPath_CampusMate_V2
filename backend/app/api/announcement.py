import os
import uuid
from pathlib import Path
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as safunc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.announcement import TeacherAnnouncement, AnnouncementRead, UrgencyLevel, TeacherSchedule
from app.schemas.announcement import AnnouncementOut, UnreadCountOut, ScheduleOut, ScheduleCreate
from app.utils.enum_helpers import safe_enum_val

router = APIRouter(tags=["announcement"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "announcements"


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
    result = []
    for a in items:
        result.append(AnnouncementOut(
            id=a.id, teacher_id=a.teacher_id, teacher_name=user.name,
            title=a.title, content=a.content, urgency=safe_enum_val(a.urgency),
            attachment_url=a.attachment_url, created_at=a.created_at,
        ))
    return result


@router.post("/api/teacher/announcements", response_model=AnnouncementOut)
async def create_announcement(
    title: str = Form(...),
    content: str = Form(...),
    urgency: str = Form("normal"),
    file: UploadFile | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(403)
    if urgency not in ("normal", "important", "urgent"):
        urgency = "normal"
    attachment_url = None
    if file:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = Path(file.filename).suffix.lower() if file.filename else ""
        save_name = f"{uuid.uuid4().hex}{ext}"
        save_path = UPLOAD_DIR / save_name
        content_bytes = await file.read()
        with open(save_path, "wb") as f:
            f.write(content_bytes)
        attachment_url = f"/uploads/announcements/{save_name}"
    item = TeacherAnnouncement(
        teacher_id=user.id, title=title, content=content,
        urgency=UrgencyLevel(urgency), attachment_url=attachment_url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return AnnouncementOut(
        id=item.id, teacher_id=item.teacher_id, teacher_name=user.name,
        title=item.title, content=item.content,
        urgency=safe_enum_val(item.urgency),
        attachment_url=item.attachment_url, created_at=item.created_at,
    )


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
    if unread_only:
        read_ids = db.query(AnnouncementRead.announcement_id).filter(
            AnnouncementRead.student_id == user.id
        ).subquery()
        query = query.filter(~TeacherAnnouncement.id.in_(read_ids))
    items = query.order_by(TeacherAnnouncement.created_at.desc()).all()
    result = []
    for a in items:
        result.append(AnnouncementOut(
            id=a.id, teacher_id=a.teacher_id, teacher_name=tutor_name,
            title=a.title, content=a.content,
            urgency=safe_enum_val(a.urgency),
            attachment_url=a.attachment_url, created_at=a.created_at,
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
    read_ids = db.query(AnnouncementRead.announcement_id).filter(
        AnnouncementRead.student_id == user.id
    ).subquery()
    count = db.query(TeacherAnnouncement).filter(
        TeacherAnnouncement.teacher_id == user.tutor_id,
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
    existing = db.query(AnnouncementRead).filter(
        AnnouncementRead.student_id == user.id,
        AnnouncementRead.announcement_id == announcement_id,
    ).first()
    if not existing:
        db.add(AnnouncementRead(student_id=user.id, announcement_id=announcement_id))
        db.commit()
    return {"ok": True}


# ── Teacher Schedule endpoints ──

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
    ).order_by(TeacherSchedule.date).all()
    return [ScheduleOut(id=i.id, date=str(i.date), content=i.content) for i in items]


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
    item = TeacherSchedule(teacher_id=user.id, date=d, content=body.content)
    db.add(item)
    db.commit()
    db.refresh(item)
    return ScheduleOut(id=item.id, date=str(item.date), content=item.content)


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
