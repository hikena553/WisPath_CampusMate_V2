from datetime import datetime

from pydantic import BaseModel


class CronTaskUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None


class CronTaskOut(BaseModel):
    id: int
    name: str
    prompt: str
    schedule_kind: str
    schedule_text: str
    hour: int | None = None
    minute: int | None = None
    weekday: int | None = None
    interval_hours: int | None = None
    enabled: bool
    conversation_id: int
    last_run_at: datetime | None = None
    next_run_at: datetime
