"""公开展示类设置接口（/api/settings/public）用例。

背景：管理端在「系统设置」中修改站点名称 / Logo / 吉祥物 / 系统公告 / 助手称谓后，
教师端、学生端与登录页需要同步生效；原 `/api/settings` 仅管理员可读，非管理员端
拿不到这些展示信息。本用例校验：免登录可读、只返回白名单键、不泄露敏感配置，
且管理员写入后各端口读取到最新值。
"""
from app.models.user import UserRole

PUBLIC_KEYS = {"site_name", "site_logo", "site_mascot", "site_announcement", "agent_name"}


def test_public_settings_readable_without_auth(client):
    """未携带任何凭据也能读取（登录页/分享页同源需要）。"""
    resp = client.get("/api/settings/public")
    assert resp.status_code == 200
    assert set(resp.json().keys()) == PUBLIC_KEYS


def test_public_settings_never_exposes_sensitive_keys(client, api, login_token):
    """白名单外（含 API Key 等敏感配置）绝不随公开接口下发。"""
    admin = login_token(UserRole.ADMIN)
    api.put(
        "/api/settings/llm_api_key",
        json={"value": "sk-should-never-leak-0123456789"},
        headers=admin["headers"],
    )
    resp = client.get("/api/settings/public")
    assert resp.status_code == 200
    assert "llm_api_key" not in resp.json()
    assert "sk-should-never-leak" not in resp.text


def test_public_settings_syncs_admin_changes(client, api, login_token):
    """管理员更新品牌/公告后，公开接口（各端数据源）即刻返回最新值。"""
    admin = login_token(UserRole.ADMIN)
    api.put("/api/settings/site_name", json={"value": "绵小城测试版"}, headers=admin["headers"])
    api.put("/api/settings/site_announcement", json={"value": "系统维护通知"}, headers=admin["headers"])

    resp = client.get("/api/settings/public")
    body = resp.json()
    assert body["site_name"] == "绵小城测试版"
    assert body["site_announcement"] == "系统维护通知"