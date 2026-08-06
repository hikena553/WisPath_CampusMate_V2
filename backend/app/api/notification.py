from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.notification import Notification, NotificationType

router = APIRouter(prefix="/api/notifications", tags=["通知管理"])


# ===== Schemas =====
class NotificationOut(BaseModel):
    id: int
    title: str
    content: str
    type: str
    is_read: bool
    link: Optional[str] = None
    related_id: Optional[int] = None
    sender_name: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class NotificationCount(BaseModel):
    total: int
    unread: int


class MarkReadRequest(BaseModel):
    notification_ids: List[int] = []


# ===== Endpoints =====
@router.get("", response_model=List[NotificationOut])
def get_notifications(
    is_read: Optional[bool] = None,
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的通知列表"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    if type:
        query = query.filter(Notification.type == type)
    
    total = query.count()
    notifications = query.order_by(desc(Notification.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for n in notifications:
        sender_name = None
        if n.sender_id:
            sender = db.query(User).filter(User.id == n.sender_id).first()
            sender_name = sender.name if sender else None
        
        result.append(NotificationOut(
            id=n.id,
            title=n.title,
            content=n.content,
            type=n.type.value if n.type else "system",
            is_read=n.is_read,
            link=n.link,
            related_id=n.related_id,
            sender_name=sender_name,
            created_at=n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else ""
        ))
    
    return result


@router.get("/count", response_model=NotificationCount)
def get_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取通知数量统计"""
    total = db.query(Notification).filter(Notification.user_id == current_user.id).count()
    unread = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return NotificationCount(total=total, unread=unread)


@router.put("/read")
def mark_notifications_read(
    request: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记通知为已读"""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    
    if request.notification_ids:
        query = query.filter(Notification.id.in_(request.notification_ids))
    
    notifications = query.all()
    for n in notifications:
        n.is_read = True
    
    db.commit()
    return {"message": f"已标记 {len(notifications)} 条通知为已读"}


@router.put("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记所有通知为已读"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    return {"message": f"已标记 {count} 条通知为已读"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除通知"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    
    db.delete(notification)
    db.commit()
    return {"message": "通知已删除"}


# ===== 内部工具函数 =====
def create_notification(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    notification_type: NotificationType = NotificationType.SYSTEM,
    link: str = None,
    related_id: int = None,
    sender_id: int = None
):
    """创建通知（供其他模块调用）"""
    notification = Notification(
        user_id=user_id,
        title=title,
        content=content,
        type=notification_type,
        link=link,
        related_id=related_id,
        sender_id=sender_id
    )
    db.add(notification)
    db.commit()
    return notification


def create_batch_notifications(
    db: Session,
    user_ids: List[int],
    title: str,
    content: str,
    notification_type: NotificationType = NotificationType.SYSTEM,
    link: str = None,
    related_id: int = None,
    sender_id: int = None
):
    """批量创建通知"""
    notifications = []
    for user_id in user_ids:
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=notification_type,
            link=link,
            related_id=related_id,
            sender_id=sender_id
        )
        db.add(notification)
        notifications.append(notification)
    
    db.commit()
    return notifications
