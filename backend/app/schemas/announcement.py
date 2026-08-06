from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class AnnouncementOut(BaseModel):
    id: int
    teacher_id: int
    teacher_name: str = ""
    title: str
    content: str
    urgency: str
    attachment_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    urgency: str = "normal"


class UnreadCountOut(BaseModel):
    count: int


class ScheduleOut(BaseModel):
    id: int
    date: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleCreate(BaseModel):
    date: str
    content: str
