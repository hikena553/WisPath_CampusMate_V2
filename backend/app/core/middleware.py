"""安全中间件

1. CsrfProtectionMiddleware：对携带认证 Cookie 的「写请求」强制要求自定义头
   X-Requested-With（axios 侧自动注入），与 SameSite=Lax 一起构成纵深 CSRF 防护。
2. RequestLogMiddleware：全量 HTTP 请求访问日志（方法/路径/状态/耗时/来源 IP/用户），
   与 JsonFormatter 配合输出单行 JSON；慢请求（>1s）与 5xx 自动升级 WARNING。

未修改初始密码（password_changed=False）不再拦截任何业务接口：仅由 /api/auth/me
返回 password_needs_change 标记，前端据此做非阻断提醒（横幅 + 改密入口）。
"""
import logging
import time
from urllib.parse import unquote

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.security import decode_access_token

# 与 core/deps.py 保持一致
AUTH_COOKIE_NAME = "campus_token"

_CSRF_REQUIRED_HINT = "请求头校验失败"

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# 慢请求阈值（毫秒）：超过记 WARNING 级日志
SLOW_REQUEST_MS = 1000


def _extract_token(headers: dict) -> str | None:
    """从 Authorization Bearer 或认证 Cookie 中提取令牌（与 deps.py 同源逻辑）。"""
    auth = headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    cookie = headers.get("cookie", "")
    return _read_cookie(cookie, AUTH_COOKIE_NAME) if cookie else None


class RequestLogMiddleware:
    """全量 HTTP 请求访问日志：method/path/status/耗时/IP/用户（可观测性 p4_1）。

    注册为最外层中间件，记录的耗时包含全部下游中间件与业务处理；
    结构化为 JSON 行（extra 字段与 JsonFormatter 对齐）。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("app.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        method = scope.get("method", "")
        path = scope.get("path", "")
        client = scope.get("client") or (None, 0)
        client_ip = client[0]

        user_id = None
        try:
            headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in (scope.get("headers") or [])}
            token = _extract_token(headers)
            if token:
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("sub")
        except Exception:  # 日志路径绝不影响业务
            user_id = None

        status_holder: dict = {"status": 500}

        async def wrapped_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        except Exception:
            status_holder["status"] = 500
            self.logger.exception(
                "request error",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": 500,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                    "user_id": user_id,
                    "client_ip": client_ip,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            status_code = status_holder["status"]
            # 慢请求（>SLOW_REQUEST_MS）与 5xx 升级为 WARNING，便于监控告警分级
            level = (
                logging.WARNING
                if status_code >= 500 or duration_ms > SLOW_REQUEST_MS
                else logging.INFO
            )
            self.logger.log(
                level,
                "request",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "client_ip": client_ip,
                },
            )


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