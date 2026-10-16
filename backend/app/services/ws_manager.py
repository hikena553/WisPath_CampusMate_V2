from fastapi import WebSocket


class ConnectionManager:
    """用户级 WebSocket 连接池。

    同一用户可能同时有多个连接（例如布局层的全局未读提醒 + 消息页的会话实时推送），
    因此按 user_id 维护一个连接集合，广播时逐个下发。
    """

    def __init__(self):
        self.active: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> bool:
        """登记一条连接，返回该用户是否由「离线」转为「在线」（首条连接）。"""
        await ws.accept()
        socks = self.active.get(user_id)
        first = not socks
        self.active.setdefault(user_id, set()).add(ws)
        return first

    def disconnect(self, user_id: int, ws: WebSocket | None = None) -> bool:
        """未指定 ws 时清空该用户全部连接（兜底）；指定时只摘除该连接。

        返回该用户是否由「在线」变为「离线」（最后一条连接被摘除）。
        """
        if ws is None:
            return bool(self.active.pop(user_id, None))
        socks = self.active.get(user_id)
        if not socks:
            return False
        socks.discard(ws)
        if not socks:
            self.active.pop(user_id, None)
            return True
        return False

    async def send_json(self, user_id: int, data: dict):
        for ws in list(self.active.get(user_id, ())):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(user_id, ws)

    def is_online(self, user_id: int) -> bool:
        """该用户是否有活跃连接（视为已登录在线）。"""
        return bool(self.active.get(user_id))

    def online_ids(self) -> set[int]:
        """当前所有在线用户 id 集合（供批量判定，如群在线人数）。"""
        return set(self.active.keys())

    async def broadcast(self, data: dict):
        """向所有在线用户下发同一条消息（用于在线状态变更广播）。"""
        for user_id in list(self.active.keys()):
            await self.send_json(user_id, data)


manager = ConnectionManager()