"""实时事件推送路由（SSE）。

前端用 EventSource 订阅 /api/realtime/stream，收到 {domains:[...]} 后
按需重拉对应接口，取代首页原先的 30 秒全量轮询。
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import _read_token
from app.core.security import decode_access_token, is_token_revoked
from app.models.user import User
from app.services.realtime import hub

router = APIRouter(prefix="/api/realtime", tags=["实时推送"])

# 心跳间隔：EventSource 自身不保证探测半开连接，靠注释帧维持链路，
# 同时让中间代理（Nginx 默认 60s 空闲超时）不会把连接掐掉。
_HEARTBEAT_SECONDS = 15


def _resolve_sse_user(request: Request, token: str | None, db: Session) -> User:
    """SSE 专用认证：EventSource 无法自定义请求头，因此依次尝试
    1) ?token= 查询参数（刷新后内存 token 仍在时由前端附加）；
    2) httpOnly Cookie（刷新后内存 token 为空时的常规通道）。
    """
    raw = token or _read_token(request)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已失效")
    payload = decode_access_token(raw)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token")
    if is_token_revoked(raw):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token")
    user = db.query(User).filter(User.id == int(sub)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    # 密码变更后旧 token 失效，与 get_current_user 保持一致
    if payload.get("ph") and not user.password_hash.startswith(payload["ph"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="密码已修改，请重新登录")
    return user


@router.get("/stream")
async def realtime_stream(
    request: Request,
    token: str | None = Query(default=None, description="SSE 无自定义头能力时的 token 通道，可省略"),
    db: Session = Depends(get_db),
):
    """教师端实时数据变更事件流。

    事件格式：
      event: ready        —— 建连成功后立即下发一次，前端据此标记「实时可用」
      event: change       —— data 为 {"domains": [...]}，前端按域重拉
      `: ping`            —— 心跳注释帧，前端忽略

    注意：本函数是 async，认证查库是同步操作。为不阻塞事件循环，
    认证在进入流式生成前完成（此时仍在请求处理阶段，连接数有限），
    之后的长连接里不再触碰数据库。
    """
    user = _resolve_sse_user(request, token, db)

    queue = hub.subscribe(user.id)
    # 内置提示：仅教师/管理员会用到工作台数据；学生端订阅也无害（不会有事件推送）
    user_id = user.id

    async def event_generator():
        try:
            yield "event: ready\ndata: " + json.dumps({"user_id": user_id}, ensure_ascii=False) + "\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    # 心跳：SSE 注释帧，EventSource 不会派发 message 事件，前端无需处理。
                    # 写心跳本身也是存活性探针：客户端已断开时写入会让框架抛异常/取消生成器。
                    yield ": ping\n\n"
                    continue
                yield "event: change\ndata: " + payload + "\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            # 客户端断开 / 代理超时 / 服务关闭：正常收尾，不当作错误
            raise
        finally:
            hub.unsubscribe(user_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # 关闭 Nginx 对 SSE 的响应缓冲，否则事件会被攒着一起发
            "X-Accel-Buffering": "no",
        },
    )
