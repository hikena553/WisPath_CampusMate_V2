"""速率限制

注意：当前为内存实现，重启后重置。多 worker 部署建议改用 Redis（见部署接口预留说明）。
旁路规则：仅 ENV=development 且 TESTING=1 时跳过限流（测试友好）；
生产 / 预发环境无论 TESTING 取值如何一律执行限流。
"""
import time
import os

from collections import defaultdict

from fastapi import HTTPException

from app.core.config import settings

_buckets: dict[str, list[float]] = defaultdict(list)

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


def _rate_limit_enabled() -> bool:
    if settings.ENV != "development":
        return True
    return os.environ.get("TESTING") != "1"


def check_rate_limit(
    key: str,
    max_attempts: int,
    window_seconds: int,
    message: str,
) -> None:
    """通用滑动窗口限流。

    key 建议组合维度隔离，例如 f"chat:user:{user.id}"、
    f"upload:ip:{client_ip}"；超限抛 429。
    """
    if not _rate_limit_enabled():
        return
    now = time.time()
    window_start = now - window_seconds
    bucket: list[float] = _buckets[key]
    bucket[:] = [t for t in bucket if t > window_start]
    if len(bucket) >= max_attempts:
        raise HTTPException(status_code=429, detail=message)
    bucket.append(now)


def check_login_rate_limit(ip: str) -> None:
    check_rate_limit(
        f"login:ip:{ip}",
        MAX_ATTEMPTS,
        WINDOW_SECONDS,
        f"登录尝试过于频繁，请{WINDOW_SECONDS}秒后再试",
    )


def reset_rate_limiter() -> None:
    _buckets.clear()