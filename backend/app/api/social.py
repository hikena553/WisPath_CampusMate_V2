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
    FriendSettingIn,
    FriendSettingOut,
    FriendSettingState,
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
    covers = social_service.post_covers_map(db, rows)
    result = []
    for row in rows:
        out = ForumMessageOut.model_validate(row)
        out.kind = row.kind.value if hasattr(row.kind, "value") else str(row.kind)
        actor = actors.get(row.actor_id)
        out.actor_name = actor.name if actor else "已注销用户"
        out.actor_avatar = actor.avatar if actor else None
        # 帖子可能已被删除：此时封面为空，标题仍用消息里的快照
        out.post_cover = covers.get(row.post_id) if row.post_id else None
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


# ==================== 好友设置（个人主页「设置」页） ====================

@router.get("/friend-settings", response_model=list[FriendSettingOut])
def list_friend_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我设过的全部联系人：消息列表按 care 给「特别关心」挂标，设置页回填各开关。"""
    return social_service.friend_settings_all(db, current_user.id)


@router.get("/friend-settings/{peer_id}", response_model=FriendSettingState)
def get_friend_setting(
    peer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我 → TA 与 TA → 我两份设置。亲密关系是双方共用展示的标识，所以两份都给。"""
    if peer_id == current_user.id:
        raise HTTPException(400, "不能对自己设置好友项")
    _user_or_404(db, peer_id)
    return social_service.friend_setting_state(db, current_user.id, peer_id)


@router.put("/friend-settings/{peer_id}", response_model=FriendSettingState)
def update_friend_setting(
    peer_id: int,
    payload: FriendSettingIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """局部更新：只传改动的字段，其余保持原值。设置自己的那一条，不碰对方。"""
    if peer_id == current_user.id:
        raise HTTPException(400, "不能对自己设置好友项")
    _user_or_404(db, peer_id)
    patch = payload.model_dump(exclude_unset=True)
    try:
        social_service.save_friend_setting(db, current_user.id, peer_id, patch)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return social_service.friend_setting_state(db, current_user.id, peer_id)
