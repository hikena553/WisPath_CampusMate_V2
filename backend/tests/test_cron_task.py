"""Agent 定时任务：周期计算 / 工具 / 执行内核 / 管理 API。"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.cron_task import AgentCronTask, CronScheduleKind
from app.services.cron_task_service import compute_next_run, describe_schedule

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
