"""失物招领认领核验闭环测试（p4_3）。

覆盖：进入 CLAIMED 必填认领人姓名/联系方式；claimed_by/claimed_at 服务端落库；
离开认领态清空认领快照；CLOSED 终态不可再流转；权限与非法状态校验。
"""
from app.models.lost_found import LostFoundItem, ItemStatus
from app.models.user import UserRole


def _create_item(api, headers, **overrides):
    resp = api.post(
        "/api/lost-found/items",
        json={"type": "found", "title": "蓝色保温杯", "description": "图书馆三楼拾到", **overrides},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_claim_requires_claimant_info(client, api, login_token):
    """进入 CLAIMED 必填认领人姓名与联系方式。"""
    user = login_token(role=UserRole.STUDENT)
    item = _create_item(api, user["headers"])

    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "claimed"},
        headers=user["headers"],
    )
    assert resp.status_code == 400
    assert "姓名" in resp.json()["detail"]

    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "claimed", "claimant_name": "张三"},
        headers=user["headers"],
    )
    assert resp.status_code == 400
    assert "联系方式" in resp.json()["detail"]


def test_claim_success_write_snapshot(client, api, login_token, db):
    """认领成功：认领信息 + 服务端落库 claimed_by/claimed_at。"""
    user = login_token(role=UserRole.STUDENT)
    item = _create_item(api, user["headers"])

    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "claimed", "claimant_name": "张三", "claimant_contact": "13800138000", "claim_note": "杯底有刻字"},
        headers=user["headers"],
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "claimed"
    assert data["claimant_name"] == "张三"
    assert data["claimant_contact"] == "13800138000"
    assert data["claim_note"] == "杯底有刻字"
    assert data["claimed_by"] == user["user"].id
    assert data["claimed_at"] is not None

    row = db.get(LostFoundItem, item["id"])
    assert row.status == ItemStatus.CLAIMED
    assert row.claimed_by == user["user"].id


def test_reopen_clears_claim_snapshot(client, api, login_token, db):
    """CLAIMED 退回 OPEN：认领快照清空，保持数据一致。"""
    user = login_token(role=UserRole.STUDENT)
    item = _create_item(api, user["headers"])
    api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "claimed", "claimant_name": "李四", "claimant_contact": "13900139000"},
        headers=user["headers"],
    )
    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "open"},
        headers=user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "open"
    assert data["claimant_name"] is None
    assert data["claimant_contact"] is None
    assert data["claimed_at"] is None


def test_closed_is_terminal(client, api, login_token):
    """CLOSED 终态：关闭后不可再流转。"""
    user = login_token(role=UserRole.STUDENT)
    item = _create_item(api, user["headers"])
    api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "claimed", "claimant_name": "王五", "claimant_contact": "13700137000"},
        headers=user["headers"],
    )
    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "closed"},
        headers=user["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "open"},
        headers=user["headers"],
    )
    assert resp.status_code == 400
    assert "关闭" in resp.json()["detail"]


def test_invalid_status_and_ownership(client, api, login_token):
    """非法状态 400；他人物品不可改状态。"""
    owner = login_token(role=UserRole.STUDENT)
    item = _create_item(api, owner["headers"])

    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "unknown"},
        headers=owner["headers"],
    )
    assert resp.status_code == 400

    stranger = login_token(role=UserRole.STUDENT)
    resp = api.put(
        f"/api/lost-found/items/{item['id']}/status",
        json={"status": "closed"},
        headers=stranger["headers"],
    )
    assert resp.status_code == 403