"""社交关系接口：关注 / 粉丝 / 好友（互关）/ 论坛互动消息

产品口径（2026-10 改版）：
- 「好友」不再是独立概念，**互相关注即好友**；关注是单向的，可以只关注不回关；
- 论坛互动消息与聊天消息分离：本模块的 /forum-messages 只服务「交流社区」页的
  互动消息（赞 / 收藏 / 评论 / 新粉丝），聊天依旧走 /api/messages 与 /api/groups；
- 论坛、个人主页、消息页通讯录共用同一套关注关系（user_follows）。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.social import Follow, ForumMessage, ForumMessageKind
from app.models.user import User
from app.services import social_service

router = APIRouter(prefix="/api/social", tags=["社交关系"])

KINDS = (ForumMessageKind.COMMENT, ForumMessageKind.LIKE, ForumMessageKind.FAVORITE, ForumMessageKind.FOLLOW)


# ==================== 输出模型 ====================

class SocialUserOut(BaseModel):
    """通讯录 / 搜索结果里的一行用户：附带与我的关系，前端据此决定按钮语义。"""

    id: int
    name: str
    username: str
    avatar: str | None = None
    role: str
    college: str | None = None
    class_name: str | None = None
    title: str | None = None
    signature: str | None = None
    is_following: bool = False
    is_follower: bool = False
    is_friend: bool = False
    followed_at: datetime | None = None


class FollowStateOut(BaseModel):
    """关注 / 取关后的最新关系与计数，前端直接覆盖本地状态即可。"""

    user_id: int
    is_following: bool
    is_follower: bool
    is_friend: bool
    following: int
    followers: int
    friends: int


class ForumMessageOut(BaseModel):
    id: int
    kind: str
    actor_id: int
    actor_name: str
    actor_avatar: str | None = None
    post_id: int | None = None
    post_title: str = ""
    content: str = ""
    is_read: bool = False
    created_at: datetime


class ForumUnreadOut(BaseModel):
    total: int = 0
    comment: int = 0
    like: int = 0
    favorite: int = 0
    follow: int = 0


# ==================== 内部工具 ====================

def _target(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    return target


def _user_out(db: Session, viewer: User, target: User, followed_at: datetime | None = None) -> SocialUserOut:
    following = social_service.is_following(db, viewer.id, target.id)
    follower = social_service.is_following(db, target.id, viewer.id)
    return SocialUserOut(
        id=target.id,
        name=target.name,
        username=target.username,
        avatar=target.avatar,
        role=target.role.value if hasattr(target.role, "value") else str(target.role),
        college=target.college,
        class_name=target.class_name,
        title=target.title,
        signature=target.signature,
        is_following=following,
        is_follower=follower,
        is_friend=following and follower,
        followed_at=followed_at,
    )


def _state_out(db: Session, viewer: User, target_id: int) -> FollowStateOut:
    rel = social_service.relation(db, viewer.id, target_id)
    return FollowStateOut(
        user_id=target_id,
        is_following=rel["is_following"],
        is_follower=rel["is_follower"],
        is_friend=rel["is_friend"],
        following=rel["following"],
        followers=rel["followers"],
        friends=rel["friends"],
    )


def _follow_rows(db: Session, viewer: User, sql_rows: list[tuple[User, datetime | None]]) -> list[SocialUserOut]:
    """批量打关系标记：一次取双向我关注/粉丝集合，避免逐行两次查询。"""
    my_following = {r for (r,) in db.query(Follow.followee_id).filter(Follow.follower_id == viewer.id)}
    my_followers = {r for (r,) in db.query(Follow.follower_id).filter(Follow.followee_id == viewer.id)}
    out: list[SocialUserOut] = []
    for target, followed_at in sql_rows:
        following = target.id in my_following
        follower = target.id in my_followers
        out.append(SocialUserOut(
            id=target.id,
            name=target.name,
            username=target.username,
            avatar=target.avatar,
            role=target.role.value if hasattr(target.role, "value") else str(target.role),
            college=target.college,
            class_name=target.class_name,
            title=target.title,
            signature=target.signature,
            is_following=following,
            is_follower=follower,
            is_friend=following and follower,
            followed_at=followed_at,
        ))
    return out


# ==================== 关注 / 取关 ====================

@router.post("/follow/{user_id}", response_model=FollowStateOut)
def follow_user(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """关注某人（幂等）：已关注时直接返回当前状态，不重复写边。

    关注会写一条论坛互动消息给对方——「谁关注了我」属于互动流，
    与聊天消息分开统计，避免新增粉丝把消息页的聊天红点刷乱。
    """
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    target = _target(db, user_id)
    exists = db.query(Follow).filter(
        Follow.follower_id == user.id, Follow.followee_id == user_id
    ).first()
    if not exists:
        db.add(Follow(follower_id=user.id, followee_id=user_id))
        social_service.push_forum_message(
            db, user_id=target.id, actor=user, kind=ForumMessageKind.FOLLOW
        )
        db.commit()
    return _state_out(db, user, user_id)


@router.delete("/follow/{user_id}", response_model=FollowStateOut)
def unfollow_user(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """取消关注（幂等）：只删「我 → TA」这条边，对方对我的关注不受影响。"""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="不能取消关注自己")
    _target(db, user_id)
    row = db.query(Follow).filter(
        Follow.follower_id == user.id, Follow.followee_id == user_id
    ).first()
    if row:
        db.delete(row)
        # 同时撤掉当初那条「关注了你」的互动消息：取消关注后不该还挂着提醒
        db.query(ForumMessage).filter(
            ForumMessage.user_id == user_id,
            ForumMessage.actor_id == user.id,
            ForumMessage.kind == ForumMessageKind.FOLLOW,
            ForumMessage.is_read.is_(False),
        ).delete(synchronize_session=False)
        db.commit()
    return _state_out(db, user, user_id)


@router.get("/relation/{user_id}", response_model=FollowStateOut)
def get_relation(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _target(db, user_id)
    return _state_out(db, user, user_id)


@router.get("/stats", response_model=FollowStateOut)
def my_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的关注 / 粉丝 / 好友计数（消息页通讯录顶部三个数字）。"""
    return _state_out(db, user, user.id)


# ==================== 通讯录列表 ====================

def _rows_with_time(db: Session, ids_query) -> list[tuple[User, datetime | None]]:
    """把「关注边查询」拼成 (User, 关注时间) 列表，按关注时间倒序。

    好友 / 搜索 / 推荐没有「关注我的时间」这一说，时间位传 None。
    """
    rows = ids_query.all()
    if not rows:
        return []
    ids = [uid for uid, _ in rows]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()}
    return [(users[uid], ts) for uid, ts in rows if uid in users]


@router.get("/following", response_model=list[SocialUserOut])
def list_following(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我关注的人（含单向关注，不一定回关）。"""
    rows = _rows_with_time(
        db,
        db.query(Follow.followee_id, Follow.created_at)
        .filter(Follow.follower_id == user.id)
        .order_by(Follow.created_at.desc()),
    )
    return _follow_rows(db, user, rows)


@router.get("/followers", response_model=list[SocialUserOut])
def list_followers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """关注我的人（粉丝）。"""
    rows = _rows_with_time(
        db,
        db.query(Follow.follower_id, Follow.created_at)
        .filter(Follow.followee_id == user.id)
        .order_by(Follow.created_at.desc()),
    )
    return _follow_rows(db, user, rows)


@router.get("/friends", response_model=list[SocialUserOut])
def list_friends(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """互关好友：双向关注才出现在这里，也是「发起群聊」的默认候选人。"""
    ids = social_service.friend_ids(db, user.id)
    if not ids:
        return []
    users = db.query(User).filter(User.id.in_(ids)).order_by(User.name.asc()).all()
    return _follow_rows(db, user, [(u, None) for u in users])


@router.get("/users/search", response_model=list[SocialUserOut])
def search_users(
    keyword: str = Query("", max_length=50),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按姓名 / 学工号搜同学与老师（排除自己与管理员）。"""
    kw = keyword.strip()
    query = db.query(User).filter(User.id != user.id, User.role != "admin")
    if kw:
        like = f"%{kw}%"
        query = query.filter(or_(User.name.like(like), User.username.like(like)))
    users = query.order_by(User.name.asc()).limit(limit).all()
    return _follow_rows(db, user, [(u, None) for u in users])


@router.get("/suggestions", response_model=list[SocialUserOut])
def follow_suggestions(
    limit: int = Query(10, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """可能认识的人：同班 / 同学院优先，已关注的不再推荐。"""
    followed = {r for (r,) in db.query(Follow.followee_id).filter(Follow.follower_id == user.id)}
    query = db.query(User).filter(User.id != user.id, User.role != "admin")
    if followed:
        query = query.filter(User.id.notin_(followed))
    candidates = query.order_by(User.role.asc(), User.name.asc()).limit(80).all()

    def _score(u: User) -> int:
        score = 0
        if user.class_name and u.class_name == user.class_name:
            score += 3
        if user.college and u.college == user.college:
            score += 2
        if user.tutor_id and u.id == user.tutor_id:
            score += 4
        if u.role == user.role:
            score += 1
        return score

    ranked = sorted(candidates, key=_score, reverse=True)[:limit]
    return _follow_rows(db, user, [(u, None) for u in ranked])


# ==================== 论坛互动消息（与聊天隔离） ====================

def _forum_out(db: Session, rows: list[ForumMessage]) -> list[ForumMessageOut]:
    actor_ids = {m.actor_id for m in rows}
    actors = {
        u.id: u for u in db.query(User).filter(User.id.in_(actor_ids)).all()
    } if actor_ids else {}
    out: list[ForumMessageOut] = []
    for m in rows:
        actor = actors.get(m.actor_id)
        out.append(ForumMessageOut(
            id=m.id,
            kind=m.kind,
            actor_id=m.actor_id,
            actor_name=actor.name if actor else "同学",
            actor_avatar=actor.avatar if actor else None,
            post_id=m.post_id,
            post_title=m.post_title or "",
            content=m.content or "",
            is_read=bool(m.is_read),
            created_at=m.created_at,
        ))
    return out


@router.get("/forum-messages", response_model=list[ForumMessageOut])
def list_forum_messages(
    kind: str | None = Query(None, description="comment / like / favorite / follow，留空为全部"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """论坛互动消息流：评论 / 点赞 / 收藏 / 新粉丝，与聊天记录完全分开。"""
    query = db.query(ForumMessage).filter(ForumMessage.user_id == user.id)
    if kind in KINDS:
        query = query.filter(ForumMessage.kind == kind)
    rows = (
        query.order_by(ForumMessage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return _forum_out(db, rows)


@router.get("/forum-messages/unread", response_model=ForumUnreadOut)
def forum_unread(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """互动未读（按类型拆分）：交流社区页互动消息的红点与分类角标都用它。"""
    rows = db.query(ForumMessage.kind, ForumMessage.id).filter(
        ForumMessage.user_id == user.id, ForumMessage.is_read.is_(False)
    ).all()
    result = ForumUnreadOut()
    for kind, _ in rows:
        result.total += 1
        if kind == ForumMessageKind.COMMENT:
            result.comment += 1
        elif kind == ForumMessageKind.LIKE:
            result.like += 1
        elif kind == ForumMessageKind.FAVORITE:
            result.favorite += 1
        elif kind == ForumMessageKind.FOLLOW:
            result.follow += 1
    return result


@router.post("/forum-messages/{message_id}/read")
def read_forum_message(message_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msg = db.query(ForumMessage).filter(
        ForumMessage.id == message_id, ForumMessage.user_id == user.id
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    msg.is_read = True
    db.commit()
    return {"message": "ok"}


@router.post("/forum-messages/read-all")
def read_all_forum_messages(
    kind: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ForumMessage).filter(
        ForumMessage.user_id == user.id, ForumMessage.is_read.is_(False)
    )
    if kind in KINDS:
        query = query.filter(ForumMessage.kind == kind)
    count = query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"message": "ok", "count": int(count or 0)}
