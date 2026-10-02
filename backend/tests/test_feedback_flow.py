"""反馈状态流转闭环测试（p4_3）。

覆盖：PENDING/PROCESSING → RESOLVED/REJECTED；终态（RESOLVED/REJECTED）不可回复、不可再改；
非法目标状态回退 RESOLVED；非管理员回复 403。
"""
from app.models.feedback import Feedback, FeedbackStatus
from app.models.user import UserRole


def _create_feedback(api, student_headers, **overrides):
    resp = api.post(
        "/api/feedbacks",
        json={"type": "bug", "title": "登录页白屏", "content": "刷新后无法显示", **overrides},
        headers=student_headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_reply_resolved_then_terminal_guard(client, api, login_token, db):
    """管理员回复后进入终态；终态不可再回复。"""
    student = login_token(role=UserRole.STUDENT)
    fb = _create_feedback(api, student["headers"])
    assert fb["status"] == "pending"

    admin = login_token(role=UserRole.ADMIN)
    resp = api.put(
        f"/api/feedbacks/{fb['id']}/reply",
        json={"reply": "已修复，刷新即可", "status": "resolved"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "resolved"
    assert resp.json()["reply"] == "已修复，刷新即可"

    # RESOLVED 终态：不可再回复、不可再改
    resp = api.put(
        f"/api/feedbacks/{fb['id']}/reply",
        json={"reply": "再改一次", "status": "rejected"},
        headers=admin["headers"],
    )
    assert resp.status_code == 400
    assert "办结" in resp.json()["detail"]
    assert db.get(Feedback, fb["id"]).status == FeedbackStatus.RESOLVED


def test_rejected_is_terminal_and_processing_intermediate(client, api, login_token, db):
    """REJECTED 终态不可再回复；PROCESSING 中间态可回复收敛。"""
    student = login_token(role=UserRole.STUDENT)
    admin = login_token(role=UserRole.ADMIN)

    # 直接驳回
    fb = _create_feedback(api, student["headers"], title="需求建议单")
    resp = api.put(
        f"/api/feedbacks/{fb['id']}/reply",
        json={"reply": "暂不采纳", "status": "rejected"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    assert db.get(Feedback, fb["id"]).status == FeedbackStatus.REJECTED

    resp = api.put(
        f"/api/feedbacks/{fb['id']}/reply",
        json={"reply": "补充说明"},
        headers=admin["headers"],
    )
    assert resp.status_code == 400

    # PROCESSING 中间态可回复（管理员处理后收敛为终态）
    fb2 = _create_feedback(api, student["headers"], title="中间态回访单")
    row = db.get(Feedback, fb2["id"])
    row.status = FeedbackStatus.PROCESSING
    db.commit()
    resp = api.put(
        f"/api/feedbacks/{fb2['id']}/reply",
        json={"reply": "处理中，已转交", "status": "resolved"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    assert db.get(Feedback, fb2["id"]).status == FeedbackStatus.RESOLVED


def test_invalid_target_status_falls_back_to_resolved(client, api, login_token, db):
    """目标状态仅允许 resolved/rejected，其余值回退 RESOLVED。"""
    student = login_token(role=UserRole.STUDENT)
    fb = _create_feedback(api, student["headers"])
    admin = login_token(role=UserRole.ADMIN)
    resp = api.put(
        f"/api/feedbacks/{fb['id']}/reply",
        json={"reply": "已处理", "status": "processing"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    row = db.get(Feedback, fb["id"])
    assert row.status == FeedbackStatus.RESOLVED


def test_reply_requires_admin(client, api, login_token):
    """非管理员回复被拒。"""
    student = login_token(role=UserRole.STUDENT)
    fb = _create_feedback(api, student["headers"])
    other = login_token(role=UserRole.STUDENT)
    resp = api.put(
        f"/api/feedbacks/{fb['id']}/reply",
        json={"reply": "冒充管理员", "status": "resolved"},
        headers=other["headers"],
    )
    assert resp.status_code == 403