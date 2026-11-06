"""写入类 AI 工具的真实落库回归。

背景：请假 / 成长档案两个工具把 ISO 字符串直接塞进 SQLAlchemy `Date` 列，
SQLite 方言只接受 Python date，commit 时抛
`TypeError: SQLite Date type only accepts Python date objects`，
被 chat() 的兜底捕获后变成「系统暂时不可用」，学生侧表现为「什么工具都用不了」。

这里用真实的 execute_tool + 测试库跑 happy path：只要有人再把字符串写回 Date 列，
用例会直接失败，而不是等到线上由模型去解释错误。
"""
from datetime import date, timedelta

import pytest

from app.models.growth import GrowthRecord
from app.models.leave import LeaveRequest
from app.models.service import ServiceTicket
from app.models.user import UserRole
from app.services.tools import _tool_call_counters, execute_tool


@pytest.fixture()
def _tool_counters_clean():
    saved = dict(_tool_call_counters)
    _tool_call_counters.clear()
    yield
    _tool_call_counters.clear()
    _tool_call_counters.update(saved)


@pytest.fixture()
def _write_cleanup(db):
    """只清本文件造的数据，不动 seed 内容（测试库是复用的 sqlite 文件）。"""
    yield
    db.query(GrowthRecord).filter(
        GrowthRecord.title.in_(["蓝桥杯省赛", "优秀学生"])
    ).delete(synchronize_session=False)
    db.query(ServiceTicket).filter(ServiceTicket.title == "补办校园卡").delete(
        synchronize_session=False
    )
    db.commit()


@pytest.mark.asyncio
async def test_create_leave_persists_date(make_user, db, _tool_counters_clean):
    """请假：字符串日期必须被转成 date 再落库，且能在请假列表里查到。"""
    student = make_user(role=UserRole.STUDENT)
    today = date.today()
    start = (today + timedelta(days=1)).isoformat()
    end = (today + timedelta(days=2)).isoformat()

    result = await execute_tool(
        "create_leave",
        {"start_date": start, "end_date": end, "reason": "发烧就医", "leave_type": "sick"},
        student,
    )

    assert "error" not in result, result
    assert result.get("success") is True, result

    leave = db.query(LeaveRequest).filter(LeaveRequest.student_id == student.id).first()
    assert leave is not None
    # 读回来必须已经是 date（而不是字符串），前端/审批流按日期比较才不会错
    assert isinstance(leave.start_date, date)
    assert leave.start_date.isoformat() == start
    assert leave.end_date.isoformat() == end
    assert leave.leave_type.value == "sick"


@pytest.mark.asyncio
async def test_create_leave_rejects_past_date(make_user, _tool_counters_clean):
    """业务校验不能被日期解析改动打乱：昨天请假仍然要拒绝。"""
    student = make_user(role=UserRole.STUDENT)
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    result = await execute_tool(
        "create_leave",
        {"start_date": yesterday, "end_date": yesterday, "reason": "测试"},
        student,
    )

    assert result.get("success") is False
    assert "不能早于今天" in result["message"]


@pytest.mark.asyncio
async def test_confirm_growth_record_persists_date(make_user, db, _tool_counters_clean, _write_cleanup):
    """成长档案：模型给的日期是字符串，落库时必须转 date。"""
    student = make_user(role=UserRole.STUDENT)

    result = await execute_tool(
        "confirm_growth_record",
        {"record_type": "competition", "title": "蓝桥杯省赛", "date": "2026-05-01",
         "competition_level": "provincial", "organizer": "组委会"},
        student,
    )

    assert "error" not in result, result
    assert result.get("success") is True, result

    record = db.query(GrowthRecord).filter(GrowthRecord.student_id == student.id).first()
    assert record is not None
    assert isinstance(record.date, date)
    assert record.date.isoformat() == "2026-05-01"


@pytest.mark.asyncio
async def test_confirm_growth_record_bad_date_is_friendly(make_user, _tool_counters_clean):
    """日期格式错误要给模型可读的提示，而不是抛异常打断整轮对话。"""
    student = make_user(role=UserRole.STUDENT)

    result = await execute_tool(
        "confirm_growth_record",
        {"record_type": "honor", "title": "优秀学生", "date": "去年五月"},
        student,
    )

    assert result.get("success") is False
    assert "YYYY-MM-DD" in result["message"]


@pytest.mark.asyncio
async def test_submit_service_request_persists(make_user, db, _tool_counters_clean, _write_cleanup):
    """办事申请：type 是 SAEnum，必须是合法枚举值，否则落库抛 LookupError。"""
    student = make_user(role=UserRole.STUDENT)

    result = await execute_tool(
        "submit_service_request",
        {"title": "补办校园卡", "content": "校园卡丢失，申请补办", "request_type": "certificate"},
        student,
    )

    assert "error" not in result, result
    assert result.get("success") is True, result

    # 按 id 取自己那张：sqlite 会复用主键，按 applicant_id 查可能命中文档残留的旧工单
    ticket = db.get(ServiceTicket, result["ticket_id"])
    assert ticket is not None
    assert ticket.type.value == "certificate"


@pytest.mark.asyncio
async def test_submit_service_request_bad_type_is_friendly(make_user, _tool_counters_clean):
    """模型传了枚举外的值时给可读提示，不要抛异常打断对话。"""
    student = make_user(role=UserRole.STUDENT)

    result = await execute_tool(
        "submit_service_request",
        {"title": "随便问问", "content": "测试", "request_type": "other"},
        student,
    )

    assert result.get("success") is False
    assert "certificate" in result["message"]
