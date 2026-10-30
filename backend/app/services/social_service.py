"""社交关系（关注 / 粉丝 / 互关好友）与论坛互动消息的统一服务层。

- 关注口径唯一实现：消息页通讯录、个人主页、勋章 metrics.contacts 全部走这里，
  避免同一个人在不同页面显示成不同关系；
- 论坛互动消息（forum_messages）与聊天消息（messages）分表，写入口只有
  push_forum_message 一处，保证自赞/自评不打扰自己。
"""
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.social import Follow, ForumMessage, ForumMessageKind
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _role_value(user: User | None) -> str:
    if user is None:
        return ""
    return user.role.value if hasattr(user.role, "value") else str(user.role or "")


def is_following(db: Session, follower_id: int, target_id: int) -> bool:
    """follower_id 是否关注了 target_id"""
    return (
        db.query(Follow.id)
        .filter(Follow.follower_id == follower_id, Follow.following_id == target_id)
        .first()
        is not None
    )


def friend_ids(db: Session, user_id: int) -> set[int]:
    """互关好友集合（好友 = 互相关注）"""
    following = {row[0] for row in db.query(Follow.following_id).filter(Follow.follower_id == user_id)}
    followers = {row[0] for row in db.query(Follow.follower_id).filter(Follow.following_id == user_id)}
    return following & followers


def counts(db: Session, user_id: int) -> dict[str, int]:
    """三公开计数：关注 / 粉丝 / 好友（互关）"""
    following = db.query(func.count(Follow.id)).filter(Follow.follower_id == user_id).scalar() or 0
    followers = db.query(func.count(Follow.id)).filter(Follow.following_id == user_id).scalar() or 0
    return {
        "following": int(following),
        "followers": int(followers),
        "friends": len(friend_ids(db, user_id)),
    }


def relation(db: Session, viewer_id: int, target_id: int) -> dict:
    """双方关系 + 目标用户的三项计数（主页数字区与关注按钮共用这一份结果）"""
    state: dict = {
        "is_following": False,
        "is_follower": False,
        "is_friend": False,
        "following": 0,
        "followers": 0,
        "friends": 0,
    }
    if not viewer_id or not target_id:
        return state
    state.update(counts(db, target_id))
    if viewer_id == target_id:
        return state
    forward = is_following(db, viewer_id, target_id)
    backward = is_following(db, target_id, viewer_id)
    state["is_following"] = forward
    state["is_follower"] = backward
    state["is_friend"] = forward and backward
    return state


def push_forum_message(
    db: Session,
    user_id: int,
    actor: User,
    kind: ForumMessageKind,
    post_id: int | None = None,
    post_title: str | None = None,
    content: str | None = None,
) -> ForumMessage | None:
    """写入一条论坛互动消息。自己触发自己的互动不打扰（返回 None）。

    不 commit：调用方（community.py 的点赞/收藏/评论）本来就在同一事务里统一提交。
    """
    if not user_id or actor is None or actor.id == user_id:
        return None
    msg = ForumMessage(
        user_id=user_id,
        actor_id=actor.id,
        kind=kind,
        post_id=post_id,
        post_title=(post_title or None) and post_title[:200],
        content=(content or None) and content[:500],
    )
    db.add(msg)
    db.flush()
    return msg


def follow(db: Session, follower: User, target_id: int) -> dict:
    """关注（幂等）：已关注不重复写，重复调用只返回最新关系"""
    exists = db.query(Follow).filter(
        Follow.follower_id == follower.id, Follow.following_id == target_id
    ).first()
    if not exists:
        db.add(Follow(follower_id=follower.id, following_id=target_id))
        db.commit()
        # 新粉丝消息：先落库再推消息（同一事务里 commit 一次）
        push_forum_message(
            db,
            user_id=target_id,
            actor=follower,
            kind=ForumMessageKind.FOLLOW,
            content=f"{follower.name} 关注了你",
        )
        db.commit()
    return relation(db, follower.id, target_id)


def unfollow(db: Session, follower: User, target_id: int) -> dict:
    """取消关注：同时撤回还没读的「新粉丝」消息（对方已反悔，作者不该再看到）"""
    deleted = db.query(Follow).filter(
        Follow.follower_id == follower.id, Follow.following_id == target_id
    ).delete(synchronize_session=False)
    if deleted:
        db.query(ForumMessage).filter(
            ForumMessage.user_id == target_id,
            ForumMessage.actor_id == follower.id,
            ForumMessage.kind == ForumMessageKind.FOLLOW,
            ForumMessage.is_read.is_(False),
        ).delete(synchronize_session=False)
        db.commit()
    return relation(db, follower.id, target_id)


def forum_messages(
    db: Session,
    user_id: int,
    kind: ForumMessageKind | None = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[ForumMessage]:
    query = db.query(ForumMessage).filter(ForumMessage.user_id == user_id)
    if kind is not None:
        query = query.filter(ForumMessage.kind == kind)
    if unread_only:
        query = query.filter(ForumMessage.is_read.is_(False))
    return (
        query.order_by(ForumMessage.created_at.desc())
        .offset(max(offset, 0))
        .limit(max(1, min(limit, 100)))
        .all()
    )


def mark_forum_read(db: Session, user_id: int, ids: list[int] | None = None) -> int:
    """标记已读；ids 为空表示全部已读"""
    query = db.query(ForumMessage).filter(
        ForumMessage.user_id == user_id, ForumMessage.is_read.is_(False)
    )
    if ids:
        query = query.filter(ForumMessage.id.in_(ids))
    updated = query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    return int(updated or 0)


def actors_map(db: Session, messages: list[ForumMessage]) -> dict[int, User]:
    if not messages:
        return {}
    ids = {m.actor_id for m in messages}
    return {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()}


def contact_list(
    db: Session,
    viewer: User,
    tab: str = "friends",
    keyword: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """通讯录：关注 / 粉丝 / 好友（互关）三页签，附带双方关系标记"""
    if tab == "following":
        ids = [row[0] for row in db.query(Follow.following_id).filter(Follow.follower_id == viewer.id)]
    elif tab == "followers":
        ids = [row[0] for row in db.query(Follow.follower_id).filter(Follow.following_id == viewer.id)]
    else:
        ids = list(friend_ids(db, viewer.id))
    if not ids:
        return []
    query = db.query(User).filter(User.id.in_(ids))
    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        query = query.filter(
            (User.name.like(like)) | (User.username.like(like)) | (User.class_name.like(like))
        )
    users = query.limit(max(1, min(limit, 500))).all()
    relation_cache = {u.id: relation(db, viewer.id, u.id) for u in users}
    return [
        {
            "id": u.id,
            "name": u.name,
            "username": u.username,
            "avatar": u.avatar,
            "role": _role_value(u),
            "college": u.college,
            "class_name": u.class_name,
            "signature": u.signature,
            "is_following": relation_cache[u.id]["is_following"],
            "is_follower": relation_cache[u.id]["is_follower"],
            "is_friend": relation_cache[u.id]["is_friend"],
        }
        for u in users
    ]


def suggestions(db: Session, viewer: User, limit: int = 10) -> list[dict]:
    """推荐关注：同学院优先，排除自己与已关注的人"""
    followed = {row[0] for row in db.query(Follow.following_id).filter(Follow.follower_id == viewer.id)}
    query = db.query(User).filter(User.id != viewer.id)
    if followed:
        query = query.filter(User.id.notin_(followed))
    if viewer.college:
        same = query.filter(User.college == viewer.college).limit(limit).all()
        if len(same) >= limit:
            users = same
        else:
            rest = query.filter(User.college != viewer.college).limit(limit - len(same)).all()
            users = same + rest
    else:
        users = query.limit(limit).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "username": u.username,
            "avatar": u.avatar,
            "role": _role_value(u),
            "college": u.college,
            "class_name": u.class_name,
            "signature": u.signature,
        }
        for u in users
    ]
