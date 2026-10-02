"""强制首登改密中间件

拦截携带有效令牌但未修改初始密码（password_changed=False）的用户，
仅放行白名单接口，其余 /api/* 一律 403，确保弱默认口令无法进入业务功能。
WebSocket（原样透传）由各 ws 端点自行校验 password_changed。
"""
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

_PASSWD_REQUIRED_HINT = "请先修改初始密码后再使用该功能"


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
            if auth.startswith("Bearer "):
                payload = decode_access_token(auth[7:])
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