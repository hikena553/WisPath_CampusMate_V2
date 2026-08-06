from datetime import datetime, date, timezone
from sqlalchemy import String, Text, Integer, Float, Date, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class StudentProfileSnapshot(Base):
    __tablename__ = "student_profile_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    academic_score: Mapped[float] = mapped_column(Float, default=0.0)
    psychological_risk: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    growth_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_risk: Mapped[float] = mapped_column(Float, default=0.0)
    behavioral_patterns: Mapped[dict | None] = mapped_column(JSON, default=dict)
    key_insights: Mapped[list | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(index=True)
    student_id: Mapped[int] = mapped_column(index=True)
    summary: Mapped[str] = mapped_column(Text)
    key_insights: Mapped[dict | None] = mapped_column(JSON, default=dict)
    topics: Mapped[list | None] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    message_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
