"""教师端公告：按班级定向发布 + 内容可见性。

覆盖两条用户反馈：
1. 发布时不能选择发布班级 → 现在可选，且只允许投递给自己名下有学生的班级；
2. 发布之后查看不到内容 → 列表接口必须回传完整 content 与班级信息。
"""
import itertools

import pytest

from app.models.academic import ClassGroup, College, Major
from app.models.user import UserRole


_seq = itertools.count(1)


def _make_class(db, name: str) -> int:
    """造一个班级（含学院/专业父级，满足外键与唯一约束）。

    College.code / Major.code 都是 NOT NULL + unique，必须给唯一值，
    否则 sqlite 直接抛 NOT NULL constraint failed。
    """
    n = next(_seq)
    college = College(name=f"学院{name}-{n}", code=f"C{n:04d}")
    db.add(college)
    db.flush()
    major = Major(name=f"专业{name}", code=f"M{n:04d}", college_id=college.id)
    db.add(major)
    db.flush()
    cg = ClassGroup(name=name, grade=2024, major_id=major.id)
    db.add(cg)
    db.commit()
    db.refresh(cg)
    return cg.id


@pytest.fixture()
def two_classes(db):
    return _make_class(db, "2024级测试1班"), _make_class(db, "2024级测试2班")


def _bind_student(db, make_user, tutor_id: int, class_group_id: int):
    stu = make_user(role=UserRole.STUDENT, tutor_id=tutor_id)
    stu.class_group_id = class_group_id
    db.commit()
    db.refresh(stu)
    return stu


def _h(t):
    return {**t["headers"], "X-Requested-With": "XMLHttpRequest"}


def test_class_options_only_lists_own_students_classes(client, login_token, db, make_user, two_classes):
    c1, c2 = two_classes
    t = login_token(UserRole.TEACHER)
    _bind_student(db, make_user, t["user"].id, c1)
    _bind_student(db, make_user, t["user"].id, c1)
    _bind_student(db, make_user, t["user"].id, c2)

    resp = client.get("/api/teacher/announcement-classes", headers=_h(t))
    assert resp.status_code == 200, resp.text
    opts = resp.json()
    print("可发布班级:", opts)
    ids = {o["id"] for o in opts}
    assert ids == {c1, c2}
    by_id = {o["id"]: o for o in opts}
    assert by_id[c1]["student_count"] == 2
    assert by_id[c2]["student_count"] == 1


def test_publish_to_class_and_content_visible(client, login_token, db, make_user, two_classes):
    c1, c2 = two_classes
    t = login_token(UserRole.TEACHER)
    s1 = _bind_student(db, make_user, t["user"].id, c1)
    s2 = _bind_student(db, make_user, t["user"].id, c2)

    long_content = "这是完整公告正文。" * 20
    resp = client.post(
        "/api/teacher/announcements",
        data={"title": "1班专属通知", "content": long_content,
              "urgency": "important", "class_group_id": str(c1)},
        headers=_h(t),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    print("发布返回:", body)
    # 问题 2：发布后必须能拿到完整内容与班级
    assert body["content"] == long_content
    assert body["class_group_id"] == c1
    assert body["class_name"] == "2024级测试1班"

    # 教师列表里同样能看到完整内容
    lst = client.get("/api/teacher/announcements", headers=_h(t)).json()
    row = next(x for x in lst if x["id"] == body["id"])
    assert row["content"] == long_content
    assert row["class_name"] == "2024级测试1班"

    # 1班学生看得到，2班学生看不到
    h1 = _h(login_token(UserRole.STUDENT))
    # login_token 造的是新学生，需要手工换成我们绑定的学生 —— 直接查库断言更直接
    from app.models.announcement import TeacherAnnouncement
    from sqlalchemy import select as sa_select
    ann = db.get(TeacherAnnouncement, body["id"])
    assert ann is not None and ann.class_group_id == c1


def test_student_scope_filtering(client, login_token, db, make_user, two_classes, monkeypatch):
    """学生端只应看到「全体」或「本班」的公告。"""
    from app.api import announcement as ann_api

    c1, c2 = two_classes
    t = login_token(UserRole.TEACHER)
    s1 = _bind_student(db, make_user, t["user"].id, c1)
    s2 = _bind_student(db, make_user, t["user"].id, c2)

    # 全班公告
    client.post("/api/teacher/announcements",
                data={"title": "全体通知", "content": "全体可见", "urgency": "normal"},
                headers=_h(t))
    # 1班公告
    client.post("/api/teacher/announcements",
                data={"title": "1班通知", "content": "仅1班", "urgency": "normal",
                      "class_group_id": str(c1)},
                headers=_h(t))

    from app.core.deps import get_current_user, get_db
    from app.main import app

    def login_as(student):
        app.dependency_overrides[get_current_user] = lambda: db.get(type(student), student.id)

    orig = dict(app.dependency_overrides)
    try:
        login_as(s1)
        r1 = client.get("/api/student/announcements", headers=_h(t))
        assert r1.status_code == 200, r1.text
        titles1 = {x["title"] for x in r1.json()}
        print("1班学生看到:", titles1)
        assert titles1 == {"全体通知", "1班通知"}

        app.dependency_overrides.clear()
        app.dependency_overrides.update({k: v for k, v in orig.items() if k != get_current_user})
        login_as(s2)
        r2 = client.get("/api/student/announcements", headers=_h(t))
        titles2 = {x["title"] for x in r2.json()}
        print("2班学生看到:", titles2)
        assert titles2 == {"全体通知"}
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(orig)


def test_cannot_publish_to_foreign_class(client, login_token, db, make_user, two_classes):
    c1, c2 = two_classes
    t = login_token(UserRole.TEACHER)
    _bind_student(db, make_user, t["user"].id, c1)

    # 教师名下没有 c2 的学生 → 拒绝
    resp = client.post(
        "/api/teacher/announcements",
        data={"title": "越界", "content": "x", "urgency": "normal", "class_group_id": str(c2)},
        headers=_h(t),
    )
    print("越界发布:", resp.status_code, resp.text[:200])
    assert resp.status_code == 400


def test_reach_uses_class_scope_denominator(client, login_token, db, make_user, two_classes):
    """定向班级公告的应读人数应为该班人数，而不是名下学生总数。"""
    c1, c2 = two_classes
    t = login_token(UserRole.TEACHER)
    for _ in range(2):
        _bind_student(db, make_user, t["user"].id, c1)
    _bind_student(db, make_user, t["user"].id, c2)  # 共 3 人

    client.post("/api/teacher/announcements",
                data={"title": "只发1班", "content": "x", "urgency": "normal",
                      "class_group_id": str(c1)},
                headers=_h(t))

    reach = client.get("/api/teacher/announcements/reach", headers=_h(t)).json()
    print("触达:", reach)
    row = next(i for i in reach["items"] if i["title"] == "只发1班")
    assert row["total"] == 2, "应读应等于1班人数"
