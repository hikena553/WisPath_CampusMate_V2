"""忘记密码申请：学生/教师在线发起身份核验，管理员审核后重置为初始密码。"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class PasswordResetStatus(str, enum.Enum):
    PENDING = "pending"
    RESET = "reset"
    REJECTED = "rejected"


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # 冗余快照：管理员审核时即使账号被改名/删除，也能看到申请时的信息
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 仅保存脱敏后的联系方式（如 138****1234 / QQ 123****78），不落明文
    contact: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PasswordResetStatus] = mapped_column(
        Enum(PasswordResetStatus), default=PasswordResetStatus.PENDING, index=True
    )
    admin_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
