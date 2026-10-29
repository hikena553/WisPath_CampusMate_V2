from datetime import datetime

from pydantic import BaseModel


class CronTaskCreate(BaseModel):
    """手动新建（移动端表单）入参；周期字段语义与聊天工具一致，hour/minute 为北京时间。"""

    name: str
    prompt: str
    schedule_kind: str
    hour: int | None = None
    minute: int | None = None
    weekday: int | None = None
    interval_hours: int | None = None


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
