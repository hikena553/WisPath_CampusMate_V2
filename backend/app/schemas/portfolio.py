from pydantic import BaseModel, ConfigDict
from datetime import date as datetime_date, datetime


class CertificateCreate(BaseModel):
    title: str
    competition_name: str | None = None
    award_level: str | None = None
    date: str | None = None
    description: str | None = None
    image_url: str | None = None


class CertificateOut(BaseModel):
    id: int
    student_id: int
    title: str
    competition_name: str | None = None
    award_level: str | None = None
    date: datetime_date | None = None
    description: str | None = None
    image_url: str | None = None
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ResumeCreate(BaseModel):
    filename: str
    url: str
    file_size: int | None = None


class ResumeOut(BaseModel):
    id: int
    filename: str
    url: str
    file_size: int | None = None
    is_current: int = 1
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)