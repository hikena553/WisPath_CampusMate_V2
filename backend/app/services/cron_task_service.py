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
# 进程内防重入：调度循环与 run-now 并发触发同一任务时，后到者直接跳过。
# 仅单进程有效：多 worker 部署下 advance-then-execute 不是原子声明，需 DB 级抢占防重复执行
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


def to_beijing_iso(dt: datetime) -> str:
    """统一对外序列化：UTC 存储值转北京时间 ISO 串（带 +08:00），供工具载荷与管理 API 共用。"""
    return _as_utc(dt).astimezone(BEIJING_TZ).isoformat()


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


def _notify(db: Session, user_id: int, title: str, content: str, conversation_id: int) -> None:
    from app.api.notification import create_notification

    create_notification(
        db,
        user_id=user_id,
        title=title[:200],
        content=content,
        link=f"/student/agent?conv={conversation_id}",
    )


async def _run_agent_reply(prompt: str, user: User, conv_id: int) -> str:
    """无头跑一轮 agent：消费流式生成器；回复由 chat 内部落库到会话。"""
    from app.services import agent_service

    reply = ""
    async for event in agent_service.chat(prompt, [], user, conv_id=conv_id):
        if isinstance(event, dict):
            if event.get("type") == "content":
                reply += event.get("content", "")
        elif isinstance(event, str) and "__SUGGESTIONS__" not in event:
            reply += event
    return reply


async def execute_once(task_id: int) -> bool:
    """执行单个任务：占坑防重入 → 落 user 消息 → 消费 agent 流 → 通知送达。

    返回 True 表示实际执行；False 表示正在执行/任务不可用。
    next_run_at 的推进由调度方（execute_due_tasks）负责，这里只管跑。
    """
    if task_id in _running_ids:
        return False
    _running_ids.add(task_id)
    db = SessionLocal()
    try:
        task = db.query(AgentCronTask).filter(AgentCronTask.id == task_id).first()
        if not task or not task.enabled:
            return False
        user = db.query(User).filter(User.id == task.user_id).first()
        conv = db.query(Conversation).filter(Conversation.id == task.conversation_id).first()
        if not user or not conv:
            logger.warning("[定时任务] 跳过：用户或会话不存在 task_id=%s", task_id)
            return False

        db.add(ConversationMessage(
            conversation_id=task.conversation_id,
            role="user",
            content=f"【定时任务】{task.name}：{task.prompt}",
        ))
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()

        try:
            reply = await _run_agent_reply(task.prompt, user, task.conversation_id)
        except Exception:
            logger.exception("[定时任务] 执行失败 task_id=%s name=%s", task_id, task.name)
            _notify(db, task.user_id, f"定时任务「{task.name}」执行失败", "AI 执行出错，下个周期会自动重试。", task.conversation_id)
            return False

        task.last_run_at = datetime.now(timezone.utc)
        db.commit()
        _notify(db, task.user_id, task.name, (reply or "（本次没有产出内容）")[:200], task.conversation_id)
        return True
    finally:
        _running_ids.discard(task_id)
        db.close()


async def execute_due_tasks(now: datetime | None = None) -> int:
    """扫描到期任务并逐个执行，返回实际执行数。

    先把 next_run_at 推进到下一周期点并提交，再执行——即使进程在执行中崩溃，
    这一次到期也只会被消费一次（最多漏跑、不会重复跑）。
    """
    now = _as_utc(now) if now else datetime.now(timezone.utc)
    db = SessionLocal()
    due_ids: list[int] = []
    try:
        rows = (
            db.query(AgentCronTask)
            .filter(AgentCronTask.enabled.is_(True), AgentCronTask.next_run_at <= now)
            .all()
        )
        for task in rows:
            task.next_run_at = compute_next_run(task, now)
            due_ids.append(task.id)
        db.commit()
    finally:
        db.close()

    executed = 0
    for task_id in due_ids:
        try:
            if await execute_once(task_id):
                executed += 1
        except Exception:
            logger.exception("[定时任务] 单任务执行异常 task_id=%s", task_id)
    return executed
