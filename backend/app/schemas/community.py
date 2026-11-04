import json

from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime


class CommunityPostCreate(BaseModel):
    category: str = "分享"
    title: str
    content: str
    # 配图：传 URL 数组，落库存 JSON 字符串（与作品集 images 同一套写法）
    images: list[str] | None = None


class CommunityPostUpdate(BaseModel):
    category: str | None = None
    title: str | None = None
    content: str | None = None
    images: list[str] | None = None


class CommunityPostOut(BaseModel):
    id: int
    student_id: int
    category: str
    title: str
    content: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime | None = None
    author_name: str | None = None
    author_avatar: str | None = None
    author_is_following: bool = False
    liked: bool = False
    images: list[str] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator("images", mode="before")
    @classmethod
    def _parse_images(cls, v):
        """库里 images 是 JSON 字符串，出参统一成数组（前端只认数组）。"""
        if not v:
            return []
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return [str(x) for x in parsed if x] if isinstance(parsed, list) else []
            except (ValueError, TypeError):
                return []
        return v


class CommunityCommentCreate(BaseModel):
    content: str


class CommunityCommentOut(BaseModel):
    id: int
    post_id: int
    student_id: int
    content: str
    created_at: datetime | None = None
    author_name: str | None = None
    author_avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LikeOut(BaseModel):
    liked: bool
    count: int