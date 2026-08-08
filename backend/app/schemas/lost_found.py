from pydantic import BaseModel, ConfigDict
from datetime import datetime


class LostFoundItemCreate(BaseModel):
    type: str
    title: str
    description: str = ""
    location: str = ""
    contact: str = ""
    image_url: str | None = None


class LostFoundCommentCreate(BaseModel):
    content: str


class LostFoundCommentOut(BaseModel):
    id: int
    item_id: int
    user_id: int
    user_name: str | None = None
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LostFoundItemOut(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    type: str
    title: str
    description: str
    location: str
    contact: str
    image_url: str | None = None
    status: str
    created_at: datetime
    comments: list[LostFoundCommentOut] | None = None

    model_config = ConfigDict(from_attributes=True)


class LostFoundStatusUpdate(BaseModel):
    status: str
