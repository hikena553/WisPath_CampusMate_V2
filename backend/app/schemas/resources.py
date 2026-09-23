from pydantic import BaseModel, ConfigDict
from datetime import datetime


class FavoriteCreate(BaseModel):
    item_type: str  # knowledge / announcement / community
    item_id: int
    title: str
    category: str | None = None
    summary: str | None = None
    link: str | None = None


class FavoriteOut(BaseModel):
    id: int
    item_type: str
    item_id: int
    title: str
    category: str | None = None
    summary: str | None = None
    link: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ResourceItem(BaseModel):
    item_type: str
    item_id: int
    title: str
    category: str | None = None
    summary: str | None = None
    link: str | None = None
    source: str | None = None
    extra: dict = {}


class RecommendItem(ResourceItem):
    reason: str = ""