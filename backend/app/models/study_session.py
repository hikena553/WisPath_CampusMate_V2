from datetime import date, datetime, timezone
from sqlalchemy import String, Date, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StudySession(Base):
    """自习室专注记录（番茄钟）：一次专注结束后落一条，用于今日/历史时长统计。

    study_date 由服务端按 Asia/Shanghai 本地日写入，跨时区查询口径与打卡一致。
    """

    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    mode: Mapped[str] = mapped_column(String(20), default="focus", comment="focus/short_break/long_break")
    task_title: Mapped[str | None] = mapped_column(String(200), comment="本次专注的学习内容")
    planned_minutes: Mapped[int] = mapped_column(Integer, default=25, comment="计划时长")
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0, comment="实际专注分钟数")
    completed: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否走完整个番茄钟")
    study_date: Mapped[date] = mapped_column(Date, index=True, comment="本地日")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="UTC")
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
