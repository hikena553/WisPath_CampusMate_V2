from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decode_access_token
from app.models.user import User
from app.models.message import Message
from app.schemas.message import MessageSend, MessageOut, ConversationOut
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.websocket("/ws")
async def websocket_chat(ws: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload:
        await ws.close(code=4001)
        return
    user_id = int(payload.get("sub", 0))
    if not user_id:
        await ws.close(code=4001)
        return
    await manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception:
        manager.disconnect(user_id)


@router.post("/send")
async def send_message(data: MessageSend, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    receiver = db.query(User).filter(User.id == data.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="接收用户不存在")
    msg = Message(sender_id=user.id, receiver_id=data.receiver_id, content=data.content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    created_at = msg.created_at.isoformat() if msg.created_at else ""
    await manager.send_json(data.receiver_id, {
        "type": "new_message",
        "id": msg.id,
        "sender_id": user.id,
        "sender_name": user.name,
        "content": data.content,
        "created_at": created_at,
    })
    return {"id": msg.id, "created_at": created_at}

@router.get("/conversations", response_model=list[ConversationOut])
def get_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sent_ids = db.query(Message.receiver_id).filter(Message.sender_id == user.id).distinct().subquery()
    received_ids = db.query(Message.sender_id).filter(Message.receiver_id == user.id).distinct().subquery()
    all_ids = db.query(sent_ids.c.receiver_id).union(db.query(received_ids.c.sender_id)).subquery()
    other_users = db.query(User).filter(User.id.in_(db.query(all_ids))).all()
    result = []
    for other in other_users:
        last_msg = db.query(Message).filter(
            or_(
                (Message.sender_id == user.id) & (Message.receiver_id == other.id),
                (Message.sender_id == other.id) & (Message.receiver_id == user.id)
            )
        ).order_by(Message.created_at.desc()).first()
        unread = db.query(Message).filter(
            Message.sender_id == other.id, Message.receiver_id == user.id, Message.read == False
        ).count()
        result.append(ConversationOut(
            user_id=other.id,
            user_name=other.name,
            user_avatar=other.avatar,
            last_message=last_msg.content[:80] if last_msg else "",
            last_message_time=last_msg.created_at if last_msg else None,
            unread_count=unread,
        ))
    return result

@router.get("/{user_id}", response_model=list[MessageOut])
def get_messages(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(
        or_(
            (Message.sender_id == user.id) & (Message.receiver_id == user_id),
            (Message.sender_id == user_id) & (Message.receiver_id == user.id)
        )
    ).order_by(Message.created_at.asc()).all()
    return [MessageOut(
        id=m.id, sender_id=m.sender_id, receiver_id=m.receiver_id,
        content=m.content, read=m.read, created_at=m.created_at
    ) for m in msgs]

@router.put("/read/{user_id}")
def mark_read(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Message).filter(
        Message.sender_id == user_id, Message.receiver_id == user.id, Message.read == False
    ).update({"read": True})
    db.commit()
    return {"message": "marked read"}
