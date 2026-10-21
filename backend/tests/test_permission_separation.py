"""角色权限分离回归测试：教师不得越权访问非名下学生数据；AI 工具按角色门控。

覆盖本次修复的越权点：
- 学生画像 / 风险指标 / 趋势（profile）
- 请假 AI 分析（leave）
- 匿名问卷结果（peer_survey）
- 成长记录创建（growth）
- 成绩分析（grade_analysis）
- 家校沟通分享链接（guardian）
- AI 工具调用角色门控（tools.dispatcher）
"""
from datetime import date
import uuid

import pytest

from app.models.academic import Grade
from app.models.leave import LeaveRequest
from app.models.user import User, UserRole
from app.services.tools import execute_tool


@pytest.mark.parametrize(
    "path",
    [
        "/api/profile/student/{sid}",
        "/api/profile/student/{sid}/trends",
        "/api/profile/student/{sid}/risk-indicators",
        "/api/profile/student/{sid}/trajectory",
        "/api/profile/cohort/{sid}",
    ],
)
def test_profile_endpoints_scope_teacher_to_tutor(api, login_token, make_user, path):
    """教师仅可查看名下学生的画像类数据，非名下学生一律 403。"""
    teacher = login_token(role=UserRole.TEACHER)
    mine = make_user(role=UserRole.STUDENT, tutor_id=teacher["user"].id, name="名下学生")
    stranger = make_user(role=UserRole.STUDENT, name="他人学生")

    ok = api.get(path.format(sid=mine.id), headers=teacher["headers"])
    assert ok.status_code == 200, f"{path} 名下学生应可访问: {ok.text}"

    denied = api.get(path.format(sid=stranger.id), headers=teacher["headers"])
    assert denied.status_code == 403, f"{path} 非名下学生应被拒绝: {denied.status_code}"


def test_leave_analyze_scope_teacher_to_tutor(api, login_token, make_user, db):
    """教师仅可对名下学生的请假发起 AI 分析。"""
    teacher = login_token(role=UserRole.TEACHER)
    stranger = make_user(role=UserRole.STUDENT, name="他人学生")
    leave = LeaveRequest(
        student_id=stranger.id,
        start_date=date.today(),
        end_date=date.today(),
        reason="家中事务",
        leave_type="personal",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)

    denied = api.get(f"/api/leave/{leave.id}/analyze", headers=teacher["headers"])
    assert denied.status_code == 403, denied.text


def test_peer_survey_result_scope_to_creator(api, login_token):
    """匿名问卷聚合结果仅创建者（或管理员）可查看。"""
    creator = login_token(role=UserRole.TEACHER)
    other = login_token(role=UserRole.TEACHER)
    resp = api.post(
        "/api/peer-surveys",
        json={
            "title": "权限校验问卷",
            "target_type": "peer",
            "period": "2026-spring",
            "questions": [{"key": "care", "label": "关心学生", "max": 5}],
            "status": "open",
        },
        headers=creator["headers"],
    )
    assert resp.status_code == 200, resp.text
    survey_id = resp.json()["id"]

    ok = api.get(f"/api/peer-surveys/{survey_id}/result", headers=creator["headers"])
    assert ok.status_code == 200, ok.text

    denied = api.get(f"/api/peer-surveys/{survey_id}/result", headers=other["headers"])
    assert denied.status_code == 403, denied.text


def test_growth_create_scope_teacher_to_tutor(api, login_token, make_user):
    """教师不得为非名下学生创建成长记录。"""
    teacher = login_token(role=UserRole.TEACHER)
    mine = make_user(role=UserRole.STUDENT, tutor_id=teacher["user"].id, name="名下学生")
    stranger = make_user(role=UserRole.STUDENT, name="他人学生")
    payload = {"type": "honor", "title": "校级奖学金", "date": "2025-01-01"}

    ok = api.post(
        "/api/growth/records",
        json={**payload, "student_id": mine.id},
        headers=teacher["headers"],
    )
    assert ok.status_code == 200, ok.text

    denied = api.post(
        "/api/growth/records",
        json={**payload, "student_id": stranger.id},
        headers=teacher["headers"],
    )
    assert denied.status_code == 403, denied.text


def test_grade_analysis_scope_teacher_to_tutor(api, login_token, make_user):
    """教师不得查看非名下学生的成绩分析。"""
    teacher = login_token(role=UserRole.TEACHER)
    mine = make_user(role=UserRole.STUDENT, tutor_id=teacher["user"].id, name="名下学生")
    stranger = make_user(role=UserRole.STUDENT, name="他人学生")

    ok = api.get(f"/api/academic/analysis/{mine.id}", headers=teacher["headers"])
    assert ok.status_code == 200, ok.text

    denied = api.get(f"/api/academic/analysis/{stranger.id}", headers=teacher["headers"])
    assert denied.status_code == 403, denied.text


def test_guardian_share_link_scope_to_owner(api, login_token, make_user):
    """教师不得查看他人沟通记录的分享链接。"""
    owner = login_token(role=UserRole.TEACHER)
    other = login_token(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=owner["user"].id, name="名下学生")

    created = api.post(
        "/api/guardians/logs",
        json={"student_id": student.id, "content_summary": "电话联系家长", "scene": "other", "channel": "note"},
        headers=owner["headers"],
    )
    assert created.status_code == 200, created.text
    log_id = created.json()["id"]

    ok = api.get(f"/api/guardians/logs/{log_id}/share-link", headers=owner["headers"])
    assert ok.status_code == 200, ok.text

    denied = api.get(f"/api/guardians/logs/{log_id}/share-link", headers=other["headers"])
    assert denied.status_code == 403, denied.text


@pytest.mark.asyncio
async def test_ai_tool_role_gate(make_user):
    """AI 工具按角色门控：学生不得调用教师端工具，教师不得调用学生端工具。"""
    student = make_user(role=UserRole.STUDENT)
    teacher = make_user(role=UserRole.TEACHER)

    student_blocked = await execute_tool("approve_leave", {"leave_id": 1, "action": "approve"}, student)
    assert student_blocked == {"error": "无权调用工具: approve_leave"}

    teacher_blocked = await execute_tool(
        "create_leave",
        {"start_date": "2025-01-01", "end_date": "2025-01-02", "reason": "x", "leave_type": "other"},
        teacher,
    )
    assert teacher_blocked == {"error": "无权调用工具: create_leave"}


def test_feed_source_rejects_internal_url(api, login_token):
    """资讯源地址防 SSRF：拒绝本机/内网地址与非 http(s) 协议（学生端与管理员端一致）。"""
    student = login_token(role=UserRole.STUDENT)
    admin = login_token(role=UserRole.ADMIN)
    body = {"name": "可疑源", "kind": "rss", "source_type": "ai_news"}

    for url in (
        "http://127.0.0.1:8000/hook",
        "http://localhost/internal",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/feed.xml",
        "ftp://example.com/feed.xml",
    ):
        student_resp = api.post("/api/feeds/sources", json={**body, "url": url}, headers=student["headers"])
        assert student_resp.status_code == 400, f"{url} 应被学生端拒绝: {student_resp.text}"
        admin_resp = api.post("/api/admin/feeds/sources", json={**body, "url": url}, headers=admin["headers"])
        assert admin_resp.status_code == 400, f"{url} 应被管理员端拒绝: {admin_resp.text}"


def test_workflow_node_role_enforced(api, login_token):
    """工作流审批：非发起人教师不得审批「管理员」节点。"""
    admin = login_token(role=UserRole.ADMIN)
    initiator = login_token(role=UserRole.TEACHER)
    peer = login_token(role=UserRole.TEACHER)
    code = f"admin_only_{uuid.uuid4().hex[:8]}"

    created = api.post(
        "/api/workflows/defs",
        json={
            "code": code,
            "name": "仅管理员终审",
            "nodes": [{"key": "final", "name": "管理员终审", "approver_role": "admin"}],
        },
        headers=admin["headers"],
    )
    assert created.status_code == 200, created.text

    started = api.post(
        "/api/workflows/instances",
        json={"def_code": code, "biz_id": 1},
        headers=initiator["headers"],
    )
    assert started.status_code == 200, started.text
    instance_id = started.json()["id"]

    denied = api.post(
        f"/api/workflows/instances/{instance_id}/approve",
        json={"comment": "越权审批"},
        headers=peer["headers"],
    )
    assert denied.status_code == 400, denied.text
    assert "角色" in denied.json()["detail"]


def test_class_grade_analysis_filters_by_class(api, login_token, make_user, db):
    """班级成绩分析按 class_id 过滤，且教师仅能看到名下学生。"""
    teacher = login_token(role=UserRole.TEACHER)
    class_a = make_user(role=UserRole.STUDENT, tutor_id=teacher["user"].id, name="一班学生")
    class_b = make_user(role=UserRole.STUDENT, tutor_id=teacher["user"].id, name="二班学生")
    db.get(User, class_a.id).class_group_id = 101
    db.get(User, class_b.id).class_group_id = 202
    db.add_all([
        Grade(student_id=class_a.id, course_name="高等数学", score=90, credit=4, gpa=4.0, semester="2025-1"),
        Grade(student_id=class_b.id, course_name="大学英语", score=80, credit=3, gpa=3.0, semester="2025-1"),
    ])
    db.commit()
    try:
        first = api.get("/api/academic/analysis/class/101", headers=teacher["headers"])
        assert first.status_code == 200, first.text
        assert [s["student_id"] for s in first.json()["students"]] == [class_a.id]

        second = api.get("/api/academic/analysis/class/202", headers=teacher["headers"])
        assert [s["student_id"] for s in second.json()["students"]] == [class_b.id]

        student = login_token(role=UserRole.STUDENT)
        denied = api.get("/api/academic/analysis/class/101", headers=student["headers"])
        assert denied.status_code == 403
    finally:
        db.query(Grade).filter(Grade.student_id.in_([class_a.id, class_b.id])).delete(synchronize_session=False)
        db.commit()