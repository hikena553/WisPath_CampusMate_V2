"""社交关系：关注 / 粉丝 / 论坛互动消息

关注是**单向边**（follower → followee），互相关注即「好友」。
好友刻意不做成独立实体：它只是 follow 表上的双向关系推导结果，
因此论坛（帖子评论 / 点赞）、个人主页、消息页通讯录看到的是同一套关系，
不会出现「主页显示是好友、消息页却查不到」的割裂。

论坛互动（评论 / 点赞 / 收藏 / 关注）单独落 forum_messages，与聊天
（messages / group_messages）物理隔离：
- 论坛互动只在「交流社区」页右上角的互动消息里看，消息页只放聊天，两边未读各自统计；
- 论坛消息带有 actor（触发者）与 post 快照，即使原帖被删也仍可展示，
  且点开可回到对应帖子或对方主页。
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    """统一用带时区的 UTC 时间（Python 3.12 起 datetime.utcnow 已弃用）。"""
    return datetime.now(timezone.utc)


class Follow(Base):
    """一条关注关系：follower 关注了 followee（一人对一人只能有一条）"""

    __tablename__ = "user_follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "followee_id", name="uq_user_follow_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    followee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ForumMessageKind:
    """互动类型（用字符串存库，便于后续扩展而不动枚举约束）"""

    COMMENT = "comment"   # 评论了我的帖子
    LIKE = "like"         # 赞了我的帖子
    FAVORITE = "favorite" # 收藏了我的帖子
    FOLLOW = "follow"     # 关注了我


class ForumMessage(Base):
    """论坛互动消息：谁（actor）对我（user）做了什么，与聊天消息互不混排"""

    __tablename__ = "forum_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 收件人：被评论 / 被点赞 / 被关注的人
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # 触发者：评论者 / 点赞者 / 关注者
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    # 关联帖子（关注类消息为空）；帖子被删也不影响消息展示，标题走快照
    post_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    post_title: Mapped[str] = mapped_column(String(200), default="")
    # 评论正文 / 点赞对象摘要等快照
    content: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
