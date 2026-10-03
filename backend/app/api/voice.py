import logging
from urllib.parse import unquote

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from app.core.security import decode_access_token, is_token_revoked
from app.core.database import SessionLocal
from app.core.deps import AUTH_COOKIE_NAME
from app.models.user import User
from app.services.voice_service import handle_voice_connection
from app.utils.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# 语音连接限流：用户级 5 次/分钟，IP 兜底 15 次/分钟
RATE_VOICE_PER_MIN = 5
RATE_VOICE_IP_PER_MIN = 15


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
async def voice_websocket(
    ws: WebSocket,
    token: str | None = Query(None),
    conversation_id: int | None = Query(None),
):
    """语音通话 WebSocket 端点（token 支持 Query 参数或 httpOnly Cookie 双通道）"""
    # 认证：Query 参数优先，其次 Cookie
    if not token:
        token = _ws_cookie_token(ws)
    payload = decode_access_token(token) if token else None
    if not payload:
        await ws.close(code=4001, reason="认证失败")
        return
    if token and is_token_revoked(token):
        await ws.close(code=4001, reason="登录已失效")
        return

    user_id = int(payload.get("sub", 0))
    if not user_id:
        await ws.close(code=4001, reason="认证失败")
        return

    # 查询用户
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await ws.close(code=4001, reason="用户不存在")
            return
        # 未修改初始密码不再阻断语音通话：仅在 /api/auth/me 打标记由前端提醒
    finally:
        db.close()

    # 限流：用户级 5 次/分钟 + IP 兜底 15 次/分钟
    client_ip = ws.client.host if ws.client else "unknown"
    try:
        check_rate_limit(f"voice:user:{user_id}", RATE_VOICE_PER_MIN, 60, "操作过于频繁")
        check_rate_limit(f"voice:ip:{client_ip}", RATE_VOICE_IP_PER_MIN, 60, "操作过于频繁")
    except HTTPException:
        await ws.close(code=4002, reason="连接过于频繁，请稍后再试")
        return

    # 验证 conversation_id 归属
    if conversation_id:
        db = SessionLocal()
        try:
            from app.models.conversation import Conversation
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            ).first()
            if not conv:
                await ws.close(code=4004, reason="对话不存在")
                return
        finally:
            db.close()

    await ws.accept()
    logger.info(f"用户 {user_id} 建立语音连接, conversation_id={conversation_id}")

    try:
        await handle_voice_connection(ws, user, conversation_id)
    except WebSocketDisconnect:
        logger.info(f"用户 {user_id} 断开语音连接")
    except Exception as e:
        logger.exception(f"语音连接异常: {e}")
        try:
            await ws.close(code=1011, reason="服务端错误")
        except Exception:
            pass
