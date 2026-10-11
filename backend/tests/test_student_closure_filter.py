"""成长档案闭环：功能页按 student_id 聚焦过滤的后端支持。

背景：教师端学生详情（成长档案）各分区需要「带着学生上下文」跳到功能页，
功能页据此只展示该生的审批/关怀/建议记录。本测试覆盖新增的 student_id 查询参数：
- /api/leave/pending、/api/leave/all
- /api/service/tickets
- /api/approval/pending、/api/approval/stats
- /api/care-center/events
- /api/agent/proactive
并校验：无参数时为超集，带参数时严格收窄到目标学生。
"""
from datetime import date, timedelta

from app.models.user import UserRole


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_leave(api, headers, reason: str):
    today = date.today()
    resp = api.post(
        "/api/leave/create",
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "reason": reason,
            "leave_type": "sick",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_feature_pages_filter_by_student_id(client, api, make_user):
    teacher = make_user(role=UserRole.TEACHER)
    stu_a = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="闭环学生A")
    stu_b = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="闭环学生B")
    t_headers = _login(client, teacher)
    a_headers = _login(client, stu_a)
    b_headers = _login(client, stu_b)

    # 两位学生各造一条请假 + 一条工单
    _create_leave(api, a_headers, "A 的请假事由")
    _create_leave(api, b_headers, "B 的请假事由")
    for h, title in ((a_headers, "A 的工单"), (b_headers, "B 的工单")):
        resp = api.post(
            "/api/service/tickets",
            json={"type": "leave", "title": title, "content": "办事诉求"},
            headers=h,
        )
        assert resp.status_code == 200, resp.text

    # ── 请假：待审批 ──
    all_pending = api.get("/api/leave/pending", headers=t_headers).json()
    all_pending_ids = {r["student_id"] for r in all_pending}
    assert {stu_a.id, stu_b.id} <= all_pending_ids
    a_pending = api.get(
        "/api/leave/pending", headers=t_headers, params={"student_id": stu_a.id}
    ).json()
    assert a_pending and all(r["student_id"] == stu_a.id for r in a_pending)
    assert {r["student_id"] for r in a_pending} <= all_pending_ids

    # ── 请假：全部（含状态筛选） ──
    a_all = api.get(
        "/api/leave/all", headers=t_headers, params={"student_id": stu_a.id}
    ).json()
    assert a_all and all(r["student_id"] == stu_a.id for r in a_all)

    # ── 办事工单：审批视角（该视角为全量队列，此处校验聚焦严格收窄） ──
    a_tickets = api.get(
        "/api/service/tickets", headers=t_headers, params={"student_id": stu_a.id}
    ).json()
    assert a_tickets and all(t["applicant_id"] == stu_a.id for t in a_tickets)
    all_tickets = api.get("/api/service/tickets", headers=t_headers).json()
    assert {stu_a.id, stu_b.id} <= {t["applicant_id"] for t in all_tickets}

    # ── 统一审批门面：聚合列表 ──
    a_items = api.get(
        "/api/approval/pending", headers=t_headers, params={"student_id": stu_a.id}
    ).json()
    assert a_items and all(i["applicant_id"] == stu_a.id for i in a_items)
    all_items = api.get("/api/approval/pending", headers=t_headers).json()
    assert {stu_a.id, stu_b.id} <= {i["applicant_id"] for i in all_items}

    # ── 统一审批：统计随聚焦收窄 ──
    focused_stats = api.get(
        "/api/approval/stats", headers=t_headers, params={"student_id": stu_a.id}
    ).json()
    full_stats = api.get("/api/approval/stats", headers=t_headers).json()
    assert focused_stats["total"] < full_stats["total"]
    assert focused_stats["total"] == 2  # A 的 1 请假 + 1 工单


def test_care_events_filter_and_foreign_guard(client, api, make_user):
    teacher = make_user(role=UserRole.TEACHER)
    other = make_user(role=UserRole.TEACHER)
    stu_a = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="关怀A")
    stu_b = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="关怀B")
    stranger = make_user(role=UserRole.STUDENT, tutor_id=other.id, name="他班学生")
    headers = _login(client, teacher)
    today = date.today().isoformat()

    for stu in (stu_a, stu_b):
        resp = api.post(
            "/api/care-center/events",
            json={
                "event_type": "other",
                "event_date": today,
                "title": f"{stu.name} 关怀事项",
                "student_id": stu.id,
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

    a_events = api.get(
        "/api/care-center/events", headers=headers, params={"student_id": stu_a.id}
    ).json()
    assert a_events and all(e["student_id"] == stu_a.id for e in a_events)
    all_events = api.get("/api/care-center/events", headers=headers).json()
    assert {e["student_id"] for e in all_events} == {stu_a.id, stu_b.id}

    # 越权：不能按非名下学生聚焦（403）
    resp = api.get(
        "/api/care-center/events", headers=headers, params={"student_id": stranger.id}
    )
    assert resp.status_code == 403


def test_proactive_filter_by_student_id(client, api, make_user):
    teacher = make_user(role=UserRole.TEACHER)
    stu_a = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="主动发现A")
    stu_b = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="主动发现B")
    headers = _login(client, teacher)

    # 接口可用且返回结构稳定
    resp = api.get("/api/agent/proactive", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "actions" in resp.json()

    resp = api.get(
        "/api/agent/proactive", headers=headers, params={"student_id": stu_a.id}
    )
    assert resp.status_code == 200, resp.text
    actions = resp.json()["actions"]
    # 聚焦后不出现其它学生的动作
    assert all(a.get("student_id") == stu_a.id for a in actions)