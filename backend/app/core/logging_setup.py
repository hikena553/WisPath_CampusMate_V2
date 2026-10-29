"""结构化日志基础设施（可观测性 p4_1）

- JsonFormatter：单行 JSON 输出，便于日志收集器（Loki/ELK 等）直接解析；
- setup_logging()：按 Settings.LOG_LEVEL 配置根 logger，同时输出到 stdout
  与轮转文件 logs/app.log，并保持与其他模块标准 logging 调用方式完全兼容。

为什么要落盘（稳定性 p4_2）：
  开发期进程崩溃 / 被关闭时，控制台窗口一关 stdout 全部丢失，事后无法判断
  是 OOM、端口占用还是未捕获异常。文件日志（10MB × 5 轮转）保证"死无对证"
  不再发生——进程重启后仍能翻到上一次崩溃前的最后几十行。

环境变量：
  LOG_TO_FILE=0  关闭文件输出（仅 stdout）
  LOG_FILE=...   自定义日志文件路径
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

# backend/logs —— 本文件位于 backend/app/core/
_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_DEFAULT_LOG_FILE = _LOG_DIR / "app.log"


class JsonFormatter(logging.Formatter):
    """输出单行 JSON 的日志格式化器。

    标准字段：ts / level / logger / msg；
    extra 自定义字段（request_id、method、path、status_code、duration_ms、
    user_id、client_ip 等）自动并入 JSON；异常堆栈写入 exc 字段。
    """

    _EXTRA_FIELDS = (
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "user_id",
        "client_ip",
    )

    @staticmethod
    def _format_time(record: logging.LogRecord) -> str:
        return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self._format_time(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in self._EXTRA_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _build_file_handler() -> logging.Handler | None:
    """构造轮转文件 handler；不可写时返回 None（不影响服务启动）。"""
    if os.getenv("LOG_TO_FILE", "1") == "0":
        return None

    log_path = Path(os.getenv("LOG_FILE") or _DEFAULT_LOG_FILE)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
    except OSError:
        # 目录只读 / 磁盘满等极端情况：降级为仅 stdout，绝不因日志导致启动失败
        return None

    handler.setFormatter(JsonFormatter())
    return handler


def setup_logging() -> None:
    """配置根 logger：JSON 行输出 + 由 LOG_LEVEL 环境变量控制级别（默认 INFO）。

    幂等设计：重复调用先清空旧 handler 再装配，方便测试中重置。
    """
    level_name = (settings.LOG_LEVEL or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    if not isinstance(level, int):
        level = logging.INFO

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)

    file_handler = _build_file_handler()
    if file_handler is not None:
        root.addHandler(file_handler)
