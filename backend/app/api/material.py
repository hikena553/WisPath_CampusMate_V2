"""材料档案：学生上传并归档个人材料（证件/证明/成绩单/学籍等）。"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.material import MaterialArchive, MaterialStatus
from app.models.notification import NotificationType

router = APIRouter(prefix="/api/materials", tags=["材料档案"])

CATEGORY_LABELS = {
    "identity": "证件",
    "statement": "证明",
    "grade": "成绩单",
    "register": "学籍",
    "other": "其他",
}


class MaterialCreate(BaseModel):
    title: str
    category: str = "other"
    file_url: str
    file_name: str = ""
    file_type: str = ""
    remark: Optional[str] = None


class MaterialReview(BaseModel):
    action: str
    reject_reason: Optional[str] = None


def _out(m: MaterialArchive):
    return {
        "id": m.id,
        "student_id": m.student_id,
        "title": m.title,
        "category": m.category.value if hasattr(m.category, "value") else m.category,
        "category_label": CATEGORY_LABELS.get(m.category.value if hasattr(m.category, "value") else m.category, "其他"),
        "file_url": m.file_url,
        "file_name": m.file_name,
        "file_type": m.file_type,
        "remark": m.remark,
        "status": m.status.value if hasattr(m.status, "value") else m.status,
        "reject_reason": m.reject_reason,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }


@router.post("")
def create_material(req: MaterialCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not req.title.strip():
        raise HTTPException(400, "材料标题不能为空")
    if not req.file_url.strip():
        raise HTTPException(400, "请先上传材料文件")
    m = MaterialArchive(
        student_id=user.id,
        title=req.title.strip(),
        category=req.category if req.category in CATEGORY_LABELS else "other",
        file_url=req.file_url,
        file_name=req.file_name,
        file_type=req.file_type,
        remark=req.remark,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    # 通知学生辅导员有新的材料待归档
    if user.tutor_id:
        from app.services.notification_service import send_notification
        send_notification(
            db, user.tutor_id,
            title="新的材料待归档",
            content=f"学生 {user.name} 上传了材料「{m.title}」，请审核归档。",
            notification_type=NotificationType.APPROVAL,
            link="/teacher/approval",
            related_id=m.id,
            sender_id=user.id,
            sms_template="新材料归档提醒",
        )
    return _out(m)


@router.get("")
def list_materials(status: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(MaterialArchive).filter(MaterialArchive.student_id == user.id)
    if status:
        q = q.filter(MaterialArchive.status == status)
    return [_out(m) for m in q.order_by(MaterialArchive.created_at.desc()).all()]


@router.get("/{material_id}")
def get_material(material_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(MaterialArchive).filter(MaterialArchive.id == material_id).first()
    if not m:
        raise HTTPException(404, "材料不存在")
    if m.student_id != user.id:
        if user.role == UserRole.ADMIN:
            pass
        elif user.role == UserRole.TEACHER:
            student = db.query(User).filter(User.id == m.student_id).first()
            if not student or student.tutor_id != user.id:
                raise HTTPException(403, "无权查看该材料")
        else:
            raise HTTPException(403, "无权查看该材料")
    return _out(m)


@router.delete("/{material_id}")
def delete_material(material_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(MaterialArchive).filter(MaterialArchive.id == material_id, MaterialArchive.student_id == user.id).first()
    if not m:
        raise HTTPException(404, "材料不存在或无权删除")
    db.delete(m)
    db.commit()
    return {"message": "已删除"}