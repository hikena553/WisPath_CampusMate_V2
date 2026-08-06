from sqlalchemy import String, Text, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import enum

from app.core.database import Base


class ConversationType(str, enum.Enum):
    NORMAL = "normal"
    PROJECT = "project"


class ProjectTemplate(str, enum.Enum):
    COMPETITION = "competition"
    THESIS = "thesis"
    PRACTICE = "practice"
    CERTIFICATE = "certificate"
    STUDENT_WORK = "student_work"
    CUSTOM = "custom"


PROJECT_STAGES: dict[str, list[str]] = {
    "competition": ["赛前准备", "方案设计", "实施优化", "答辩展示"],
    "thesis": ["选题开题", "文献综述", "实验/调研", "撰写修改", "答辩"],
    "practice": ["方案申报", "前期准备", "实施执行", "总结评优"],
    "certificate": ["考情分析", "学习规划", "备考刷题", "考前冲刺"],
    "student_work": ["活动策划", "审批协调", "执行落地", "复盘总结"],
    "custom": [],
}


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    type: Mapped[ConversationType] = mapped_column(SAEnum(ConversationType), default=ConversationType.NORMAL)
    project_template: Mapped[str | None] = mapped_column(String(50))
    project_stage: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
