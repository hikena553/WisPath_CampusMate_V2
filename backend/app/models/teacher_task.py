"""教师待办 / 跟进任务：所有闭环的公共基座。

AI 建议、预警随访、审批待办、关怀计划统一挂到这张表，避免各模块各自维护待办。
"""
import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskSourceType(str, enum.Enum):
    AI_SUGGEST = "ai_suggest"
    FOLLOW_UP = "follow_up"
    APPROVAL = "approval"
    CARE_PLAN = "care_plan"
    ALERT = "alert"
    MANUAL = "manual"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    CARED = "cared"
    DONE = "done"
    EXPIRED = "expired"


# 允许的状态流转：防止前端/接口把任务改成非法状态
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.CONTACTED, TaskStatus.CARED, TaskStatus.DONE, TaskStatus.EXPIRED},
    TaskStatus.CONTACTED: {TaskStatus.CARED, TaskStatus.DONE, TaskStatus.PENDING},
    TaskStatus.CARED: {TaskStatus.DONE, TaskStatus.PENDING},
    TaskStatus.DONE: {TaskStatus.PENDING},
    TaskStatus.EXPIRED: {TaskStatus.PENDING, TaskStatus.DONE},
}


class TeacherTask(Base):
    __tablename__ = "teacher_tasks"
    __table_args__ = (
        # 同一来源对象对同一教师只建一条任务，从数据库层杜绝重复推荐
        UniqueConstraint("source_type", "source_id", "teacher_id", name="uq_teacher_task_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(index=True)
    source_type: Mapped[TaskSourceType] = mapped_column(
        SAEnum(TaskSourceType), default=TaskSourceType.MANUAL
    )
    source_id: Mapped[int | None] = mapped_column(default=None)
    student_id: Mapped[int | None] = mapped_column(index=True, default=None)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    # 来源规则编码（预警 pipeline 使用，便于按「规则 + 学生 + 当日」幂等去重）
    rule_code: Mapped[str | None] = mapped_column(String(50), default=None, index=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.PENDING, index=True
    )
    due_at: Mapped[date | None] = mapped_column(Date, default=None)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
