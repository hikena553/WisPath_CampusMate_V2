"""AI 对话链路（p3_1）：SSE 流格式 / 权限 / 消息校验 / 推荐 / 主动触达。

LLM 调用均为模块级 import（app.api.agent.chat / generate_reply），
用 monkeypatch 替换为假流，避免真实网络调用。
"""
import json

import pytest

from app.api import agent as agent_api
from app.models.conversation import Conversation
from app.models.user import UserRole


def _fake_chat_stream(*args, **_kwargs):
    """模拟 chat() 产出的 dict 事件流。"""
    async def _gen():
        yield {"type": "reasoning", "content": "正在思考中"}
        yield {"type": "content", "content": "你好，同学！"}

    return _gen()


def _fake_reply_stream(*args, **_kwargs):
    async def _gen():
        yield "这是模拟回复"

    return _gen()


def test_chat_requires_valid_auth(client, api):
    """无效 token 访问 /chat 返回 401（Bearer 与 Cookie 双通道均走同一校验）。"""
    resp = api.post(
        "/api/agent/chat",
        json={"message": "你好"},
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401


def test_chat_message_too_long_400(api, login_token, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_MAX_INPUT_CHARS", 10)
    login = login_token()
    resp = api.post(
        "/api/agent/chat",
        json={"message": "这是一条超过十个字的消息内容测试"},
        headers=login["headers"],
    )
    assert resp.status_code == 400
    assert "消息过长" in resp.json()["detail"]


def test_chat_conv_id_not_owned_404(api, login_token, db, make_user):
    """conversation_id 非本人会话 → 404，不泄露他人对话。"""
    owner = make_user()
    conv = Conversation(user_id=owner.id, title="他人对话")
    db.add(conv)
    db.commit()
    db.refresh(conv)

    login = login_token()
    resp = api.post(
        "/api/agent/chat",
        json={"message": "你好", "conversation_id": conv.id},
        headers=login["headers"],
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "对话不存在"


def test_chat_sse_stream_format(api, login_token, monkeypatch):
    """SSE 契约：event: reasoning / event: content + JSON data。"""
    monkeypatch.setattr(agent_api, "chat", _fake_chat_stream)
    login = login_token()
    resp = api.post(
        "/api/agent/chat",
        json={"message": "你好", "skip_conversation": True},
        headers=login["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert "event: reasoning" in body
    assert "event: content" in body
    assert "正在思考中" in body
    assert "你好，同学！" in body


def test_chat_stream_data_is_valid_json(api, login_token, monkeypatch):
    """SSE data 段必须是合法 JSON。"""
    monkeypatch.setattr(agent_api, "chat", _fake_chat_stream)
    login = login_token()
    resp = api.post(
        "/api/agent/chat",
        json={"message": "你好", "skip_conversation": True},
        headers=login["headers"],
    )
    for block in resp.text.strip().split("\n\n"):
        lines = block.splitlines()
        data_line = next((l for l in lines if l.startswith("data: ")), None)
        if data_line:
            json.loads(data_line[len("data: "):])


def test_analyze_sse_stream(api, login_token, monkeypatch):
    monkeypatch.setattr(agent_api, "generate_reply", _fake_reply_stream)
    login = login_token()
    resp = api.post(
        "/api/agent/analyze",
        json={"prompt": "分析一下"},
        headers=login["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "模拟回复" in resp.text


def test_recommendations_without_history_returns_default(api, login_token):
    """无历史会话时直接返回默认推荐（不触发 LLM）。"""
    login = login_token(UserRole.STUDENT)
    resp = api.get("/api/agent/recommendations", headers=login["headers"])
    assert resp.status_code == 200, resp.text
    recs = resp.json()["recommendations"]
    assert isinstance(recs, list) and recs
    assert recs == agent_api.DEFAULT_RECOMMENDATIONS[UserRole.STUDENT]


def test_proactive_structure(api, login_token):
    """主动触达驾驶舱返回固定结构：actions/count/evaluated_at/trace_id。"""
    login = login_token(UserRole.STUDENT)
    resp = api.get("/api/agent/proactive", headers=login["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"actions", "count", "evaluated_at", "trace_id"}
    assert body["count"] == len(body["actions"])
    assert body["trace_id"].startswith("prc-")