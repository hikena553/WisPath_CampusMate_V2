"""反馈模块 DTO：入参 Create/Reply 与出参 Out 统一收敛于此。"""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FeedbackCreate(BaseModel):
    type: str = "other"
    title: str
    content: str
    contact: Optional[str] = None


class FeedbackReply(BaseModel):
    reply: str
    status: str = "resolved"


class FeedbackWordOut(BaseModel):
    """词云统计项：关键词 + 出现次数"""
    word: str
    count: int


class FeedbackOut(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    type: str
    title: str
    content: str
    contact: Optional[str] = None
    status: str
    reply: Optional[str] = None
    replied_by: Optional[int] = None
    replier_name: Optional[str] = None
    replied_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)