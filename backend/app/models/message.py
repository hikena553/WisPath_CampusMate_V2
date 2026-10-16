from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MessageSessionPin(Base):
    """消息会话置顶（用户级持久化，跨端同步）。

    session_key 形如 ``g-<groupId>``（群聊）/ ``s-<userId>``（单聊）；
    服务端只存不解析该 key，排序与展示由前端按 key 匹配。
    """

    __tablename__ = "message_session_pins"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pinned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MessageSessionHidden(Base):
    """消息会话删除（用户级隐藏，跨端同步）。

    只把会话从**本人**的列表里移除：聊天记录保留、对方不受影响。
    ``hidden_upto_id`` 记录删除时刻该会话的最后一条消息 id（隐藏水位），
    一旦出现比水位更新的消息，会话自动重新出现在列表里——即"删除条目"
    而非"删除聊天记录"。
    """

    __tablename__ = "message_session_hidden"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hidden_upto_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hidden_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
