from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FigureCategory:
    STUDENT = "student"
    TEACHER = "teacher"
    ALUMNI = "alumni"


class CampusFigure(Base):
    __tablename__ = "campus_figures"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(100))
    avatar: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20))
    proofs: Mapped[str | None] = mapped_column(Text, default=None)


class CampusArea:
    ANZHOU = "anzhou"
    YOUXIAN = "youxian"


class CampusScenery(Base):
    __tablename__ = "campus_sceneries"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    image_url: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(100))
    area: Mapped[str] = mapped_column(String(20), default=CampusArea.ANZHOU)
