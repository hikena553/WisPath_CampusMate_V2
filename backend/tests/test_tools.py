"""AI 工具注册表（p3_1）：未知工具 / S5 脱敏 / 工具级限流。

注意：_tool_call_counters 独立于限流桶，reset_rate_limiter() 不清理它，
超限测试需手动清空/回填计数，避免跨用例污染。
"""
import time

import pytest

from app.models.user import UserRole
from app.services.tool_registry import (
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