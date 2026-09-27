from pydantic import BaseModel, ConfigDict
from datetime import date, datetime


# ---------- 长期目标 ----------
class GrowthGoalCreate(BaseModel):
    goal_type: str = "就业"
    title: str
    target_date: str | None = None
    note: str | None = None


class GrowthGoalUpdate(BaseModel):
    goal_type: str | None = None
    title: str | None = None
    target_date: str | None = None
    status: str | None = None
    progress: int | None = None
    note: str | None = None


class GrowthGoalOut(BaseModel):
    id: int
    student_id: int
    goal_type: str
    title: str
    target_date: date | None = None
    status: str
    progress: int = 0
    note: str | None = None
    created_at: datetime | None = None
    plan_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------- 学习计划 ----------
class StudyPlanCreate(BaseModel):
    title: str
    objective: str | None = None
    stage: str | None = None
    start_date: str
    end_date: str | None = None
    goal_id: int | None = None


class StudyPlanUpdate(BaseModel):
    title: str | None = None
    objective: str | None = None
    stage: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    goal_id: int | None = None
    status: str | None = None


class PlanTaskBrief(BaseModel):
    id: int
    title: str
    status: str


class StudyPlanOut(BaseModel):
    id: int
    student_id: int
    goal_id: int | None = None
    title: str
    objective: str | None = None
    stage: str | None = None
    start_date: date
    end_date: date | None = None
    status: str
    created_at: datetime | None = None
    # 附加统计
    task_total: int = 0
    task_done: int = 0
    done_rate: int = 0       # 0-100
    overdue: int = 0         # 逾期未完成数
    goal_title: str | None = None
    checkin_days: int = 0    # 打卡天数

    model_config = ConfigDict(from_attributes=True)


# ---------- 计划任务 ----------
class PlanTaskCreate(BaseModel):
    plan_id: int
    stage_id: int | None = None
    title: str
    description: str | None = None
    due_date: str | None = None
    priority: str = "medium"
    order_index: int = 0


class PlanTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str | None = None
    order_index: int | None = None
    stage_id: int | None = None


class PlanTaskOut(BaseModel):
    id: int
    plan_id: int
    stage_id: int | None = None
    title: str
    description: str | None = None
    due_date: date | None = None
    priority: str
    status: str
    order_index: int = 0
    created_at: datetime | None = None
    plan_title: str | None = None
    checked_today: bool = False

    model_config = ConfigDict(from_attributes=True)


# ---------- 计划阶段（任务流关卡） ----------
class PlanStageCreate(BaseModel):
    plan_id: int
    title: str
    goal: str | None = None
    order_index: int = 0


class PlanStageUpdate(BaseModel):
    title: str | None = None
    goal: str | None = None
    order_index: int | None = None
    status: str | None = None


class PlanStageOut(BaseModel):
    id: int
    plan_id: int
    title: str
    goal: str | None = None
    order_index: int = 0
    status: str
    ai_generated: bool = False
    score: int | None = None
    evaluation: str | None = None
    weaknesses: str | None = None
    suggestions: str | None = None
    submitted_result: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime | None = None
    # 附加统计
    task_total: int = 0
    task_done: int = 0
    done_rate: int = 0

    model_config = ConfigDict(from_attributes=True)


class StageSubmitRequest(BaseModel):
    result: str


class StageSubmitOut(BaseModel):
    id: int
    status: str
    score: int | None = None
    evaluation: str | None = None
    weaknesses: str | None = None
    suggestions: str | None = None


class StageGenerateOut(BaseModel):
    summary: str
    stages: list[PlanStageOut]


# ---------- 打卡 ----------
class CheckinCreate(BaseModel):
    plan_id: int
    task_id: int | None = None
    minutes: int = 30
    note: str | None = None


class CheckinOut(BaseModel):
    id: int
    plan_id: int
    task_id: int | None = None
    check_date: date
    minutes: int
    note: str | None = None
    plan_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StreakOut(BaseModel):
    current: int = 0
    longest: int = 0
    today_checked: bool = False
    days: list[str] = []


class TodayTaskOut(BaseModel):
    task_id: int | None = None
    title: str
    due_date: date | None = None
    priority: str = "medium"
    status: str = "todo"
    plan_id: int = 0
    plan_title: str = ""
    checked_today: bool = False


class AISuggestItem(BaseModel):
    task_id: int
    title: str
    due_date: date | None = None
    status: str
    suggest: str


class AISuggestOut(BaseModel):
    summary: str
    items: list[AISuggestItem]