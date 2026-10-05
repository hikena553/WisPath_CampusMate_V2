"""教师侧写记录的请求 / 响应模型。"""
from pydantic import BaseModel, ConfigDict, Field


class CareRecordCreate(BaseModel):
    student_id: int
    record_type: str = "care"
    content: str = Field(min_length=1)
    is_private: bool = True
    task_id: int | None = None


class CareRecordUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    is_private: bool | None = None


class CareRecordOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    teacher_id: int
    teacher_name: str = ""
    record_type: str
    content: str
    is_private: bool
    task_id: int | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class WorkloadStats(BaseModel):
    care: int = 0
    talk: int = 0
    comment: int = 0
    total: int = 0
