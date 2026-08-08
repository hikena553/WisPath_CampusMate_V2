from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decode_access_token
from app.models.user import User
from app.models.message import Message
from app.models.group import Group, GroupMember, GroupMessage
from app.schemas.group import (
    GroupCreate, GroupMemberAdd, GroupMessageSend, AnnouncementUpdate,
    GroupOut, GroupMemberOut, GroupMessageOut, UserSearchResult
)
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("/search/users", response_model=list[UserSearchResult])
def search_users(keyword: str = Query(..., min_length=1), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(
        or_(
            User.name.contains(keyword),
            User.username.contains(keyword),
        )
    ).filter(User.id != user.id).limit(20).all()

    return [UserSearchResult(
        id=u.id,
        name=u.name,
        username=u.username,
        avatar=u.avatar,
        role=getattr(u, 'role', 'student'),
    ) for u in users]


@router.post("/create")
async def create_group(data: GroupCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = Group(name=data.name, creator_id=user.id)
    db.add(group)
    db.flush()

    db.add(GroupMember(group_id=group.id, user_id=user.id, role="owner"))
    for uid in data.member_ids:
        if uid != user.id:
            db.add(GroupMember(group_id=group.id, user_id=uid, role="member"))

    db.commit()
    db.refresh(group)
    return {"id": group.id, "name": group.name}


@router.get("", response_model=list[GroupOut])
def get_groups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member_group_ids = db.query(GroupMember.group_id).filter(GroupMember.user_id == user.id).subquery()
    groups = db.query(Group).filter(
        Group.id.in_(db.query(member_group_ids)),
        Group.is_dismissed == False
    ).all()

    result = []
    for g in groups:
        member_count = db.query(GroupMember).filter(GroupMember.group_id == g.id).count()
        last_msg = db.query(GroupMessage).filter(GroupMessage.group_id == g.id).order_by(GroupMessage.created_at.desc()).first()

        # 获取用户的最后阅读时间
        member = db.query(GroupMember).filter(
            GroupMember.group_id == g.id,
            GroupMember.user_id == user.id
        ).first()
        last_read = member.last_read_at if member and member.last_read_at else datetime(1970, 1, 1, tzinfo=timezone.utc)

        unread = db.query(GroupMessage).filter(
            GroupMessage.group_id == g.id,
            GroupMessage.sender_id != user.id,
            GroupMessage.created_at > last_read
        ).count()

        result.append(GroupOut(
            id=g.id,
            name=g.name,
            avatar=g.avatar,
            creator_id=g.creator_id,
            announcement=g.announcement,
            is_dismissed=g.is_dismissed,
            member_count=member_count,
            last_message=last_msg.content[:80] if last_msg else "",
            last_message_time=last_msg.created_at if last_msg else None,
            unread_count=unread,
        ))
    return result


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    member_count = db.query(GroupMember).filter(GroupMember.group_id == group_id).count()
    last_msg = db.query(GroupMessage).filter(GroupMessage.group_id == group_id).order_by(GroupMessage.created_at.desc()).first()

    # 计算未读消息数
    last_read = member.last_read_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
    unread = db.query(GroupMessage).filter(
        GroupMessage.group_id == group_id,
        GroupMessage.sender_id != user.id,
        GroupMessage.created_at > last_read
    ).count()

    return GroupOut(
        id=group.id,
        name=group.name,
        avatar=group.avatar,
        creator_id=group.creator_id,
        announcement=group.announcement,
        is_dismissed=group.is_dismissed,
        member_count=member_count,
        last_message=last_msg.content[:80] if last_msg else "",
        last_message_time=last_msg.created_at if last_msg else None,
        unread_count=unread,
    )


@router.get("/{group_id}/members", response_model=list[GroupMemberOut])
def get_group_members(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            result.append(GroupMemberOut(
                user_id=u.id,
                user_name=u.name,
                user_avatar=u.avatar,
                role=m.role,
                joined_at=m.joined_at,
            ))
    return result


@router.post("/{group_id}/members")
async def add_group_members(group_id: int, data: GroupMemberAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    added = 0
    for uid in data.user_ids:
        existing = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == uid).first()
        if not existing:
            db.add(GroupMember(group_id=group_id, user_id=uid, role="member"))
            added += 1

    db.commit()
    return {"added": added}


@router.delete("/{group_id}/members/{target_user_id}")
async def remove_group_member(group_id: int, target_user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member or member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="无权移除成员")

    if target_user_id == member.user_id and member.role == "owner":
        raise HTTPException(status_code=400, detail="群主不能移除自己")

    target = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == target_user_id).first()
    if target:
        db.delete(target)
        db.commit()

    return {"message": "已移除"}


@router.post("/{group_id}/send")
async def send_group_message(group_id: int, data: GroupMessageSend, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    msg = GroupMessage(group_id=group_id, sender_id=user.id, content=data.content)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    members = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id != user.id).all()
    for m in members:
        await manager.send_json(m.user_id, {
            "type": "new_group_message",
            "group_id": group_id,
            "id": msg.id,
            "sender_id": user.id,
            "sender_name": user.name,
            "content": data.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else "",
        })

    return {"id": msg.id, "created_at": msg.created_at.isoformat() if msg.created_at else ""}


@router.get("/{group_id}/messages", response_model=list[GroupMessageOut])
def get_group_messages(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    msgs = db.query(GroupMessage).filter(GroupMessage.group_id == group_id).order_by(GroupMessage.created_at.asc()).all()
    result = []
    for m in msgs:
        u = db.query(User).filter(User.id == m.sender_id).first()
        result.append(GroupMessageOut(
            id=m.id,
            group_id=m.group_id,
            sender_id=m.sender_id,
            sender_name=u.name if u else "未知",
            sender_avatar=u.avatar if u else None,
            content=m.content,
            created_at=m.created_at,
        ))
    return result


@router.post("/{group_id}/read")
def mark_group_read(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """标记群聊消息为已读"""
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    member.last_read_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "已标记为已读"}


@router.put("/{group_id}/announcement")
def update_group_announcement(group_id: int, data: AnnouncementUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    group.announcement = data.announcement or None
    db.commit()
    return {"message": "群公告已更新", "announcement": group.announcement}


@router.post("/{group_id}/leave")
def leave_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    if member.role == "owner":
        raise HTTPException(status_code=400, detail="群主不能退群，请先转让群主或解散群聊")

    db.delete(member)
    db.commit()
    return {"message": "已退出群聊"}


@router.delete("/{group_id}")
def disband_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user.id).first()
    if not member or member.role != "owner":
        raise HTTPException(status_code=403, detail="仅群主可以解散群聊")

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    group.is_dismissed = True
    db.commit()
    return {"message": "群聊已解散"}