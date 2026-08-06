from pydantic import BaseModel, ConfigDict


class CampusFigureOut(BaseModel):
    id: int
    name: str
    title: str
    avatar: str
    description: str
    category: str
    proofs: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CampusFigureCreate(BaseModel):
    name: str
    title: str
    avatar: str = ""
    description: str
    category: str
    proofs: str = ""


class CampusFigureUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    avatar: str | None = None
    description: str | None = None
    category: str | None = None
    proofs: str | None = None


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
