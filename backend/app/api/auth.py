import base64
import logging
import random
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.core.security import (
    create_access_token,
    create_quick_token,
    decode_quick_token,
    hash_password,
    verify_password,
    revoke_token,
)
from app.models.academic import College, Major
from app.models.announcement import UrgencyLevel
from app.models.notification import NotificationType
from app.models.password_reset import PasswordResetRequest, PasswordResetStatus
from app.models.sms import SmsLog
from app.models.user import User, UserRole
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordStatusOut,
    LoginRequest,
    LoginResponse,
    PhoneBindRequest,
    PhoneLoginRequest,
    ProfileUpdate,
    QqExchangeRequest,
    QqMobileAuthorizeOut,
    QqMobileTokenRequest,
    QuickCredentialOut,
    QuickLoginRequest,
    RegisterPhoneVerifyRequest,
    RegisterRequest,
    RegisterSmsRequest,
    SmsCodeRequest,
    UserInfo,
)
from app.services import qq_oauth_service, sms_service
from app.services.auth_service import login_user
from app.services.notification_service import send_batch_notifications
from app.utils.rate_limiter import check_login_rate_limit

logger = logging.getLogger(__name__)

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
    if user.qq or user.qq_openid:
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
        # 资讯账号是系统运营身份，只用于自动发帖，不开放任何登录通道
        if user.role == UserRole.MEDIA:
            raise HTTPException(status_code=403, detail="该账号为系统资讯账号，不支持登录")
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
    if user.role == UserRole.MEDIA:
        raise HTTPException(status_code=403, detail="该账号为系统资讯账号，不支持登录")
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


# ==================== 手机号短信验证码登录 / QQ 互联 OAuth 登录 ====================

_PHONE_RE = re.compile(r"1[3-9]\d{9}")


def _normalize_phone(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _require_phone(value: str | None) -> str:
    digits = _normalize_phone(value)
    if not _PHONE_RE.fullmatch(digits):
        raise HTTPException(status_code=400, detail="请输入正确的 11 位手机号")
    return digits


def _phone_user(db: Session, phone: str) -> User:
    """按手机号反查账号：手机号必须唯一绑定，重复绑定视为数据异常。"""
    users = db.query(User).filter(User.phone == phone).all()
    if not users:
        raise HTTPException(status_code=404, detail="该手机号尚未绑定校园账号")
    if len(users) > 1:
        raise HTTPException(status_code=409, detail="该手机号绑定了多个账号，请联系管理员处理")
    return users[0]


def _assert_login_allowed(user: User) -> None:
    """资讯账号不开放任何登录通道；管理员端保持账号密码登录。"""
    if user.role == UserRole.MEDIA:
        raise HTTPException(status_code=403, detail="该账号为系统资讯账号，不支持登录")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="管理员账号请使用账号密码登录")


def _login_result(user: User) -> dict:
    token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "ph": user.password_hash[:8],
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user).model_dump(),
    }


def _record_sms_log(db: Session, user_id: int | None, phone: str, provider: str, status: str) -> None:
    """落一条短信日志，便于排查是否真的发出（不保存验证码明文）。"""
    db.add(SmsLog(
        user_id=user_id,
        receiver_phone=phone,
        provider=provider,
        template="登录验证码",
        content="校园账号快捷登录验证码短信",
        status=status,
    ))
    db.commit()


@router.post("/sms/send")
def send_login_sms(
    req: SmsCodeRequest,
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """发送手机验证码：purpose=login 用于手机号登录，purpose=bind 用于已登录账号换绑。"""
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)

    phone = _require_phone(req.phone)
    purpose = req.purpose if req.purpose in ("login", "bind") else "login"

    if purpose == "login":
        target = _phone_user(db, phone)
        _assert_login_allowed(target)
    else:
        if not user:
            raise HTTPException(status_code=401, detail="请先登录后再绑定手机号")
        other = db.query(User).filter(User.phone == phone, User.id != user.id).first()
        if other:
            raise HTTPException(status_code=409, detail="该手机号已被其他账号绑定")

    try:
        issued = sms_service.issue_code(phone, purpose)
    except sms_service.SmsCooldown as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except sms_service.SmsNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except sms_service.SmsSendFailed as exc:
        _record_sms_log(db, user.id if user else None, phone, sms_service.provider_name(), "failed")
        raise HTTPException(status_code=502, detail=str(exc))

    _record_sms_log(
        db,
        user.id if user else None,
        phone,
        issued.provider,
        "skipped" if issued.debug_code else "sent",
    )
    return {
        "provider": issued.provider,
        "configured": issued.configured,
        "expires_in": issued.expires_in,
        "cooldown": issued.cooldown,
        # 仅开发环境且未配置服务商时返回，生产环境恒为 None
        "debug_code": issued.debug_code,
    }


@router.post("/phone-login", response_model=LoginResponse)
def phone_login(req: PhoneLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """手机号 + 短信验证码登录：验证码一次性消费，手机号必须已绑定账号。"""
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)

    phone = _require_phone(req.phone)
    try:
        sms_service.verify_code(phone, "login", req.code)
    except sms_service.SmsCodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user = _phone_user(db, phone)
    _assert_login_allowed(user)
    result = _attach_quick(user, _login_result(user))
    _set_auth_cookie(response, result["access_token"])
    return result


@router.post("/phone/bind")
def bind_phone(
    req: PhoneBindRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """验证码校验通过后绑定手机号；同一个手机号只能绑定一个账号。"""
    phone = _require_phone(req.phone)
    try:
        sms_service.verify_code(phone, "bind", req.code)
    except sms_service.SmsCodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    other = db.query(User).filter(User.phone == phone, User.id != user.id).first()
    if other:
        raise HTTPException(status_code=409, detail="该手机号已被其他账号绑定")
    user.phone = phone
    db.commit()
    db.refresh(user)
    return UserInfo.model_validate(user)


def _qq_redirect_uri(request: Request) -> str:
    configured = (settings.QQ_REDIRECT_URI or "").strip()
    if configured:
        return configured
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}/api/auth/qq/callback"


def _frontend_base() -> str:
    return (settings.FRONTEND_BASE_URL or "http://localhost:5173").rstrip("/")


@router.get("/qq/authorize")
def qq_authorize(
    request: Request,
    mode: str = "login",
    user: User | None = Depends(get_optional_user),
):
    """返回 QQ 互联授权地址；mode=bind 时必须已登录，用于把 QQ 绑到当前账号。"""
    if not qq_oauth_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="QQ 互联未配置：请在 .env 填写 QQ_APP_ID / QQ_APP_KEY / QQ_REDIRECT_URI",
        )
    if mode not in ("login", "bind", "register"):
        raise HTTPException(status_code=400, detail="不支持的授权类型")
    if mode == "bind" and not user:
        raise HTTPException(status_code=401, detail="请先登录后再绑定 QQ")
    url = qq_oauth_service.build_authorize_url(mode, _qq_redirect_uri(request), user.id if user else None)
    return {"url": url}


@router.get("/qq/callback")
def qq_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """QQ 授权回跳：换取 openid 后按 mode 完成登录或绑定，再回跳前端。"""
    base = _frontend_base()
    if error:
        return RedirectResponse(f"{base}/qq-callback?error={error}")
    if not qq_oauth_service.is_configured():
        return RedirectResponse(f"{base}/qq-callback?error=not_configured")
    payload = qq_oauth_service.decode_state(state)
    if not payload or not code:
        return RedirectResponse(f"{base}/qq-callback?error=state_invalid")
    mode = payload.get("mode")

    try:
        access_token, openid = qq_oauth_service.exchange_code(code, _qq_redirect_uri(request))
    except Exception as exc:  # pragma: no cover - 外部服务
        logger.warning("[QQ] code 换 token 失败: %s", exc)
        return RedirectResponse(f"{base}/qq-callback?error=exchange_failed")

    if mode == "register":
        if db.query(User).filter(User.qq_openid == openid).first():
            return RedirectResponse(f"{base}/register?error=qq_occupied")
        nickname = qq_oauth_service.fetch_nickname(access_token, openid)
        ticket = qq_oauth_service.create_register_ticket(openid, nickname)
        from urllib.parse import quote

        return RedirectResponse(
            f"{base}/register?qq_ticket={ticket}&qq_nickname={quote(nickname or '')}"
        )

    if mode == "bind":
        uid = payload.get("uid")
        user = db.query(User).filter(User.id == int(uid)).first() if uid else None
        if not user:
            return RedirectResponse(f"{base}/qq-callback?error=state_invalid")
        occupied = (
            db.query(User)
            .filter(User.qq_openid == openid, User.id != user.id)
            .first()
        )
        if occupied:
            return RedirectResponse(f"{base}/qq-callback?error=qq_occupied")
        user.qq_openid = openid
        user.qq_nickname = qq_oauth_service.fetch_nickname(access_token, openid) or user.qq_nickname
        db.commit()
        return RedirectResponse(f"{base}/qq-callback?bind=ok")

    user = db.query(User).filter(User.qq_openid == openid).first()
    if not user:
        return RedirectResponse(f"{base}/qq-callback?error=unbound")
    if user.role in (UserRole.MEDIA, UserRole.ADMIN):
        return RedirectResponse(f"{base}/qq-callback?error=forbidden")
    ticket = qq_oauth_service.create_login_ticket(user.id, user.password_hash)
    return RedirectResponse(f"{base}/qq-callback?ticket={ticket}")


@router.post("/qq/exchange", response_model=LoginResponse)
def qq_exchange(req: QqExchangeRequest, response: Response, db: Session = Depends(get_db)):
    """前端用一次性回跳票据换取正式登录态。"""
    payload = qq_oauth_service.decode_login_ticket(req.ticket)
    if not payload:
        raise HTTPException(status_code=401, detail="QQ 登录信息已失效，请重新登录")
    try:
        user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    except (TypeError, ValueError):
        user = None
    if not user or payload.get("ph") != user.password_hash[:8]:
        raise HTTPException(status_code=401, detail="QQ 登录信息已失效，请重新登录")
    if not user.qq_openid:
        raise HTTPException(status_code=401, detail="该 QQ 尚未绑定校园账号")
    _assert_login_allowed(user)

    result = _attach_quick(user, _login_result(user))
    _set_auth_cookie(response, result["access_token"])
    return result


@router.post("/qq/unbind")
def unbind_qq(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """解除 QQ 互联授权绑定（不影响手动填写的 QQ 号）。"""
    user.qq_openid = None
    user.qq_nickname = None
    db.commit()
    db.refresh(user)
    return UserInfo.model_validate(user)


# ==================== QQ 互联移动端（Android SDK 直通） ====================

_QQ_MOBILE_NOT_CONFIGURED = "QQ 互联未配置：请在 .env 填写 QQ_APP_ID"


def _qq_mobile_verify(req: QqMobileTokenRequest) -> str | None:
    """核验移动端上报的 SDK 凭证，失败统一 401。返回 QQ 昵称（可为空）。"""
    if not (settings.QQ_APP_ID or "").strip():
        raise HTTPException(status_code=503, detail=_QQ_MOBILE_NOT_CONFIGURED)
    try:
        return qq_oauth_service.verify_mobile_token(req.access_token, req.openid)
    except Exception as exc:  # 网络异常 / 伪造凭证 / openid 不一致
        logger.warning("[QQ] 移动端凭证核验失败: %s", exc)
        raise HTTPException(status_code=401, detail="QQ 授权信息校验失败，请重新授权")


@router.post("/qq/mobile/authorize", response_model=QqMobileAuthorizeOut)
def qq_mobile_authorize(
    req: QqMobileTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """App 内 QQ 登录：原生 SDK 授权后前端直报 access_token/openid。

    已绑定校园账号 → 直接登录；未绑定 → 下发 15 分钟注册票据，
    前端引导到注册页补全学籍信息后凭 qq_ticket 完成注册。
    与网站应用 OAuth 不同，本通道只需要 QQ_APP_ID（无需 AppKey 与回调域名）。
    """
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)
    nickname = _qq_mobile_verify(req)

    openid = req.openid.strip()
    user = db.query(User).filter(User.qq_openid == openid).first()
    if user:
        _assert_login_allowed(user)
        result = _attach_quick(user, _login_result(user))
        _set_auth_cookie(response, result["access_token"])
        return {"status": "login", "login": result}

    ticket = qq_oauth_service.create_register_ticket(openid, nickname)
    return {"status": "unregistered", "register_ticket": ticket, "nickname": nickname}


@router.post("/qq/mobile/bind", response_model=UserInfo)
def qq_mobile_bind(
    req: QqMobileTokenRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """App 内绑定 QQ：当前登录账号与 SDK 授权的 QQ 建立绑定，被占用即拒绝。"""
    nickname = _qq_mobile_verify(req)

    openid = req.openid.strip()
    occupied = db.query(User).filter(User.qq_openid == openid, User.id != user.id).first()
    if occupied:
        raise HTTPException(status_code=409, detail="该 QQ 已绑定其他校园账号")
    user.qq_openid = openid
    user.qq_nickname = nickname or user.qq_nickname
    db.commit()
    db.refresh(user)
    return UserInfo.model_validate(user)


# ==================== 学生自助注册 ====================

_REG_PHONE_TICKET_PURPOSE = "reg_phone_ticket"
_STUDENT_NO_RE = re.compile(r"[0-9]{5,15}")
_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*[0-9])[\x21-\x7e]{8,20}$")


def _create_reg_phone_ticket(phone: str) -> str:
    payload = {
        "purpose": _REG_PHONE_TICKET_PURPOSE,
        "phone": phone,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_reg_phone_ticket(ticket: str | None) -> str | None:
    if not ticket:
        return None
    try:
        payload = jwt.decode(ticket, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.JWTError:
        return None
    if payload.get("purpose") != _REG_PHONE_TICKET_PURPOSE:
        return None
    return payload.get("phone")


@router.get("/register/options")
def register_options(db: Session = Depends(get_db)):
    """注册页公开选项：学院、专业、导师（导师按学院归属过滤）。"""
    colleges = db.query(College).order_by(College.name).all()
    majors = db.query(Major).order_by(Major.name).all()
    teachers = db.query(User).filter(User.role == UserRole.TEACHER).order_by(User.name).all()
    return {
        "colleges": [{"id": c.id, "name": c.name} for c in colleges],
        "majors": [{"id": m.id, "college_id": m.college_id, "name": m.name} for m in majors],
        "tutors": [
            {"id": t.id, "name": t.name, "college": t.college, "title": t.title}
            for t in teachers
        ],
    }


@router.post("/register/sms/send")
def send_register_sms(req: RegisterSmsRequest, request: Request, db: Session = Depends(get_db)):
    """注册短信验证码：先校验图形验证码，再做号码占用检查。"""
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)

    phone = _require_phone(req.phone)
    _verify_captcha(req.captcha_id, req.captcha_code)
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=409, detail="该手机号已绑定校园账号，请直接登录")

    try:
        issued = sms_service.issue_code(phone, "register")
    except sms_service.SmsCooldown as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except sms_service.SmsNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except sms_service.SmsSendFailed as exc:
        _record_sms_log(db, None, phone, sms_service.provider_name(), "failed")
        raise HTTPException(status_code=502, detail=str(exc))

    _record_sms_log(db, None, phone, issued.provider, "skipped" if issued.debug_code else "sent")
    return {
        "provider": issued.provider,
        "configured": issued.configured,
        "expires_in": issued.expires_in,
        "cooldown": issued.cooldown,
        "debug_code": issued.debug_code,
    }


@router.post("/register/phone/verify")
def verify_register_phone(req: RegisterPhoneVerifyRequest, db: Session = Depends(get_db)):
    """校验注册短信验证码，通过后下发短期手机号凭证（15 分钟）。"""
    phone = _require_phone(req.phone)
    try:
        sms_service.verify_code(phone, "register", req.code)
    except sms_service.SmsCodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=409, detail="该手机号已绑定校园账号，请直接登录")
    return {"phone": phone, "phone_ticket": _create_reg_phone_ticket(phone)}


@router.post("/register", response_model=LoginResponse)
def register_student(req: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """自助注册：先选身份（学生 / 教师），手机号/QQ 至少一种完成真实验证。"""
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)

    role_key = (req.role or "student").strip().lower()
    if role_key not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="请先选择注册身份（学生或教师）")
    is_teacher = role_key == "teacher"
    account_label = "工号" if is_teacher else "学号"

    student_no = (req.student_no or "").strip()
    if not _STUDENT_NO_RE.fullmatch(student_no):
        raise HTTPException(status_code=400, detail=f"{account_label}必须为 5-15 位数字")
    if db.query(User).filter(User.username == student_no).first():
        raise HTTPException(status_code=409, detail=f"该{account_label}已存在，请直接登录")
    if not _PASSWORD_RE.match(req.password or ""):
        raise HTTPException(status_code=400, detail="密码需为 8-20 位，且同时包含字母和数字")

    name = (req.name or "").strip()
    if not 2 <= len(name) <= 20:
        raise HTTPException(status_code=400, detail="请填写 2-20 个字的真实姓名")

    college = db.query(College).filter(College.id == req.college_id).first()
    if not college:
        raise HTTPException(status_code=400, detail="所选学院不存在")

    major: Major | None = None
    tutor: User | None = None
    if not is_teacher:
        major = db.query(Major).filter(Major.id == req.major_id).first()
        if not major or major.college_id != college.id:
            raise HTTPException(status_code=400, detail="所选专业不属于该学院")
        # 导师为选填：仅在提交了 tutor_id 时校验归属
        if req.tutor_id:
            tutor = db.query(User).filter(User.id == req.tutor_id, User.role == UserRole.TEACHER).first()
            if not tutor:
                raise HTTPException(status_code=400, detail="所选导师不存在")
            if tutor.college and tutor.college != college.name:
                raise HTTPException(status_code=400, detail="所选导师不属于该学院")

    verified_phone: str | None = None
    qq_openid: str | None = None
    qq_nickname: str | None = None

    if req.phone_ticket:
        ticket_phone = _decode_reg_phone_ticket(req.phone_ticket)
        if not ticket_phone:
            raise HTTPException(status_code=400, detail="手机号验证已失效，请重新验证")
        if req.phone and _normalize_phone(req.phone) != ticket_phone:
            raise HTTPException(status_code=400, detail="手机号与验证凭证不一致")
        verified_phone = ticket_phone
    elif req.qq_ticket:
        # QQ 授权通道：QQ 已完成真实验证，手机号改为选填
        verified_phone = None
    else:
        # 短信通道申请期间，注册页直接收集手机号，不做短信归属校验
        verified_phone = _require_phone(req.phone)

    if req.qq_ticket:
        qq_payload = qq_oauth_service.decode_register_ticket(req.qq_ticket)
        if not qq_payload:
            raise HTTPException(status_code=400, detail="QQ 授权已失效，请重新授权")
        qq_openid = qq_payload.get("openid")
        qq_nickname = qq_payload.get("nickname")
        if db.query(User).filter(User.qq_openid == qq_openid).first():
            raise HTTPException(status_code=409, detail="该 QQ 已绑定其他账号")

    # 手机号需唯一（QQ 票据通道下可为空，空值不做查询，避免 == None 误匹配 NULL 行）；
    # 手动填写的 QQ 号仅作展示/找回密码辅助，不做登录凭据
    if verified_phone and db.query(User).filter(User.phone == verified_phone).first():
        raise HTTPException(status_code=409, detail="该手机号已绑定校园账号，请直接登录")
    manual_qq = (req.qq or "").strip() or None
    if manual_qq and not re.fullmatch(r"[0-9]{5,12}", manual_qq):
        raise HTTPException(status_code=400, detail="QQ 号格式不正确")

    # 未通过短信 / QQ 票据验证时（第三方通道申请期间），用图形验证码防刷
    if not req.phone_ticket and not req.qq_ticket:
        _verify_captcha(req.captcha_id, req.captcha_code)

    user = User(
        username=student_no,
        name=name,
        role=UserRole.TEACHER if is_teacher else UserRole.STUDENT,
        password_hash=hash_password(req.password),
        college=college.name,
        department=major.name if major else None,
        tutor_id=tutor.id if tutor else None,
        phone=verified_phone,
        qq=manual_qq,
        qq_openid=qq_openid,
        qq_nickname=qq_nickname,
        password_changed=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    result = _attach_quick(user, _login_result(user))
    _set_auth_cookie(response, result["access_token"])
    return result


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
        # 管理员在顶栏消息中点击后直接进入对应人员管理页，按账号聚焦后一键重置
        manage_page = "学生管理" if user.role == UserRole.STUDENT else "教师管理"
        manage_link = "/admin/students" if user.role == UserRole.STUDENT else "/admin/teachers"
        send_batch_notifications(
            db,
            admin_ids,
            title="收到密码重置申请",
            content=(
                f"{user.name}（{user.username}）申请重置密码，联系方式 {_mask_contact(contact_digits)}。"
                f"请在「{manage_page}」中搜索该账号并重置密码，重置后将恢复为初始密码 {PASSWORD_RESET_INITIAL_PASSWORD}。"
            ),
            notification_type=NotificationType.SYSTEM,
            link=f"{manage_link}?focus={user.username}",
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
    # 先校验图形验证码，避免被脚本暴力枚举旧密码
    _verify_captcha(data.captcha_id, data.captcha_code)

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