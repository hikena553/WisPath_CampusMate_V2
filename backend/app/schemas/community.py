from pydantic import BaseModel, ConfigDict
from datetime import datetime


class CommunityPostCreate(BaseModel):
    category: str = "分享"
    title: str
    content: str


class CommunityPostUpdate(BaseModel):
    category: str | None = None
    title: str | None = None
    content: str | None = None


class CommunityPostOut(BaseModel):
    id: int
    student_id: int
    category: str
    title: str
    content: str
    view_count: int = 0
    like_count: int = 0
    favorite_count: int = 0
    comment_count: int = 0
    created_at: datetime | None = None
    author_name: str | None = None
    author_avatar: str | None = None
    liked: bool = False
    favorited: bool = False

    model_config = ConfigDict(from_attributes=True)


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


class MyCommentOut(BaseModel):
    """我发出的评论（互动消息「我评论的」页签）：带帖子标题快照"""

    id: int
    post_id: int
    post_title: str
    content: str
    created_at: datetime | None = None


class LikeOut(BaseModel):
    liked: bool
    count: int


class FavoriteOut(BaseModel):
    """收藏切换结果：favorited 是我的状态，count 是这篇帖子的总收藏数"""

    favorited: bool
    count: int