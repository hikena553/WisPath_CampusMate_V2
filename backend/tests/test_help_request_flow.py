"""学生求助闭环：学生提交（含匿名）→ 辅导员受理回复 → 越权保护。"""
from app.models.help_request import HelpRequest, HelpRequestStatus
from app.models.user import UserRole


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_help_request_flow(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="求助学生")
    t_headers = _login(client, teacher)
    s_headers = _login(client, student)

    # 学生提交实名求助
    real = api.post(
        "/api/help-requests",
        json={"category": "academic", "content": "高数挂科了，想请老师帮忙规划复习", "anonymous": False},
        headers=s_headers,
    )
    assert real.status_code == 200, real.text
    assert real.json()["status"] == "pending"
    assert real.json()["student_name"] == student.name

    # 学生提交匿名求助
    anon = api.post(
        "/api/help-requests",
        json={"category": "mental", "content": "最近压力很大，睡不好", "anonymous": True},
        headers=s_headers,
    )
    assert anon.status_code == 200, anon.text

    # 学生查看自己的求助（含辅导员回复，实名可见）
    mine = api.get("/api/help-requests/mine", headers=s_headers).json()
    assert len(mine) == 2
    assert {m["id"] for m in mine} == {real.json()["id"], anon.json()["id"]}

    # 辅导员概览
    overview = api.get("/api/help-requests/overview", headers=t_headers).json()
    assert overview == {"pending": 2, "processing": 0, "resolved": 0, "total": 2}

    # 辅导员列表：实名显示姓名，匿名隐去姓名
    listing = api.get("/api/help-requests", headers=t_headers).json()
    assert len(listing) == 2
    by_id = {h["id"]: h for h in listing}
    assert by_id[real.json()["id"]]["student_name"] == student.name
    assert by_id[anon.json()["id"]]["student_name"] == ""
    assert by_id[anon.json()["id"]]["anonymous"] is True

    # 状态过滤
    pending_only = api.get("/api/help-requests", params={"status": "pending"}, headers=t_headers).json()
    assert len(pending_only) == 2

    # 受理并回复（帮扶中）
    reply1 = api.put(
        f"/api/help-requests/{real.json()['id']}/reply",
        json={"reply": "已安排本周三下午答疑，别着急", "status": "processing"},
        headers=t_headers,
    )
    assert reply1.status_code == 200, reply1.text
    assert reply1.json()["status"] == "processing"
    assert reply1.json()["teacher_id"] == teacher.id
    assert reply1.json()["teacher_name"] == teacher.name

    # 再次回复收敛为已帮助
    reply2 = api.put(
        f"/api/help-requests/{anon.json()['id']}/reply",
        json={"reply": "已联系心理中心，明天可预约面谈", "status": "resolved"},
        headers=t_headers,
    )
    assert reply2.status_code == 200, reply2.text
    assert reply2.json()["status"] == "resolved"

    # 学生能看到回复
    mine2 = api.get("/api/help-requests/mine", headers=s_headers).json()
    replied = next(m for m in mine2 if m["id"] == real.json()["id"])
    assert replied["reply"] == "已安排本周三下午答疑，别着急"
    assert replied["teacher_name"] == teacher.name

    # 概览已更新
    overview2 = api.get("/api/help-requests/overview", headers=t_headers).json()
    assert overview2 == {"pending": 0, "processing": 1, "resolved": 1, "total": 2}

    # 状态过滤（已帮助）
    resolved_only = api.get("/api/help-requests", params={"status": "resolved"}, headers=t_headers).json()
    assert len(resolved_only) == 1
    assert resolved_only[0]["id"] == anon.json()["id"]


def test_help_request_role_and_scope_guard(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    other = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="本班学生")
    stranger = make_user(role=UserRole.STUDENT, tutor_id=other.id, name="别班学生")
    t_headers = _login(client, teacher)
    other_headers = _login(client, other)
    s_headers = _login(client, student)
    stranger_headers = _login(client, stranger)

    created = api.post(
        "/api/help-requests",
        json={"category": "life", "content": "生活费有点紧张", "anonymous": False},
        headers=s_headers,
    )
    assert created.status_code == 200, created.text

    # 教师端接口学生不可访问
    assert api.get("/api/help-requests", headers=s_headers).status_code == 403
    assert api.get("/api/help-requests/overview", headers=s_headers).status_code == 403

    # 学生端接口教师不可访问
    assert api.post(
        "/api/help-requests",
        json={"content": "教师误提交"},
        headers=t_headers,
    ).status_code == 403

    # 非本班辅导员：列表为空，且无权受理
    assert api.get("/api/help-requests", headers=other_headers).json() == []
    denied = api.put(
        f"/api/help-requests/{created.json()['id']}/reply",
        json={"reply": "越权回复", "status": "resolved"},
        headers=other_headers,
    )
    assert denied.status_code == 403

    # 未变更状态与回复
    record = db.query(HelpRequest).filter(HelpRequest.id == created.json()["id"]).first()
    assert record.status == HelpRequestStatus.PENDING
    assert record.reply is None

    # 别班学生也看不到本班学生的求助
    assert api.get("/api/help-requests/mine", headers=stranger_headers).json() == []