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
    claimant_name: str | None = None
    claimant_contact: str | None = None
    claim_note: str | None = None
    claimed_by: int | None = None
    claimed_at: datetime | None = None
    created_at: datetime
    # 留言数：列表里直接给出来，前端行右侧的计数与「最热」排序都靠它
    # （详情接口带 comments，这个值就等于 len(comments)）
    comment_count: int = 0
    comments: list[LostFoundCommentOut] | None = None

    model_config = ConfigDict(from_attributes=True)


class LostFoundStatusUpdate(BaseModel):
    status: str
    claimant_name: str | None = None
    claimant_contact: str | None = None
    claim_note: str | None = None
