"""今日报告：重新生成（绕过缓存）与浏览器下载导出。

两条底线：
1. 「重新生成」必须真的重跑 —— 服务端 10 分钟缓存按事实指纹命中，不带 refresh 会原样返回旧文案，
   用户看到的就是「点了没反应」；
2. 导出必须给浏览器一个真实下载链接（带 Content-Disposition 的附件），
   前端不再拼 Blob —— 手机端 Blob 下载没有进度、也没有「文件在哪」的提示。
"""
import pytest

from app.models.user import UserRole
from app.services import daily_report


@pytest.fixture()
def offline_report(monkeypatch):
    """切断天气与 LLM 外部调用：只验证接口契约，不让用例等网络。"""

    async def _no_weather():
        return None

    async def _no_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(daily_report, "get_weather", _no_weather)
    monkeypatch.setattr(daily_report, "_llm_sections", _no_llm)


def test_daily_report_refresh_passthrough(api, login_token, monkeypatch):
    """refresh=1 必须把 force_refresh 透传给服务层（否则缓存命中，重新生成等于没点）。"""
    calls: list[bool] = []

    async def fake_build(db, user, force_refresh=False):
        calls.append(force_refresh)
        return {"date": "2026-11-06", "greeting": "hi", "weather": None,
                "mood": {"from": "none"}, "fortune": {"level": "中签", "score": 60},
                "sections": [], "suggestions": [], "generated_at": "2026-11-06T12:00:00Z"}

    monkeypatch.setattr("app.api.agent.build_daily_report", fake_build)
    me = login_token(role=UserRole.STUDENT)

    resp = api.get("/api/agent/daily-report", headers=me["headers"])
    assert resp.status_code == 200, resp.text
    resp = api.get("/api/agent/daily-report?refresh=1", headers=me["headers"])
    assert resp.status_code == 200, resp.text
    assert calls == [False, True]


def test_export_ticket_downloads_markdown(api, client, login_token, offline_report):
    """票据换真实下载链接：不登录也能下（票据即凭证），响应是附件且内容是报告正文。"""
    me = login_token(role=UserRole.STUDENT)

    resp = api.post("/api/agent/daily-report/export-ticket", headers=me["headers"])
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["url"].startswith("/api/agent/daily-report/export?ticket=")

    # 模拟浏览器新开标签页：不带任何登录态，只带票据
    resp = client.get(payload["url"])
    assert resp.status_code == 200, resp.text
    assert "attachment" in resp.headers["content-disposition"]
    assert "filename*=UTF-8''" in resp.headers["content-disposition"]
    assert "# AI 今日报告" in resp.text


def test_export_ticket_rejects_bad_ticket(client):
    resp = client.get("/api/agent/daily-report/export?ticket=not-a-real-ticket")
    assert resp.status_code == 401
