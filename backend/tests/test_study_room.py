"""自习室：专注记录写入、今日/历史汇总、休息不落库与用户隔离。"""
from datetime import date, datetime, timezone

from app.models.study_session import StudySession
from app.models.user import UserRole


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_study_room_flow(client, api, make_user, db):
    student = make_user(role=UserRole.STUDENT)
    other = make_user(role=UserRole.STUDENT)
    headers = _login(client, student)
    start = datetime.now(timezone.utc)

    try:
        # 正常写入一条 25 分钟专注
        created = api.post(
            "/api/study-room/sessions",
            json={
                "mode": "focus",
                "task_title": "数据结构复习",
                "planned_minutes": 25,
                "actual_minutes": 25,
                "completed": True,
                "started_at": start.isoformat(),
                "ended_at": start.isoformat(),
            },
            headers=headers,
        )
        assert created.status_code == 200, created.text
        body = created.json()
        assert body["actual_minutes"] == 25
        assert body["study_date"] == date.today().isoformat()
        assert body["start_time"]

        # 今日汇总 + 近 7 天明细
        overview = client.get("/api/study-room/overview?days=7", headers=headers)
        assert overview.status_code == 200, overview.text
        data = overview.json()
        assert data["today"]["focus_minutes"] == 25
        assert data["today"]["session_count"] == 1
        assert len(data["days"]) == 7
        assert data["days"][-1]["date"] == date.today().isoformat()
        assert any(s["task_title"] == "数据结构复习" for s in data["sessions"])

        # 休息时段不落库、非法时长拒绝
        break_resp = api.post(
            "/api/study-room/sessions",
            json={"mode": "short_break", "planned_minutes": 5, "actual_minutes": 5},
            headers=headers,
        )
        assert break_resp.status_code == 400
        bad_resp = api.post(
            "/api/study-room/sessions",
            json={"mode": "focus", "planned_minutes": 25, "actual_minutes": 1000},
            headers=headers,
        )
        assert bad_resp.status_code == 400

        # 用户隔离
        other_headers = _login(client, other)
        other_view = client.get("/api/study-room/overview?days=7", headers=other_headers)
        assert other_view.status_code == 200
        assert other_view.json()["today"]["focus_minutes"] == 0
    finally:
        db.query(StudySession).filter(
            StudySession.student_id.in_([student.id, other.id])
        ).delete(synchronize_session=False)
        db.commit()
