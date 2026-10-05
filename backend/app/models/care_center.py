"""人文关怀中心：关怀日历事件 / 家访记录 / 正向激励，三子域同模块内聚。

- CareEvent：关怀日历事项（生日 / 困难学生 / 学业预警 / 其他），支持自动生成与手动添加；
- HomeVisitRecord：家访记录（时间 / 方式 / 对象 / 内容 / 后续计划）；
- PraiseRecord：正向激励（表扬 / 徽章）。

匿名求助入口不建新表，复用既有 Feedback 匿名通道，本模块只提供入口。
"""
import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CareEventType(str, enum.Enum):
    BIRTHDAY = "birthday"      # 生日关怀
    DIFFICULTY = "difficulty"  # 困难学生
    ACADEMIC = "academic"      # 学业预警
    OTHER = "other"


class HomeVisitMethod(str, enum.Enum):
    HOME = "home"      # 实地家访
    PHONE = "phone"    # 电话
    VIDEO = "video"    # 视频
    SCHOOL = "school"  # 校内约谈家长
    OTHER = "other"


class PraiseType(str, enum.Enum):
    PRAISE = "praise"  # 口头 / 书面表扬
    BADGE = "badge"    # 徽章激励


class CareEvent(Base):
    __tablename__ = "care_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(index=True)
    student_id: Mapped[int | None] = mapped_column(index=True, default=None)
    event_type: Mapped[CareEventType] = mapped_column(
        SAEnum(CareEventType), default=CareEventType.OTHER, index=True
    )
    event_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text, default=None)
    auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HomeVisitRecord(Base):
    __tablename__ = "home_visit_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    teacher_id: Mapped[int] = mapped_column(index=True)
    visit_date: Mapped[date] = mapped_column(Date, index=True)
    method: Mapped[HomeVisitMethod] = mapped_column(
        SAEnum(HomeVisitMethod), default=HomeVisitMethod.PHONE
    )
    content: Mapped[str] = mapped_column(Text)
    follow_up: Mapped[str | None] = mapped_column(Text, default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PraiseRecord(Base):
    __tablename__ = "praise_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    teacher_id: Mapped[int] = mapped_column(index=True)
    praise_type: Mapped[PraiseType] = mapped_column(SAEnum(PraiseType), default=PraiseType.PRAISE)
    badge_name: Mapped[str | None] = mapped_column(String(50), default=None)
    reason: Mapped[str] = mapped_column(Text)
    occurred_on: Mapped[date | None] = mapped_column(Date, default=None, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)