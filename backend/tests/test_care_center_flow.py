"""人文关怀中心：关怀日历（自动生成幂等）/ 家访记录 / 正向激励 / 越权保护。"""
from datetime import date, timedelta

from app.models.care_center import CareEvent, CareEventType, HomeVisitRecord, PraiseRecord
from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.user import UserRole


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_care_center_events_visits_praise(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="关怀对象")
    headers = _login(client, teacher)
    today = date.today()

    # 手动添加关怀事项
    manual = api.post(
        "/api/care-center/events",
        json={
            "event_type": "birthday",
            "event_date": today.isoformat(),
            "title": f"{student.name} 生日关怀",
            "note": "准备一张手写贺卡",
            "student_id": student.id,
        },
        headers=headers,
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["auto_generated"] is False

    # 造数据：一条未处理的中度危机预警 + 3 次非驳回请假 → 自动生成两类事项
    db.add(
        AIDialogSummary(
            student_id=student.id,
            summary="近期情绪低落",
            level=CrisisLevel.MODERATE,
            resolved=False,
        )
    )
    db.commit()
    s_headers = _login(client, student)
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

    first_gen = api.post("/api/care-center/events/generate", headers=headers)
    assert first_gen.status_code == 200, first_gen.text
    assert first_gen.json()["created"] == 2  # 学业预警 + 困难学生

    # 幂等：再次触发生成不重复
    second_gen = api.post("/api/care-center/events/generate", headers=headers)
    assert second_gen.json()["created"] == 0

    events = api.get("/api/care-center/events", headers=headers).json()
    types = {e["event_type"] for e in events}
    assert {"birthday", "academic", "difficulty"} <= types
    assert len([e for e in events if e["auto_generated"]]) == 2

    # 家访记录
    visit = api.post(
        "/api/care-center/visits",
        json={
            "student_id": student.id,
            "visit_date": today.isoformat(),
            "method": "phone",
            "content": "与家长沟通近期缺勤情况",
            "follow_up": "两周后回访",
        },
        headers=headers,
    )
    assert visit.status_code == 200, visit.text
    assert visit.json()["student_name"] == student.name

    # 正向激励
    praise = api.post(
        "/api/care-center/praises",
        json={
            "student_id": student.id,
            "praise_type": "badge",
            "badge_name": "进步之星",
            "reason": "本月出勤与作业完成度明显提升",
        },
        headers=headers,
    )
    assert praise.status_code == 200, praise.text
    assert praise.json()["badge_name"] == "进步之星"

    overview = api.get("/api/care-center/overview", headers=headers).json()
    assert overview["event_count"] == 3
    assert overview["visit_count"] == 1
    assert overview["praise_count"] == 1

    # 删除：事件硬删，家访 / 激励软删
    assert api.delete(f"/api/care-center/events/{manual.json()['id']}", headers=headers).status_code == 200
    assert api.delete(f"/api/care-center/visits/{visit.json()['id']}", headers=headers).status_code == 200
    assert api.delete(f"/api/care-center/praises/{praise.json()['id']}", headers=headers).status_code == 200

    assert api.get("/api/care-center/visits", headers=headers).json() == []
    assert api.get("/api/care-center/praises", headers=headers).json() == []
    assert db.query(HomeVisitRecord).filter(HomeVisitRecord.id == visit.json()["id"]).first().is_deleted
    assert db.query(PraiseRecord).filter(PraiseRecord.id == praise.json()["id"]).first().is_deleted
    assert db.query(CareEvent).filter(CareEvent.id == manual.json()["id"]).count() == 0


def test_care_center_rejects_foreign_student(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    other = make_user(role=UserRole.TEACHER)
    stranger = make_user(role=UserRole.STUDENT, tutor_id=other.id, name="陌生学生")
    headers = _login(client, teacher)
    today = date.today()

    visit = api.post(
        "/api/care-center/visits",
        json={
            "student_id": stranger.id,
            "visit_date": today.isoformat(),
            "content": "越权写入",
        },
        headers=headers,
    )
    assert visit.status_code == 403

    praise = api.post(
        "/api/care-center/praises",
        json={"student_id": stranger.id, "reason": "越权写入"},
        headers=headers,
    )
    assert praise.status_code == 403

    event = api.post(
        "/api/care-center/events",
        json={
            "event_type": "other",
            "event_date": today.isoformat(),
            "title": "越权事项",
            "student_id": stranger.id,
        },
        headers=headers,
    )
    assert event.status_code == 403
    assert db.query(CareEvent).filter(CareEvent.student_id == stranger.id).count() == 0