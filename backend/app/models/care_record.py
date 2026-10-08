"""教师侧写记录：关怀记录 / 谈心谈话 / 评语。

同时是"教师工作量统计"的唯一数据源，成长看板的工作量趋势直接读本表，不再另建计数表。
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CareRecordType(str, enum.Enum):
    CARE = "care"
    TALK = "talk"
    COMMENT = "comment"


class CareRecord(Base):
    __tablename__ = "care_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    teacher_id: Mapped[int] = mapped_column(index=True)
    record_type: Mapped[CareRecordType] = mapped_column(
        SAEnum(CareRecordType), default=CareRecordType.CARE
    )
    content: Mapped[str] = mapped_column(Text)
    # 是否仅教师可见（学生档案中默认不向学生展示评语草稿）
    is_private: Mapped[bool] = mapped_column(Boolean, default=True)
    # 回链到触发本次记录的任务，便于闭环追溯
    task_id: Mapped[int | None] = mapped_column(default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
