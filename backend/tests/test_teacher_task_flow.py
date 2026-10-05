"""教师端 P0 闭环测试：待办任务层 + 侧写记录 + 销假确认 + 随访到期。

覆盖设计规划 §3 的验收标准：
① 同一来源重复触发不产生重复任务；
② 任务状态可流转且非法流转被拒；
③ 侧写记录可写、可回链任务并推进任务状态、工作量统计正确；
④ 请假能走完「审批通过 → 返校确认」，统计口径正确；
⑤ 到期随访能被「待随访」接口检出。
"""
from datetime import date, datetime, timedelta

from app.models.care_record import CareRecord, CareRecordType
from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.teacher_task import TaskSourceType, TaskStatus, TeacherTask
from app.models.user import UserRole


def _login(client, user) -> dict:
    """以指定用户登录，返回 Bearer 头。"""
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── 模块 1：统一待办任务层 ──────────────────────────────────────────────


def test_task_idempotent_by_source(client, api, make_user):
    """同一 (source_type, source_id, teacher_id) 重复建任务只保留一条。"""
    teacher = make_user(role=UserRole.TEACHER)
    headers = _login(client, teacher)

    payload = {
        "title": "跟进联系：张三",
        "detail": "最近情绪波动",
        "student_id": 999,
        "source_type": "ai_suggest",
        "source_id": 42,
    }
    first = api.post("/api/teacher-tasks", json=payload, headers=headers)
    assert first.status_code == 200, first.text
    second = api.post("/api/teacher-tasks", json=payload, headers=headers)
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]

    listing = api.get("/api/teacher-tasks", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_task_summary_and_overdue_filter(client, api, make_user):
    """首页 KPI：待办 / 逾期 / 今日口径正确。"""
    teacher = make_user(role=UserRole.TEACHER)
    headers = _login(client, teacher)
    today = date.today()

    def _mk(title, due, source_id):
        return api.post(
            "/api/teacher-tasks",
            json={"title": title, "due_at": due.isoformat(), "source_id": source_id},
            headers=headers,
        )

    _mk("逾期任务", today - timedelta(days=1), 1)
    _mk("今日任务", today, 2)
    _mk("未来任务", today + timedelta(days=3), 3)

    summary = api.get("/api/teacher-tasks/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["pending"] == 3
    assert body["overdue"] == 1
    assert body["today"] == 1
    assert body["total"] == 3

    overdue = api.get("/api/teacher-tasks", params={"due": "overdue"}, headers=headers)
    assert [t["title"] for t in overdue.json()] == ["逾期任务"]


def test_task_state_machine_rejects_invalid(client, api, make_user):
    """状态机：pending→done 允许；done→cared 非法被拒。"""
    teacher = make_user(role=UserRole.TEACHER)
    headers = _login(client, teacher)
    created = api.post(
        "/api/teacher-tasks", json={"title": "约谈小李", "source_id": 7}, headers=headers
    ).json()

    ok = api.patch(
        f"/api/teacher-tasks/{created['id']}", json={"status": "done"}, headers=headers
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "done"
    assert ok.json()["done_at"]

    bad = api.patch(
        f"/api/teacher-tasks/{created['id']}", json={"status": "cared"}, headers=headers
    )
    assert bad.status_code == 400
    assert "不允许的状态流转" in bad.json()["detail"]


# ── 模块 2：教师侧写记录 ────────────────────────────────────────────────


def test_care_record_advances_task_and_workload(client, api, make_user):
    """侧写记录回链任务 → 任务推进为 cared；工作量统计按类型聚合。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id)
    headers = _login(client, teacher)

    task = api.post(
        "/api/teacher-tasks", json={"title": "跟进小王", "source_id": 11}, headers=headers
    ).json()

    rec = api.post(
        "/api/care-records",
        json={
            "student_id": student.id,
            "record_type": "talk",
            "content": "谈心：近期学习压力较大，已疏导",
            "task_id": task["id"],
        },
        headers=headers,
    )
    assert rec.status_code == 200, rec.text
    assert rec.json()["record_type"] == "talk"
    assert rec.json()["student_name"] == student.name

    refreshed = api.get("/api/teacher-tasks", headers=headers).json()[0]
    assert refreshed["status"] == "cared"

    api.post(
        "/api/care-records",
        json={"student_id": student.id, "record_type": "comment", "content": "期末评语：进步明显"},
        headers=headers,
    )
    workload = api.get("/api/care-records/workload", headers=headers)
    assert workload.status_code == 200, workload.text
    assert workload.json() == {"care": 0, "talk": 1, "comment": 1, "total": 2}

    # 软删除后不再计入工作量
    api.delete(f"/api/care-records/{rec.json()['id']}", headers=headers)
    after = api.get("/api/care-records/workload", headers=headers).json()
    assert after["total"] == 1
    assert after["talk"] == 0


def test_care_record_rejects_foreign_student(client, api, make_user, db):
    """教师不得为他人名下学生写侧写记录。"""
    teacher = make_user(role=UserRole.TEACHER)
    other = make_user(role=UserRole.TEACHER)
    stranger = make_user(role=UserRole.STUDENT, tutor_id=other.id)
    headers = _login(client, teacher)

    resp = api.post(
        "/api/care-records",
        json={"student_id": stranger.id, "content": "越权写入"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert db.query(CareRecord).filter(CareRecord.student_id == stranger.id).count() == 0


# ── 模块 5：销假确认 + 统计 ─────────────────────────────────────────────


def test_leave_confirm_return_and_stats(client, api, make_user, db):
    """请假闭环：审批通过 → 返校确认；统计口径含待销假数。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id)
    s_headers = _login(client, student)
    t_headers = _login(client, teacher)

    today = date.today()
    created = api.post(
        "/api/leave/create",
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat(),
            "reason": "参加省级竞赛",
            "leave_type": "competition",
        },
        headers=s_headers,
    )
    assert created.status_code == 200, created.text
    leave_id = created.json()["id"]

    approved = api.post(
        f"/api/leave/{leave_id}/review", json={"action": "approve"}, headers=t_headers
    )
    assert approved.status_code == 200, approved.text

    stats_before = api.get("/api/leave/stats", headers=t_headers).json()
    assert stats_before["approved"] == 1
    assert stats_before["awaiting_return"] == 1

    confirmed = api.post(f"/api/leave/{leave_id}/confirm-return", headers=t_headers)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["return_confirmed"] is True
    assert db.get(LeaveRequest, leave_id).return_confirmed is True

    stats_after = api.get("/api/leave/stats", headers=t_headers).json()
    assert stats_after["awaiting_return"] == 0


def test_frequent_leave_triggers_alert_task(client, api, make_user, db):
    """同生频繁请假（窗口期内达阈值）→ 自动生成 alert 跟进任务，且只保留一条。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id)
    s_headers = _login(client, student)
    t_headers = _login(client, teacher)
    today = date.today()

    for _ in range(3):
        created = api.post(
            "/api/leave/create",
            json={
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=1)).isoformat(),
                "reason": "身体不适",
                "leave_type": "sick",
            },
            headers=s_headers,
        )
        assert created.status_code == 200, created.text
        approved = api.post(
            f"/api/leave/{created.json()['id']}/review",
            json={"action": "approve"},
            headers=t_headers,
        )
        assert approved.status_code == 200, approved.text

    alerts = (
        db.query(TeacherTask)
        .filter(
            TeacherTask.teacher_id == teacher.id,
            TeacherTask.source_type == TaskSourceType.ALERT,
            TeacherTask.student_id == student.id,
        )
        .all()
    )
    assert len(alerts) == 1
    assert "频繁请假" in alerts[0].title


def test_confirm_return_rejects_pending_leave(client, api, make_user):
    """未通过的请假不允许确认返校。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id)
    s_headers = _login(client, student)
    t_headers = _login(client, teacher)

    today = date.today()
    leave_id = api.post(
        "/api/leave/create",
        json={
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "reason": "事假",
            "leave_type": "personal",
        },
        headers=s_headers,
    ).json()["id"]

    resp = api.post(f"/api/leave/{leave_id}/confirm-return", headers=t_headers)
    assert resp.status_code == 400
    assert "已通过" in resp.json()["detail"]


# ── 模块 4：随访到期提醒 ────────────────────────────────────────────────


def test_crisis_follow_up_due(client, api, make_user, db):
    """随访到期且未办结的预警出现在「待随访」；已办结的不出现。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id)
    headers = _login(client, teacher)

    due = AIDialogSummary(
        student_id=student.id,
        summary="近期多次表达焦虑",
        level=CrisisLevel.MODERATE,
        resolved=False,
        follow_up_date=date.today() - timedelta(days=1),
    )
    future = AIDialogSummary(
        student_id=student.id,
        summary="随访日期未到",
        level=CrisisLevel.MILD,
        resolved=False,
        follow_up_date=date.today() + timedelta(days=5),
    )
    closed = AIDialogSummary(
        student_id=student.id,
        summary="已闭环",
        level=CrisisLevel.SEVERE,
        resolved=True,
        follow_up_date=date.today() - timedelta(days=2),
    )
    db.add_all([due, future, closed])
    db.commit()

    resp = api.get("/api/crisis/follow-up-due", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = [a["id"] for a in resp.json()]
    assert due.id in ids
    assert future.id not in ids
    assert closed.id not in ids
