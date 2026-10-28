"""Agent 定时任务：周期计算 / 工具 / 执行内核 / 管理 API。"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.cron_task import AgentCronTask, CronScheduleKind
from app.services.cron_task_service import (
    compute_next_run,
    describe_schedule,
    validate_schedule_args,
)

BJ = timezone(timedelta(hours=8))
UTC = timezone.utc


def _task(kind, **kw):
    return AgentCronTask(schedule_kind=kind, **kw)


# ---------- compute_next_run ----------

def test_daily_before_trigger_same_day():
    # 2026-10-29 是周四；北京 07:00 → 当天 08:30 北京 == 00:30 UTC
    now = datetime(2026, 10, 29, 7, 0, tzinfo=BJ)
    t = _task(CronScheduleKind.DAILY, hour=8, minute=30)
    assert compute_next_run(t, now=now) == datetime(2026, 10, 29, 0, 30, tzinfo=UTC)


def test_daily_after_trigger_next_day():
    now = datetime(2026, 10, 29, 9, 0, tzinfo=BJ)
    t = _task(CronScheduleKind.DAILY, hour=8, minute=30)
    assert compute_next_run(t, now=now) == datetime(2026, 10, 30, 0, 30, tzinfo=UTC)


def test_weekly_today_not_past():
    now = datetime(2026, 10, 29, 8, 0, tzinfo=BJ)  # 周四
    t = _task(CronScheduleKind.WEEKLY, weekday=3, hour=9, minute=0)
    assert compute_next_run(t, now=now) == datetime(2026, 10, 29, 1, 0, tzinfo=UTC)


def test_weekly_same_day_past_rolls_next_week():
    now = datetime(2026, 10, 29, 12, 0, tzinfo=BJ)  # 周四 12:00，每周四 9:00 已过
    t = _task(CronScheduleKind.WEEKLY, weekday=3, hour=9, minute=0)
    assert compute_next_run(t, now=now) == datetime(2026, 11, 5, 1, 0, tzinfo=UTC)


def test_interval_adds_hours():
    now = datetime(2026, 10, 29, 3, 0, tzinfo=UTC)
    t = _task(CronScheduleKind.INTERVAL, interval_hours=6)
    assert compute_next_run(t, now=now) == datetime(2026, 10, 29, 9, 0, tzinfo=UTC)


# ---------- describe_schedule ----------

def test_describe_schedule():
    assert describe_schedule(_task(CronScheduleKind.DAILY, hour=8, minute=30)) == "每天 08:30"
    assert describe_schedule(_task(CronScheduleKind.WEEKLY, weekday=2, hour=8, minute=5)) == "每周三 08:05"
    assert describe_schedule(_task(CronScheduleKind.INTERVAL, interval_hours=2)) == "每 2 小时"


# ---------- validate_schedule_args / 回归 ----------

def test_daily_midnight_not_swallowed():
    # 回归：hour=0 曾被 `or 8` 兜底吞成 8 点；午夜 00:30 北京已过 → 明天 00:30 北京 == 16:30 UTC
    now = datetime(2026, 10, 29, 7, 0, tzinfo=BJ)
    t = _task(CronScheduleKind.DAILY, hour=0, minute=30)
    assert compute_next_run(t, now=now) == datetime(2026, 10, 29, 16, 30, tzinfo=UTC)


def test_weekly_earlier_weekday_rolls_forward():
    # 周四 12:00 建「每周一 09:00」→ 下周一 2026-11-02 09:00 北京 == 01:00 UTC，中间不回滚到本周
    now = datetime(2026, 10, 29, 12, 0, tzinfo=BJ)  # 周四
    t = _task(CronScheduleKind.WEEKLY, weekday=0, hour=9, minute=0)
    assert compute_next_run(t, now=now) == datetime(2026, 11, 2, 1, 0, tzinfo=UTC)


def test_validate_rejects_unknown_kind():
    out, err = validate_schedule_args({"schedule_kind": "hourly"})
    assert out == {} and err is not None and "daily/weekly/interval" in err


def test_validate_bad_hour_returns_error_not_raise():
    # 非法参数必须返回错误字符串而不是抛 ValueError（LLM 澄清回路依赖该契约）
    out, err = validate_schedule_args({"schedule_kind": "daily", "hour": "abc", "minute": 0})
    assert out == {} and err is not None


# ---------- 工具 handler ----------

from app.models.user import UserRole  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.services.tools.cron_task import _create_cron_task, _list_cron_tasks  # noqa: E402
from app.services.cron_task_service import MAX_TASKS_PER_USER  # noqa: E402


def _args(**over):
    a = {"name": "早报汇总", "prompt": "汇总今日校园要闻", "schedule_kind": "daily", "hour": 8, "minute": 30}
    a.update(over)
    return a


def test_tool_create_ok(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, _args(), student)
    assert out["success"] is True
    task = db.query(AgentCronTask).filter(AgentCronTask.user_id == student.id).first()
    assert task is not None and task.conversation_id > 0
    conv = db.query(Conversation).filter(Conversation.id == task.conversation_id).first()
    assert conv is not None and conv.title == "早报汇总"
    assert task.next_run_at is not None


def test_tool_create_missing_prompt(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, {"name": "x", "schedule_kind": "daily", "hour": 8, "minute": 0}, student)
    assert out["success"] is False


def test_tool_create_weekly_missing_weekday(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, _args(schedule_kind="weekly", hour=9, minute=0), student)
    assert out["success"] is False


def test_tool_create_limit(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    for i in range(MAX_TASKS_PER_USER):
        assert _create_cron_task(db, _args(name=f"任务{i}"), student)["success"] is True
    out = _create_cron_task(db, _args(name="超额"), student)
    assert out["success"] is False
    assert str(MAX_TASKS_PER_USER) in out["message"]


def test_tool_list(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    _create_cron_task(db, _args(), student)
    out = _list_cron_tasks(db, {}, student)
    assert out["success"] is True and len(out["tasks"]) == 1
    assert out["tasks"][0]["schedule"] == "每天 08:30"


def test_tool_create_weekly_ok(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, _args(schedule_kind="weekly", weekday=2, hour=9, minute=5), student)
    assert out["success"] is True
    assert out["task"]["schedule"] == "每周三 09:05"
    # 对外载荷必须带北京时间偏移，否则 LLM 会把 UTC 裸串当学生本地时间转述
    assert out["task"]["next_run_at"].endswith("+08:00")


def test_tool_create_interval_ok(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, _args(schedule_kind="interval", interval_hours=6), student)
    assert out["success"] is True
    assert out["task"]["schedule"] == "每 6 小时"


def test_tool_create_string_hour_minute(db, make_user):
    # 回归护栏：LLM 可能传字符串数字，_to_int 宽容取整须经 handler 全链路生效
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, _args(hour="9", minute="30"), student)
    assert out["success"] is True
    assert out["task"]["schedule"] == "每天 09:30"


# ---------- 调度执行内核 ----------

import asyncio  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.conversation import ConversationMessage  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.services import cron_task_service as svc  # noqa: E402


@pytest.fixture()
def due_task(db, make_user):
    """一条已到期（next_run_at 早于当前）的启用任务。"""
    student = make_user(role=UserRole.STUDENT)
    conv = Conversation(user_id=student.id, title="到期任务")
    db.add(conv)
    db.flush()
    t = AgentCronTask(
        user_id=student.id, name="早报", prompt="干点活",
        schedule_kind=CronScheduleKind.DAILY, hour=8, minute=0,
        conversation_id=conv.id,
        next_run_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture()
def fake_agent_reply(monkeypatch):
    """把 _run_agent_reply 换成假执行：记录调用并模拟 chat 的落库行为。"""
    calls = []

    async def _fake(prompt, user, conv_id):
        calls.append({"prompt": prompt, "user_id": user.id, "conv_id": conv_id})
        s = SessionLocal()
        try:
            s.add(ConversationMessage(conversation_id=conv_id, role="assistant", content="模拟结果"))
            s.commit()
        finally:
            s.close()
        return "模拟结果"

    monkeypatch.setattr(svc, "_run_agent_reply", _fake)
    return calls


def test_execute_due_runs_and_notifies(db, due_task, fake_agent_reply):
    before = due_task.next_run_at
    ran = asyncio.run(svc.execute_due_tasks())
    assert ran == 1

    db.expire_all()
    t = db.query(AgentCronTask).filter(AgentCronTask.id == due_task.id).first()
    assert t.next_run_at > before          # 先推进再执行
    assert t.last_run_at is not None
    notif = (
        db.query(Notification)
        .filter(Notification.user_id == due_task.user_id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notif is not None and notif.title == "早报" and "模拟结果" in notif.content
    assert f"conv={due_task.conversation_id}" in (notif.link or "")
    msgs = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == due_task.conversation_id)
        .all()
    )
    assert {m.role for m in msgs} >= {"user", "assistant"}
    assert fake_agent_reply[0]["prompt"] == "干点活"


def test_execute_due_skips_not_due(db, due_task, fake_agent_reply):
    db.query(AgentCronTask).filter(AgentCronTask.id == due_task.id).update(
        {"next_run_at": datetime.now(UTC) + timedelta(hours=1)}
    )
    db.commit()
    assert asyncio.run(svc.execute_due_tasks()) == 0


def test_execute_failure_still_advances(db, due_task, monkeypatch):
    async def _boom(prompt, user, conv_id):
        raise RuntimeError("LLM 超时")

    monkeypatch.setattr(svc, "_run_agent_reply", _boom)
    before = due_task.next_run_at
    assert asyncio.run(svc.execute_due_tasks()) == 0
    db.expire_all()
    t = db.query(AgentCronTask).filter(AgentCronTask.id == due_task.id).first()
    assert t.next_run_at > before          # 失败也不阻塞下个周期
    notif = (
        db.query(Notification)
        .filter(Notification.user_id == due_task.user_id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notif is not None and "失败" in notif.title


def test_execute_once_reentrant_guard(db, due_task, fake_agent_reply):
    svc._running_ids.add(due_task.id)
    try:
        assert asyncio.run(svc.execute_once(due_task.id)) is False
    finally:
        svc._running_ids.discard(due_task.id)


def test_execute_once_skips_disabled(db, make_user):
    student = make_user(role=UserRole.STUDENT)
    conv = Conversation(user_id=student.id, title="停用")
    db.add(conv)
    db.flush()
    t = AgentCronTask(
        user_id=student.id, name="停用任务", prompt="x",
        schedule_kind=CronScheduleKind.INTERVAL, interval_hours=1,
        conversation_id=conv.id, enabled=False,
        next_run_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    assert asyncio.run(svc.execute_once(t.id)) is False
