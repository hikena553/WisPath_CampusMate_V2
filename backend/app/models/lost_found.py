from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class ItemType(str, enum.Enum):
    LOST = "lost"
    FOUND = "found"


class ItemStatus(str, enum.Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    CLOSED = "closed"


class LostFoundItem(Base):
    __tablename__ = "lost_found_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[ItemType] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    contact: Mapped[str] = mapped_column(String(200), default="")
    image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ItemStatus] = mapped_column(Text, default=ItemStatus.OPEN)
    claimant_name: Mapped[str | None] = mapped_column(String(50), default=None)
    claimant_contact: Mapped[str | None] = mapped_column(String(200), default=None)
    claim_note: Mapped[str | None] = mapped_column(String(500), default=None)
    claimed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class LostFoundComment(Base):
    __tablename__ = "lost_found_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("lost_found_items.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
