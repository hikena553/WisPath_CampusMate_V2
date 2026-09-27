from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmsLog(Base):
    """短信发送记录（通道预留：未配置真实服务商时记录 skipped）"""
    __tablename__ = "sms_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    receiver_phone: Mapped[str | None] = mapped_column(String(30), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="reserved")
    template: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent/skipped/failed/not_configured
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))