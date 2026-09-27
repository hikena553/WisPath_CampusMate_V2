"""后台周期任务：统一在此登记与启停，避免业务逻辑散落在应用入口。"""
import asyncio
import contextlib
import logging

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 1800


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


def start_periodic_tasks() -> list[asyncio.Task]:
    """创建全部周期任务，返回任务句柄供应用生命周期管理。"""
    return [
        asyncio.create_task(_periodic_impression_refresh()),
        asyncio.create_task(_periodic_feed_refresh()),
    ]


async def stop_periodic_tasks(tasks: list[asyncio.Task]) -> None:
    """优雅取消全部周期任务。"""
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await task