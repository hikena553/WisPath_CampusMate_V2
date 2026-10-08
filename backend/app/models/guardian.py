"""家校沟通（家长观察者）：联系人 / 沟通台账 / 只读分享链接。

设计要点（对应规划 A1–A10）：
- 家长无账号、无登录，仅作为联系人档案存在；
- 沟通台账三通道：短信（复用 notification_service）、报告（前端打印导出）、链接（本模块只读分享）；
- 安全：手机号脱敏输出；危机类记录禁止生成分享链接；关键操作写审计日志。
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GuardianScene(str, enum.Enum):
    LEAVE = "leave"        # 请假告知
    CRISIS = "crisis"      # 危机干预
    ACADEMIC = "academic"  # 学业预警
    CARE = "care"          # 日常关怀
    OTHER = "other"        # 其他


class GuardianChannel(str, enum.Enum):
    SMS = "sms"        # 短信提示
    REPORT = "report"  # 报告导出
    LINK = "link"      # 只读分享链接
    NOTE = "note"      # 仅内部留痕


class GuardianContactStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PENDING = "pending"
    FAILED = "failed"


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(50))
    relation: Mapped[str] = mapped_column(String(20), default="家长")
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(String(200), default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GuardianContactLog(Base):
    __tablename__ = "guardian_contact_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    guardian_id: Mapped[int | None] = mapped_column(index=True, default=None)
    teacher_id: Mapped[int] = mapped_column(index=True)
    scene: Mapped[GuardianScene] = mapped_column(
        SAEnum(GuardianScene), default=GuardianScene.OTHER, index=True
    )
    channel: Mapped[GuardianChannel] = mapped_column(
        SAEnum(GuardianChannel), default=GuardianChannel.NOTE
    )
    status: Mapped[GuardianContactStatus] = mapped_column(
        SAEnum(GuardianContactStatus), default=GuardianContactStatus.DRAFT
    )
    content_summary: Mapped[str] = mapped_column(Text, default="")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GuardianShareLink(Base):
    __tablename__ = "guardian_share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[int] = mapped_column(index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)