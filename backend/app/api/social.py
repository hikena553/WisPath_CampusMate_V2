"""社交模块 API：关注关系 / 通讯录 / 论坛互动消息

共性口径全部落在 app/services/social_service.py，这里只做参数校验与响应组装，
避免消息页、个人主页、勋章各自算一套关注关系。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.social import ForumMessage, ForumMessageKind
from app.models.user import User
from app.schemas.social import (
    ContactOut,
    ForumMessageOut,
    ForumReadIn,
    RelationOut,
    SuggestOut,
)
from app.services import social_service

router = APIRouter(prefix="/api/social", tags=["社交"])

CONTACT_TABS = {"following", "followers", "friends"}


def _user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    return user


# ==================== 关注关系 ====================

@router.get("/relation/{user_id}", response_model=RelationOut)
def get_relation(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _user_or_404(db, user_id)
    return social_service.relation(db, current_user.id, user_id)


@router.post("/follow/{user_id}", response_model=RelationOut)
def follow_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id == current_user.id:
        raise HTTPException(400, "不能关注自己")
    target = _user_or_404(db, user_id)
    return social_service.follow(db, current_user, target.id)


@router.delete("/follow/{user_id}", response_model=RelationOut)
def unfollow_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id == current_user.id:
        raise HTTPException(400, "不能取关自己")
    _user_or_404(db, user_id)
    return social_service.unfollow(db, current_user, user_id)


# ==================== 通讯录 ====================

@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    tab: str = Query("friends", description="following=我关注的 followers=关注我的 friends=互关好友"),
    keyword: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if tab not in CONTACT_TABS:
        raise HTTPException(400, "无法识别的通讯录页签")
    return social_service.contact_list(db, current_user, tab=tab, keyword=keyword, limit=limit)


@router.get("/suggestions", response_model=list[SuggestOut])
def list_suggestions(
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return social_service.suggestions(db, current_user, limit=limit)


# ==================== 论坛互动消息 ====================

@router.get("/forum-messages", response_model=list[ForumMessageOut])
def list_forum_messages(
    kind: str | None = Query(None, description="like/favorite/comment/follow，为空表示全部"),
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parsed: ForumMessageKind | None = None
    if kind:
        try:
            parsed = ForumMessageKind(kind)
        except ValueError:
            raise HTTPException(400, "无法识别的互动类型")
    rows = social_service.forum_messages(
        db, current_user.id, kind=parsed, unread_only=unread_only, limit=limit, offset=offset
    )
    actors = social_service.actors_map(db, rows)
    result = []
    for row in rows:
        out = ForumMessageOut.model_validate(row)
        out.kind = row.kind.value if hasattr(row.kind, "value") else str(row.kind)
        actor = actors.get(row.actor_id)
        out.actor_name = actor.name if actor else "已注销用户"
        out.actor_avatar = actor.avatar if actor else None
        result.append(out)
    return result


@router.put("/forum-messages/read")
def mark_forum_read(
    payload: ForumReadIn | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ids = payload.ids if payload else None
    return {"updated": social_service.mark_forum_read(db, current_user.id, ids=ids)}


@router.get("/forum-messages/unread-count")
def forum_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total = db.query(ForumMessage).filter(
        ForumMessage.user_id == current_user.id, ForumMessage.is_read.is_(False)
    ).count()
    return {"count": int(total)}
