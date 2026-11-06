from datetime import datetime
from pydantic import BaseModel, ConfigDict

class MessageSend(BaseModel):
    receiver_id: int
    content: str

class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    read: bool
    created_at: datetime
    # 发送者头像：会话列表（ConversationOut.user_avatar）与聊天气泡共用同一份用户头像，
    # 缺了它气泡只能退回首字母，和列表里的头像对不上。
    sender_avatar: str | None = None
    model_config = ConfigDict(from_attributes=True)

class ConversationOut(BaseModel):
    user_id: int
    user_name: str
    user_avatar: str | None = None
    last_message: str
    last_message_time: datetime | None = None
    unread_count: int = 0
    # 对方当前是否在线（有活跃 WebSocket 连接即视为已登录在线）
    online: bool = False
