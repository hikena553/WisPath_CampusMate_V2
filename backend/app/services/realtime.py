"""教师端实时数据通道（SSE）。

设计取舍：
- 工作台 / 工作量的「同步」只关心「哪个业务域变了」，不需要双向通信，
  因此走 SSE（单向、浏览器原生 EventSource 自动重连、可穿过大多数代理），
  WebSocket 继续只服务聊天这类需要双向高频交互的场景，不混用。
- 推送粒度是「域」（domain），不是具体数据。服务端只告知 teacher-care 变了，
  前端按需重拉相应接口，避免在推送里维护一份与接口易漂移的冗余数据快照。
- 多进程 / 多 worker 部署时，进程内的订阅表只能推送到本进程；
  因此业务侧变更后由前端兜底轮询补齐（见前端 realtime.ts），
  这里不引入 Redis 依赖，保持单机零额外组件。

复用前端已有的事件域命名（src/utils/dataSync.ts 的 DataDomain），
两端字符串必须保持一致，否则前端收到未知域会丢弃事件。
"""

from __future__ import annotations

import asyncio
import json
from typing import Iterable

# 与前端 DataDomain 对齐：新增域时两边同步修改
VALID_DOMAINS = {
    "teacher-tasks",
    "teacher-students",
    "teacher-dashboard",
    "teacher-care",
    "teacher-approval",
    "teacher-crisis",
}

# 单个教师的待推送队列上限：前端长时间卡死或网络中断时，避免无界堆积占内存。
# 超出后丢弃最旧事件（只保留最新状态），因为推送语义是「数据变了，来拉一次」，
# 丢中间事件不影响最终一致性。
_MAX_QUEUE = 32


class RealtimeHub:
    """按 user_id 维护 SSE 订阅者。

    每个订阅者是一条 asyncio.Queue，publish 为同步方法：
    业务代码大多跑在同步路由里（FastAPI 的 def 路由在线程池执行），
    通过 loop.call_soon_threadsafe 把事件投递回事件循环，避免跨线程直接操作队列。
    """

    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue]] = {}
        # 记录每个 user_id 的订阅者绑定的 loop，用于跨线程投递
        self._loops: dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}

    def subscribe(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 非异步上下文（理论上不会走到）
            loop = None
        if loop is not None:
            self._loops[queue] = loop
        self._subscribers.setdefault(user_id, set()).add(queue)
        return queue

    def unsubscribe(self, user_id: int, queue: asyncio.Queue) -> None:
        self._loops.pop(queue, None)
        socks = self._subscribers.get(user_id)
        if not socks:
            return
        socks.discard(queue)
        if not socks:
            self._subscribers.pop(user_id, None)

    def listener_count(self, user_id: int) -> int:
        return len(self._subscribers.get(user_id, ()))

    def publish(self, user_id: int, domains: Iterable[str]) -> None:
        """向指定教师的所有在线标签页推送一次「域变更」事件。

        同步、不抛异常：业务写操作的成败不应被推送失败影响。
        """
        clean = [d for d in dict.fromkeys(domains) if d in VALID_DOMAINS]
        if not clean:
            return
        payload = json.dumps({"domains": clean}, ensure_ascii=False)
        for queue in list(self._subscribers.get(user_id, ())):
            loop = self._loops.get(queue)
            if loop is None or loop.is_closed():
                continue
            try:
                loop.call_soon_threadsafe(self._offer, queue, payload)
            except RuntimeError:
                # loop 已关闭（进程退出 / 事件循环回收），静默跳过
                continue

    @staticmethod
    def _offer(queue: asyncio.Queue, payload: str) -> None:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            # 队列满：丢掉最旧的一条再放新的，保证订阅者拿到的是最新变更
            try:
                queue.get_nowait()
                queue.put_nowait(payload)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

    def publish_many(self, user_ids: Iterable[int], domains: Iterable[str]) -> None:
        """同一变更影响多位教师时（如管理员批量审批），逐个推送。"""
        domain_list = list(domains)
        for uid in set(user_ids):
            self.publish(uid, domain_list)


hub = RealtimeHub()
