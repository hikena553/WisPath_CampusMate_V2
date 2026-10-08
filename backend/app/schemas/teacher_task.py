"""教师待办任务的请求 / 响应模型。"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TeacherTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = None
    student_id: int | None = None
    due_at: date | None = None
    source_type: str = "manual"
    source_id: int | None = None


class TeacherTaskUpdate(BaseModel):
    status: str | None = None
    title: str | None = Field(default=None, max_length=200)
    detail: str | None = None
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
