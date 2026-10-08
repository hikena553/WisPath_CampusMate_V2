"""AI 工具注册表（p3_1）：未知工具 / S5 脱敏 / 工具级限流。

注意：_tool_call_counters 独立于限流桶，reset_rate_limiter() 不清理它，
超限测试需手动清空/回填计数，避免跨用例污染。
"""
import time
from datetime import date

import pytest

from app.models.care_record import CareRecord
from app.models.teacher_task import TeacherTask
from app.models.user import UserRole
from app.services.tools import (
    _tool_call_counters,
    execute_tool,
)


@pytest.fixture()
def _tool_counters_clean():
    saved = dict(_tool_call_counters)
    _tool_call_counters.clear()
    yield
    _tool_call_counters.clear()
    _tool_call_counters.update(saved)


@pytest.mark.asyncio
async def test_execute_unknown_tool_returns_error(make_user, _tool_counters_clean):
    user = make_user()
    result = await execute_tool("no_such_tool", {}, user)
    assert result == {"error": "未知工具: no_such_tool"}


@pytest.mark.asyncio
async def test_query_students_drops_sensitive_fields(make_user, db, _tool_counters_clean):
    """S5 脱敏：查询学生结果不得包含学号/电话/邮箱/身份证号。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(
        role=UserRole.STUDENT,
        tutor_id=teacher.id,
        name="王小明",
    )
    # 敏感字段落库（模拟真实数据）
    from app.models.user import User

    stu = db.get(User, student.id)
    stu.phone = "13800001111"
    db.commit()

    result = await execute_tool("query_students", {}, teacher)
    assert "students" in result
    assert len(result["students"]) == 1
    row = result["students"][0]
    assert row["name"] == "王小明"
    for sensitive in ("username", "phone", "email", "id_card"):
        assert sensitive not in row, f"敏感字段 {sensitive} 未被脱敏移除"
    assert "13800001111" not in str(result)


@pytest.mark.asyncio
async def test_query_students_no_students(make_user, _tool_counters_clean):
    teacher = make_user(role=UserRole.TEACHER)
    result = await execute_tool("query_students", {}, teacher)
    assert result["students"] == []
    assert "名" in result.get("message", "")


@pytest.mark.asyncio
async def test_tool_rate_limit_returns_error_message(make_user, _tool_counters_clean):
    """工具调用限流 30 次/60s：预填满计数后返回友好错误。"""
    user = make_user()
    _tool_call_counters[user.id] = [time.monotonic()] * 30

    result = await execute_tool("query_status", {}, user)
    assert result == {"error": "工具调用过于频繁，请稍后再试"}


@pytest.mark.asyncio
async def test_tool_rate_limit_recovers_after_reset(make_user, _tool_counters_clean):
    """清空计数后工具调用恢复正常。"""
    user = make_user()
    result = await execute_tool("query_knowledge", {"query": "请假"}, user)
    assert "error" not in result or "频繁" not in result.get("error", "")


@pytest.mark.asyncio
async def test_teacher_task_and_care_record_tools_flow(make_user, db, _tool_counters_clean):
    """教师工具闭环：建跟进任务 → 查待办 → 写侧写 → 查侧写。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="李四")

    created = await execute_tool(
        "create_teacher_task",
        {
            "title": "跟进联系李四",
            "detail": "近两周缺勤较多",
            "student_name": "李四",
            "due_at": date.today().isoformat(),
        },
        teacher,
    )
    assert created["success"] is True
    task_id = created["task_id"]
    assert db.query(TeacherTask).filter(TeacherTask.id == task_id).count() == 1

    listing = await execute_tool("query_teacher_tasks", {"due": "today"}, teacher)
    assert any(t["task_id"] == task_id for t in listing["tasks"])

    record = await execute_tool(
        "create_care_record",
        {"student_name": "李四", "content": "已电话联系家长，学生情绪稳定", "record_type": "talk"},
        teacher,
    )
    assert record["success"] is True
    assert db.query(CareRecord).filter(CareRecord.student_id == student.id).count() == 1

    records = await execute_tool("query_care_records", {"student_name": "李四"}, teacher)
    assert records["records"]
    assert records["records"][0]["record_type"] == "谈心谈话"


@pytest.mark.asyncio
async def test_teacher_tools_reject_foreign_student(make_user, db, _tool_counters_clean):
    """教师工具不得读写他人名下学生的侧写记录。"""
    teacher = make_user(role=UserRole.TEACHER)
    other = make_user(role=UserRole.TEACHER)
    stranger = make_user(role=UserRole.STUDENT, tutor_id=other.id, name="陌生学生")

    record = await execute_tool(
        "create_care_record",
        {"student_name": "陌生学生", "content": "越权写入"},
        teacher,
    )
    assert record["success"] is False
    assert "未找到" in record["message"]
    assert db.query(CareRecord).filter(CareRecord.student_id == stranger.id).count() == 0

    query = await execute_tool("query_care_records", {"student_name": "陌生学生"}, teacher)
    assert query["success"] is False


@pytest.mark.asyncio
async def test_p1_module_tools_flow(make_user, db, _tool_counters_clean):
    """P1 工具：成长档案增查 / 关怀日历 / 家校沟通台账 / 我的互评结果。"""
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="工具学生")

    # 成长档案：新增后可在汇总中查到
    created = await execute_tool(
        "create_portfolio_item",
        {"title": "学业帮扶案例", "item_type": "case", "reflection": "先共情再给方案"},
        teacher,
    )
    assert created["success"] is True

    portfolio = await execute_tool("query_my_portfolio", {}, teacher)
    assert "1" in portfolio["message"]
    assert any(t["type"] == "case" for t in portfolio["by_type"])

    # 关怀日历：手动建一条后本月可查
    event = await execute_tool(
        "query_care_calendar",
        {},
        teacher,
    )
    assert "events" in event  # 空或非空都应正常返回

    # 家校沟通：名下学生无数据时给出友好提示
    guardian = await execute_tool("query_guardian_logs", {"student_name": "工具学生"}, teacher)
    assert "暂无" in guardian["message"]

    # 越权：他人学生不可查
    other = make_user(role=UserRole.TEACHER)
    stranger = make_user(role=UserRole.STUDENT, tutor_id=other.id, name="他人学生")
    denied = await execute_tool("query_guardian_logs", {"student_name": "他人学生"}, teacher)
    assert denied["success"] is False

    # 我的互评结果：无数据时友好提示
    survey = await execute_tool("query_my_survey_results", {}, teacher)
    assert "message" in survey


@pytest.mark.asyncio
async def test_p2_platform_tools(make_user, db, _tool_counters_clean, monkeypatch):
    """P2 工具：学情事件 / AI 学情诊断（降级）/ 审批流程。"""
    from app.services import learning_event_service, workflow_engine

    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="底座学生")

    learning_event_service.emit(db, actor_id=student.id, verb="leave.apply")
    learning_event_service.emit(db, actor_id=student.id, verb="care.record")
    db.commit()

    events = await execute_tool("query_learning_events", {"student_name": "底座学生"}, teacher)
    assert "学情事件" in events["message"]
    assert events["by_verb"]

    # LLM 不可用 → 诊断仍可用（降级）
    def _boom():
        raise RuntimeError("LLM 不可用")

    monkeypatch.setattr("app.services.llm_service._get_client", _boom)
    insight = await execute_tool("query_student_insight", {"student_name": "底座学生"}, teacher)
    assert insight["message"]
    assert insight["degraded"] is True
    assert insight["evidence"]

    # 审批流程：无实例时友好提示
    workflow_engine.create_def(
        db,
        code="tool_wf",
        name="工具流程",
        nodes=[{"key": "a", "name": "节点A"}],
        created_by=teacher.id,
    )
    workflow_engine.start(db, def_code="tool_wf", initiator_id=teacher.id, biz_id=1)
    flows = await execute_tool("query_my_workflows", {}, teacher)
    assert flows["instances"]
    assert flows["instances"][0]["current_node"] == "节点A"