from datetime import datetime
from sqlalchemy import String, Float, Integer, Date, Time, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class College(Base):
    """学院"""
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, comment="学院代码，如 SE")
    description: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    majors = relationship("Major", back_populates="college", cascade="all, delete-orphan")


class Major(Base):
    """专业"""
    __tablename__ = "majors"
    __table_args__ = (UniqueConstraint("college_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(20), comment="专业代码")
    description: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    college = relationship("College", back_populates="majors")
    class_groups = relationship("ClassGroup", back_populates="major", cascade="all, delete-orphan")


class ClassGroup(Base):
    """班级"""
    __tablename__ = "class_groups"
    __table_args__ = (UniqueConstraint("major_id", "grade", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    major_id: Mapped[int] = mapped_column(ForeignKey("majors.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), comment="班级名称，如 2024级软件工程1班")
    grade: Mapped[int] = mapped_column(Integer, comment="入学年份")
    student_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    major = relationship("Major", back_populates="class_groups")
    courses = relationship("Course", back_populates="class_group", cascade="all, delete-orphan")
    students = relationship("User", back_populates="class_group")


class Course(Base):
    """课程 - 按班级维度"""
    __tablename__ = "courses"
    __table_args__ = (Index("ix_courses_class_semester", "class_group_id", "semester"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    class_group_id: Mapped[int] = mapped_column(ForeignKey("class_groups.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    teacher: Mapped[str] = mapped_column(String(50))
    location: Mapped[str] = mapped_column(String(100))
    day_of_week: Mapped[int] = mapped_column(Integer, comment="星期几 1-7")
    start_period: Mapped[int] = mapped_column(Integer)
    end_period: Mapped[int] = mapped_column(Integer)
    week_start: Mapped[int] = mapped_column(Integer)
    week_end: Mapped[int] = mapped_column(Integer)
    semester: Mapped[str] = mapped_column(String(20), comment="学期，如 2024-2025-1")
    credit: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    class_group = relationship("ClassGroup", back_populates="courses")


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    course_name: Mapped[str] = mapped_column(String(100))
    score: Mapped[float] = mapped_column(Float)
    credit: Mapped[float] = mapped_column(Float)
    gpa: Mapped[float] = mapped_column(Float)
    semester: Mapped[str] = mapped_column(String(20))


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    course_name: Mapped[str] = mapped_column(String(100))
    exam_date: Mapped[str] = mapped_column(Date)
    start_time: Mapped[str] = mapped_column(Time)
    end_time: Mapped[str] = mapped_column(Time)
    location: Mapped[str] = mapped_column(String(100))
