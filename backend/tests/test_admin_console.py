"""管理端闭环（外部数据源 / 外部资讯统一管理 / 系统监控与运维）。

覆盖用户反馈的三处缺口：
1. 知识库 = 项目需引进的外部数据源（网络数据位置 + 外部文件）的展示与入库接口；
2. 学生端订阅/爬取的外部数据源在管理端统一查看、新增、删除；
3. 项目基底监控与功能维护接口（服务/数据库/后台任务/模块注册表 + 维护动作）。
"""
import uuid

from app.models.feed import ExternalFeedItem, FeedSource
from app.models.user import UserRole


def _hex() -> str:
    return uuid.uuid4().hex[:8]


# ==================== 1. 知识库外部数据源 ====================

def test_knowledge_url_source_create_list_refetch_delete(api, login_token, monkeypatch, db):
    """新增网络数据源 → 落库 → 列表展示来源位置 → 重新抓取 → 删除。"""
    admin = login_token(UserRole.ADMIN)
    from app.services import knowledge_service as ks

    calls = {"n": 0}

    def fake_fetch(url: str) -> str:
        calls["n"] += 1
        return f"外部数据源正文第 {calls['n']} 版 " + ("校园制度说明。" * 100)

    monkeypatch.setattr(ks, "fetch_url_text", fake_fetch)

    url = f"https://example.edu.cn/policy/{_hex()}"
    resp = api.post(
        "/api/admin/knowledge/sources/url",
        json={"url": url, "title": "校园制度外部数据"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["chunk_count"] >= 1
    doc_id = body["document_id"]

    # 列表展示：来源类型 url + 来源位置 source_url
    listing = api.get("/api/admin/knowledge/documents", headers=admin["headers"])
    assert listing.status_code == 200, listing.text
    doc = next(d for d in listing.json() if d["id"] == doc_id)
    assert doc["source_type"] == "url"
    assert doc["source_url"] == url

    # 统计：网络来源计数 >= 1
    stats = api.get("/api/admin/knowledge/source-stats", headers=admin["headers"])
    assert stats.status_code == 200
    assert stats.json()["url_count"] >= 1

    # 重新抓取：正文更新为第 2 版
    refetch = api.post(
        f"/api/admin/knowledge/documents/{doc_id}/refetch", headers=admin["headers"]
    )
    assert refetch.status_code == 200, refetch.text
    assert calls["n"] == 2

    # 删除数据源
    deleted = api.delete(
        f"/api/admin/knowledge/documents/{doc_id}", headers=admin["headers"]
    )
    assert deleted.status_code == 200


def test_knowledge_url_source_invalid_scheme_400(api, login_token):
    admin = login_token(UserRole.ADMIN)
    resp = api.post(
        "/api/admin/knowledge/sources/url",
        json={"url": "ftp://example.com/a"},
        headers=admin["headers"],
    )
    assert resp.status_code == 400
    assert "http" in resp.json()["detail"]


def test_knowledge_url_source_student_forbidden(api, login_token):
    student = login_token(UserRole.STUDENT)
    resp = api.post(
        "/api/admin/knowledge/sources/url",
        json={"url": "https://example.com/a"},
        headers=student["headers"],
    )
    assert resp.status_code == 403


# ==================== 2. 外部资讯统一管理 ====================

def test_admin_feed_source_crud(api, login_token, db):
    """管理员对资讯源：新增 → 列表可见 → 停用 → 删除。"""
    admin = login_token(UserRole.ADMIN)

    created = api.post(
        "/api/admin/feeds/sources",
        json={
            "name": f"测试源{_hex()}",
            "kind": "rss",
            "source_type": "ai_news",
            "url": f"https://feed.example.com/{_hex()}.xml",
            "per_page": 5,
        },
        headers=admin["headers"],
    )
    assert created.status_code == 200, created.text
    src = created.json()
    src_id = src["id"]
    assert src["is_builtin"] is False
    assert src["enabled"] is True

    listed = api.get("/api/admin/feeds/sources", headers=admin["headers"])
    assert listed.status_code == 200
    assert any(s["id"] == src_id for s in listed.json())

    patched = api.patch(
        f"/api/admin/feeds/sources/{src_id}",
        json={"enabled": False, "name": "改名后的源"},
        headers=admin["headers"],
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["enabled"] is False
    assert patched.json()["name"] == "改名后的源"

    removed = api.delete(f"/api/admin/feeds/sources/{src_id}", headers=admin["headers"])
    assert removed.status_code == 200
    assert db.query(FeedSource).filter(FeedSource.id == src_id).first() is None


def test_admin_feed_builtin_source_not_deletable(api, login_token, db):
    """内置预设源受保护：不可删除（可停用）。"""
    admin = login_token(UserRole.ADMIN)
    builtin = FeedSource(
        name=f"内置源{_hex()}", kind="rss", source_type="ai_news",
        url=f"https://builtin.example.com/{_hex()}.xml", is_builtin=True, enabled=True,
    )
    db.add(builtin)
    db.commit()
    db.refresh(builtin)
    try:
        resp = api.delete(f"/api/admin/feeds/sources/{builtin.id}", headers=admin["headers"])
        assert resp.status_code == 403
        assert "不可删除" in resp.json()["detail"]
    finally:
        db.delete(db.get(FeedSource, builtin.id))
        db.commit()


def test_admin_feed_items_view_and_delete(api, login_token, db):
    """管理员分页查看外部资讯条目并删除。"""
    admin = login_token(UserRole.ADMIN)
    link = f"https://news.example.com/{_hex()}"
    item = ExternalFeedItem(
        source_type="news", feed_key=f"k{_hex()}", title="测试要闻标题",
        summary="摘要", link=link, source_name="测试源",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item_id = item.id
    try:
        resp = api.get(
            "/api/admin/feeds/items",
            params={"source_type": "news", "q": "测试要闻", "page": 1, "page_size": 10},
            headers=admin["headers"],
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1
        assert any(i["id"] == item_id for i in body["items"])

        deleted = api.delete(f"/api/admin/feeds/items/{item_id}", headers=admin["headers"])
        assert deleted.status_code == 200
        assert db.query(ExternalFeedItem).filter(ExternalFeedItem.id == item_id).first() is None
    finally:
        db.query(ExternalFeedItem).filter(ExternalFeedItem.id == item_id).delete()
        db.commit()


def test_admin_feeds_student_forbidden(api, login_token):
    student = login_token(UserRole.STUDENT)
    resp = api.get("/api/admin/feeds/sources", headers=student["headers"])
    assert resp.status_code == 403


# ==================== 3. 系统监控与运维 ====================

def test_system_overview_contains_project_base(api, login_token):
    admin = login_token(UserRole.ADMIN)
    resp = api.get("/api/admin/system/overview", headers=admin["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()

    for key in ("service", "database", "background_tasks", "feeds", "knowledge", "integrations", "modules"):
        assert key in body, f"缺少监控字段: {key}"

    assert body["service"]["status"] == "ok"
    assert body["service"]["version"]
    assert body["database"]["reachable"] is True
    assert "users" in body["database"]["table_counts"]
    assert isinstance(body["background_tasks"], list) and body["background_tasks"]
    # 功能模块注册表：全站路由域都在监控内
    prefixes = {m["prefix"] for m in body["modules"]}
    assert "/api/admin" in prefixes
    assert len(body["modules"]) >= 10


def test_system_maintenance_invalid_action_400(api, login_token):
    admin = login_token(UserRole.ADMIN)
    resp = api.post(
        "/api/admin/system/maintenance",
        json={"action": "drop_everything"},
        headers=admin["headers"],
    )
    assert resp.status_code == 400


def test_system_maintenance_reindex(api, login_token):
    """重建向量索引维护动作可执行（未配置向量模型时正常返回错误说明）。"""
    admin = login_token(UserRole.ADMIN)
    resp = api.post(
        "/api/admin/system/maintenance",
        json={"action": "reindex_knowledge"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["action"] == "reindex_knowledge"
    assert "result" in resp.json()


def test_system_overview_student_forbidden(api, login_token):
    student = login_token(UserRole.STUDENT)
    resp = api.get("/api/admin/system/overview", headers=student["headers"])
    assert resp.status_code == 403