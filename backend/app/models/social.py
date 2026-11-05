"""社交关系与论坛互动消息。

- Follow：关注关系（user_follows）。「好友」= 互相关注，不再用「聊过天」代替；
- ForumMessage：论坛互动消息（forum_messages）。点赞 / 收藏 / 评论 / 新粉丝
  独立成一条流，与聊天消息（messages）彻底分表，避免两种消息混排；
- FriendSetting：好友设置（user_friend_settings）。个人主页「设置」那一页的
  备注 / 特别关心 / 动态权限 / 亲密关系落在这里，登录换设备也跟着走。

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
        # 库里存的是小写值（like / favorite / comment / follow）：种子数据、
        # 建表迁移的注释、前端按 kind 过滤都按这个口径。SQLAlchemy 默认按**枚举名**
        # 读写，会在读到 'follow' 时抛 LookupError，故显式指定取值函数。
        SAEnum(ForumMessageKind, values_callable=lambda e: [m.value for m in e]),
        default=ForumMessageKind.LIKE,
        index=True,
    )
    post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 标题快照：帖子被删除后消息仍可读，不至于只剩一条空记录
    post_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class FriendSetting(Base):
    """好友设置：user_id 对 peer_id 这一条，只由 user_id 自己读写。

    主页设置页的每一项都在这张表里，语义与 QQ 好友设置对齐：

    - remark            备注：只有自己看得见的称呼，不改对方账号名；
    - care              特别关心：打开后消息列表带「特别」标、主页封面挂金标；
    - mute              消息免打扰；
    - blocked           加入黑名单；
    - hide_peer_posts   动态权限「不看 TA 的动态」：信息流里过滤掉 TA 的帖子；
    - hide_my_posts     动态权限「不让 TA 看我的动态」：TA 的信息流里过滤掉我的帖子；
    - intimacy          亲密关系标识（闺蜜 / 基友 / 搭子 / 同桌），空串表示未设置。

    两个动态权限是**单向各自一条**：A 屏蔽 B 的动态，只影响 A 的信息流；
    B 想反过来屏蔽 A，是 B 自己那条记录上的 hide_peer_posts。
    """

    __tablename__ = "user_friend_settings"
    __table_args__ = (UniqueConstraint("user_id", "peer_id", name="uq_friend_setting_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    peer_id: Mapped[int] = mapped_column(Integer, index=True)
    remark: Mapped[str] = mapped_column(String(32), default="")
    care: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    mute: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    hide_peer_posts: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    hide_my_posts: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    intimacy: Mapped[str] = mapped_column(String(16), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
