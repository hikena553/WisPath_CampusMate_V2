from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmotionRecord(Base):
    """学生通话/交互过程中的人脸情绪识别记录（情绪垃圾桶数据源）"""
    __tablename__ = "emotion_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    # 情绪标签：neutral / happy / sad / angry / fearful / disgusted / surprised
    emotion: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # 来源场景：voice_call（语音通话）/ manual（手动）等
    source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )