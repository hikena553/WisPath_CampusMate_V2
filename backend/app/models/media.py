"""资讯账号（媒体账号）：管理端维护的运营身份，自动在交流社区发资讯帖。

- MediaAccount：账号配置（启停 / 内容方向），1:1 挂在 role=MEDIA 的 users 记录上；
  name / avatar / signature 直接复用 users 字段，即社区帖子里的作者形象。
- MediaPost：发帖流水。既做「账号发了什么」的统计口径，也做转发去重
  （同一资讯条目对同一账号只转发一次）与日报幂等（每账号每天最多一条）的约束依据。
"""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MediaAccount(Base):
    """资讯账号配置：users 表中 role=MEDIA 的记录的业务扩展"""

    __tablename__ = "media_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, comment="对应的 users.id（role=MEDIA）"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="停用后不参与自动发帖")
    content_scope: Mapped[list | None] = mapped_column(
        JSON, default=None, comment="绑定的资讯分类（external_feed_items.source_type 列表），空/None 表示全部"
    )
    relay_interval_minutes: Mapped[int] = mapped_column(
        Integer, default=30,
        comment="逐条转发频率（分钟）：距上次转发的最小间隔；0=不逐条转发仅发每日汇总；每日汇总帖固定每天一条不受此限",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.now
    )


class MediaPost(Base):
    """资讯账号发帖流水：转发去重 + 日报幂等 + 发帖数统计的统一口径"""

    __tablename__ = "media_posts"
    __table_args__ = (
        # 转发去重：同一资讯条目对同一账号只发一帖（digest 行 feed_item_id 为 NULL 不受约束）
        UniqueConstraint("account_user_id", "feed_item_id", name="uq_media_posts_relay"),
        # 日报幂等：每账号每天最多一条汇总帖（relay 行 digest_date 为 NULL 不受约束）
        UniqueConstraint("account_user_id", "digest_date", name="uq_media_posts_digest"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_user_id: Mapped[int] = mapped_column(Integer, index=True, comment="发帖的资讯账号 users.id")
    post_id: Mapped[int] = mapped_column(
        ForeignKey("community_posts.id"), index=True, comment="生成的 community_posts.id"
    )
    # 不加 FK：external_feed_items 是快照式数据、管理端会物理删除，条目删掉后帖子留存
    feed_item_id: Mapped[int | None] = mapped_column(Integer, index=True, default=None, comment="转发的资讯条目 id")
    kind: Mapped[str] = mapped_column(String(20), comment="digest=每日汇总 / relay=逐条转发")
    digest_date: Mapped[date | None] = mapped_column(Date, default=None, comment="汇总帖归属日期（转发帖为空）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
