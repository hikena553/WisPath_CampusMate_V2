"""敏感配置加解密工具。

使用 Fernet（对称加密）加密存储敏感设置（如 LLM API Key），
密钥由 settings.SECRET_KEY 派生，加密值带 `enc:v1:` 前缀以便识别。
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

# 敏感设置 key 集合：这些值在数据库中加密存储，接口返回时脱敏
_SENSITIVE_KEYS = {
    "llm_api_key",
}

# 加密值前缀
_PREFIX = "enc:v1:"

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """基于 SECRET_KEY 派生稳定的 Fernet 密钥。"""
    global _fernet
    if _fernet is None:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        _fernet = Fernet(key)
    return _fernet


def is_sensitive_key(key: str) -> bool:
    """判断设置 key 是否为敏感字段。"""
    return key in _SENSITIVE_KEYS


def is_encrypted(value: str) -> bool:
    """判断值是否为加密存储格式。"""
    return bool(value) and value.startswith(_PREFIX)


def is_masked_value(value: str) -> bool:
    """判断值是否为接口脱敏后的掩码（形如 `xxxx****yyyy`）。

    掩码含 `****`，前端未修改直接回传时用于跳过加密。
    """
    return bool(value) and "****" in value


def encrypt_value(value: str) -> str:
    """加密明文，返回带前缀的密文。"""
    if is_encrypted(value):
        return value
    token = _get_fernet().encrypt(value.encode())
    return _PREFIX + token.decode()


def decrypt_value(value: str) -> str:
    """解密取值。

    未加密（如来自 .env 的明文）原样返回；加密值解密失败时
    为避免服务崩溃，记录警告并原样返回。
    """
    if not is_encrypted(value):
        return value
    try:
        token = value[len(_PREFIX):].encode()
        return _get_fernet().decrypt(token).decode()
    except (InvalidToken, ValueError):
        import logging
        logging.getLogger(__name__).warning("敏感值解密失败，请检查 SECRET_KEY 是否变更")
        return value