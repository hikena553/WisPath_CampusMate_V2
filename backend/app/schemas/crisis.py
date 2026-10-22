from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional


class AIDialogSummaryOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    summary: str
    level: str
    keywords_matched: str | None = None
    resolved: bool
    created_at: str | datetime
    intervention_type: str | None = None
    intervention_note: str | None = None
    resolved_by: int | None = None
    resolved_at: str | datetime | None = None
    follow_up_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CrisisResolve(BaseModel):
    resolved: bool = True


class CrisisInterveneIn(BaseModel):
    intervention_type: str
    intervention_note: str | None = None
    follow_up_date: str | None = None
    resolved: bool = True


# ============================ 心理预警聚合分析（工作台态势） ============================

class CrisisLevelDistOut(BaseModel):
    """等级分布：四档预警条数"""
    severe: int = 0
    moderate: int = 0
    mild: int = 0
    normal: int = 0


class CrisisStageOut(BaseModel):
    """处置阶段：发现 → 干预 → 随访 → 闭环"""
    found: int = 0
    intervened: int = 0
    following: int = 0
    closed: int = 0


class CrisisTrendPointOut(BaseModel):
    """趋势折线单点：day 为 MM-DD"""
    day: str
    count: int = 0


class CrisisKeywordOut(BaseModel):
    """词云词条：word 为分词结果，count 为词频"""
    word: str
    count: int = 0


class CrisisSlaItemOut(BaseModel):
    """超时（24 小时内需办结）的未闭环预警条目"""
    id: int
    student_name: str = ""
    summary: str = ""
    created_at: str = ""


class CrisisSlaOut(BaseModel):
    """处置时限：未闭环且创建超 24 小时计 overdue，12~24 小时计 due_soon"""
    overdue: int = 0
    due_soon: int = 0
    items: list[CrisisSlaItemOut] = Field(default_factory=list)


class CrisisAnalyticsOut(BaseModel):
    """心理预警工作台聚合分析出参（全部为真实统计，不做硬编码）"""
    level_dist: CrisisLevelDistOut = Field(default_factory=CrisisLevelDistOut)
    stage: CrisisStageOut = Field(default_factory=CrisisStageOut)
    trend: list[CrisisTrendPointOut] = Field(default_factory=list)
    keywords: list[CrisisKeywordOut] = Field(default_factory=list)
    sla: CrisisSlaOut = Field(default_factory=CrisisSlaOut)
    total: int = 0
    unresolved: int = 0
    high_risk: int = 0
