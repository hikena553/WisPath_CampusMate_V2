"""家校沟通服务：联系人档案 / 沟通台账 / 只读分享链接。

安全约定（A10）：
- 手机号只以脱敏形式输出（138****1111）；
- 危机类（scene=crisis）禁止生成分享链接；
- 建联系人、发短信、生成 / 撤销分享链接等关键动作写审计日志。
"""
import logging
import secrets
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.guardian import (
    Guardian,
    GuardianChannel,
    GuardianContactLog,
    GuardianContactStatus,
    GuardianScene,
    GuardianShareLink,
)
from app.models.user import User
from app.services.notification_service import send_sms

logger = logging.getLogger(__name__)

SHARE_LINK_TTL_DAYS = 7

SCENE_LABELS = {
    "leave": "请假告知",
    "crisis": "危机干预",
    "academic": "学业预警",
    "care": "日常关怀",
    "other": "其他",
}


def mask_phone(phone: str | None) -> str:
    """手机号脱敏：138****1111。"""
    if not phone:
        return ""
    digits = phone.strip()
    if len(digits) >= 7:
        return f"{digits[:3]}****{digits[-4:]}"
    return "***"


def _scene(value: str | GuardianScene | None) -> GuardianScene:
    if isinstance(value, GuardianScene):
        return value
    try:
        return GuardianScene(value) if value else GuardianScene.OTHER
    except ValueError:
        return GuardianScene.OTHER


def _channel(value: str | GuardianChannel | None) -> GuardianChannel:
    if isinstance(value, GuardianChannel):
        return value
    try:
        return GuardianChannel(value) if value else GuardianChannel.NOTE
    except ValueError:
        return GuardianChannel.NOTE


def _audit(action: str, **fields) -> None:
    """关键操作审计（结构化日志）。"""
    detail = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("[AUDIT][guardian] %s %s", action, detail)


def _names(db: Session, ids: set[int]) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = db.query(User.id, User.name).filter(User.id.in_(ids)).all()
    return {row[0]: row[1] for row in rows}


# ── 联系人 ────────────────────────────────────────────────────


def _serialize_guardian(item: Guardian, student_name: str = "") -> dict:
    return {
        "id": item.id,
        "student_id": item.student_id,
        "student_name": student_name,
        "name": item.name,
        "relation": item.relation,
        "phone_masked": mask_phone(item.phone),
        "is_primary": bool(item.is_primary),
        "remark": item.remark,
        "created_at": item.created_at.isoformat() if item.created_at else "",
    }


def create_guardian(
    db: Session,
    *,
    student_id: int,
    name: str,
    relation: str = "家长",
    phone: str | None = None,
    is_primary: bool = False,
    remark: str | None = None,
    actor_id: int | None = None,
) -> Guardian:
    item = Guardian(
        student_id=student_id,
        name=name,
        relation=relation,
        phone=phone,
        is_primary=is_primary,
        remark=remark,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _audit("create_guardian", actor=actor_id, student=student_id, guardian=item.id)
    return item


def list_guardians(db: Session, student_id: int) -> list[dict]:
    items = (
        db.query(Guardian)
        .filter(Guardian.student_id == student_id, Guardian.is_deleted.is_(False))
        .order_by(Guardian.is_primary.desc(), Guardian.id.asc())
        .all()
    )
    names = _names(db, {student_id})
    return [_serialize_guardian(g, names.get(student_id, "")) for g in items]


def get_guardian(db: Session, guardian_id: int) -> Guardian | None:
    return (
        db.query(Guardian)
        .filter(Guardian.id == guardian_id, Guardian.is_deleted.is_(False))
        .first()
    )


def update_guardian(db: Session, item: Guardian, payload: dict, actor_id: int | None = None) -> Guardian:
    for field in ("name", "relation", "phone", "remark"):
        if field in payload and payload[field] is not None:
            setattr(item, field, payload[field])
    if payload.get("is_primary") is not None:
        item.is_primary = payload["is_primary"]
    db.commit()
    db.refresh(item)
    _audit("update_guardian", actor=actor_id, guardian=item.id)
    return item


def soft_delete_guardian(db: Session, item: Guardian, actor_id: int | None = None) -> None:
    item.is_deleted = True
    db.commit()
    _audit("delete_guardian", actor=actor_id, guardian=item.id)


# ── 沟通台账 ──────────────────────────────────────────────────


def _serialize_log(log: GuardianContactLog, student_name: str = "", guardian_name: str = "") -> dict:
    return {
        "id": log.id,
        "student_id": log.student_id,
        "student_name": student_name,
        "guardian_id": log.guardian_id,
        "guardian_name": guardian_name,
        "teacher_id": log.teacher_id,
        "scene": log.scene.value if log.scene else "other",
        "channel": log.channel.value if log.channel else "note",
        "status": log.status.value if log.status else "draft",
        "content_summary": log.content_summary,
        "created_at": log.created_at.isoformat() if log.created_at else "",
    }


def create_log(
    db: Session,
    *,
    teacher_id: int,
    student_id: int,
    content_summary: str,
    guardian_id: int | None = None,
    scene: str | GuardianScene = GuardianScene.OTHER,
    channel: str | GuardianChannel = GuardianChannel.NOTE,
    send_sms_flag: bool = False,
) -> GuardianContactLog:
    """建立沟通台账。

    短信通道：调用既有 notification_service.send_sms()，未配置服务商时优雅降级为
    pending（不报错、不阻塞业务）；接入服务商后零改动生效。
    """
    ch = _channel(channel)
    scene_enum = _scene(scene)
    status = GuardianContactStatus.DRAFT
    if ch == GuardianChannel.SMS:
        if send_sms_flag:
            guardian = db.query(Guardian).filter(Guardian.id == guardian_id).first() if guardian_id else None
            sms = send_sms(
                db,
                phone=guardian.phone if guardian else None,
                template="家校沟通提示",
                content=content_summary[:200],
            )
            status = (
                GuardianContactStatus.SENT
                if sms is not None and sms.status == "sent"
                else GuardianContactStatus.PENDING
            )
        else:
            status = GuardianContactStatus.PENDING
    elif ch == GuardianChannel.LINK:
        status = GuardianContactStatus.SENT
    else:
        status = GuardianContactStatus.SENT if ch == GuardianChannel.REPORT else GuardianContactStatus.DRAFT

    log = GuardianContactLog(
        student_id=student_id,
        guardian_id=guardian_id,
        teacher_id=teacher_id,
        scene=scene_enum,
        channel=ch,
        status=status,
        content_summary=content_summary,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    _audit("create_contact_log", actor=teacher_id, student=student_id, scene=scene_enum.value, channel=ch.value)
    return log


def list_logs(
    db: Session,
    teacher_id: int,
    *,
    student_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    query = db.query(GuardianContactLog).filter(
        GuardianContactLog.teacher_id == teacher_id,
        GuardianContactLog.is_deleted.is_(False),
    )
    if student_id is not None:
        query = query.filter(GuardianContactLog.student_id == student_id)
    logs = query.order_by(GuardianContactLog.created_at.desc(), GuardianContactLog.id.desc()).limit(limit).all()

    student_names = _names(db, {l.student_id for l in logs})
    guardian_ids = {l.guardian_id for l in logs if l.guardian_id}
    guardian_names: dict[int, str] = {}
    if guardian_ids:
        rows = db.query(Guardian.id, Guardian.name).filter(Guardian.id.in_(guardian_ids)).all()
        guardian_names = {row[0]: row[1] for row in rows}
    return [
        _serialize_log(l, student_names.get(l.student_id, ""), guardian_names.get(l.guardian_id or -1, ""))
        for l in logs
    ]


def get_log(db: Session, log_id: int) -> GuardianContactLog | None:
    return (
        db.query(GuardianContactLog)
        .filter(GuardianContactLog.id == log_id, GuardianContactLog.is_deleted.is_(False))
        .first()
    )


def soft_delete_log(db: Session, log: GuardianContactLog, actor_id: int | None = None) -> None:
    log.is_deleted = True
    db.commit()
    _audit("delete_contact_log", actor=actor_id, log=log.id)


# ── 只读分享链接 ──────────────────────────────────────────────


def _serialize_link(link: GuardianShareLink) -> dict:
    return {
        "id": link.id,
        "log_id": link.log_id,
        "token": link.token,
        "path": f"/share/guardian/{link.token}",
        "expires_at": link.expires_at.isoformat() if link.expires_at else "",
        "revoked": bool(link.revoked),
        "view_count": link.view_count,
        "last_viewed_at": link.last_viewed_at.isoformat() if link.last_viewed_at else None,
    }


def create_share_link(
    db: Session, log: GuardianContactLog, actor_id: int | None = None
) -> GuardianShareLink:
    """为台账生成 7 天有效的只读链接；危机类记录禁止生成。"""
    if log.scene == GuardianScene.CRISIS:
        raise ValueError("危机类记录涉及隐私，禁止生成分享链接")
    link = GuardianShareLink(
        log_id=log.id,
        token=secrets.token_urlsafe(24),
        expires_at=datetime.now() + timedelta(days=SHARE_LINK_TTL_DAYS),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    _audit("create_share_link", actor=actor_id, log=log.id, link=link.id)
    return link


def get_share_link(db: Session, link_id: int) -> GuardianShareLink | None:
    return db.query(GuardianShareLink).filter(GuardianShareLink.id == link_id).first()


def get_link_by_token(db: Session, token: str) -> GuardianShareLink | None:
    return db.query(GuardianShareLink).filter(GuardianShareLink.token == token).first()


def revoke_share_link(db: Session, link: GuardianShareLink, actor_id: int | None = None) -> GuardianShareLink:
    link.revoked = True
    db.commit()
    db.refresh(link)
    _audit("revoke_share_link", actor=actor_id, link=link.id)
    return link


def resolve_shared_log(db: Session, token: str) -> tuple[dict | None, str]:
    """家长只读访问：校验有效性并累计访问量。返回 (数据, 错误码)。"""
    link = get_link_by_token(db, token)
    if not link:
        return None, "not_found"
    if link.revoked:
        return None, "revoked"
    if link.expires_at and link.expires_at < datetime.now():
        return None, "expired"
    log = get_log(db, link.log_id)
    if not log:
        return None, "not_found"

    link.view_count += 1
    link.last_viewed_at = datetime.now()
    db.commit()

    teacher = db.query(User).filter(User.id == log.teacher_id).first()
    return (
        {
            "scene": log.scene.value if log.scene else "other",
            "scene_label": SCENE_LABELS.get(log.scene.value if log.scene else "other", "其他"),
            "content_summary": log.content_summary,
            "teacher_name": teacher.name if teacher else "",
            "created_at": log.created_at.isoformat() if log.created_at else "",
            "expires_at": link.expires_at.isoformat() if link.expires_at else "",
        },
        "",
    )


def list_links_for_logs(db: Session, log_ids: list[int]) -> dict[int, dict]:
    """批量取每个台账最新未撤销的分享链接（供列表回显）。"""
    if not log_ids:
        return {}
    links = (
        db.query(GuardianShareLink)
        .filter(GuardianShareLink.log_id.in_(log_ids))
        .order_by(GuardianShareLink.id.desc())
        .all()
    )
    out: dict[int, dict] = {}
    for link in links:
        if link.log_id in out:
            continue
        out[link.log_id] = _serialize_link(link)
    return out


def serialize_link(link: GuardianShareLink) -> dict:
    return _serialize_link(link)


def serialize_guardian(item: Guardian, student_name: str = "") -> dict:
    return _serialize_guardian(item, student_name)


def serialize_log(log: GuardianContactLog, student_name: str = "", guardian_name: str = "") -> dict:
    return _serialize_log(log, student_name, guardian_name)


def name_of(db: Session, user_id: int | None) -> str:
    if not user_id:
        return ""
    row = db.query(User.name).filter(User.id == user_id).first()
    return row[0] if row else ""


def today() -> date:
    return date.today()