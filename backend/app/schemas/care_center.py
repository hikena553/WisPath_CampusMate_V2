"""人文关怀中心的请求 / 响应模型。"""
from datetime import date

from pydantic import BaseModel, Field


# ── 关怀日历事件 ──────────────────────────────────────────────


class CareEventCreate(BaseModel):
    event_type: str = "other"
    event_date: date
    title: str = Field(min_length=1, max_length=200)
    note: str | None = None
    student_id: int | None = None


class CareEventOut(BaseModel):
    id: int
    teacher_id: int
    student_id: int | None = None
    student_name: str = ""
    event_type: str
    event_date: date
    title: str
    note: str | None = None
    auto_generated: bool = False
    created_at: str = ""


# ── 家访记录 ──────────────────────────────────────────────────


class HomeVisitCreate(BaseModel):
    student_id: int
    visit_date: date
    method: str = "phone"
    content: str = Field(min_length=1)
    follow_up: str | None = None
    # 可选：同步到家校沟通台账（默认关，保持向后兼容）
    sync_to_guardian: bool = False


class HomeVisitUpdate(BaseModel):
    """家访记录更新：回访状态 / 后续计划 / 内容（局部更新，未传字段不动）。"""

    content: str | None = Field(default=None, min_length=1)
    follow_up: str | None = None
    follow_up_status: str | None = None


class HomeVisitOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    teacher_id: int
    visit_date: date
    method: str
    content: str
    follow_up: str | None = None
    follow_up_status: str = "pending"
    follow_up_done_at: str = ""
    created_at: str = ""


# ── 正向激励 ──────────────────────────────────────────────────


class PraiseCreate(BaseModel):
    student_id: int
    praise_type: str = "praise"
    badge_name: str | None = Field(default=None, max_length=50)
    reason: str = Field(min_length=1)
    occurred_on: date | None = None


class PraiseOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    teacher_id: int
    praise_type: str
    badge_name: str | None = None
    reason: str
    occurred_on: date | None = None
    created_at: str = ""


# ── 概览 ──────────────────────────────────────────────────────


class CareCenterOverview(BaseModel):
    """关怀中心首页概览（当月/累计口径）。"""

    month: str = ""
    event_count: int = 0
    visit_count: int = 0
    praise_count: int = 0
    # 待回访家访数（follow_up_status == pending），语义修正
    pending_events: int = 0
    # 未来（含今天）的关怀事项数
    upcoming_events: int = 0
    # 已回访家访数（follow_up_status == done）
    closed_visit_count: int = 0


# ── 学生端「我的关怀」（只读） ────────────────────────────────


class StudentCareSummary(BaseModel):
    praises: int = 0
    visits: int = 0
    records: int = 0


class StudentCarePraiseOut(BaseModel):
    id: int
    praise_type: str = "praise"
    badge_name: str | None = None
    reason: str = ""
    occurred_on: date | None = None
    teacher_name: str = ""


class StudentCareRecordOut(BaseModel):
    id: int
    record_type: str = "care"
    content: str = ""
    created_at: str = ""
    teacher_name: str = ""


class StudentCareVisitOut(BaseModel):
    id: int
    visit_date: date
    method: str = "phone"
    content: str = ""
    follow_up: str | None = None
    follow_up_status: str = "pending"
    teacher_name: str = ""