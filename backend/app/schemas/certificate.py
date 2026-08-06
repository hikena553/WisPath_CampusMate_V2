from datetime import date
from pydantic import BaseModel, ConfigDict


class CertificateCreate(BaseModel):
    title: str
    competition_name: str | None = None
    award_level: str | None = None
    date: date | None = None
    description: str | None = None
    image_url: str | None = None


class CertificateOut(BaseModel):
    id: int
    student_id: int
    title: str
    competition_name: str | None = None
    award_level: str | None = None
    date: date | None = None
    description: str | None = None
    image_url: str | None = None
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)
