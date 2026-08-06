from datetime import datetime, timezone
from sqlalchemy import String, Text, Enum as SAEnum, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class AwardLevel(str, enum.Enum):
    SCHOOL = "school"
    CITY = "city"
    PROVINCE = "province"
    NATIONAL = "national"
    INTERNATIONAL = "international"


class CertStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(200))
    competition_name: Mapped[str | None] = mapped_column(String(200))
    award_level: Mapped[AwardLevel | None] = mapped_column(SAEnum(AwardLevel))
    date: Mapped[str | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CertStatus] = mapped_column(SAEnum(CertStatus), default=CertStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
