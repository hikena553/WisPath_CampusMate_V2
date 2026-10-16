import json
import logging
from datetime import datetime, timezone
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db

logger = logging.getLogger(__name__)
from app.core.deps import get_current_user, AUTH_COOKIE_NAME
from app.core.security import decode_access_token, is_token_revoked
from app.models.user import User
from app.models.message import Message, MessageSessionPin, MessageSessionHidden
from app.models.group import Group, GroupMember, GroupMessage
from app.models.notification import Notification
from app.schemas.message import MessageSend, MessageOut, ConversationOut
from app.services.session_hidden import hidden_watermarks, is_hidden, hide_session
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _ws_cookie_token(ws: WebSocket) -> str | None:
    """WebSocket 升级请求 Cookie 中提取认证 token（httpOnly Cookie 通道）。"""
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in (ws.headers.raw or [])}
    cookie = headers.get("cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith(f"{AUTH_COOKIE_NAME}="):
            return unquote(part[len(AUTH_COOKIE_NAME) + 1:])
    return None


@router.websocket("/ws")
async def websocket_chat(ws: WebSocket, token: str | None = Query(None), db: Session = Depends(get_db)):
    # 认证：Query 参数优先，其次 httpOnly Cookie（刷新后内存 token 为空时靠 Cookie 保持会话）
    if not token:
        token = _ws_cookie_token(ws)
    payload = decode_access_token(token) if token else None
    if not payload:
        await ws.close(code=4001)
        return
    if token and is_token_revoked(token):
        await ws.close(code=4001)
        return
    user_id = int(payload.get("sub", 0))
    if not user_id:
        await ws.close(code=4001)
        return
    first_connect = await manager.connect(user_id, ws)
    if first_connect:
        # 首次连接（离线 → 在线）：广播上线状态
        await manager.broadcast({"type": "presence", "user_id": user_id, "online": True})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        # 最后一条连接断开（在线 → 离线）：广播下线状态
        if manager.disconnect(user_id, ws):
            await manager.broadcast({"type": "presence", "user_id": user_id, "online": False})


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
    watermarks = hidden_watermarks(db, user.id)
    result = []
    tutor_conv = None
    # 获取用户的 tutor_id
    user_tutor_id = getattr(user, 'tutor_id', None)
    for other in other_users:
        last_msg = db.query(Message).filter(
            or_(
                (Message.sender_id == user.id) & (Message.receiver_id == other.id),
                (Message.sender_id == other.id) & (Message.receiver_id == user.id)
            )
        ).order_by(Message.created_at.desc()).first()
        # 已删除的会话：隐藏水位之后没有新消息就不展示（来了新消息自动恢复）
        if is_hidden(watermarks, f"s-{other.id}", last_msg.id if last_msg else 0):
            continue
        unread = db.query(Message).filter(
            Message.sender_id == other.id, Message.receiver_id == user.id, Message.read == False
        ).count()
        conv = ConversationOut(
            user_id=other.id,
            user_name=other.name,
            user_avatar=other.avatar,
            last_message=last_msg.content[:80] if last_msg else "",
            last_message_time=last_msg.created_at if last_msg else None,
            unread_count=unread,
            online=manager.is_online(other.id),
        )
        # 检查是否是辅导员
        if user_tutor_id and other.id == user_tutor_id:
            tutor_conv = conv
        else:
            result.append(conv)
    # 如果学生有辅导员，将辅导员会话始终置顶
    if user_tutor_id:
        if tutor_conv:
            result.insert(0, tutor_conv)
        elif f"s-{user_tutor_id}" not in watermarks:
            tutor = db.query(User).filter(User.id == user_tutor_id).first()
            if tutor:
                result.insert(0, ConversationOut(
                    user_id=tutor.id,
                    user_name=tutor.name,
                    user_avatar=tutor.avatar,
                    last_message="",
                    last_message_time=None,
                    unread_count=0,
                    online=manager.is_online(tutor.id),
                ))
    return result

# ==================== 会话置顶（服务端持久化，跨端同步） ====================

class SessionPinUpdate(BaseModel):
    session_key: str
    pinned: bool


@router.get("/pins")
def list_session_pins(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户置顶的会话 key 列表（形如 g-<groupId> / s-<userId>）。"""
    rows = (
        db.query(MessageSessionPin)
        .filter(MessageSessionPin.user_id == user.id)
        .order_by(MessageSessionPin.pinned_at.desc())
        .all()
    )
    return {"keys": [r.session_key for r in rows]}


@router.put("/pins")
def set_session_pin(data: SessionPinUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """置顶 / 取消置顶某个会话（幂等）。"""
    key = (data.session_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="session_key 不能为空")
    if len(key) > 64:
        raise HTTPException(status_code=400, detail="session_key 过长")

    existing = db.query(MessageSessionPin).filter(
        MessageSessionPin.user_id == user.id,
        MessageSessionPin.session_key == key,
    ).first()
    if data.pinned and not existing:
        db.add(MessageSessionPin(user_id=user.id, session_key=key))
        db.commit()
    elif not data.pinned and existing:
        db.delete(existing)
        db.commit()
    return {"key": key, "pinned": bool(data.pinned)}


# ==================== 会话删除（用户级隐藏，跨端同步） ====================

@router.delete("/sessions/{session_key}")
def delete_session(session_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除会话条目：只从本人列表移除，聊天记录与对方都不受影响。

    - 记下删除时刻的最后一条消息 id 作为隐藏水位，出现更新的消息时会话自动恢复；
    - 同时把该会话置为已读，避免"列表里看不到条目、导航却一直挂着红点"。
    """
    key = (session_key or "").strip()
    prefix, _, raw_id = key.partition("-")
    if prefix not in ("s", "g") or not raw_id.isdigit():
        raise HTTPException(status_code=400, detail="session_key 格式不正确")
    target_id = int(raw_id)

    if prefix == "s":
        pair = or_(
            (Message.sender_id == user.id) & (Message.receiver_id == target_id),
            (Message.sender_id == target_id) & (Message.receiver_id == user.id),
        )
        last_msg = db.query(Message).filter(pair).order_by(Message.id.desc()).first()
        db.query(Message).filter(
            Message.sender_id == target_id,
            Message.receiver_id == user.id,
            Message.read.is_(False),
        ).update({"read": True}, synchronize_session=False)
        # 无消息的会话（如辅导员占位条目）水位取 0，来消息即恢复
        latest_id = last_msg.id if last_msg else 0
    else:
        member = db.query(GroupMember).filter(
            GroupMember.group_id == target_id,
            GroupMember.user_id == user.id,
        ).first()
        if not member:
            raise HTTPException(status_code=404, detail="群聊不存在或您不是群成员")
        last_msg = db.query(GroupMessage).filter(
            GroupMessage.group_id == target_id,
        ).order_by(GroupMessage.id.desc()).first()
        member.last_read_at = datetime.now(timezone.utc)
        latest_id = last_msg.id if last_msg else 0

    hide_session(db, user.id, key, latest_id)
    db.commit()
    return {"session_key": key, "hidden_upto_id": latest_id}


# ==================== 未读汇总 / 一键清除（导航红点数据源） ====================

def _group_unread_count(db: Session, user: User) -> int:
    """本人所有群的未读合计：与群列表口径一致——免打扰群不计、只算他人发的、晚于 last_read_at。"""
    members = db.query(GroupMember).filter(
        GroupMember.user_id == user.id,
        GroupMember.is_muted.is_(False),
    ).all()
    total = 0
    for m in members:
        last = m.last_read_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
        total += db.query(GroupMessage).filter(
            GroupMessage.group_id == m.group_id,
            GroupMessage.sender_id != user.id,
            GroupMessage.created_at > last,
        ).count()
    return total


@router.get("/unread-summary")
def get_unread_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """全局未读汇总：单聊 + 群聊 + 站内通知，供各端导航红点一次取齐。"""
    chat = db.query(Message).filter(
        Message.receiver_id == user.id,
        Message.read.is_(False),
    ).count()
    group = _group_unread_count(db, user)
    notification = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read.is_(False),
    ).count()
    return {
        "chat": chat,
        "group": group,
        "notification": notification,
        "total": chat + group + notification,
    }


@router.put("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """清除未读提示：单聊全部置已读 + 全部群的 last_read_at 推进到现在。

    站内通知由通知模块的「全部已读」各自负责（/api/notifications/read-all）。
    """
    chat = db.query(Message).filter(
        Message.receiver_id == user.id,
        Message.read.is_(False),
    ).update({"read": True}, synchronize_session=False)
    now = datetime.now(timezone.utc)
    groups = db.query(GroupMember).filter(GroupMember.user_id == user.id).update(
        {"last_read_at": now}, synchronize_session=False
    )
    db.commit()
    return {"message": "已清除未读", "chat": int(chat or 0), "group": int(groups or 0)}


# ==================== 跨会话文件汇总（QQ「文件」页） ====================

_ATTACHMENT_TYPES = ("file", "image", "voice")


def _parse_attachment(content: str | None) -> dict | None:
    """解析消息内容中的结构化附件（文件 / 图片 / 语音），非附件返回 None。"""
    if not content or not content.startswith("{"):
        return None
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("type") not in _ATTACHMENT_TYPES or not data.get("url"):
        return None
    return {
        "type": data["type"],
        "text": data.get("text") or "",
        "url": data["url"],
        "duration": data.get("duration") or 0,
    }


@router.get("/files")
def list_shared_files(
    keyword: str | None = Query(None, description="按文件名搜索"),
    file_type: str | None = Query(None, description="按类型过滤：file / image / voice"),
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """跨会话文件汇总：本人单聊 + 所属群聊中发送过的文件 / 图片 / 语音。

    对应 QQ「文件」入口：一处查看历史各聊天里发送过的文件（含自己发出的）。
    已删除的会话按其隐藏水位一并过滤，避免"列表里看不到会话、文件页却还在"。
    """
    watermarks = hidden_watermarks(db, user.id)
    items: list[dict] = []

    # ---- 单聊 ----
    single_rows = (
        db.query(Message)
        .filter(
            or_(Message.sender_id == user.id, Message.receiver_id == user.id),
            Message.content.like("{%"),
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    peer_ids = {m.receiver_id if m.sender_id == user.id else m.sender_id for m in single_rows}
    peer_names = (
        {u.id: u.name for u in db.query(User).filter(User.id.in_(peer_ids)).all()} if peer_ids else {}
    )
    for m in single_rows:
        meta = _parse_attachment(m.content)
        if not meta:
            continue
        peer_id = m.receiver_id if m.sender_id == user.id else m.sender_id
        session_key = f"s-{peer_id}"
        if is_hidden(watermarks, session_key, m.id):
            continue
        mine = m.sender_id == user.id
        items.append({
            "id": f"s-{m.id}",
            "message_id": m.id,
            "file_type": meta["type"],
            "name": meta["text"],
            "url": meta["url"],
            "duration": meta["duration"],
            "session_key": session_key,
            "session_name": peer_names.get(peer_id, ""),
            "is_group": False,
            "sender_name": "我" if mine else peer_names.get(peer_id, ""),
            "created_at": m.created_at,
        })

    # ---- 群聊 ----
    group_ids = [r.group_id for r in db.query(GroupMember).filter(GroupMember.user_id == user.id).all()]
    if group_ids:
        group_rows = (
            db.query(GroupMessage)
            .filter(GroupMessage.group_id.in_(group_ids), GroupMessage.content.like("{%"))
            .order_by(GroupMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        group_names = {g.id: g.name for g in db.query(Group).filter(Group.id.in_(group_ids)).all()}
        sender_ids = {m.sender_id for m in group_rows}
        sender_names = (
            {u.id: u.name for u in db.query(User).filter(User.id.in_(sender_ids)).all()} if sender_ids else {}
        )
        for m in group_rows:
            meta = _parse_attachment(m.content)
            if not meta:
                continue
            session_key = f"g-{m.group_id}"
            if is_hidden(watermarks, session_key, m.id):
                continue
            mine = m.sender_id == user.id
            items.append({
                "id": f"g-{m.id}",
                "message_id": m.id,
                "file_type": meta["type"],
                "name": meta["text"],
                "url": meta["url"],
                "duration": meta["duration"],
                "session_key": session_key,
                "session_name": group_names.get(m.group_id, ""),
                "is_group": True,
                "sender_name": "我" if mine else sender_names.get(m.sender_id, ""),
                "created_at": m.created_at,
            })

    # ---- 过滤 + 排序（最新在前） ----
    kw = (keyword or "").strip().lower()
    if kw:
        items = [i for i in items if kw in (i["name"] or "").lower()]
    if file_type in _ATTACHMENT_TYPES:
        items = [i for i in items if i["file_type"] == file_type]
    items.sort(key=lambda i: i["created_at"], reverse=True)
    return {"items": items[:limit], "total": len(items)}


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
    logger.debug("mark_read: user_id=%s, current_user=%s", user_id, user.id)
    count = db.query(Message).filter(
        Message.sender_id == user_id, Message.receiver_id == user.id, Message.read == False
    ).count()
    logger.debug("Found %d unread messages to mark", count)
    db.query(Message).filter(
        Message.sender_id == user_id, Message.receiver_id == user.id, Message.read == False
    ).update({"read": True})
    db.commit()
    return {"message": "marked read", "count": count}
