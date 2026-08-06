"""速率限制

注意：当前为内存实现，重启后重置。多 worker 部署建议改用 Redis。
"""
import time
import os
from collections import defaultdict
from fastapi import HTTPException


_attempts: dict[str, list[float]] = defaultdict(list)

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


def check_login_rate_limit(ip: str) -> None:
    if os.environ.get("TESTING") == "1":
        return
    now = time.time()
    window_start = now - WINDOW_SECONDS
    _attempts[ip] = [t for t in _attempts[ip] if t > window_start]
    if len(_attempts[ip]) >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"登录尝试过于频繁，请{WINDOW_SECONDS}秒后再试",
        )
    _attempts[ip].append(now)


def reset_rate_limiter() -> None:
    _attempts.clear()
