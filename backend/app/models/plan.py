from datetime import date, datetime, timezone
from sqlalchemy import String, Text, Date, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"


class PlanStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GrowthGoal(Base):
    """长期发展目标（个人中心成长画像 -> AI 成长地图/驾驶舱）"""

    __tablename__ = "growth_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    goal_type: Mapped[str] = mapped_column(String(50), default="就业")  # 就业/考研/技能/证书/其他
    title: Mapped[str] = mapped_column(String(200), comment="长期目标描述")
    target_date: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[GoalStatus] = mapped_column(SAEnum(GoalStatus), default=GoalStatus.ACTIVE)
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="0-100")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class StudyPlan(Base):
    """学习计划（主题/周期/目标/阶段），可挂在长期目标下"""

    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("growth_goals.id"), default=None, comment="关联长期目标")
    title: Mapped[str] = mapped_column(String(200))
    objective: Mapped[str | None] = mapped_column(Text, comment="计划目标描述")
    stage: Mapped[str | None] = mapped_column(String(100), comment="当前阶段/周期描述")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[PlanStatus] = mapped_column(SAEnum(PlanStatus), default=PlanStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class PlanTask(Base):
    """计划内任务"""

    __tablename__ = "plan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date, default=None)
    priority: Mapped[TaskPriority] = mapped_column(SAEnum(TaskPriority), default=TaskPriority.MEDIUM)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.TODO)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class PlanCheckin(Base):
    """任务打卡记录（完成时记录时长）"""

    __tablename__ = "plan_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("plan_tasks.id"), default=None)
    check_date: Mapped[date] = mapped_column(Date, index=True)
    minutes: Mapped[int] = mapped_column(Integer, default=0, comment="投入时长(分钟)")
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))