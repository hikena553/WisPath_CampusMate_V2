"""P2 底座：学情事件底座 / 预警 pipeline / AI 学情助手 / 审批流程引擎。

覆盖规划验收口径：
① 学情事件旁路写入，失败不影响主流程；
② 预警能自动生成待办，且同规则同学生当日只生成一次（规则可配置）；
③ AI 建议可溯源（证据清单）且 LLM 失败可降级；
④ 新增审批类型无需改代码（节点 JSON 化），四个原语可跑通。
"""
from datetime import date, timedelta

import pytest

from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.learning_event import LearningEvent
from app.models.teacher_task import TeacherTask
from app.models.user import UserRole
from app.models.workflow import WorkflowInstance
from app.services import alert_pipeline_service, learning_event_service, student_insight_service


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _apply_leave(api, headers, days: int = 1):
    """走 api fixture（自动附加 CSRF 头）。"""
    today = date.today()
    return api.post(
        "/api/leave/create",
        json={
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=days - 1)).isoformat(),
            "reason": "身体不适",
            "leave_type": "sick",
        },
        headers=headers,
    )


# ── 模块 12：学情数据底座 ──────────────────────────────────────


def test_learning_event_emit_and_query(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="学情学生")
    s_headers = _login(client, student)
    t_headers = _login(client, teacher)

    created = _apply_leave(api, s_headers)
    assert created.status_code == 200, created.text

    # 事件已随主流程写入
    rows = db.query(LearningEvent).filter(LearningEvent.actor_id == student.id).all()
    assert len(rows) == 1
    assert rows[0].verb == "leave.apply"
    assert rows[0].object_type == "leave"

    # 教师可查名下学生聚合
    agg = api.get(
        "/api/learning-events/aggregate", params={"actor_id": student.id}, headers=t_headers
    )
    assert agg.status_code == 200, agg.text
    assert agg.json()["total"] >= 1
    assert any(v["verb"] == "leave.apply" for v in agg.json()["by_verb"])

    # 越权：其他教师不可查
    other = make_user(role=UserRole.TEACHER)
    denied = api.get(
        "/api/learning-events/aggregate", params={"actor_id": student.id}, headers=_login(client, other)
    )
    assert denied.status_code == 403


def test_learning_event_emit_never_breaks_main_flow(make_user, db):
    """旁路约束：异常载荷 / 不可序列化对象都不应抛出，且不影响调用方。"""
    user = make_user(role=UserRole.STUDENT)

    class Weird:
        def __repr__(self):  # noqa: D105
            return "weird"

    assert learning_event_service.emit(
        db, actor_id=user.id, verb="test.weird", result={"obj": Weird()}
    ) is None
    db.commit()

    assert learning_event_service.emit(
        None, actor_id=user.id, verb="test.no_session"
    ) is None


# ── 模块 15：预警 pipeline ─────────────────────────────────────


def test_alert_pipeline_scan_generates_once_per_day(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="预警学生")
    s_headers = _login(client, student)
    t_headers = _login(client, teacher)

    for _ in range(3):
        assert _apply_leave(api, s_headers).status_code == 200

    first = alert_pipeline_service.scan(db, force=True)
    assert first["created"] == 1, first
    assert any(m["rule"] == "leave_frequent" for m in first["matched"])

    task = (
        db.query(TeacherTask)
        .filter(
            TeacherTask.student_id == student.id,
            TeacherTask.rule_code == "leave_frequent",
        )
        .first()
    )
    assert task is not None
    assert task.teacher_id == teacher.id  # 自动分配给辅导员
    assert "频繁请假" in task.title

    # 幂等：同规则同学生当日再扫描不重复生成
    second = alert_pipeline_service.scan(db, force=True)
    assert second["created"] == 0

    # 教师端任务列表能看到该预警任务
    listed = api.get("/api/teacher-tasks", headers=t_headers).json()
    assert any(t["rule_code"] == "leave_frequent" for t in listed)


def test_alert_pipeline_rules_configurable(make_user, db):
    """规则可配置：通过 SystemSetting 覆盖后，新规则立即生效。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="规则学生")

    learning_event_service.emit(db, actor_id=student.id, verb="leave.apply")
    learning_event_service.emit(db, actor_id=student.id, verb="leave.apply")
    db.commit()

    custom = [
        {
            "code": "leave_twice",
            "name": "请假偏多",
            "verb": "leave.apply",
            "threshold": 2,
            "window_days": 30,
            "metric_label": "近 30 天请假次数",
            "due_in_days": 2,
        }
    ]
    result = alert_pipeline_service.scan(db, force=True, rules=custom)
    assert result["created"] == 1
    task = db.query(TeacherTask).filter(TeacherTask.student_id == student.id).first()
    assert task.rule_code == "leave_twice"
    assert "请假偏多" in task.title

    # 清理规则配置，避免污染其它用例
    from app.models.setting import SystemSetting

    db.query(SystemSetting).filter(SystemSetting.key == alert_pipeline_service.RULES_KEY).delete()
    db.commit()


def test_alert_pipeline_skips_without_tutor(make_user, db):
    """无辅导员的学生无处派单，跳过。"""
    student = make_user(role=UserRole.STUDENT, name="无导师学生")
    for _ in range(3):
        learning_event_service.emit(db, actor_id=student.id, verb="leave.apply")
    db.commit()

    result = alert_pipeline_service.scan(db, force=True)
    assert result["created"] == 0
    assert db.query(TeacherTask).filter(TeacherTask.student_id == student.id).count() == 0


# ── 模块 13：AI 学情助手 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_student_insight_is_traceable_and_degrades(make_user, db, monkeypatch):
    """建议必须可溯源；LLM 不可用时降级为规则建议。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="诊断学生")

    for _ in range(3):
        learning_event_service.emit(db, actor_id=student.id, verb="leave.apply")
    db.add(
        AIDialogSummary(
            student_id=student.id,
            summary="情绪波动",
            level=CrisisLevel.MODERATE,
            resolved=False,
        )
    )
    db.commit()

    # 强制 LLM 不可用 → 必须降级且不抛错
    def _boom():
        raise RuntimeError("LLM 不可用")

    monkeypatch.setattr("app.services.llm_service._get_client", _boom)

    insight = await student_insight_service.get_insight(db, student.id)
    # 只有学情事件 + 未处理中度预警（无真实请假记录）→ 中风险
    assert insight["profile"]["risk_level"] == "medium"
    assert any("危机" in r for r in insight["profile"]["risk_reasons"])
    # 证据清单可溯源：每条指标都有 source / label / value
    assert insight["profile"]["evidence"]
    assert all({"source", "label", "value"} <= set(e.keys()) for e in insight["profile"]["evidence"])
    assert insight["degraded"] is True
    assert insight["advice"]


def test_student_insight_to_task(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="转任务学生")
    headers = _login(client, teacher)

    resp = api.post(
        f"/api/teacher/students/{student.id}/insight/task",
        json={"advice": "建议本周约谈一次", "risk_level": "high"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    task = resp.json()
    assert task["source_type"] == "care_plan"
    assert task["student_id"] == student.id
    assert task["student_name"] == student.name


# ── 模块 14：审批流程引擎 ──────────────────────────────────────


def test_workflow_engine_full_flow(client, api, make_user, db):
    admin = make_user(role=UserRole.ADMIN)
    teacher = make_user(role=UserRole.TEACHER)
    a_headers = _login(client, admin)
    t_headers = _login(client, teacher)

    # 新增一种审批类型：无需改代码，仅登记节点 JSON
    defn = api.post(
        "/api/workflows/defs",
        json={
            "code": "material_approve",
            "name": "材料归档审批",
            "biz_type": "material",
            "nodes": [
                {"key": "tutor", "name": "辅导员初审", "approver_role": "teacher"},
                {"key": "admin", "name": "管理员终审", "approver_role": "admin"},
            ],
        },
        headers=a_headers,
    )
    assert defn.status_code == 200, defn.text
    assert len(defn.json()["nodes"]) == 2

    # 重复编码被拒
    dup = api.post(
        "/api/workflows/defs",
        json={"code": "material_approve", "name": "重复", "nodes": [{"key": "a", "name": "A"}]},
        headers=a_headers,
    )
    assert dup.status_code == 400

    started = api.post(
        "/api/workflows/instances",
        json={"def_code": "material_approve", "biz_type": "material", "biz_id": 123},
        headers=t_headers,
    )
    assert started.status_code == 200, started.text
    body = started.json()
    instance_id = body["id"]
    assert body["status"] == "running"
    assert body["current_node"]["key"] == "tutor"

    first = api.post(
        f"/api/workflows/instances/{instance_id}/approve",
        json={"comment": "初审通过"},
        headers=t_headers,
    )
    assert first.json()["status"] == "running"
    assert first.json()["current_node"]["key"] == "admin"

    second = api.post(
        f"/api/workflows/instances/{instance_id}/approve",
        json={"comment": "终审通过"},
        headers=a_headers,
    )
    assert second.json()["status"] == "approved"

    # 已结束流程不可再操作
    again = api.post(
        f"/api/workflows/instances/{instance_id}/approve", json={}, headers=a_headers
    )
    assert again.status_code == 400

    # 历史可追溯：发起 + 两次审批
    history = api.get("/api/workflows/instances", params={"mine": False}, headers=a_headers).json()
    target = next(i for i in history if i["id"] == instance_id)
    assert [h["action"] for h in target["history"]] == ["start", "approve", "approve"]


def test_workflow_reject_and_cancel(client, api, make_user, db):
    admin = make_user(role=UserRole.ADMIN)
    teacher = make_user(role=UserRole.TEACHER)
    a_headers = _login(client, admin)
    t_headers = _login(client, teacher)

    api.post(
        "/api/workflows/defs",
        json={
            "code": "leave_approve_wf",
            "name": "请假审批流程",
            "biz_type": "leave",
            "nodes": [{"key": "tutor", "name": "辅导员审批"}],
        },
        headers=a_headers,
    )

    # 驳回
    r1 = api.post(
        "/api/workflows/instances",
        json={"def_code": "leave_approve_wf", "biz_id": 1},
        headers=t_headers,
    ).json()["id"]
    rejected = api.post(
        f"/api/workflows/instances/{r1}/reject", json={"comment": "材料不全"}, headers=t_headers
    )
    assert rejected.json()["status"] == "rejected"
    assert db.get(WorkflowInstance, r1).status.value == "rejected"

    # 撤销（发起人本人）
    r2 = api.post(
        "/api/workflows/instances",
        json={"def_code": "leave_approve_wf", "biz_id": 2},
        headers=t_headers,
    ).json()["id"]
    cancelled = api.post(f"/api/workflows/instances/{r2}/cancel", json={}, headers=t_headers)
    assert cancelled.json()["status"] == "cancelled"

    # 非发起人且非管理员不可撤销
    r3 = api.post(
        "/api/workflows/instances",
        json={"def_code": "leave_approve_wf", "biz_id": 3},
        headers=t_headers,
    ).json()["id"]
    other = make_user(role=UserRole.TEACHER)
    denied = api.post(
        f"/api/workflows/instances/{r3}/cancel", json={}, headers=_login(client, other)
    )
    assert denied.status_code == 400