from datetime import date
from sqlalchemy import String, Text, Date, Integer, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class RecordType(str, enum.Enum):
    HONOR = "honor"
    COMPETITION = "competition"
    PRACTICE = "practice"
    PAPER = "paper"
    ACHIEVEMENT = "achievement"


class GrowthRecord(Base):
    __tablename__ = "growth_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    type: Mapped[RecordType] = mapped_column(SAEnum(RecordType))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date)
    attachment_url: Mapped[str | None] = mapped_column(String(255))

    # 荣誉
    honor_level: Mapped[str | None] = mapped_column(String(20))

    # 竞赛
    organizer: Mapped[str | None] = mapped_column(String(200))
    competition_level: Mapped[str | None] = mapped_column(String(100))

    # 实践
    practice_type: Mapped[str | None] = mapped_column(String(100))
    practice_certificate: Mapped[str | None] = mapped_column(Text)

    # 论文
    paper_type: Mapped[str | None] = mapped_column(String(50))
    paper_name: Mapped[str | None] = mapped_column(String(300))
    first_author: Mapped[str | None] = mapped_column(String(100))
    second_author: Mapped[str | None] = mapped_column(String(100))
    third_author: Mapped[str | None] = mapped_column(String(100))

    # 成果
    achievement_type: Mapped[str | None] = mapped_column(String(50))
    achievement_name: Mapped[str | None] = mapped_column(String(300))


class StudentProject(Base):
    __tablename__ = "student_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    project_name: Mapped[str] = mapped_column(String(200))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_team: Mapped[bool] = mapped_column(Boolean, default=False)
    team_members: Mapped[str | None] = mapped_column(String(500))
    attachment_url: Mapped[str | None] = mapped_column(String(255))
