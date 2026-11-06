from datetime import datetime
from sqlalchemy import String, Text, Boolean, Enum as SAEnum, DateTime, Date, Index
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
    # 历史遗留列：销假链路已下线（审批通过即流程结束）。
    # 保留列定义只为兼容既有表结构（含 NOT NULL 的 return_confirmed），
    # 业务代码不再读写这两个字段；后续可随一次正式迁移一并删除。
    return_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    return_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        # 辅导员待办列表：WHERE tutor_id=? AND status=? ORDER BY created_at DESC
        Index("ix_leave_requests_tutor_status_created", "tutor_id", "status", "created_at"),
    )
