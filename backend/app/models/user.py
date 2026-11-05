from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    # 资讯账号（运营用机器人身份）：在交流社区自动发爬取资讯/每日汇总，禁止登录
    MEDIA = "media"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(50))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), index=True)
    college: Mapped[str | None] = mapped_column(String(100))
    avatar: Mapped[str | None] = mapped_column(String(255))
    tutor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None, index=True)
    skills_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    gender: Mapped[str | None] = mapped_column(String(10))
    political_status: Mapped[str | None] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(50))
    hometown: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    qq: Mapped[str | None] = mapped_column(String(20), comment="绑定的 QQ 号，用于一键登录")
    # QQ 互联 OAuth 的 openid：真正的 QQ 授权登录凭据（与手动填写的 QQ 号是两回事）
    qq_openid: Mapped[str | None] = mapped_column(String(64), index=True, comment="QQ 互联 openid，用于 OAuth 登录")
    qq_nickname: Mapped[str | None] = mapped_column(String(64), comment="QQ 互联授权后获取的昵称")
    department: Mapped[str | None] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer)
    class_name: Mapped[str | None] = mapped_column(String(50), default=None, comment="班级")
    class_group_id: Mapped[int | None] = mapped_column(ForeignKey("class_groups.id"), default=None, index=True, comment="关联班级")
    password_changed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已修改过密码")
    signature: Mapped[str | None] = mapped_column(String(60), default=None, comment="个性签名，展示在个人中心与个人主页")

    @property
    def qq_bound(self) -> bool:
        """是否已完成 QQ 互联授权绑定（OAuth openid 存在）。"""
        return bool(self.qq_openid)

    # 关系
    class_group = relationship("ClassGroup", back_populates="students")
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user")
    feedbacks = relationship("Feedback", foreign_keys="Feedback.user_id", back_populates="user")
