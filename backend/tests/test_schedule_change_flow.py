"""单次调课链路端到端：教师提交 → 管理员审批 → 原课 skip_weeks + 补课记录 → 学生通知。

背景：旧实现审批通过后直接改原课的 day_of_week / week_start / week_end，
等于把整门课整学期搬走。正确语义是「把某一周的课挪到以后某周某天」：
原课保留并记 skip_weeks，另建一条 week_start==week_end==目标周 的补课记录。
"""

from app.models.academic import ClassGroup, Course
from app.models.notification import Notification
from app.models.schedule_change import ScheduleChangeKind, ScheduleChangeStatus
from app.models.user import UserRole

from tests.conftest import CSRF_HEADER


def _mk_course(db, teacher, cg, **kw):
    defaults = dict(
        name="数据结构",
        class_group_id=cg.id,
        teacher=teacher.name,
        teacher_id=teacher.id,
        location="教学楼A-101",
        day_of_week=1,
        start_period=1,
        end_period=2,
        week_start=1,
        week_end=16,
        semester="2026-2027-1",
        credit=3.0,
    )
    defaults.update(kw)
    c = Course(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _mk_cg(db):
    cg = db.query(ClassGroup).first()
    if cg is None:
        cg = ClassGroup(name="软工2401", grade="2024", student_count=30)
        db.add(cg)
        db.commit()
        db.refresh(cg)
    return cg


def _login(client, user):
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers=CSRF_HEADER,
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_single_week_swap_flow(client, db, make_user):
    teacher = make_user(role=UserRole.TEACHER, name="王老师")
    admin = make_user(role=UserRole.ADMIN, name="教务主任")
    cg = _mk_cg(db)
    course = _mk_course(db, teacher, cg)
    student = make_user(role=UserRole.STUDENT, name="李同学")
    student.class_group_id = cg.id
    db.commit()

    th = _login(client, teacher)

    # ── 教师提交：把第 5 周的课挪到第 8 周周六 3-4 节 ──
    resp = client.post(
        "/api/schedule-change/create",
        json={
            "kind": "swap",
            "course_id": course.id,
            "origin_week_no": 5,
            "target_week": 8,
            "day_of_week": 6,
            "start_period": 3,
            "end_period": 4,
            "location": "教学楼B-203",
            "reason": "第5周开会冲突，顺延到第8周周六",
            "semester": "2026-2027-1",
        },
        headers={**CSRF_HEADER, **th},
    )
    assert resp.status_code == 200, resp.text
    req_id = resp.json()["id"]
    body = resp.json()
    assert body["origin_week_no"] == 5
    assert body["week_start"] == 8 and body["week_end"] == 8  # 单次：目标周==生效周

    # 目标周与原课同周同时段的旧冲突不应触发；真冲突按设计「不硬拦、写入备注」：
    # 同班同学期同周同节再提一笔，应成功创建但 reason 里带待审重叠提示
    course2 = _mk_course(db, teacher, cg, name="操作系统", day_of_week=3, start_period=5, end_period=6)
    resp = client.post(
        "/api/schedule-change/create",
        json={
            "kind": "swap",
            "course_id": course2.id,
            "origin_week_no": 5,
            "target_week": 8,
            "day_of_week": 6,
            "start_period": 3,
            "end_period": 4,  # 与上面那条申请同班同学期同周同节 → 冲突
            "reason": "x",
            "semester": "2026-2027-1",
        },
        headers={**CSRF_HEADER, **th},
    )
    assert resp.status_code == 200, resp.text
    assert "待审批" in resp.json()["reason"], "待审重叠应写入 reason 备注"

    # ── 管理员审批通过 ──
    ah = _login(client, admin)
    resp = client.post(
        f"/api/schedule-change/{req_id}/review",
        json={"action": "approve"},
        headers={**CSRF_HEADER, **ah},
    )
    assert resp.status_code == 200, resp.text
    applied_id = resp.json()["course_id"]
    assert applied_id and applied_id != course.id  # 补课是新记录，原课不动

    db.expire_all()
    # 原课：仍在周一1-2节，整学期范围不变，只是第5周被挪走
    db.refresh(course)
    assert course.day_of_week == 1 and course.start_period == 1
    assert course.week_start == 1 and course.week_end == 16
    assert course.skip_weeks == "5"

    # 补课：单周记录，挂在目标周
    makeup = db.get(Course, applied_id)
    assert makeup.week_start == 8 and makeup.week_end == 8
    assert makeup.day_of_week == 6 and makeup.start_period == 3
    assert makeup.location == "教学楼B-203"
    assert makeup.source_change_id == req_id

    # ── 学生收到通知 ──
    notes = (
        db.query(Notification)
        .filter(Notification.user_id == student.id)
        .all()
    )
    assert notes, "调课应通知到班级学生"
    assert any("第5周" in n.content and "第8周" in n.content for n in notes), \
        f"通知应包含原周与目标周: {[n.content for n in notes]}"

    # ── 教师课表接口：skip_weeks 与补课记录都能看到 ──
    resp = client.get("/api/teaching/schedule", headers=th)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = {c["id"]: c for c in data["courses"]}
    assert ids[course.id]["skip_weeks"] == [5]
    assert applied_id in ids and ids[applied_id]["week_start"] == 8

    # ── 状态落库 ──
    resp = client.get("/api/schedule-change/my", headers=th)
    row = next(r for r in resp.json() if r["id"] == req_id)
    assert row["status"] == ScheduleChangeStatus.APPROVED.value


def test_add_course_flow_notifies_students(client, db, make_user):
    """增课链路回归：审批通过 → 新课整段生效 → 学生收到通知。"""
    teacher = make_user(role=UserRole.TEACHER, name="张老师")
    admin = make_user(role=UserRole.ADMIN, name="教务主任B")
    cg = _mk_cg(db)
    student = make_user(role=UserRole.STUDENT, name="赵同学")
    student.class_group_id = cg.id
    db.commit()

    th = _login(client, teacher)
    resp = client.post(
        "/api/schedule-change/create",
        json={
            "kind": "add",
            "class_group_id": cg.id,
            "course_name": "算法竞赛实训",
            "day_of_week": 7,
            "start_period": 5,
            "end_period": 6,
            "week_start": 9,
            "week_end": 12,
            "location": "实训楼301",
            "reason": "竞赛备赛",
            "semester": "2026-2027-1",
        },
        headers={**CSRF_HEADER, **th},
    )
    assert resp.status_code == 200, resp.text
    req_id = resp.json()["id"]

    ah = _login(client, admin)
    resp = client.post(
        f"/api/schedule-change/{req_id}/review",
        json={"action": "approve"},
        headers={**CSRF_HEADER, **ah},
    )
    assert resp.status_code == 200, resp.text
    new_id = resp.json()["course_id"]

    db.expire_all()
    nc = db.get(Course, new_id)
    assert nc.name == "算法竞赛实训"
    assert nc.week_start == 9 and nc.week_end == 12
    assert nc.teacher_id == teacher.id

    notes = db.query(Notification).filter(Notification.user_id == student.id).all()
    assert any("算法竞赛实训" in n.content for n in notes)
