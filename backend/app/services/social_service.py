"""社交关系服务：关注 / 好友推导 / 论坛互动消息

好友不是独立实体——互相关注即好友。这里集中提供关系查询，
供个人主页（badge_service）、消息页通讯录、论坛互动共用，避免三处各算一套。
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.social import Follow, ForumMessage, ForumMessageKind
from app.models.user import User


def is_following(db: Session, follower_id: int, followee_id: int) -> bool:
    if follower_id == followee_id:
        return False
    return db.query(Follow.id).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == followee_id,
    ).first() is not None


def friend_ids(db: Session, user_id: int) -> set[int]:
    """互关好友 id 集合：我关注的 ∩ 关注我的。"""
    following = {r for (r,) in db.query(Follow.followee_id).filter(Follow.follower_id == user_id)}
    followers = {r for (r,) in db.query(Follow.follower_id).filter(Follow.followee_id == user_id)}
    return following & followers


def counts(db: Session, user_id: int) -> dict[str, int]:
    """关注数 / 粉丝数 / 好友数（好友 = 互关）。"""
    following = db.query(func.count(Follow.id)).filter(Follow.follower_id == user_id).scalar() or 0
    followers = db.query(func.count(Follow.id)).filter(Follow.followee_id == user_id).scalar() or 0
    return {
        "following": int(following),
        "followers": int(followers),
        "friends": len(friend_ids(db, user_id)),
    }


def relation(db: Session, viewer_id: int, target_id: int) -> dict:
    """当前用户与目标用户的关系（个人主页「我们之间」与按钮状态都用它）。"""
    if viewer_id == target_id:
        c = counts(db, target_id)
        return {
            "is_self": True,
            "is_following": False,
            "is_follower": False,
            "is_friend": False,
            **c,
        }
    following = is_following(db, viewer_id, target_id)
    follower = is_following(db, target_id, viewer_id)
    c = counts(db, target_id)
    return {
        "is_self": False,
        "is_following": following,
        "is_follower": follower,
        "is_friend": following and follower,
        **c,
    }


def push_forum_message(
    db: Session,
    *,
    user_id: int,
    actor: User,
    kind: str,
    post_id: int | None = None,
    post_title: str = "",
    content: str = "",
) -> ForumMessage | None:
    """写入一条论坛互动消息（自己的操作不通知自己）。

    只 add 不 commit：与调用方（评论 / 点赞 / 关注）处于同一事务，
    互动成功与通知落库要么一起成功、要么一起回滚。
    """
    if user_id == actor.id:
        return None
    msg = ForumMessage(
        user_id=user_id,
        actor_id=actor.id,
        kind=kind,
        post_id=post_id,
        post_title=(post_title or "")[:200],
        content=content or "",
    )
    db.add(msg)
    return msg


__all__ = [
    "ForumMessageKind",
    "is_following",
    "friend_ids",
    "counts",
    "relation",
    "push_forum_message",
]
