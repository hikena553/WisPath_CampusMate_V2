from datetime import datetime, date, timezone
from sqlalchemy import String, Text, Boolean, DateTime, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class CrisisLevel(str, enum.Enum):
    NORMAL = "normal"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class InterventionType(str, enum.Enum):
    TALK = "谈话"
    PARENT_MEETING = "约谈家长"
    PSYCHOLOGY_REFERRAL = "转介心理咨询"
    OTHER = "其他"


class AIDialogSummary(Base):
    __tablename__ = "ai_dialog_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    summary: Mapped[str] = mapped_column(Text)
    level: Mapped[CrisisLevel] = mapped_column(SAEnum(CrisisLevel), default=CrisisLevel.NORMAL)
    keywords_matched: Mapped[str | None] = mapped_column(String(200))
    raw_snippet: Mapped[str | None] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    intervention_type: Mapped[InterventionType | None] = mapped_column(SAEnum(InterventionType), nullable=True)
    intervention_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
