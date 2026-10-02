"""结构化日志基础设施（可观测性 p4_1）

- JsonFormatter：单行 JSON 输出，便于日志收集器（Loki/ELK 等）直接解析；
- setup_logging()：按 Settings.LOG_LEVEL 配置根 logger，保持与其他模块标准
  logging 调用方式完全兼容（logger.info/exception 等用法不变）。
"""
import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings


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


def setup_logging() -> None:
    """配置根 logger：JSON 行输出 + 由 LOG_LEVEL 环境变量控制级别（默认 INFO）。

    幂等设计：重复调用先清空旧 handler 再装配，方便测试中重置。
    """
    level_name = (settings.LOG_LEVEL or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    if not isinstance(level, int):
        level = logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)