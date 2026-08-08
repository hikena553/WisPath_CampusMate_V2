from datetime import datetime
from pydantic import BaseModel, ConfigDict


class GroupCreate(BaseModel):
    name: str
    member_ids: list[int] = []


class GroupMemberAdd(BaseModel):
    user_ids: list[int]


class GroupMessageSend(BaseModel):
    content: str


class GroupOut(BaseModel):
    id: int
    name: str
    avatar: str | None = None
    creator_id: int
    announcement: str | None = None
    is_dismissed: bool = False
    member_count: int = 0
    last_message: str = ""
    last_message_time: datetime | None = None
    unread_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class GroupMemberOut(BaseModel):
    user_id: int
    user_name: str
    user_avatar: str | None = None
    role: str
    joined_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GroupMessageOut(BaseModel):
    id: int
    group_id: int
    sender_id: int
    sender_name: str
    sender_avatar: str | None = None
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserSearchResult(BaseModel):
    id: int
    name: str
    username: str
    avatar: str | None = None
    role: str = "student"
    model_config = ConfigDict(from_attributes=True)


class AnnouncementUpdate(BaseModel):
    announcement: str