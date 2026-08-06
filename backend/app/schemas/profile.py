from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class BehavioralPatterns(BaseModel):
    leave_frequency: str = "normal"
    crisis_trend: str = "stable"
    grade_trajectory: str = "stable"
    engagement_level: str = "normal"
    inactive_days: int = 0


class KeyInsight(BaseModel):
    dimension: str
    type: str
    content: str


class ProfileSnapshotOut(BaseModel):
    id: int
    student_id: int
    snapshot_date: date
    academic_score: float
    psychological_risk: float
    engagement_score: float
    growth_score: float
    overall_risk: float
    behavioral_patterns: dict | None = None
    key_insights: list | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfileTrendPoint(BaseModel):
    date: str
    academic_score: float
    psychological_risk: float
    engagement_score: float
    growth_score: float
    overall_risk: float


class CohortComparison(BaseModel):
    dimension: str
    student_score: float
    cohort_avg: float
    percentile: float


class ProfileTrendsOut(BaseModel):
    trends: list[ProfileTrendPoint]


class CohortComparisonOut(BaseModel):
    comparisons: list[CohortComparison]
