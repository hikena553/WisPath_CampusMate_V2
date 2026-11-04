"""QQ 互联 OAuth 服务：授权跳转、code 换 token、openid 获取。

前置条件（QQ 互联后台 https://connect.qq.com 创建网站应用）：
- 拿到 AppID / AppKey，写入 QQ_APP_ID / QQ_APP_KEY；
- 回调地址登记为「{$后端域名}/api/auth/qq/callback」，并原样写入 QQ_REDIRECT_URI；
- 站点完成备案与域名校验后，QQ 才允许真实用户授权。

登录链路：
1. 前端取 /api/auth/qq/authorize 返回的 URL 并跳转 QQ；
2. QQ 带 code 回跳 /api/auth/qq/callback；
3. 后端用 code 换 access_token → 取 openid → 按 openid 找到已授权绑定的校园账号；
4. 回跳前端 /qq-callback?ticket=...，前端用 ticket 换正式 access_token。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

QQ_AUTHORIZE_URL = "https://graph.qq.com/oauth2.0/authorize"
QQ_TOKEN_URL = "https://graph.qq.com/oauth2.0/token"
QQ_ME_URL = "https://graph.qq.com/oauth2.0/me"
QQ_USER_INFO_URL = "https://graph.qq.com/user/get_user_info"

_STATE_TTL_SECONDS = 600
_TICKET_TTL_SECONDS = 300


def is_configured() -> bool:
    return bool(
        (settings.QQ_APP_ID or "").strip()
        and (settings.QQ_APP_KEY or "").strip()
    )


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode(token: str | None, purpose: str) -> dict | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.JWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload


def build_state(mode: str, user_id: int | None = None) -> str:
    payload = {
        "purpose": "qq_oauth_state",
        "mode": mode,
        "uid": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=_STATE_TTL_SECONDS),
    }
    return _encode(payload)


def decode_state(state: str | None) -> dict | None:
    return _decode(state, "qq_oauth_state")


def build_authorize_url(mode: str, redirect_uri: str, user_id: int | None = None) -> str:
    state = build_state(mode, user_id)
    params = {
        "response_type": "code",
        "client_id": settings.QQ_APP_ID,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "get_user_info",
    }
    return f"{QQ_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> tuple[str, str]:
    """用授权 code 换取 access_token 与 openid。"""
    resp = httpx.get(
        QQ_TOKEN_URL,
        params={
            "grant_type": "authorization_code",
            "client_id": settings.QQ_APP_ID,
            "client_secret": settings.QQ_APP_KEY,
            "code": code,
            "redirect_uri": redirect_uri,
            "fmt": "json",
        },
        timeout=10,
    )
    text = resp.text.strip()
    try:
        token_data = resp.json()
    except ValueError:
        # 兼容 QQ 返回 query string 的情况：access_token=xxx&expires_in=...
        token_data = dict(
            item.split("=", 1) for item in text.split("&") if "=" in item
        )
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError(token_data.get("error_description") or "QQ 授权失败：未获取到 access_token")

    me_resp = httpx.get(QQ_ME_URL, params={"access_token": access_token, "fmt": "json"}, timeout=10)
    me_text = me_resp.text.strip()
    try:
        me_data = me_resp.json()
    except ValueError:
        # 兼容 callback( {"client_id":"...","openid":"..."} ); 形式
        start, end = me_text.find("{"), me_text.rfind("}")
        if start < 0 or end < 0:
            raise RuntimeError("QQ 授权失败：openid 解析失败")
        import json as _json

        me_data = _json.loads(me_text[start : end + 1])
    openid = me_data.get("openid")
    if not openid:
        raise RuntimeError("QQ 授权失败：未获取到 openid")
    return access_token, openid


def fetch_nickname(access_token: str, openid: str) -> str | None:
    """取 QQ 昵称用于个人中心展示；失败不影响绑定结果。"""
    try:
        resp = httpx.get(
            QQ_USER_INFO_URL,
            params={
                "access_token": access_token,
                "oauth_consumer_key": settings.QQ_APP_ID,
                "openid": openid,
                "fmt": "json",
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("ret") == 0:
            return (data.get("nickname") or "").strip() or None
        logger.warning("[QQ] 昵称获取失败: %s", data)
    except Exception as exc:  # pragma: no cover - 外部服务
        logger.warning("[QQ] 昵称获取异常: %s", exc)
    return None


def create_login_ticket(user_id: int, password_hash: str) -> str:
    """一次性回跳票据：前端用它在换取正式 token，避免把 token 暴露在 URL。"""
    payload = {
        "purpose": "qq_login_ticket",
        "sub": str(user_id),
        "ph": password_hash[:8],
        "exp": datetime.now(timezone.utc) + timedelta(seconds=_TICKET_TTL_SECONDS),
    }
    return _encode(payload)


def decode_login_ticket(ticket: str | None) -> dict | None:
    return _decode(ticket, "qq_login_ticket")


def create_register_ticket(openid: str, nickname: str | None) -> str:
    """注册场景：QQ 授权完成后下发短期票据，前端凭它提交学籍信息完成注册。"""
    payload = {
        "purpose": "qq_register_ticket",
        "openid": openid,
        "nickname": nickname,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=900),
    }
    return _encode(payload)


def decode_register_ticket(ticket: str | None) -> dict | None:
    return _decode(ticket, "qq_register_ticket")
