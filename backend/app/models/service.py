from datetime import datetime, timezone
from sqlalchemy import String, Text, Enum as SAEnum, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class TicketType(str, enum.Enum):
    LEAVE = "leave"
    CERTIFICATE = "certificate"
    PROJECT = "project"


class TicketStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ServiceTicket(Base):
    __tablename__ = "service_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    applicant_id: Mapped[int] = mapped_column(index=True)
    applicant_name: Mapped[str] = mapped_column(String(50), default="")
    applicant_no: Mapped[str] = mapped_column(String(50), default="")
    applicant_college: Mapped[str] = mapped_column(String(100), default="")
    type: Mapped[TicketType] = mapped_column(SAEnum(TicketType))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    attachment: Mapped[str | None] = mapped_column(String(255))
    form_data: Mapped[dict | None] = mapped_column(JSON, default=None)
    attachments: Mapped[list | None] = mapped_column(JSON, default=None)
    status: Mapped[TicketStatus] = mapped_column(SAEnum(TicketStatus), default=TicketStatus.PENDING)
    approver_id: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
