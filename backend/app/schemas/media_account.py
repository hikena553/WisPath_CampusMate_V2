"""资讯账号管理 DTO：管理端「资讯管理 → 账号管理」页签专用。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MediaAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="展示名（社区帖子作者名）")
    avatar: str | None = Field(default=None, max_length=255, description="头像 URL，空则按名字首字回退")
    signature: str | None = Field(default=None, max_length=60, description="个性签名")
    content_scope: list[str] | None = Field(default=None, description="绑定的资讯分类（空=全部）")
    relay_interval_minutes: int = Field(
        default=30, description="逐条转发频率（分钟）：30/60/180/360/720/1440，0=不逐条转发仅发每日汇总",
    )
    is_enabled: bool = True


class MediaAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    avatar: str | None = Field(default=None, max_length=255)
    signature: str | None = Field(default=None, max_length=60)
    content_scope: list[str] | None = None
    relay_interval_minutes: int | None = None
    is_enabled: bool | None = None


class MediaAccountOut(BaseModel):
    id: int
    user_id: int
    username: str
    name: str
    avatar: str | None = None
    signature: str | None = None
    is_enabled: bool = True
    station_connected: bool = True
    content_scope: list[str] | None = None
    relay_interval_minutes: int = 30
    post_count: int = 0
    last_posted_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MediaPublishResult(BaseModel):
    """发帖动作结果：发布成功返回帖子 id，幂等跳过时 posted=False。"""
    posted: bool
    message: str
    post_id: int | None = None
    title: str | None = None


class MediaStationUpdate(BaseModel):
    """资讯站（画布根节点）配置更新。"""
    name: str | None = Field(default=None, min_length=1, max_length=60)
    is_enabled: bool | None = None
    ingest_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    digest_hour: int | None = Field(default=None, ge=0, le=23)
    publish_mode: str | None = Field(default=None, pattern="^(auto|digest|manual)$")
    description: str | None = Field(default=None, max_length=200)


class MediaStationLinkToggle(BaseModel):
    """资讯站 ↔ 资讯账号 连接线开合。"""
    connected: bool


class MediaSourceLinkCreate(BaseModel):
    """资讯账号 → 资讯源 连接线创建。"""
    feed_source_id: int
    name: str | None = Field(default=None, max_length=60)


class MediaSourceLinkUpdate(BaseModel):
    """连接线重命名 / 开合。"""
    name: str | None = Field(default=None, min_length=1, max_length=60)
    enabled: bool | None = None

