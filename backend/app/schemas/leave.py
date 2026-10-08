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
    return_confirmed: bool = False
    return_confirmed_at: str | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class LeaveApprove(BaseModel):
    action: str  # 操作类型：approve或reject
    reject_reason: str | None = None


class LeaveStatsItem(BaseModel):
    key: str
    label: str
    total: int = 0
    approved: int = 0
    rejected: int = 0
    pending: int = 0


class LeaveStats(BaseModel):
    total: int = 0
    approved: int = 0
    rejected: int = 0
    pending: int = 0
    awaiting_return: int = 0
    by_type: list[LeaveStatsItem] = []
    by_class: list[LeaveStatsItem] = []
