"""安全中间件

1. EnforcePasswordChangeMiddleware：拦截携带有效令牌但未修改初始密码（password_changed=False）的
   用户，仅放行白名单接口，其余 /api/* 一律 403，确保弱默认口令无法进入业务功能。
   WebSocket（原样透传）由各 ws 端点自行校验 password_changed。
2. CsrfProtectionMiddleware：对携带认证 Cookie 的「写请求」强制要求自定义头
   X-Requested-With（axios 侧自动注入），与 SameSite=Lax 一起构成纵深 CSRF 防护。
"""
from urllib.parse import unquote

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

# 未改密用户可访问的接口白名单
PASSWORD_CHANGE_WHITELIST = (
    "/api/auth/login",
    "/api/auth/me",
    "/api/auth/change-password",
    "/api/health",
)

# 与 core/deps.py 保持一致
AUTH_COOKIE_NAME = "campus_token"

_PASSWD_REQUIRED_HINT = "请先修改初始密码后再使用该功能"
_CSRF_REQUIRED_HINT = "请求头校验失败"

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class EnforcePasswordChangeMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # websocket 等协议原样透传，由端点自校验
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith("/api") and not path.startswith(PASSWORD_CHANGE_WHITELIST):
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in (scope.get("headers") or [])
            }
            auth = headers.get("authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else None
            if not token:
                # httpOnly Cookie 通道（F3）
                cookie = headers.get("cookie", "")
                token = _read_cookie(cookie, AUTH_COOKIE_NAME)
            if token:
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        db = SessionLocal()
                        try:
                            user = db.get(User, int(user_id))
                            if user is not None and not user.password_changed:
                                response = JSONResponse(status_code=403, content={"detail": _PASSWD_REQUIRED_HINT})
                                await response(scope, receive, send)
                                return
                        finally:
                            db.close()

        await self.app(scope, receive, send)


class CsrfProtectionMiddleware:
    """CSRF 纵深防护：写请求若携带认证 Cookie，必须同时带有 X-Requested-With 头。

    - SameSite=Lax 已阻断绝大多数跨站 Cookie 携带；
    - 自定义头无法被跨站表单/图片自动附带，是第二道防线。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        if method not in _SAFE_METHODS:
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in (scope.get("headers") or [])
            }
            cookie = headers.get("cookie", "")
            if _read_cookie(cookie, AUTH_COOKIE_NAME) and not headers.get("x-requested-with"):
                response = JSONResponse(status_code=403, content={"detail": _CSRF_REQUIRED_HINT})
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


def _read_cookie(cookie_header: str, name: str) -> str | None:
    """解析 Cookie 头中指定名称的值（兼容 URL-encoded 值）。"""
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(f"{name}="):
            return unquote(part[len(name) + 1:])
    return None