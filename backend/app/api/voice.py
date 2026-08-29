import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_access_token
from app.core.database import SessionLocal
from app.models.user import User
from app.services.voice_service import handle_voice_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.websocket("/ws")
async def voice_websocket(
    ws: WebSocket,
    token: str = Query(...),
    conversation_id: int | None = Query(None),
):
    """语音通话 WebSocket 端点"""
    # 认证
    payload = decode_access_token(token)
    if not payload:
        await ws.close(code=4001, reason="认证失败")
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
    finally:
        db.close()

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
