from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(50))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))
    college: Mapped[str | None] = mapped_column(String(100))
    avatar: Mapped[str | None] = mapped_column(String(255))
    tutor_id: Mapped[int | None] = mapped_column(default=None)
    skills_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    gender: Mapped[str | None] = mapped_column(String(10))
    political_status: Mapped[str | None] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(50))
    hometown: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    department: Mapped[str | None] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer)
    class_name: Mapped[str | None] = mapped_column(String(50), default=None, comment="班级")
    class_group_id: Mapped[int | None] = mapped_column(ForeignKey("class_groups.id"), default=None, index=True, comment="关联班级")
    password_changed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已修改过密码")

    # 关系
    class_group = relationship("ClassGroup", back_populates="students")
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user")
    feedbacks = relationship("Feedback", foreign_keys="Feedback.user_id", back_populates="user")
