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
    model_config = ConfigDict(from_attributes=True)

class ConversationOut(BaseModel):
    user_id: int
    user_name: str
    user_avatar: str | None = None
    last_message: str
    last_message_time: datetime | None = None
    unread_count: int = 0
