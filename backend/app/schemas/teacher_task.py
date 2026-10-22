"""教师待办任务的请求 / 响应模型。"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TeacherTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = None
    student_id: int | None = None
    priority: str = "mid"
    remind_at: date | None = None
    due_at: date | None = None
    source_type: str = "manual"
    source_id: int | None = None


class TeacherTaskUpdate(BaseModel):
    status: str | None = None
    title: str | None = Field(default=None, max_length=200)
    detail: str | None = None
    student_id: int | None = None
    priority: str | None = None
    remind_at: date | None = None
    due_at: date | None = None


class TeacherTaskOut(BaseModel):
    id: int
    teacher_id: int
    source_type: str
    source_id: int | None = None
    student_id: int | None = None
    student_name: str = ""
    title: str
    detail: str | None = None
    rule_code: str | None = None
    status: str
    priority: str = "mid"
    remind_at: date | None = None
    # 今日是否应提醒（remind_at 为空时视为按 due_at 提醒）
    remind_due: bool = False
    due_at: date | None = None
    overdue: bool = False
    done_at: str | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TeacherTaskSummary(BaseModel):
    pending: int = 0
    overdue: int = 0
    today: int = 0
    done_this_week: int = 0
    total: int = 0
    high: int = 0
    remind_today: int = 0


class TaskAutoGenItem(BaseModel):
    """本次智能生成建出的任务（用于前端回显「生成了哪些」）。"""

    student_id: int | None = None
    student_name: str = ""
    rule: str = ""


class TaskAutoGenResult(BaseModel):
    """智能生成结果：created 为本次新增数，breakdown 说明各信号来源的贡献。"""

    created: int = 0
    date: str = ""
    breakdown: dict = {}
    items: list[TaskAutoGenItem] = []


class AdminTaskCreate(BaseModel):
    """管理员向教师下发任务：自动进入该教师的日程任务清单。"""

    teacher_id: int
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = None
    student_id: int | None = None
    priority: str = "mid"
    remind_at: date | None = None
    due_at: date | None = None
