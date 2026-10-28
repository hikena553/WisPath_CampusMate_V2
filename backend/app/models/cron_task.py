import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CronScheduleKind(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"


class CronTaskSource(str, enum.Enum):
    CHAT = "chat"
    MANUAL = "manual"


class AgentCronTask(Base):
    """Agent 定时任务：到点由 cron_task_service 以学生身份无头执行一轮 agent。"""

    __tablename__ = "agent_cron_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 每次执行下发给 AI 的指令（不含任务名前缀，落库会话时再加）
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_kind: Mapped[CronScheduleKind] = mapped_column(SAEnum(CronScheduleKind), nullable=False)
    # daily/weekly 的触发时刻；hour/minute/weekday 语义是学生口中的北京时间，落库前换算为 UTC
    hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=周一 … 6=周日
    interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True, index=True)
    # 任务专属会话：每次执行的消息都追加于此，学生可在会话里回溯历史运行
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    created_via: Mapped[CronTaskSource] = mapped_column(SAEnum(CronTaskSource), default=CronTaskSource.CHAT)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
