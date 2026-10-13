"""学生求助的请求 / 响应模型。"""
from pydantic import BaseModel, Field


class HelpRequestCreate(BaseModel):
    category: str = "other"
    content: str = Field(min_length=1, max_length=1000)
    anonymous: bool = False


class HelpRequestReply(BaseModel):
    reply: str = Field(min_length=1, max_length=1000)
    status: str = "resolved"


class HelpRequestOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    anonymous: bool = False
    category: str
    content: str
    status: str
    teacher_id: int | None = None
    teacher_name: str = ""
    reply: str | None = None
    replied_at: str = ""
    created_at: str = ""


class HelpRequestOverview(BaseModel):
    """辅导员端求助受理概览。"""

    pending: int = 0
    processing: int = 0
    resolved: int = 0
    total: int = 0