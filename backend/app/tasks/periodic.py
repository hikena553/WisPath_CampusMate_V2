"""后台周期任务：统一在此登记与启停，避免业务逻辑散落在应用入口。"""
import asyncio
import contextlib
import logging

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 1800
# 主动触达推送间隔：30 分钟扫一轮全体学生，命中规则即落库站内通知
PROACTIVE_INTERVAL_SECONDS = 1800
# Agent 定时任务：每分钟扫一次到期任务
CRON_TASK_SCAN_INTERVAL_SECONDS = 60


async def _periodic_impression_refresh() -> None:
    """定期刷新心情印象数据。"""
    from app.services.impression_crawler import refresh_impression_data

    while True:
        try:
            await asyncio.to_thread(refresh_impression_data)
        except Exception:
            logger.exception("后台定期刷新任务异常")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


async def _periodic_feed_refresh() -> None:
    """定期抓取外部资讯（论文/开源榜/智能体榜/权威要闻）入库。"""
    from app.services.feed_ingest import ingest_all

    while True:
        try:
            await asyncio.to_thread(ingest_all)
        except Exception:
            logger.exception("后台定期外部资讯抓取异常")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


async def _periodic_proactive_push() -> None:
    """定期执行 AI 主动触达全量评估：命中规则即落库站内通知，实现服务端自动推送。"""
    from app.services.proactive_engine import evaluate_all

    while True:
        try:
            await asyncio.to_thread(evaluate_all)
        except Exception:
            logger.exception("后台主动触达推送异常")
        await asyncio.sleep(PROACTIVE_INTERVAL_SECONDS)


async def _periodic_cron_task_runner() -> None:
    """Agent 定时任务调度：每分钟扫描一次到期任务并执行。

    测试环境不启动（conftest 注入 TESTING=1）：测试会直接调用
    execute_due_tasks() 验证内核，避免调度循环抢跑真实任务。
    """
    import os

    if os.getenv("TESTING") == "1":
        return
    from app.services.cron_task_service import execute_due_tasks

    while True:
        try:
            await execute_due_tasks()
        except Exception:
            logger.exception("[定时任务] 调度扫描异常")
        await asyncio.sleep(CRON_TASK_SCAN_INTERVAL_SECONDS)


def start_periodic_tasks() -> list[asyncio.Task]:
    """创建全部周期任务，返回任务句柄供应用生命周期管理。"""
    from app.tasks.learning_alert import _periodic_learning_alert

    return [
        asyncio.create_task(_periodic_impression_refresh()),
        asyncio.create_task(_periodic_feed_refresh()),
        # 学习预警 pipeline：每小时检查，内部按「每日一次」标记真正执行
        asyncio.create_task(_periodic_learning_alert()),
        # AI 主动触达：每 30 分钟扫描全体学生，命中规则落到站内通知
        asyncio.create_task(_periodic_proactive_push()),
        # Agent 定时任务：每分钟扫描到期任务，AI 到点自动执行
        asyncio.create_task(_periodic_cron_task_runner()),
    ]


async def stop_periodic_tasks(tasks: list[asyncio.Task]) -> None:
    """优雅取消全部周期任务。"""
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await task