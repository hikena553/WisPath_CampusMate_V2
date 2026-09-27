from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, Enum as SAEnum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class MaterialCategory(str, enum.Enum):
    IDENTITY = "identity"        # 证件
    STATEMENT = "statement"      # 证明
    GRADE = "grade"              # 成绩单
    REGISTER = "register"        # 学籍
    OTHER = "other"              # 其他


class MaterialStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MaterialArchive(Base):
    """学生个人材料档案（工作台-材料档案）"""
    __tablename__ = "material_archives"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[MaterialCategory] = mapped_column(SAEnum(MaterialCategory), default=MaterialCategory.OTHER)
    file_url: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(255), default="")
    file_type: Mapped[str] = mapped_column(String(50), default="")
    remark: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MaterialStatus] = mapped_column(SAEnum(MaterialStatus), default=MaterialStatus.PENDING)
    reject_reason: Mapped[str | None] = mapped_column(String(500))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))