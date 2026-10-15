from fastapi import WebSocket


class ConnectionManager:
    """用户级 WebSocket 连接池。

    同一用户可能同时有多个连接（例如布局层的全局未读提醒 + 消息页的会话实时推送），
    因此按 user_id 维护一个连接集合，广播时逐个下发。
    """

    def __init__(self):
        self.active: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket | None = None):
        """未指定 ws 时清空该用户全部连接（兜底）；指定时只摘除该连接。"""
        if ws is None:
            self.active.pop(user_id, None)
            return
        socks = self.active.get(user_id)
        if not socks:
            return
        socks.discard(ws)
        if not socks:
            self.active.pop(user_id, None)

    async def send_json(self, user_id: int, data: dict):
        for ws in list(self.active.get(user_id, ())):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(user_id, ws)


manager = ConnectionManager()