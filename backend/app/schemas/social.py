"""社交（关注 / 通讯录 / 论坛互动消息）数据模型"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RelationOut(BaseModel):
    is_following: bool = False
    is_follower: bool = False
    is_friend: bool = False
    following: int = 0
    followers: int = 0
    friends: int = 0


class ContactOut(BaseModel):
    id: int
    name: str
    username: str
    avatar: str | None = None
    role: str = ""
    college: str | None = None
    class_name: str | None = None
    signature: str | None = None
    is_following: bool = False
    is_follower: bool = False
    is_friend: bool = False


class SuggestOut(BaseModel):
    id: int
    name: str
    username: str
    avatar: str | None = None
    role: str = ""
    college: str | None = None
    class_name: str | None = None
    signature: str | None = None


class ForumMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    actor_id: int
    post_id: int | None = None
    post_title: str | None = None
    content: str | None = None
    is_read: bool = False
    created_at: datetime
    actor_name: str = ""
    actor_avatar: str | None = None


class ForumReadIn(BaseModel):
    ids: list[int] | None = None
