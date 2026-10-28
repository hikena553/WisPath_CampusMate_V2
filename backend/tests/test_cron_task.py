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
