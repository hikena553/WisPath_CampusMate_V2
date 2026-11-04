"""短信验证码服务：阿里云 / 腾讯云双通道 + 验证码存储。

设计要点：
- 验证码存内存（与图形验证码一致，单进程部署够用），按「用途 + 手机号」隔离；
- 同一手机号有发送冷却，验证码有有效期与最大尝试次数，防止脚本刷短信；
- 未配置服务商时：开发环境返回 debug_code 便于本地联调完整链路，生产环境直接拒绝。

接入方式（二选一，写到 backend/.env）：
阿里云：SMS_PROVIDER=aliyun + ALIYUN_SMS_ACCESS_KEY_ID/SECRET/SIGN_NAME/TEMPLATE_CODE
腾讯云：SMS_PROVIDER=tencent + TENCENT_SMS_SECRET_ID/SECRET_KEY/APP_ID/SIGN_NAME/TEMPLATE_ID
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import quote

import httpx

from app.core.config import settings

SmsPurpose = Literal["login", "bind", "register"]

_MAX_ATTEMPTS = 5
_store: dict[str, dict] = {}
_lock = threading.Lock()


class SmsCooldown(Exception):
    """发送过于频繁。"""

    def __init__(self, remaining: int):
        self.remaining = remaining
        super().__init__(f"请 {remaining} 秒后再获取验证码")


class SmsNotConfigured(Exception):
    """未接入短信服务商（生产环境）。"""


class SmsSendFailed(Exception):
    """服务商调用失败。"""


class SmsCodeError(Exception):
    """验证码校验失败。"""


@dataclass
class IssuedCode:
    provider: str
    configured: bool
    debug_code: str | None
    expires_in: int
    cooldown: int


def provider_name() -> str:
    return (settings.SMS_PROVIDER or "").strip().lower()


def is_configured() -> bool:
    name = provider_name()
    if name == "aliyun":
        return all(
            [
                settings.ALIYUN_SMS_ACCESS_KEY_ID,
                settings.ALIYUN_SMS_ACCESS_KEY_SECRET,
                settings.ALIYUN_SMS_SIGN_NAME,
                settings.ALIYUN_SMS_TEMPLATE_CODE,
            ]
        )
    if name == "tencent":
        return all(
            [
                settings.TENCENT_SMS_SECRET_ID,
                settings.TENCENT_SMS_SECRET_KEY,
                settings.TENCENT_SMS_APP_ID,
                settings.TENCENT_SMS_SIGN_NAME,
                settings.TENCENT_SMS_TEMPLATE_ID,
            ]
        )
    return False


def _key(phone: str, purpose: SmsPurpose) -> str:
    return f"{purpose}:{phone}"


def _cleanup_locked() -> None:
    now = time.time()
    expired = [k for k, v in _store.items() if v["expire"] < now]
    for k in expired:
        _store.pop(k, None)


def issue_code(phone: str, purpose: SmsPurpose = "login") -> IssuedCode:
    """生成并发送验证码；返回可回显给前端的元信息。"""
    cooldown = max(30, int(settings.SMS_CODE_COOLDOWN_SECONDS))
    ttl = max(60, int(settings.SMS_CODE_TTL_SECONDS))
    k = _key(phone, purpose)
    now = time.time()

    with _lock:
        _cleanup_locked()
        last = _store.get(k)
        if last and now - last["sent_at"] < cooldown:
            remaining = int(cooldown - (now - last["sent_at"]))
            raise SmsCooldown(max(1, remaining))
        code = f"{secrets.randbelow(1_000_000):06d}"
        _store[k] = {
            "code": code,
            "expire": now + ttl,
            "sent_at": now,
            "attempts": 0,
        }

    configured = is_configured()
    if not configured:
        # 开发环境允许回显验证码，便于在无短信服务商时联调完整链路
        if (settings.ENV or "").strip().lower() != "production":
            return IssuedCode(
                provider="debug",
                configured=False,
                debug_code=code,
                expires_in=ttl,
                cooldown=cooldown,
            )
        with _lock:
            _store.pop(k, None)
        raise SmsNotConfigured("短信服务未配置，暂时无法使用手机号验证码登录")

    try:
        if provider_name() == "aliyun":
            _send_aliyun(phone, code)
        else:
            _send_tencent(phone, code)
    except Exception as exc:  # pragma: no cover - 依赖外部服务商
        with _lock:
            _store.pop(k, None)
        raise SmsSendFailed(f"短信发送失败：{exc}") from exc

    return IssuedCode(
        provider=provider_name(),
        configured=True,
        debug_code=None,
        expires_in=ttl,
        cooldown=cooldown,
    )


def verify_code(phone: str, purpose: SmsPurpose, code: str) -> None:
    """校验验证码；成功即一次性消费，失败累计尝试次数。"""
    k = _key(phone, purpose)
    entered = (code or "").strip()
    with _lock:
        item = _store.get(k)
        if not item:
            raise SmsCodeError("验证码已过期，请重新获取")
        if item["expire"] < time.time():
            _store.pop(k, None)
            raise SmsCodeError("验证码已过期，请重新获取")
        if not secrets.compare_digest(item["code"], entered):
            item["attempts"] += 1
            if item["attempts"] >= _MAX_ATTEMPTS:
                _store.pop(k, None)
                raise SmsCodeError("验证码错误次数过多，请重新获取")
            raise SmsCodeError("验证码不正确")
        _store.pop(k, None)


# ==================== 阿里云短信 ====================

def _percent(value: str) -> str:
    return quote(str(value), safe="~")


def _aliyun_send(phone: str, code: str) -> None:
    params = {
        "AccessKeyId": settings.ALIYUN_SMS_ACCESS_KEY_ID,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone,
        "RegionId": "cn-hangzhou",
        "SignName": settings.ALIYUN_SMS_SIGN_NAME,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": secrets.token_hex(16),
        "SignatureVersion": "1.0",
        "TemplateCode": settings.ALIYUN_SMS_TEMPLATE_CODE,
        "TemplateParam": json.dumps({"code": code}, ensure_ascii=False, separators=(",", ":")),
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    canonical = "&".join(f"{_percent(k)}={_percent(params[k])}" for k in sorted(params))
    string_to_sign = f"GET&%2F&{_percent(canonical)}"
    digest = hmac.new(
        f"{settings.ALIYUN_SMS_ACCESS_KEY_SECRET}&".encode(),
        string_to_sign.encode(),
        hashlib.sha1,
    ).digest()
    params["Signature"] = base64.b64encode(digest).decode()

    resp = httpx.get("https://dysmsapi.aliyuncs.com/", params=params, timeout=10)
    data = resp.json()
    if data.get("Code") != "OK":
        raise RuntimeError(data.get("Message") or data.get("Code") or "阿里云返回异常")


# ==================== 腾讯云短信 ====================

def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _tencent_send(phone: str, code: str) -> None:
    host = "sms.tencentcloudapi.com"
    payload = json.dumps(
        {
            "PhoneNumberSet": [f"+86{phone}"],
            "SmsSdkAppId": settings.TENCENT_SMS_APP_ID,
            "SignName": settings.TENCENT_SMS_SIGN_NAME,
            "TemplateId": settings.TENCENT_SMS_TEMPLATE_ID,
            "TemplateParamSet": [code],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    timestamp = int(time.time())
    date = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    content_type = "application/json; charset=utf-8"
    canonical_headers = f"content-type:{content_type}\nhost:{host}\n"
    signed_headers = "content-type;host"
    hashed_payload = hashlib.sha256(payload.encode()).hexdigest()
    canonical_request = (
        f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
    )
    credential_scope = f"{date}/sms/tc3_request"
    string_to_sign = (
        f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )
    secret_date = _hmac_sha256(f"TC3{settings.TENCENT_SMS_SECRET_KEY}".encode(), date)
    secret_service = _hmac_sha256(secret_date, "sms")
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    headers = {
        "Authorization": (
            f"TC3-HMAC-SHA256 Credential={settings.TENCENT_SMS_SECRET_ID}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
        "Content-Type": content_type,
        "Host": host,
        "X-TC-Action": "SendSms",
        "X-TC-Version": "2021-01-11",
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Region": settings.TENCENT_SMS_REGION,
    }
    resp = httpx.post(f"https://{host}/", content=payload, headers=headers, timeout=10)
    data = resp.json().get("Response", {})
    if data.get("Error"):
        raise RuntimeError(data["Error"].get("Message") or data["Error"].get("Code"))
    statuses = data.get("SendStatusSet") or []
    if not statuses or statuses[0].get("Code") != "Ok":
        raise RuntimeError((statuses[0].get("Message") if statuses else "") or "腾讯云返回异常")
