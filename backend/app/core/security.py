import hashlib
import secrets
import string
import time
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.config import settings


def generate_random_password(length: int = 10) -> str:
    """生成一次性随机强密码：至少 8 位且同时包含字母与数字（满足 change_password 强度校验）。"""
    if length < 8:
        length = 8
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isalpha() for c in pwd) and any(c.isdigit() for c in pwd):
            return pwd


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ============ 登出撤销（内存黑名单） ============
# key: token 的 SHA-256 指纹 -> value: exp 时间戳（unix）
# 说明：内存实现，重启后失效；多 worker 生产部署建议后续替换为 Redis（第四批可观测性配套）。
_revoked_tokens: dict[str, float] = {}


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_token(token: str) -> None:
    """登出撤销：将 token 指纹加入撤销表直至其自然过期，同时惰性清理过期条目。"""
    payload = decode_access_token(token)
    if not payload:
        # 无效/已过期的 token 无需撤销
        return
    exp = payload.get("exp")
    if not exp:
        return
    _revoked_tokens[_token_fingerprint(token)] = float(exp)
    now = time.time()
    for fp in [k for k, v in _revoked_tokens.items() if v <= now]:
        _revoked_tokens.pop(fp, None)


def is_token_revoked(token: str) -> bool:
    fp = _token_fingerprint(token)
    exp = _revoked_tokens.get(fp)
    if exp is None:
        return False
    return exp > time.time()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "jti": secrets.token_hex(16),
        "exp": expire,
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None
