"""校园资讯互动：点赞 / 评论 / 转发 / 浏览

背景：校园资讯（教务处、学院、图书馆的爬虫结果）本身是「无主」的抓取产物——
没有数据库 id，唯一稳定的身份就是原文 url。因此这里的互动表全部以 article_url
作为逻辑外键，而不是外键到某张资讯表：
- 爬虫会重抓、会改标题、会下线重上，若用内部 id 关联，重抓一次互动数据就全丢了；
- url 天然跨来源唯一，同一篇被多个栏目转载时也能共享一份互动数据。

计数值（like/comment/repost/view）冗余在 campus_article_socials 上，而不是每次
COUNT(*)：信息流一页要渲染几十篇文章，逐篇聚合会变成 N+1 查询；写入时在同一事务里
维护计数，读路径保持 O(1)。明细表（comments/likes/reposts）才是事实来源，计数可以由
明细重建，容忍极端情况下的小幅漂移。

点赞用唯一约束做去重（一人一次），转反而刻意不去重（一人可多次转发，每次都算传播）。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    """统一用带时区的 UTC 时间（Python 3.12 起 datetime.utcnow 已弃用）。"""
    return datetime.now(timezone.utc)


class CampusArticleSocial(Base):
    """一篇文章一条互动计数记录，url 为唯一键（懒创建：首次被互动/被浏览时才插入）"""
    __tablename__ = "campus_article_socials"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 700 而非 500：资讯链接带中文参数/追踪参数时很容易超长，MySQL utf8mb4 下
    # 700 仍能放进 InnoDB 的 3072 字节索引上限（700*4=2800），保证 unique+index 可用。
    url: Mapped[str] = mapped_column(String(700), unique=True, index=True)
    # title/source/image_url 是创建时对资讯做的快照：资讯源可能临时抓取失败或下线，
    # 有了快照，互动列表（如「我的点赞」）仍能展示标题与封面，不必回源。
    title: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(30), default="")      # jwc_jxdt/jwc_tzgg/college_news/library ...
    image_url: Mapped[str | None] = mapped_column(String(500), default=None)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repost_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class CampusArticleComment(Base):
    """文章评论明细（事实来源，comment_count 由此维护）"""
    __tablename__ = "campus_article_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_url: Mapped[str] = mapped_column(String(700), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CampusArticleLike(Base):
    """点赞明细：唯一约束保证一人对一篇只算一次（重复点赞靠约束兜底，避免并发双写）"""
    __tablename__ = "campus_article_likes"
    __table_args__ = (
        UniqueConstraint("article_url", "user_id", name="uq_campus_article_like_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    article_url: Mapped[str] = mapped_column(String(700), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CampusArticleRepost(Base):
    """转发明细：刻意不加唯一约束——转发是传播行为，同一用户可多次转发，每次计一行"""
    __tablename__ = "campus_article_reposts"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_url: Mapped[str] = mapped_column(String(700), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # channel 预留给未来的多去向转发（timeline 动态 / 私聊 / 班级群），目前仅用 timeline
    channel: Mapped[str] = mapped_column(String(20), default="timeline")
    content: Mapped[str] = mapped_column(Text, default="")           # 用户附言，可为空
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
