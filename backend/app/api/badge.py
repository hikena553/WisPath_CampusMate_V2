from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.badge import (
    BadgeSyncOut,
    BadgeWallOut,
    SignatureUpdate,
    UserHomepageOut,
)
from app.services import badge_service

router = APIRouter(prefix="/api/badges", tags=["badges"])


@router.get("/me", response_model=BadgeWallOut)
def my_badge_wall(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的勋章墙：等级 + 已获得 + 未获得（含解锁进度）。"""
    return badge_service.build_wall(db, user)


@router.post("/sync", response_model=BadgeSyncOut)
def sync_badges(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """结算勋章：返回本次新解锁 + 历史上尚未播放动画的勋章（供前端补播奖励动画）。"""
    new_items = badge_service.evaluate_and_award(db, user)
    pending = badge_service.pending_badges(db, user)
    seen = {item["code"] for item in new_items}
    merged = new_items + [item for item in pending if item["code"] not in seen]
    return {"new": merged}


@router.post("/seen")
def mark_seen(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获得动画已播放完毕，清空待播队列。"""
    count = badge_service.mark_all_seen(db, user)
    return {"message": "已读", "count": count}


@router.put("/signature")
def update_signature(
    data: SignatureUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存个性签名（展示在个人中心与个人主页）。"""
    value = badge_service.update_signature(db, user, data.signature)
    return {"signature": value}


@router.get("/user/{user_id}", response_model=BadgeWallOut)
def user_badge_wall(
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """他人勋章墙（消息页点开某人主页时使用）。"""
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    return badge_service.build_wall(db, target)


@router.get("/user/{user_id}/homepage", response_model=UserHomepageOut)
def user_homepage(
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人主页：签名 / 等级 / 勋章 / 角色化数据 / 近期亮点 / 双方关系。"""
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    return badge_service.build_homepage(db, user, target)