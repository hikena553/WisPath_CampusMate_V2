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
