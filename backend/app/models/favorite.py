from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResourceFavorite(Base):
    """资源收藏（知识/资讯/社区帖子，快照式存储便于去重与展示）"""

    __tablename__ = "resource_favorites"
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    item_type: Mapped[str] = mapped_column(String(20), comment="knowledge/announcement/community")
    item_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str | None] = mapped_column(String(50), default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    link: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))