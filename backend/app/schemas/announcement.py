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


class AnnouncementReachItem(BaseModel):
    """单条公告的触达回执：应读人数、已读数与触达率（percent 0~100）。"""

    announcement_id: int
    title: str
    urgency: str = "normal"
    total: int = 0
    read: int = 0
    rate: int = 0


class AnnouncementReachOut(BaseModel):
    items: list[AnnouncementReachItem] = []
    total: int = 0
    read: int = 0
    rate: int = 0


class ScheduleOut(BaseModel):
    id: int
    date: str
    content: str
    urgency: str = "normal"
    completed: bool = False
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleCreate(BaseModel):
    date: str
    content: str
    urgency: str = "normal"


class ScheduleUpdate(BaseModel):
    completed: bool
