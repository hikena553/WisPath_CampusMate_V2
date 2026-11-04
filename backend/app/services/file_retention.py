"""聊天文件保留策略：聊天里发送的文件只在服务器保留 7 天，到期自动删除。

周期任务 `app/tasks/periodic.py` 每小时调一次 `purge_expired_chat_files`。
删除后历史消息里的附件链接会返回 404，这是预期行为（消息文本仍在）。
"""
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CHAT_FILE_DIR = BACKEND_ROOT / "uploads" / "chat_files"
CHAT_FILE_RETENTION_DAYS = 7


def purge_expired_chat_files(retention_days: int = CHAT_FILE_RETENTION_DAYS) -> int:
    """删除超过保留期的聊天文件，返回删除数量。"""
    if not CHAT_FILE_DIR.is_dir():
        return 0
    cutoff = time.time() - retention_days * 24 * 3600
    removed = 0
    for path in CHAT_FILE_DIR.iterdir():
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            logger.warning("[聊天文件] 删除失败: %s", path, exc_info=True)
    if removed:
        logger.info("[聊天文件] 已清理 %d 个超过 %d 天的文件", removed, retention_days)
    return removed
