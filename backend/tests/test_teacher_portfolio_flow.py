"""教师成长档案（e-Portfolio）：增删改查 + 四段式字段 + 成长报告聚合 + 越权保护。"""
from app.models.teacher_portfolio import TeacherPortfolioItem
from app.models.user import UserRole


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_portfolio_crud_and_report(client, api, make_user):
    teacher = make_user(role=UserRole.TEACHER)
    headers = _login(client, teacher)

    created = api.post(
        "/api/teacher-portfolio",
        json={
            "item_type": "case",
            "title": "学业困难学生帮扶案例",
            "evidence": [{"name": "帮扶记录.pdf", "url": "/uploads/case.pdf"}],
            "reflection": "先共情再给方案，比单纯说教有效",
            "occurred_on": "2026-03-10",
            "visibility": "private",
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["item_type"] == "case"
    assert body["evidence"][0]["url"] == "/uploads/case.pdf"
    item_id = body["id"]

    api.post(
        "/api/teacher-portfolio",
        json={"item_type": "honor", "title": "校级优秀辅导员", "visibility": "public"},
        headers=headers,
    )

    # 列表 + 类型筛选
    all_items = api.get("/api/teacher-portfolio", headers=headers)
    assert all_items.status_code == 200
    assert len(all_items.json()) == 2
    only_honor = api.get(
        "/api/teacher-portfolio", params={"item_type": "honor"}, headers=headers
    )
    assert [i["item_type"] for i in only_honor.json()] == ["honor"]

    # 报告聚合：四类齐全，合计与条目数一致
    report = api.get("/api/teacher-portfolio/report", headers=headers)
    assert report.status_code == 200, report.text
    data = report.json()
    assert data["total"] == 2
    assert {t["type"] for t in data["by_type"]} == {"case", "honor", "training", "research"}
    assert sum(t["count"] for t in data["by_type"]) == 2
    assert data["teacher_name"] == teacher.name

    # 更新（四段式：证据 / 反思可改）
    updated = api.patch(
        f"/api/teacher-portfolio/{item_id}",
        json={"reflection": "复盘：需要更早介入", "visibility": "public"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["reflection"] == "复盘：需要更早介入"
    assert updated.json()["visibility"] == "public"

    # 软删除：默认列表不再出现，但数据保留可追溯
    deleted = api.delete(f"/api/teacher-portfolio/{item_id}", headers=headers)
    assert deleted.status_code == 200
    assert len(api.get("/api/teacher-portfolio", headers=headers).json()) == 1


def test_portfolio_rejects_foreign_item(client, api, make_user, db):
    owner = make_user(role=UserRole.TEACHER)
    other = make_user(role=UserRole.TEACHER)
    owner_headers = _login(client, owner)
    other_headers = _login(client, other)

    item_id = api.post(
        "/api/teacher-portfolio",
        json={"item_type": "training", "title": "省级培训研修"},
        headers=owner_headers,
    ).json()["id"]

    patched = api.patch(
        f"/api/teacher-portfolio/{item_id}", json={"title": "篡改"}, headers=other_headers
    )
    assert patched.status_code == 403

    removed = api.delete(f"/api/teacher-portfolio/{item_id}", headers=other_headers)
    assert removed.status_code == 403
    assert db.get(TeacherPortfolioItem, item_id).is_deleted is False