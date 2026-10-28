"""Agent 定时任务：周期计算、到期执行、调度扫描。

设计要点（specs/2026-10-29-agent-cron-task-design.md §3）：
- next_run_at 一律 UTC 落库；hour/minute/weekday 是学生口中的北京时间（UTC+8），
  计算时先按北京时间定位触发点，再换算回 UTC，避免触发时刻整体偏移 8 小时。
- 调度循环「先推进 next_run_at 并提交，再执行」——崩溃/异常最多漏跑一轮，
  绝不会把同一次到期执行两遍。
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationMessage
from app.models.cron_task import AgentCronTask, CronScheduleKind
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)

BEIJING_TZ = timezone(timedelta(hours=8))
MAX_TASKS_PER_USER = 10
# 进程内防重入：调度循环与 run-now 并发触发同一任务时，后到者直接跳过
_running_ids: set[int] = set()

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _as_utc(dt: datetime) -> datetime:
    """SQLite 不保留时区，读回的 naive datetime 一律视为 UTC。"""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def compute_next_run(task: AgentCronTask, now: datetime | None = None) -> datetime:
    """计算下一次触发时间（UTC）。daily/weekly 的触发时刻按北京时间解释。"""
    now = _as_utc(now) if now else datetime.now(timezone.utc)
    if task.schedule_kind == CronScheduleKind.INTERVAL:
        hours = task.interval_hours if task.interval_hours and task.interval_hours >= 1 else 24
        return now + timedelta(hours=hours)

    bj_now = now.astimezone(BEIJING_TZ)
    # 显式 is None 判断而非 `or` 兜底：hour=0（午夜）是合法值，不能被吞成 8
    target = bj_now.replace(
        hour=8 if task.hour is None else task.hour,
        minute=0 if task.minute is None else task.minute,
        second=0,
        microsecond=0,
    )
    if task.schedule_kind == CronScheduleKind.WEEKLY:
        target += timedelta(days=(task.weekday - bj_now.weekday()) % 7)
    if target <= bj_now:
        target += timedelta(days=1 if task.schedule_kind == CronScheduleKind.DAILY else 7)
    return target.astimezone(timezone.utc)


def describe_schedule(task: AgentCronTask) -> str:
    """把周期翻译成学生看得见的人话（列表页/通知/工具返回共用）。"""
    # 显式 is None 判断而非 `or` 兜底：hour=0（午夜）是合法值，不能被吞成 8
    hm = f"{0 if task.hour is None else task.hour:02d}:{0 if task.minute is None else task.minute:02d}"
    if task.schedule_kind == CronScheduleKind.DAILY:
        return f"每天 {hm}"
    if task.schedule_kind == CronScheduleKind.WEEKLY:
        # 越界/None 的 weekday 不再 IndexError，兜底为周一
        wd = task.weekday if task.weekday is not None and 0 <= task.weekday <= 6 else 0
        return f"每{WEEKDAY_NAMES[wd]} {hm}"
    return f"每 {task.interval_hours or 24} 小时"


def _to_int(v) -> int | None:
    """宽容取整：非法输入（'abc'/None/浮串等）返回 None，交由调用方给错误文案。"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def validate_schedule_args(args: dict) -> tuple[dict, str | None]:
    """校验创建参数，返回 (归一化参数, 错误信息)。错误信息为 None 表示通过。"""
    kind = args.get("schedule_kind")
    if kind not in (k.value for k in CronScheduleKind):
        return {}, f"schedule_kind 必须是 daily/weekly/interval 之一，收到：{kind}"
    kind = CronScheduleKind(kind)
    out: dict = {"schedule_kind": kind}
    if kind in (CronScheduleKind.DAILY, CronScheduleKind.WEEKLY):
        hour, minute = _to_int(args.get("hour")), _to_int(args.get("minute"))
        if hour is None or minute is None or not (0 <= hour <= 23) or not (0 <= minute <= 59):
            return {}, "daily/weekly 周期需要合法的 hour（0-23）与 minute（0-59）"
        out["hour"], out["minute"] = hour, minute
    if kind == CronScheduleKind.WEEKLY:
        weekday = _to_int(args.get("weekday"))
        if weekday is None or not (0 <= weekday <= 6):
            return {}, "weekly 周期需要 weekday（0=周一 … 6=周日）"
        out["weekday"] = weekday
    if kind == CronScheduleKind.INTERVAL:
        hours = _to_int(args.get("interval_hours"))
        if hours is None or not (1 <= hours <= 720):
            return {}, "interval 周期需要 interval_hours（1-720 小时）"
        out["interval_hours"] = hours
    return out, None
