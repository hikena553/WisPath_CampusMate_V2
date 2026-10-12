from pydantic import BaseModel, ConfigDict


class CampusSceneryOut(BaseModel):
    id: int
    title: str
    image_url: str
    description: str | None = None
    location: str | None = None
    area: str

    model_config = ConfigDict(from_attributes=True)


class AnnouncementOut(BaseModel):
    title: str
    date: str | None = None
    url: str | None = None


class GalleryImageOut(BaseModel):
    title: str
    image_url: str
    campus: str  # 安州 / 游仙


class CampusArticleLink(BaseModel):
    title: str
    url: str
    date: str | None = None


class CampusArticleOut(BaseModel):
    """站内阅读器数据：文章正文或列表页链接清单"""
    kind: str  # article / links
    title: str
    date: str | None = None
    content_html: str | None = None
    links: list[CampusArticleLink] = []
    source_url: str
