from datetime import date, datetime

from pydantic import BaseModel


class StudySessionCreate(BaseModel):
    mode: str = "focus"
    task_title: str | None = None
    planned_minutes: int = 25
    actual_minutes: int = 0
    completed: bool = True
    started_at: datetime | None = None
    ended_at: datetime | None = None


class StudySessionOut(BaseModel):
    id: int
    mode: str
    task_title: str | None = None
    planned_minutes: int
    actual_minutes: int
    completed: bool
    study_date: date
    start_time: str | None = None
    end_time: str | None = None
    created_at: datetime | None = None


class StudyDayOut(BaseModel):
    date: date
    focus_minutes: int = 0
    session_count: int = 0


class StudyTodayOut(BaseModel):
    date: date
    focus_minutes: int = 0
    session_count: int = 0


class StudyOverviewOut(BaseModel):
    today: StudyTodayOut
    days: list[StudyDayOut]
    sessions: list[StudySessionOut]
