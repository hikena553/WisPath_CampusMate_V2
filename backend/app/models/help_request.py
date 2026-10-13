"""学生求助：学生向辅导员发起求助（可匿名），辅导员受理并回复，形成「求助 → 帮扶」闭环。

与「意见反馈（Feedback）」的区别：
- 反馈面向平台 / 管理员，处理的是 bug / 建议 / 投诉；
- 求助面向学生自己的辅导员，由辅导员一对一受理、帮扶、回复。
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HelpRequestStatus(str, enum.Enum):
    PENDING = "pending"        # 待受理
    PROCESSING = "processing"  # 帮扶中
    RESOLVED = "resolved"      # 已帮助


class HelpRequest(Base):
    __tablename__ = "help_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    # 求助类别：academic 学业困扰 / life 生活困难 / mental 心理情绪 / relation 人际关系 / other 其他
    category: Mapped[str] = mapped_column(String(20), default="other", index=True)
    content: Mapped[str] = mapped_column(Text)
    # 是否匿名：为真时辅导员列表中隐去学生姓名，但仍可受理与回复
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[HelpRequestStatus] = mapped_column(
        SAEnum(HelpRequestStatus), default=HelpRequestStatus.PENDING, index=True
    )
    # 受理辅导员（首次回复时写入）
    teacher_id: Mapped[int | None] = mapped_column(index=True, default=None)
    reply: Mapped[str | None] = mapped_column(Text, default=None)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)