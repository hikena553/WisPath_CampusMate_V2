from datetime import datetime, timezone
from sqlalchemy import String, Text, Enum as SAEnum, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class LeaveType(str, enum.Enum):
    COMPETITION = "competition"
    SICK = "sick"
    PERSONAL = "personal"
    OTHER = "other"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    start_date: Mapped[str] = mapped_column(Date)
    end_date: Mapped[str] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    leave_type: Mapped[LeaveType] = mapped_column(SAEnum(LeaveType))
    status: Mapped[LeaveStatus] = mapped_column(SAEnum(LeaveStatus), default=LeaveStatus.PENDING)
    tutor_id: Mapped[int | None] = mapped_column(default=None)
    reject_reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
