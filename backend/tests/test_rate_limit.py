"""限流验证（p3_1）：翻转 TESTING=0 使滑动窗口限流生效，验证 429 兜底。

测试运行顺序与旁路规则：_rate_limit_enabled() 实时读 ENV + TESTING，
本文件用 monkeypatch.setenv("TESTING", "0") 在用例内翻转，用后还原。
"""
import os

import pytest

from app.api import agent as agent_api
from app.models.user import UserRole


def _enable_rate_limit(monkeypatch):
    monkeypatch.setenv("TESTING", "0")


def test_upload_rate_limit_429(api, login_token, monkeypatch):
    """上传限流 20 次/分：非法扩展名请求同样计数（限流在文件校验之前）。"""
    _enable_rate_limit(monkeypatch)
    login = login_token()
    files = {"file": ("a.txt", b"plain text not allowed")}

    for _ in range(20):
        resp = api.post("/api/upload", files=files, headers=login["headers"])
        assert resp.status_code in (400, 413, 415), resp.text

    blocked = api.post("/api/upload", files=files, headers=login["headers"])
    assert blocked.status_code == 429
    assert "上传过于频繁" in blocked.json()["detail"]


def test_chat_rate_limit_429(api, login_token, monkeypatch):
    """对话限流 30 次/分（SSE 接口同样受控）。"""
    _enable_rate_limit(monkeypatch)
    monkeypatch.setattr(agent_api, "chat", _fake_chat_stream)
    login = login_token()
    payload = {"message": "你好", "skip_conversation": True}

    for _ in range(30):
        resp = api.post("/api/agent/chat", json=payload, headers=login["headers"])
        assert resp.status_code == 200, resp.text

    blocked = api.post("/api/agent/chat", json=payload, headers=login["headers"])
    assert blocked.status_code == 429
    assert "请求过于频繁" in blocked.json()["detail"]


def test_analyze_rate_limit_429(api, login_token, monkeypatch):
    """智能分析限流 20 次/分。"""
    _enable_rate_limit(monkeypatch)
    monkeypatch.setattr(agent_api, "generate_reply", _fake_reply_stream)
    login = login_token()
    payload = {"prompt": "分析一下"}

    for _ in range(20):
        resp = api.post("/api/agent/analyze", json=payload, headers=login["headers"])
        assert resp.status_code == 200, resp.text

    blocked = api.post("/api/agent/analyze", json=payload, headers=login["headers"])
    assert blocked.status_code == 429


def test_rate_limit_bypassed_in_testing_mode(api, login_token, monkeypatch):
    """恢复 TESTING=1 后限流旁路（本地开发/CI 不误伤）。"""
    login = login_token()
    for _ in range(25):
        resp = api.post(
            "/api/agent/chat",
            json={"message": "你好", "skip_conversation": True},
            headers=login["headers"],
        )
        assert resp.status_code == 200, resp.text


def _fake_chat_stream(*args, **_kwargs):
    async def _gen():
        yield {"type": "content", "content": "测试回复"}

    return _gen()


def _fake_reply_stream(*args, **_kwargs):
    async def _gen():
        yield "测试分析结果"

    return _gen()