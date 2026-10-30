"""社交关系与论坛互动消息。

- Follow：关注关系（user_follows）。「好友」= 互相关注，不再用「聊过天」代替；
- ForumMessage：论坛互动消息（forum_messages）。点赞 / 收藏 / 评论 / 新粉丝
  独立成一条流，与聊天消息（messages）彻底分表，避免两种消息混排。

关注口径与消息页通讯录、个人主页、勋章 metrics.contacts 共用 social_service，
不得各自实现一套，否则同一个人在不同页面会显示成不同关系。
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ForumMessageKind(str, enum.Enum):
    LIKE = "like"          # 点赞了你的帖子
    FAVORITE = "favorite"  # 收藏了你的帖子
    COMMENT = "comment"    # 评论了你的帖子
    FOLLOW = "follow"      # 新粉丝


class Follow(Base):
    """关注关系：follower（关注者）→ following（被关注者）

    一人对同一人只保留一条，重复关注在服务层按幂等处理。
    """

    __tablename__ = "user_follows"
    __table_args__ = (UniqueConstraint("follower_id", "following_id", name="uq_follow_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(Integer, index=True)
    following_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ForumMessage(Base):
    """论坛互动消息：接收者（帖子作者 / 被关注者）+ 触发者 + 互动类型"""

    __tablename__ = "forum_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    actor_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[ForumMessageKind] = mapped_column(
        SAEnum(ForumMessageKind), default=ForumMessageKind.LIKE, index=True
    )
    post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 标题快照：帖子被删除后消息仍可读，不至于只剩一条空记录
    post_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
