"""匿名工作问卷互评：辅导员互评 / 学生评辅导员。

匿名硬约束：
- 答卷表不存任何提交人字段（无 submitter_id）；
- 防重靠匿名令牌（HMAC 摘要），而非身份，令牌不出接口；
- 结果只返回聚合分布，且样本量低于阈值时不出分布，避免小样本反推。
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PeerSurveyTargetType(str, enum.Enum):
    PEER = "peer"        # 辅导员互评
    STUDENT = "student"  # 学生评辅导员


class PeerSurveyStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class PeerSurvey(Base):
    __tablename__ = "peer_surveys"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    target_type: Mapped[PeerSurveyTargetType] = mapped_column(
        SAEnum(PeerSurveyTargetType), default=PeerSurveyTargetType.PEER
    )
    period: Mapped[str | None] = mapped_column(String(64), default=None)
    # 题目定义 JSON：[{"key": "care", "label": "关心学生", "max": 5}]
    questions_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[PeerSurveyStatus] = mapped_column(
        SAEnum(PeerSurveyStatus), default=PeerSurveyStatus.DRAFT, index=True
    )
    created_by: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class PeerSurveyResponse(Base):
    __tablename__ = "peer_survey_responses"
    __table_args__ = (
        # 同一问卷 + 同一被评人 + 同一匿名令牌 只允许一条：防重但不落身份
        UniqueConstraint(
            "survey_id", "target_teacher_id", "anonymous_token",
            name="uq_peer_response_token",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(index=True)
    target_teacher_id: Mapped[int] = mapped_column(index=True)
    # 评分 JSON：{"care": 5, "fair": 4, ...}
    scores_json: Mapped[str] = mapped_column(Text, default="{}")
    suggestion: Mapped[str | None] = mapped_column(Text, default=None)
    # 匿名令牌（HMAC 摘要），非身份；接口任何返回体都不含该字段
    anonymous_token: Mapped[str] = mapped_column(String(64), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)