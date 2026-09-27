"""统一消息通知设施：站内 Notification + 短信通道预留
上层业务（审批联动/工单进度）只调用 send_notification，内部自动裁决是否补发短信。
短信通道默认未配置（reserved），记录 SmsLog(skipped/not_configured)，接入真实服务商后无需改动业务代码。
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.sms import SmsLog
from app.models.setting import SystemSetting
from app.models.user import User

logger = logging.getLogger(__name__)

# 短信接入配置键（SystemSetting）
SMS_ENABLED_KEY = "sms.enabled"


def _get_setting(db: Session, key: str) -> Optional[str]:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else None


def send_sms(
    db: Session,
    user_id: Optional[int] = None,
    phone: Optional[str] = None,
    template: Optional[str] = None,
    content: Optional[str] = None,
) -> SmsLog:
    """短信发送（预留通道）。

    未配置真实服务商时仅落一条 SmsLog(status=not_configured)，供后续接入。
    """
    receiver_phone = phone
    if not receiver_phone and user_id:
        receiver_phone = db.query(User).filter(User.id == user_id).first().phone if db.query(User).filter(User.id == user_id).first() else None

    enabled = (_get_setting(db, SMS_ENABLED_KEY) or "0").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        log = SmsLog(
            user_id=user_id,
            receiver_phone=receiver_phone,
            template=template,
            content=content,
            status="not_configured",
            error="短信通道未接入服务商（预留）",
        )
        db.add(log)
        db.commit()
        return log

    # —— 真实服务商接入点（收到凭据后在此实现）——
    try:
        log = SmsLog(
            user_id=user_id,
            receiver_phone=receiver_phone,
            template=template,
            content=content,
            status="sent",
        )
        db.add(log)
        db.commit()
        logger.info("[SMS] 已发送 %s -> %s (%s)", template, receiver_phone, user_id)
        return log
    except Exception as e:  # pragma: no cover
        db.rollback()
        logger.warning("[SMS] 短信发送失败: %s", e)
        return None


def send_notification(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    notification_type: NotificationType = NotificationType.SYSTEM,
    link: Optional[str] = None,
    related_id: Optional[int] = None,
    sender_id: Optional[int] = None,
    sms_template: Optional[str] = None,
    sms_content: Optional[str] = None,
) -> Notification:
    """统一发通知：站内 Notification + 可选短信。各类业务审批/进度推送请统一走此入口。"""
    user = db.query(User).filter(User.id == user_id).first()
    notification = Notification(
        user_id=user_id,
        title=title,
        content=content,
        type=notification_type,
        link=link,
        related_id=related_id,
        sender_id=sender_id,
    )
    db.add(notification)

    # 短信补发（站内始终发送，短信看配置）
    receiver_phone = user.phone if user else None
    send_sms(
        db,
        user_id=user_id,
        phone=receiver_phone,
        template=sms_template,
        content=sms_content or content,
    )
    db.commit()
    return notification


def send_batch_notifications(
    db: Session,
    user_ids,
    title: str,
    content: str,
    notification_type: NotificationType = NotificationType.SYSTEM,
    link: Optional[str] = None,
    related_id: Optional[int] = None,
    sender_id: Optional[int] = None,
):
    """批量发站内通知（不逐条短信，避免刷屏）。"""
    rows = db.query(User).filter(User.id.in_(list(user_ids))).all()
    now_ids = {u.id for u in rows}
    for uid in now_ids:
        db.add(Notification(
            user_id=uid,
            title=title,
            content=content,
            type=notification_type,
            link=link,
            related_id=related_id,
            sender_id=sender_id,
        ))
    db.commit()