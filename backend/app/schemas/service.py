from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any


class TicketCreate(BaseModel):
    type: str
    title: str
    content: str = ""
    applicant_name: str = ""
    applicant_no: str = ""
    applicant_college: str = ""
    form_data: dict[str, Any] | None = None
    attachments: list[str] | None = None


class TicketOut(BaseModel):
    id: int
    applicant_id: int
    applicant_name: str
    applicant_no: str
    applicant_college: str
    type: str
    title: str
    content: str
    form_data: dict[str, Any] | None = None
    attachments: list[str] | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketApprove(BaseModel):
    action: str
    comment: str | None = None
