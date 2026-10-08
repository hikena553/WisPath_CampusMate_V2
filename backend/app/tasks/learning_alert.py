"""学习预警定时任务：每日扫描学情事件，命中规则即生成教师待办。

设计：任务本身每小时醒一次，是否真正执行由 alert_pipeline_service.scan() 内部的
「每日一次」标记（SystemSetting.learning_alert_last_run）决定，避免重复派单。
"""
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 3600


def run_daily_scan(force: bool = False) -> dict:
    """同步执行一次扫描（供定时任务与手动触发复用）。"""
    from app.core.database import SessionLocal
    from app.services import alert_pipeline_service

    db = SessionLocal()
    try:
        return alert_pipeline_service.scan(db, force=force)
    except Exception:
        logger.exception("[ALERT-PIPELINE] 扫描执行失败")
        return {"error": "scan_failed"}
    finally:
        db.close()


async def _periodic_learning_alert() -> None:
    """每小时检查一次；测试环境跳过，避免干扰用例确定性。"""
    while True:
        if os.environ.get("TESTING") != "1":
            await asyncio.to_thread(run_daily_scan)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)