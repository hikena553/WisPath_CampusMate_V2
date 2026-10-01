"""反馈管理 API：仅负责 HTTP 语义（鉴权/参数/响应），业务逻辑下沉 services。"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackOut, FeedbackReply, FeedbackWordOut
from app.services import feedback_service

router = APIRouter(prefix="/api/feedbacks", tags=["反馈管理"])


@router.post("", response_model=FeedbackOut)
def create_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交反馈"""
    return feedback_service.create_feedback(db, current_user, data)


@router.get("", response_model=List[FeedbackOut])
def get_feedbacks(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取反馈列表"""
    return feedback_service.list_feedbacks(db, current_user, status, type, page, page_size)


@router.get("/word-cloud", response_model=List[FeedbackWordOut])
def get_feedback_word_cloud(
    top_n: int = Query(60, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """反馈关键词词云统计（管理员可见全部，普通用户仅自己）"""
    return feedback_service.get_feedback_word_cloud(db, current_user, top_n)


@router.get("/{feedback_id}", response_model=FeedbackOut)
def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取反馈详情"""
    return feedback_service.get_feedback_detail(db, current_user, feedback_id)


@router.put("/{feedback_id}/reply", response_model=FeedbackOut)
def reply_feedback(
    feedback_id: int,
    data: FeedbackReply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """回复反馈（仅管理员）"""
    return feedback_service.reply_feedback(db, current_user, feedback_id, data)