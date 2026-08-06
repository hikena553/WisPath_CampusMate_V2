from datetime import date
from pydantic import BaseModel, ConfigDict


class LeaveRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str
    leave_type: str


class LeaveRequestOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    start_date: date
    end_date: date
    reason: str
    leave_type: str
    status: str
    reject_reason: str | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class LeaveApprove(BaseModel):
    action: str  # 操作类型：approve或reject
    reject_reason: str | None = None
