"""教师成长档案（e-Portfolio）：工作案例 / 荣誉 / 培训研修 / 工作研究成果。

四段式沉淀：证据 → 反思 → 展示 → 评价；评价段预留 reviewer_id / review_comment，
为后续匿名互评接入留好挂点。
"""
import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PortfolioItemType(str, enum.Enum):
    CASE = "case"          # 工作案例
    HONOR = "honor"        # 荣誉表彰
    TRAINING = "training"  # 培训研修
    RESEARCH = "research"  # 工作研究成果


class PortfolioVisibility(str, enum.Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class TeacherPortfolioItem(Base):
    __tablename__ = "teacher_portfolio_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(index=True)
    item_type: Mapped[PortfolioItemType] = mapped_column(
        SAEnum(PortfolioItemType), default=PortfolioItemType.CASE, index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    # 证据：附件 / 链接，JSON 数组文本 [{"name": "...", "url": "..."}]
    evidence_json: Mapped[str | None] = mapped_column(Text, default=None)
    reflection: Mapped[str | None] = mapped_column(Text, default=None)
    occurred_on: Mapped[date | None] = mapped_column(Date, default=None)
    visibility: Mapped[PortfolioVisibility] = mapped_column(
        SAEnum(PortfolioVisibility), default=PortfolioVisibility.PRIVATE
    )
    # 评价段（预留，供互评模块回填）
    reviewer_id: Mapped[int | None] = mapped_column(default=None)
    review_comment: Mapped[str | None] = mapped_column(Text, default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )