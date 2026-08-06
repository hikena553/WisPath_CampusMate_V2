from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.feedback import Feedback, FeedbackType, FeedbackStatus

router = APIRouter(prefix="/api/feedbacks", tags=["反馈管理"])


# ===== Schemas =====
class FeedbackCreate(BaseModel):
    type: str = "other"
    title: str
    content: str
    contact: Optional[str] = None


class FeedbackReply(BaseModel):
    reply: str
    status: str = "resolved"


class FeedbackOut(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    type: str
    title: str
    content: str
    contact: Optional[str] = None
    status: str
    reply: Optional[str] = None
    replied_by: Optional[int] = None
    replier_name: Optional[str] = None
    replied_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


# ===== Endpoints =====
@router.post("", response_model=FeedbackOut)
def create_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交反馈"""
    feedback = Feedback(
        user_id=current_user.id,
        type=FeedbackType(data.type) if data.type in [t.value for t in FeedbackType] else FeedbackType.OTHER,
        title=data.title,
        content=data.content,
        contact=data.contact
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return FeedbackOut(
        id=feedback.id,
        user_id=feedback.user_id,
        user_name=current_user.name,
        type=feedback.type.value,
        title=feedback.title,
        content=feedback.content,
        contact=feedback.contact,
        status=feedback.status.value,
        created_at=feedback.created_at.strftime("%Y-%m-%d %H:%M:%S") if feedback.created_at else ""
    )


@router.get("", response_model=List[FeedbackOut])
def get_feedbacks(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取反馈列表"""
    query = db.query(Feedback)
    
    # 非管理员只能看自己的反馈
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Feedback.user_id == current_user.id)
    
    if status:
        query = query.filter(Feedback.status == status)
    if type:
        query = query.filter(Feedback.type == type)
    
    feedbacks = query.order_by(desc(Feedback.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for f in feedbacks:
        user = db.query(User).filter(User.id == f.user_id).first()
        replier = db.query(User).filter(User.id == f.replied_by).first() if f.replied_by else None
        
        result.append(FeedbackOut(
            id=f.id,
            user_id=f.user_id,
            user_name=user.name if user else None,
            type=f.type.value if f.type else "other",
            title=f.title,
            content=f.content,
            contact=f.contact,
            status=f.status.value if f.status else "pending",
            reply=f.reply,
            replied_by=f.replied_by,
            replier_name=replier.name if replier else None,
            replied_at=f.replied_at.strftime("%Y-%m-%d %H:%M:%S") if f.replied_at else None,
            created_at=f.created_at.strftime("%Y-%m-%d %H:%M:%S") if f.created_at else ""
        ))
    
    return result


@router.get("/{feedback_id}", response_model=FeedbackOut)
def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取反馈详情"""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    # 非管理员只能看自己的反馈
    if current_user.role != UserRole.ADMIN and feedback.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问")
    
    user = db.query(User).filter(User.id == feedback.user_id).first()
    replier = db.query(User).filter(User.id == feedback.replied_by).first() if feedback.replied_by else None
    
    return FeedbackOut(
        id=feedback.id,
        user_id=feedback.user_id,
        user_name=user.name if user else None,
        type=feedback.type.value if feedback.type else "other",
        title=feedback.title,
        content=feedback.content,
        contact=feedback.contact,
        status=feedback.status.value if feedback.status else "pending",
        reply=feedback.reply,
        replied_by=feedback.replied_by,
        replier_name=replier.name if replier else None,
        replied_at=feedback.replied_at.strftime("%Y-%m-%d %H:%M:%S") if feedback.replied_at else None,
        created_at=feedback.created_at.strftime("%Y-%m-%d %H:%M:%S") if feedback.created_at else ""
    )


@router.put("/{feedback_id}/reply", response_model=FeedbackOut)
def reply_feedback(
    feedback_id: int,
    data: FeedbackReply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """回复反馈（仅管理员）"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可回复")
    
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    feedback.reply = data.reply
    feedback.status = FeedbackStatus(data.status) if data.status in [s.value for s in FeedbackStatus] else FeedbackStatus.RESOLVED
    feedback.replied_by = current_user.id
    feedback.replied_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(feedback)
    
    return FeedbackOut(
        id=feedback.id,
        user_id=feedback.user_id,
        user_name=db.query(User).filter(User.id == feedback.user_id).first().name,
        type=feedback.type.value if feedback.type else "other",
        title=feedback.title,
        content=feedback.content,
        contact=feedback.contact,
        status=feedback.status.value if feedback.status else "pending",
        reply=feedback.reply,
        replied_by=feedback.replied_by,
        replier_name=current_user.name,
        replied_at=feedback.replied_at.strftime("%Y-%m-%d %H:%M:%S") if feedback.replied_at else None,
        created_at=feedback.created_at.strftime("%Y-%m-%d %H:%M:%S") if feedback.created_at else ""
    )
