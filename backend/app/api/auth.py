import base64
import random
import re
import secrets
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_quick_token,
    decode_quick_token,
    hash_password,
    verify_password,
    revoke_token,
)
from app.models.announcement import UrgencyLevel
from app.models.notification import NotificationType
from app.models.password_reset import PasswordResetRequest, PasswordResetStatus
from app.models.user import User, UserRole
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordStatusOut,
    LoginRequest,
    LoginResponse,
    ProfileUpdate,
    QuickCredentialOut,
    QuickLoginRequest,
    UserInfo,
)
from app.services.auth_service import login_user
from app.services.notification_service import send_batch_notifications
from app.utils.rate_limiter import check_login_rate_limit

# 与 core/deps.py 保持一致
AUTH_COOKIE_NAME = "campus_token"

# 管理员处理密码重置申请的承诺时限（小时），用于前端提示「多久后可以尝试重新登录」
PASSWORD_RESET_ETA_HOURS = 2
# 管理员通过后，账号密码恢复为学校统一初始密码
PASSWORD_RESET_INITIAL_PASSWORD = "123456"


def _extract_token(request: Request) -> str | None:
    """从 Authorization 头或 httpOnly Cookie 中提取 token（用于幂等登出撤销）。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return request.cookies.get(AUTH_COOKIE_NAME)


router = APIRouter(prefix="/api/auth", tags=["auth"])

# ===== 图形验证码（内存存储，单进程部署够用；重启后失效，前端刷新即可） =====
_CAPTCHA_TTL_SECONDS = 300
_CAPTCHA_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_captcha_store: dict[str, tuple[str, float]] = {}
_captcha_lock = threading.Lock()


def _cleanup_captchas() -> None:
    now = time.time()
    expired = [key for key, (_, expire) in _captcha_store.items() if expire < now]
    for key in expired:
        _captcha_store.pop(key, None)


def _captcha_svg(code: str) -> str:
    """生成轻量 SVG 验证码：字符旋转 + 干扰线，无需 Pillow 依赖。"""
    rng = random.Random(secrets.randbits(64))
    width, height = 108, 44
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f6f6f7"/>',
    ]
    for _ in range(5):
        parts.append(
            '<path d="M{0} {1} L{2} {3}" stroke="#d8d8dd" stroke-width="1"/>'.format(
                rng.randint(0, width), rng.randint(0, height),
                rng.randint(0, width), rng.randint(0, height),
            )
        )
    for index, char in enumerate(code):
        x = 18 + index * 23 + rng.randint(-2, 2)
        y = 29 + rng.randint(-3, 3)
        rotate = rng.randint(-16, 16)
        color = rng.choice(["#111111", "#3d3d43", "#5c5c63"])
        parts.append(
            f'<text x="{x}" y="{y}" fill="{color}" font-size="22" font-weight="700" '
            f'font-family="Helvetica,Arial,sans-serif" text-anchor="middle" '
            f'transform="rotate({rotate} {x} {y})">{char}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


@router.get("/captcha")
def create_captcha():
    """获取图形验证码：返回 id 与 base64 图片，5 分钟有效，一次性使用。"""
    code = "".join(secrets.choice(_CAPTCHA_CHARS) for _ in range(4))
    captcha_id = secrets.token_urlsafe(18)
    with _captcha_lock:
        _cleanup_captchas()
        _captcha_store[captcha_id] = (code, time.time() + _CAPTCHA_TTL_SECONDS)
    image = base64.b64encode(_captcha_svg(code).encode("utf-8")).decode("ascii")
    return {
        "captcha_id": captcha_id,
        "image": f"data:image/svg+xml;base64,{image}",
        "expires_in": _CAPTCHA_TTL_SECONDS,
    }


def _verify_captcha(captcha_id: str, captcha: str) -> None:
    """校验并消费验证码；失败抛出对应提示。"""
    with _captcha_lock:
        item = _captcha_store.pop(captcha_id, None)
    if not item:
        raise HTTPException(status_code=400, detail="验证码已过期，请刷新后重试")
    code, expire = item
    if expire < time.time():
        raise HTTPException(status_code=400, detail="验证码已过期，请刷新后重试")
    if not secrets.compare_digest(code, (captcha or "").strip().upper()):
        raise HTTPException(status_code=400, detail="验证码不正确，请重新输入")


def _quick_channels(user: User) -> list[str]:
    """账号已绑定的快捷登录通道：phone / qq。

    管理员端登录方式保持不变：不下发也不接受一键登录凭证。
    """
    if user.role == UserRole.ADMIN:
        return []
    channels: list[str] = []
    if user.phone:
        channels.append("phone")
    if user.qq:
        channels.append("qq")
    return channels


def _attach_quick(user: User, payload: dict) -> dict:
    """为登录响应补上一键登录凭证（仅在已绑定手机号/QQ 时下发）。"""
    channels = _quick_channels(user)
    payload["quick_channels"] = channels
    payload["quick_token"] = create_quick_token(user.id, user.password_hash) if channels else None
    return payload


def _set_auth_cookie(response: Response, token: str) -> None:
    """附加 httpOnly Cookie 通道（F3）：JS 不可读，降低 XSS 窃取面；
    与 Bearer 双轨并存，原有前端契约不变。"""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=(settings.ENV == "production"),
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)
    result = login_user(db, req.username, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user = db.query(User).filter(User.username == req.username).first()
    if user:
        _attach_quick(user, result)
    _set_auth_cookie(response, result["access_token"])
    return result


@router.post("/quick-login", response_model=LoginResponse)
def quick_login(req: QuickLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """本设备一键登录：凭长期凭证登录已绑定手机号/QQ 的账号。

    凭证由上次账号密码登录时下发，缺失或失效时前端引导回账号密码登录。
    """
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)
    payload = decode_quick_token(req.quick_token)
    if not payload:
        raise HTTPException(status_code=401, detail="一键登录信息已失效，请使用账号密码登录")
    try:
        user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    except (TypeError, ValueError):
        user = None
    if not user or payload.get("ph") != user.password_hash[:8]:
        raise HTTPException(status_code=401, detail="一键登录信息已失效，请使用账号密码登录")
    if not _quick_channels(user):
        raise HTTPException(status_code=401, detail="暂无信息，请使用账号密码登录")
    # 认证通过后再校验通道：账号存在但对应手机号/QQ 未绑定时，才提示「无账号」
    if req.channel == "phone" and not user.phone:
        raise HTTPException(status_code=401, detail="该手机号尚未绑定校园账号，请使用账号密码登录")
    if req.channel == "qq" and not user.qq:
        raise HTTPException(status_code=401, detail="该 QQ 尚未绑定校园账号，请使用账号密码登录")

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "ph": user.password_hash[:8],
    })
    result = {
        "access_token": token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user).model_dump(),
    }
    _attach_quick(user, result)
    _set_auth_cookie(response, token)
    return result


@router.post("/quick-credential", response_model=QuickCredentialOut)
def quick_credential(user: User = Depends(get_current_user)):
    """资料页绑定手机号/QQ 后刷新本设备的一键登录凭证。"""
    channels = _quick_channels(user)
    return {
        "quick_token": create_quick_token(user.id, user.password_hash) if channels else None,
        "quick_channels": channels,
    }


def _status_message(item: PasswordResetRequest) -> str:
    if item.status == PasswordResetStatus.RESET:
        return f"密码已重置为初始密码 {PASSWORD_RESET_INITIAL_PASSWORD}，请立即登录并修改"
    if item.status == PasswordResetStatus.REJECTED:
        return f"申请未通过：{item.admin_note or '请联系管理员处理'}"
    return f"已通知管理员，预计 {PASSWORD_RESET_ETA_HOURS} 小时内完成重置，请稍后尝试重新登录"


def _status_out(item: PasswordResetRequest) -> dict:
    return {
        "id": item.id,
        "status": item.status.value,
        "submitted_at": item.created_at,
        "eta_hours": PASSWORD_RESET_ETA_HOURS,
        "message": _status_message(item),
    }


def _mask_contact(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 8:
        return f"{digits[:3]}****{digits[-4:]}"
    if len(digits) >= 5:
        return f"{digits[:2]}****{digits[-2:]}"
    return "****"


@router.post("/forgot-password", response_model=ForgotPasswordStatusOut)
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """忘记密码：核验学号/工号 + 姓名 + 已绑定手机号/QQ，通过后自动通知管理员。

    无短信/邮件通道，因此身份核验采用「账号 + 姓名 + 资料中已绑定的联系方式」比对；
    核验通过后创建申请并给所有管理员发送站内消息，管理员审核后重置为初始密码。
    """
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)

    # 先校验验证码，避免被脚本枚举学号/姓名
    _verify_captcha(req.captcha_id, req.captcha)

    username = req.username.strip()
    name = req.name.strip()
    contact_digits = re.sub(r"\D", "", req.contact or "")
    if not username or not name or len(contact_digits) < 5:
        raise HTTPException(status_code=400, detail="请完整填写学号/工号、姓名与已绑定的手机号或 QQ")

    user = db.query(User).filter(User.username == username).first()
    # 管理员不开放自助找回，避免与后台权限体系混淆
    if not user:
        raise HTTPException(status_code=400, detail="该学号/工号不存在，请核对后重试")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="管理员账号不支持自助找回，请联系系统维护人员")
    if user.name.strip() != name:
        raise HTTPException(status_code=400, detail="姓名与学号/工号不匹配，请核对后重试")

    phone_digits = re.sub(r"\D", "", user.phone or "")
    qq_digits = re.sub(r"\D", "", user.qq or "")
    if not phone_digits and not qq_digits:
        raise HTTPException(
            status_code=400,
            detail="该账号未绑定手机号或 QQ，无法在线核验身份，请联系辅导员或管理员",
        )
    if contact_digits not in {phone_digits, qq_digits}:
        raise HTTPException(status_code=400, detail="手机号/QQ 与账号绑定的信息不一致")

    pending = (
        db.query(PasswordResetRequest)
        .filter(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == PasswordResetStatus.PENDING,
        )
        .order_by(PasswordResetRequest.created_at.desc())
        .first()
    )
    if pending:
        return _status_out(pending)

    item = PasswordResetRequest(
        user_id=user.id,
        username=user.username,
        name=user.name,
        contact=_mask_contact(contact_digits),
        reason=(req.reason or "").strip()[:200] or None,
        status=PasswordResetStatus.PENDING,
    )
    db.add(item)
    db.flush()

    admin_ids = [row[0] for row in db.query(User.id).filter(User.role == UserRole.ADMIN).all()]
    if admin_ids:
        send_batch_notifications(
            db,
            admin_ids,
            title="收到密码重置申请",
            content=(
                f"{user.name}（{user.username}）申请重置密码，联系方式 {_mask_contact(contact_digits)}。"
                f"请在「密码重置」页审核，通过后将重置为初始密码 {PASSWORD_RESET_INITIAL_PASSWORD}。"
            ),
            notification_type=NotificationType.SYSTEM,
            link="/admin/password-requests",
            related_id=item.id,
            sender_id=user.id,
            level=UrgencyLevel.IMPORTANT,
        )
    db.commit()
    db.refresh(item)
    return _status_out(item)


@router.get("/forgot-password/{request_id}", response_model=ForgotPasswordStatusOut)
def forgot_password_status(
    request_id: int,
    username: str,
    db: Session = Depends(get_db),
):
    """查询申请进度：仅返回状态，不暴露账号与联系方式。"""
    item = (
        db.query(PasswordResetRequest)
        .filter(
            PasswordResetRequest.id == request_id,
            PasswordResetRequest.username == username.strip(),
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="申请不存在")
    return _status_out(item)


@router.post("/logout")
def logout(request: Request, response: Response):
    """登出：撤销当前 token（幂等），并清除 httpOnly Cookie。"""
    token = _extract_token(request)
    if token:
        revoke_token(token)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return {"message": "已退出登录"}


@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    teachers = db.query(User).filter(User.role == UserRole.TEACHER).all()
    from app.schemas.user import UserInfo
    return [UserInfo.model_validate(t) for t in teachers]


@router.get("/me")
def current_identity(user: User = Depends(get_current_user)):
    """SSO 统一身份信息：校验 token 并返回当前登录者身份（学号/姓名/角色/需改密标志）。"""
    from app.schemas.user import UserInfo
    info = UserInfo.model_validate(user).model_dump()
    info["password_needs_change"] = not user.password_changed
    return info


@router.put("/profile")
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.qq and not re.fullmatch(r"[0-9]{5,12}", data.qq.strip()):
        raise HTTPException(status_code=400, detail="QQ 号格式不正确")
    for field in ("avatar", "gender", "political_status", "title", "hometown", "phone", "qq", "department", "class_name", "age", "signature"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(user, field, val.strip() if field == "qq" else val)
    db.commit()
    db.refresh(user)
    return UserInfo.model_validate(user)


@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    import re
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少 8 位")
    if not re.search(r"[A-Za-z]", data.new_password) or not re.search(r"\d", data.new_password):
        raise HTTPException(status_code=400, detail="新密码必须同时包含字母和数字")
    if data.new_password == data.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
    
    user.password_hash = hash_password(data.new_password)
    user.password_changed = True
    db.commit()
    return {"message": "密码修改成功"}