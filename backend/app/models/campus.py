from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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


class CampusImpressionItem(Base):
    """教务处/学院/图书馆爬取结果统一存储"""
    __tablename__ = "campus_impression_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), index=True)      # jwc_entries/jwc_jxdt/jwc_tzgg/jwc_gjxx/jwc_jxjs/college_news/library
    college_key: Mapped[str | None] = mapped_column(String(50), index=True, default=None)
    title: Mapped[str] = mapped_column(String(200))
    image_url: Mapped[str | None] = mapped_column(String(500), default=None)
    url: Mapped[str] = mapped_column(String(500))
    date: Mapped[str | None] = mapped_column(String(20), default=None)
    fetched_at: Mapped[str] = mapped_column(String(30))
