"""教师成长档案的请求 / 响应模型。"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EvidenceItem(BaseModel):
    """证据条目：附件或外链。"""

    name: str = ""
    url: str


class PortfolioItemCreate(BaseModel):
    item_type: str = "case"
    title: str = Field(min_length=1, max_length=200)
    evidence: list[EvidenceItem] = []
    reflection: str | None = None
    occurred_on: date | None = None
    visibility: str = "private"


class PortfolioItemUpdate(BaseModel):
    item_type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    evidence: list[EvidenceItem] | None = None
    reflection: str | None = None
    occurred_on: date | None = None
    visibility: str | None = None


class PortfolioItemOut(BaseModel):
    id: int
    teacher_id: int
    item_type: str
    title: str
    evidence: list[EvidenceItem] = []
    reflection: str | None = None
    occurred_on: date | None = None
    visibility: str
    reviewer_id: int | None = None
    review_comment: str | None = None
    created_at: str
    updated_at: str = ""

    model_config = ConfigDict(from_attributes=True)


class PortfolioTypeStat(BaseModel):
    type: str
    label: str
    count: int = 0


class PortfolioReport(BaseModel):
    """成长报告数据：按类型聚合 + 时间线，供前端打印导出。"""

    teacher_id: int
    teacher_name: str = ""
    total: int = 0
    by_type: list[PortfolioTypeStat] = []
    items: list[PortfolioItemOut] = []
    generated_at: str = ""