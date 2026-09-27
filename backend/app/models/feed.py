from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, JSON, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FeedSource(Base):
    """外部资讯抓取源配置（运行时动态管理，不再硬编码源）"""

    __tablename__ = "feed_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), comment="来源名称")
    kind: Mapped[str] = mapped_column(String(20), comment="rss/html/arxiv/github/gitee/lmarena")
    source_type: Mapped[str] = mapped_column(String(20), index=True, comment="归属分类")
    feed_key: Mapped[str] = mapped_column(String(50), nullable=True, comment="去重标识(可空自动生成)")
    url: Mapped[str] = mapped_column(String(700))
    query: Mapped[str | None] = mapped_column(String(500), default=None, comment="API 类源的查询参数")
    base_url: Mapped[str | None] = mapped_column(String(300), default=None, comment="html 相对链接基础")
    filter_kw: Mapped[dict | None] = mapped_column(JSON, default=None, comment="标题关键词过滤")
    date_only: Mapped[bool] = mapped_column(Boolean, default=False, comment="仅保留标题含日期的条目")
    per_page: Mapped[int] = mapped_column(Integer, default=10)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, comment="内置预设源，不可删除")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.now)


class ExternalFeedItem(Base):
    """外部资讯条目：AI 论文 / 开源项目榜 / 智能体榜 / 权威要闻，快照式存储按 URL 去重"""

    __tablename__ = "external_feed_items"
    __table_args__ = (UniqueConstraint("link", name="uq_feed_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), index=True, comment="papers/agents/opensource/news")
    feed_key: Mapped[str] = mapped_column(String(50), index=True, comment="来源标识 arxiv/github-stars/gitee/...")
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    link: Mapped[str] = mapped_column(String(700))
    author: Mapped[str | None] = mapped_column(String(200), default=None, comment="论文作者或仓库全名")
    source_name: Mapped[str | None] = mapped_column(String(100), default=None, comment="展示用来源名")
    is_highlight: Mapped[bool] = mapped_column(Boolean, default=False, comment="热点/置顶标记")
    meta: Mapped[dict | None] = mapped_column(JSON, default=None, comment="排行指标等额外信息")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.now)