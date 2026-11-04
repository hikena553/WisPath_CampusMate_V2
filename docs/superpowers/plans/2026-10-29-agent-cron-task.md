# Agent 定时任务（学生端）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 学生在聊天里让 AI 建周期任务，到点后端自动以学生身份跑一轮 agent，结果落任务专属会话并推站内通知；管理子页支持启停/删除/立即执行。

**Architecture:** 新表 `agent_cron_tasks` + alembic 迁移；`services/cron_task_service.py` 承载周期计算（北京时间解释、UTC 落库）与执行内核（先推进 next_run_at 再执行，防重入）；`tools/` 注册 `create_cron_task` / `list_cron_tasks` 两个学生端工具；`tasks/periodic.py` 挂 60 秒扫描循环；`api/cron_task.py` 提供管理 API；前端 `AgentCronPage.vue` 覆盖式子页（Teleport + Transition subpage）由 ChatPanel 顶栏时钟入口挂载，ChatPanel 支持 `?conv=<id>` 直达会话。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest；Vue3 + Element Plus + Pinia。规格：`docs/superpowers/specs/2026-10-29-agent-cron-task-design.md`。

**仓库约定（每个提交任务的 step 都适用）:**
- 工作区有他人未提交改动，`git add` 只加本任务明确列出的文件，禁止 `git add -A`。
- 后端命令一律 `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest ...`（conftest 自动建 tests/test.db 并跑迁移）。
- 前端构建受沙箱 TMP 限制：`npm run build` 前先 `export TMP="$PWD/.tmpbuild" TEMP="$PWD/.tmpbuild" TMPDIR="$PWD/.tmpbuild"`（目录不存在则先建）。

---

## 文件结构总览

| 动作 | 路径 | 职责 |
| --- | --- | --- |
| Create | `backend/app/models/cron_task.py` | AgentCronTask 模型 + 周期/来源枚举 |
| Modify | `backend/app/models/__init__.py` | 注册新模型 |
| Create | `backend/alembic/versions/m8n9p0q1r2s3_agent_cron_tasks.py` | 建表迁移（down_revision=k2f3a4b5c6d7） |
| Create | `backend/app/services/cron_task_service.py` | 周期计算 / 人话描述 / 校验 / 执行内核 |
| Create | `backend/app/services/tools/cron_task.py` | 工具 handler：创建 / 列表 |
| Modify | `backend/app/services/tools/definitions.py` | 两个工具的 function 定义 |
| Modify | `backend/app/services/tools/dispatcher.py` | handler 分发登记 |
| Modify | `backend/app/tasks/periodic.py` | 60 秒调度循环（TESTING 不启动） |
| Create | `backend/app/schemas/cron_task.py` | Pydantic Out/Update |
| Create | `backend/app/api/cron_task.py` | 管理 API（prefix=/api/cron-tasks） |
| Modify | `backend/app/api/registry.py` | ROUTERS 列表登记 |
| Create | `backend/tests/test_cron_task.py` | 全部后端测试 |
| Create | `frontend/src/api/cronTask.ts` | API client |
| Create | `frontend/src/components/agent/AgentCronPage.vue` | 管理子页 |
| Modify | `frontend/src/components/agent/ChatPanel.vue` | 顶栏时钟入口 + 子页挂载 + ?conv= 直达 |

---

### Task 1: 数据模型与迁移

**Files:**
- Create: `backend/app/models/cron_task.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/m8n9p0q1r2s3_agent_cron_tasks.py`

- [ ] **Step 1: 写模型文件** `backend/app/models/cron_task.py`

```python
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CronScheduleKind(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"


class CronTaskSource(str, enum.Enum):
    CHAT = "chat"
    MANUAL = "manual"


class AgentCronTask(Base):
    """Agent 定时任务：到点由 cron_task_service 以学生身份无头执行一轮 agent。"""

    __tablename__ = "agent_cron_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 每次执行下发给 AI 的指令（不含任务名前缀，落库会话时再加）
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_kind: Mapped[CronScheduleKind] = mapped_column(SAEnum(CronScheduleKind), nullable=False)
    # daily/weekly 的触发时刻；hour/minute/weekday 语义是学生口中的北京时间，落库前换算为 UTC
    hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=周一 … 6=周日
    interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True, index=True)
    # 任务专属会话：每次执行的消息都追加于此，学生可在会话里回溯历史运行
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    created_via: Mapped[CronTaskSource] = mapped_column(SAEnum(CronTaskSource), default=CronTaskSource.CHAT)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: 注册模型** —— `backend/app/models/__init__.py` 在 `from app.models.conversation import ...` 一行之后加入：

```python
from app.models.cron_task import AgentCronTask, CronScheduleKind, CronTaskSource
```

- [ ] **Step 3: 写迁移** `backend/alembic/versions/m8n9p0q1r2s3_agent_cron_tasks.py`

```python
"""Agent 定时任务表

Revision ID: m8n9p0q1r2s3
Revises: k2f3a4b5c6d7
Create Date: 2026-10-29 00:00:00.000000

每个任务绑定一个专属会话：执行输出全部追加在同一会话，学生可回溯历史运行，
会话列表也不会被定时输出刷屏（specs/2026-10-29-agent-cron-task-design.md §1）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'm8n9p0q1r2s3'
down_revision: Union[str, Sequence[str], None] = 'k2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    # 幂等：开发库可能已手动建过表，避免 DuplicateTable 卡死整条 upgrade head
    if not inspector.has_table("agent_cron_tasks"):
        op.create_table(
            'agent_cron_tasks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('prompt', sa.Text(), nullable=False),
            sa.Column('schedule_kind', sa.Enum('DAILY', 'WEEKLY', 'INTERVAL', name='cronschedulekind'), nullable=False),
            sa.Column('hour', sa.Integer(), nullable=True),
            sa.Column('minute', sa.Integer(), nullable=True),
            sa.Column('weekday', sa.Integer(), nullable=True),
            sa.Column('interval_hours', sa.Integer(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('conversation_id', sa.Integer(), nullable=False),
            sa.Column('created_via', sa.Enum('CHAT', 'MANUAL', name='crontasksource'), nullable=False, server_default='CHAT'),
            sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_agent_cron_tasks_id'), 'agent_cron_tasks', ['id'], unique=False)
        op.create_index(op.f('ix_agent_cron_tasks_user_id'), 'agent_cron_tasks', ['user_id'], unique=False)
        op.create_index(op.f('ix_agent_cron_tasks_enabled'), 'agent_cron_tasks', ['enabled'], unique=False)
        op.create_index(op.f('ix_agent_cron_tasks_next_run_at'), 'agent_cron_tasks', ['next_run_at'], unique=False)


def downgrade() -> None:
    op.drop_table('agent_cron_tasks')
```

- [ ] **Step 4: 验证迁移可跑通**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -c "from alembic import command; from alembic.config import Config; command.upgrade(Config('alembic.ini'), 'head')"`
Expected: 无异常退出（开发库出现 agent_cron_tasks 表）。之后再删掉本地的 tests/test.db（若存在），让下一轮 pytest 重建。

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/cron_task.py backend/app/models/__init__.py backend/alembic/versions/m8n9p0q1r2s3_agent_cron_tasks.py
git commit -m "feat(cron): Agent 定时任务数据模型与建表迁移"
```

---

### Task 2: 周期计算与人话描述（service 纯函数）

**Files:**
- Create: `backend/app/services/cron_task_service.py`
- Test: `backend/tests/test_cron_task.py`

- [ ] **Step 1: 写失败测试** `backend/tests/test_cron_task.py`（先只放本任务的用例）

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'app.services.cron_task_service'`

- [ ] **Step 3: 实现** `backend/app/services/cron_task_service.py`

```python
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
# 单进程边界：多 worker 部署时 advance-then-execute 不是原子声明，需改 DB 级抢占
_running_ids: set[int] = set()

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _as_utc(dt: datetime) -> datetime:
    """SQLite 不保留时区，读回的 naive datetime 一律视为 UTC。"""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def to_beijing_iso(dt: datetime) -> str:
    """统一对外序列化：UTC 存储值转北京时间 ISO 串（带 +08:00），供工具载荷与管理 API 共用。"""
    return _as_utc(dt).astimezone(BEIJING_TZ).isoformat()


def compute_next_run(task: AgentCronTask, now: datetime | None = None) -> datetime:
    """计算下一次触发时间（UTC）。daily/weekly 的触发时刻按北京时间解释。"""
    now = _as_utc(now) if now else datetime.now(timezone.utc)
    if task.schedule_kind == CronScheduleKind.INTERVAL:
        # 独立防护：即便绕过 validate 直写 DB 也要保证正间隔，否则任务永远处于到期
        hours = task.interval_hours if task.interval_hours and task.interval_hours >= 1 else 24
        return now + timedelta(hours=hours)

    bj_now = now.astimezone(BEIJING_TZ)
    # 显式 is None 判断而非 or 兑底：hour=0（午夜）是合法值，`or` 会把它吞成 8
    target = bj_now.replace(
        hour=8 if task.hour is None else task.hour,
        minute=0 if task.minute is None else task.minute,
        second=0, microsecond=0,
    )
    if task.schedule_kind == CronScheduleKind.WEEKLY:
        target += timedelta(days=(task.weekday - bj_now.weekday()) % 7)
    if target <= bj_now:
        target += timedelta(days=1 if task.schedule_kind == CronScheduleKind.DAILY else 7)
    return target.astimezone(timezone.utc)


def describe_schedule(task: AgentCronTask) -> str:
    """把周期翻译成学生看得见的人话（列表页/通知/工具返回共用）。"""
    hm = f"{0 if task.hour is None else task.hour:02d}:{0 if task.minute is None else task.minute:02d}"
    if task.schedule_kind == CronScheduleKind.DAILY:
        return f"每天 {hm}"
    if task.schedule_kind == CronScheduleKind.WEEKLY:
        wd = task.weekday if task.weekday is not None and 0 <= task.weekday <= 6 else 0
        return f"每周{WEEKDAY_NAMES[wd]} {hm}"
    return f"每 {task.interval_hours or 24} 小时"


def _to_int(v) -> int | None:
    """宽容取整：LLM 给的参数可能是字符串/None，非法一律返回 None 而非抛异常。"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def validate_schedule_args(args: dict) -> tuple[dict, str | None]:
    """校验创建参数，返回 (归一化参数, 错误信息)。错误信息为 None 表示通过。

    契约：只返回错误、绝不抛异常——错误信息会原样交回 LLM 用于向学生澄清。
    """
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/cron_task_service.py backend/tests/test_cron_task.py
git commit -m "feat(cron): 周期计算（北京时间解释/UTC 落库）与人话描述"
```

---

### Task 3: agent 工具（创建 / 列表）

**Files:**
- Create: `backend/app/services/tools/cron_task.py`
- Modify: `backend/app/services/tools/definitions.py`（TOOL_DEFINITIONS 列表末尾追加）
- Modify: `backend/app/services/tools/dispatcher.py`
- Test: `backend/tests/test_cron_task.py`（追加）

- [ ] **Step 1: 追加失败测试**（`backend/tests/test_cron_task.py` 末尾）

```python
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
    from app.models.user import UserRole
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, {"name": "x", "schedule_kind": "daily", "hour": 8, "minute": 0}, student)
    assert out["success"] is False


def test_tool_create_weekly_missing_weekday(db, make_user):
    from app.models.user import UserRole
    student = make_user(role=UserRole.STUDENT)
    out = _create_cron_task(db, _args(schedule_kind="weekly", hour=9, minute=0), student)
    assert out["success"] is False


def test_tool_create_limit(db, make_user):
    from app.models.user import UserRole
    student = make_user(role=UserRole.STUDENT)
    for i in range(MAX_TASKS_PER_USER):
        assert _create_cron_task(db, _args(name=f"任务{i}"), student)["success"] is True
    out = _create_cron_task(db, _args(name="超额"), student)
    assert out["success"] is False
    assert str(MAX_TASKS_PER_USER) in out["message"]


def test_tool_list(db, make_user):
    from app.models.user import UserRole
    student = make_user(role=UserRole.STUDENT)
    _create_cron_task(db, _args(), student)
    out = _list_cron_tasks(db, {}, student)
    assert out["success"] is True and len(out["tasks"]) == 1
    assert out["tasks"][0]["schedule"] == "每天 08:30"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: 新增 5 条 FAIL — `ModuleNotFoundError: No module named 'app.services.tools.cron_task'`

- [ ] **Step 3: 实现 handler** `backend/app/services/tools/cron_task.py`

```python
"""Agent 定时任务工具 handler：创建 / 列表。

执行与调度在 services/cron_task_service.py；这里只负责工具协议层：
参数校验、上限校验、建会话+任务、返回给 LLM 的结构化结果。
"""
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.cron_task import AgentCronTask, CronTaskSource
from app.models.user import User
from app.services.cron_task_service import (
    MAX_TASKS_PER_USER,
    compute_next_run,
    describe_schedule,
    to_beijing_iso,
    validate_schedule_args,
)


def _create_cron_task(db: Session, args: dict, user: User) -> dict:
    name = (args.get("name") or "").strip()
    prompt = (args.get("prompt") or "").strip()
    if not name or not prompt:
        return {"success": False, "message": "缺少任务名称(name)或执行指令(prompt)，请补充后重试"}
    normalized, err = validate_schedule_args(args)
    if err:
        return {"success": False, "message": err}
    count = db.query(AgentCronTask).filter(AgentCronTask.user_id == user.id).count()
    if count >= MAX_TASKS_PER_USER:
        return {"success": False, "message": f"每人最多 {MAX_TASKS_PER_USER} 个定时任务，请先在定时任务页删除部分任务"}

    conv = Conversation(user_id=user.id, title=name[:200])
    db.add(conv)
    db.flush()
    task = AgentCronTask(
        user_id=user.id,
        name=name[:100],
        prompt=prompt,
        conversation_id=conv.id,
        created_via=CronTaskSource.CHAT,
        **normalized,
    )
    task.next_run_at = compute_next_run(task)
    db.add(task)
    db.commit()
    return {
        "success": True,
        "task": {
            "id": task.id,
            "name": task.name,
            "schedule": describe_schedule(task),
            # to_beijing_iso：SQLite 读回是无偏移 UTC 裸值，直接 isoformat 会被 LLM 当本地时间转述（差 8 小时）
            "next_run_at": to_beijing_iso(task.next_run_at),
        },
        "message": f"定时任务「{task.name}」已创建，{describe_schedule(task)}自动执行",
    }


def _list_cron_tasks(db: Session, args: dict, user: User) -> dict:
    rows = (
        db.query(AgentCronTask)
        .filter(AgentCronTask.user_id == user.id)
        .order_by(AgentCronTask.created_at.desc())
        .all()
    )
    return {
        "success": True,
        "message": f"共 {len(rows)} 个定时任务",
        "tasks": [
            {
                "id": t.id,
                "name": t.name,
                "schedule": describe_schedule(t),
                "enabled": t.enabled,
                "last_run_at": to_beijing_iso(t.last_run_at) if t.last_run_at else None,
            }
            for t in rows
        ],
    }
```

- [ ] **Step 4: 注册工具定义** —— `backend/app/services/tools/definitions.py` 的 `TOOL_DEFINITIONS = [` 列表**末尾**（闭合 `]` 之前）追加：

```python
    {
        "type": "function",
        "function": {
            "name": "create_cron_task",
            "description": "创建 Agent 定时任务（到点自动执行）。当学生表达'每天/每周/每隔多久自动帮我做某事'的意图时调用。调用前必须先向学生复述任务名称、执行内容与周期并得到确认；周期只支持三种：每天固定时刻（daily）、每周固定星期几的固定时刻（weekly）、每隔 N 小时（interval）。hour/minute 按学生说的北京时间。歧义（如'每隔一阵'）先追问再创建。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "任务名称，简短，如'早报汇总'"},
                    "prompt": {"type": "string", "description": "每次执行时交给 AI 的完整指令，写清楚要做什么、输出什么"},
                    "schedule_kind": {"type": "string", "enum": ["daily", "weekly", "interval"], "description": "周期类型"},
                    "hour": {"type": "integer", "description": "触发时刻-小时（0-23，北京时间），daily/weekly 必填"},
                    "minute": {"type": "integer", "description": "触发时刻-分钟（0-59），daily/weekly 必填"},
                    "weekday": {"type": "integer", "description": "每周几（0=周一…6=周日），weekly 必填"},
                    "interval_hours": {"type": "integer", "description": "间隔小时数（1-720），interval 必填"}
                },
                "required": ["name", "prompt", "schedule_kind"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_cron_tasks",
            "description": "查询学生当前的 Agent 定时任务列表（名称、周期、启用状态、上次执行时间）。当学生问'我的定时任务/自动任务'时调用。",
            "parameters": {"type": "object", "properties": {}}
        }
    },
```

- [ ] **Step 5: 注册分发** —— `backend/app/services/tools/dispatcher.py`：

(a) import 区（`from .community import ...` 之前）加：

```python
from .cron_task import _create_cron_task, _list_cron_tasks
```

(b) `execute_tool` 内 `handler = {` 字典里（如 `"create_leave": _create_leave,` 之后）加两行：

```python
            "create_cron_task": _create_cron_task,
            "list_cron_tasks": _list_cron_tasks,
```

注意：`_STUDENT_TOOL_NAMES` 由 `TOOL_DEFINITIONS` 自动推导（dispatcher.py:68），加完定义即纳入学生端门控，无需另改。

- [ ] **Step 6: 跑测试确认通过**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: 11 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/tools/cron_task.py backend/app/services/tools/definitions.py backend/app/services/tools/dispatcher.py backend/tests/test_cron_task.py
git commit -m "feat(cron): agent 工具 create/list_cron_task，聊天动嘴建任务"
```

---

### Task 4: 调度执行内核

**Files:**
- Modify: `backend/app/services/cron_task_service.py`（追加执行部分）
- Modify: `backend/app/tasks/periodic.py`
- Test: `backend/tests/test_cron_task.py`（追加）

- [ ] **Step 1: 追加失败测试**（`backend/tests/test_cron_task.py` 末尾）

```python
# ---------- 调度执行内核 ----------

import asyncio  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.conversation import ConversationMessage  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.services import cron_task_service as svc  # noqa: E402


@pytest.fixture()
def due_task(db, make_user):
    """一条已到期（next_run_at 早于当前）的启用任务。"""
    from app.models.user import UserRole
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
    from app.models.user import UserRole
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: 新增用例 FAIL — `AttributeError: ... has no attribute 'execute_due_tasks'`

- [ ] **Step 3: 实现执行内核** —— `backend/app/services/cron_task_service.py` 末尾追加：

```python
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
        # 收尾字段先取出：rollback 会 expire 本行，行若已被删再取属性会 ObjectDeletedError
        notify_title, notify_content = task.name, (reply or "（本次没有产出内容）")[:200]
        notify_user_id, notify_conv_id = task.user_id, task.conversation_id
        try:
            db.commit()
        except Exception:
            # 执行期间任务被删：行已不在，收尾更新落空不碍事——AI 回复已落会话，通知照发
            db.rollback()
            logger.info("[定时任务] 任务在执行期间被删除 task_id=%s", task_id)
        _notify(db, notify_user_id, notify_title, notify_content, notify_conv_id)
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
        # 单任务异常隔离：一个任务的失败不能烧掉同轮其余已推进任务的执行名额
        try:
            if await execute_once(task_id):
                executed += 1
        except Exception:
            logger.exception("[定时任务] 单任务执行异常 task_id=%s", task_id)
    return executed
```

- [ ] **Step 4: 挂调度循环** —— `backend/app/tasks/periodic.py`：

(a) 常量区（`PROACTIVE_INTERVAL_SECONDS = 1800` 之后）加：

```python
# Agent 定时任务：每分钟扫一次到期任务
CRON_TASK_SCAN_INTERVAL_SECONDS = 60
```

(b) `_periodic_proactive_push` 函数之后加：

```python
async def _periodic_cron_task_runner() -> None:
    """Agent 定时任务调度：每分钟扫描一次到期任务并执行。

    测试环境不启动（conftest 注入 TESTING=1）：测试会直接调用
    execute_due_tasks() 验证内核，避免调度循环抢跑真实任务。
    """
    import os

    if os.getenv("TESTING") == "1":
        return
    from app.services.cron_task_service import execute_due_tasks

    while True:
        try:
            await execute_due_tasks()
        except Exception:
            logger.exception("[定时任务] 调度扫描异常")
        await asyncio.sleep(CRON_TASK_SCAN_INTERVAL_SECONDS)
```

(c) `start_periodic_tasks` 返回列表末尾加：

```python
        # Agent 定时任务：每分钟扫描到期任务，AI 到点自动执行
        asyncio.create_task(_periodic_cron_task_runner()),
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: 16 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/cron_task_service.py backend/app/tasks/periodic.py backend/tests/test_cron_task.py
git commit -m "feat(cron): 到期执行内核与每分钟调度循环，先推进再执行防重入"
```

---

### Task 5: 管理 API

**Files:**
- Create: `backend/app/schemas/cron_task.py`
- Create: `backend/app/api/cron_task.py`
- Modify: `backend/app/api/registry.py`
- Test: `backend/tests/test_cron_task.py`（追加）

- [ ] **Step 1: 追加失败测试**（`backend/tests/test_cron_task.py` 末尾）

```python
# ---------- 管理 API ----------

from app.services.tools.cron_task import _create_cron_task as _svc_create  # noqa: E402


def test_api_crud_and_permission(client, api, login_token, db, make_user):
    from app.models.user import UserRole
    owner = login_token(role=UserRole.STUDENT)
    other = login_token(role=UserRole.STUDENT)

    _svc_create(db, _args(), owner["user"])
    task = db.query(AgentCronTask).filter(AgentCronTask.user_id == owner["user"].id).first()
    assert task is not None

    # 列表：只含本人任务
    rows = api.get("/api/cron-tasks", headers=owner["headers"]).json()
    assert len(rows) == 1 and rows[0]["schedule_text"] == "每天 08:30" and rows[0]["enabled"] is True

    # 越权：他人访问一律 404，不暴露存在性
    assert api.get("/api/cron-tasks", headers=other["headers"]).json() == []
    assert api.put(f"/api/cron-tasks/{task.id}", json={"enabled": False}, headers=other["headers"]).status_code == 404

    # 启停 + 恢复时重算过期 next_run_at
    assert api.put(f"/api/cron-tasks/{task.id}", json={"enabled": False}, headers=owner["headers"]).json()["enabled"] is False
    resumed = api.put(f"/api/cron-tasks/{task.id}", json={"enabled": True}, headers=owner["headers"]).json()
    assert resumed["enabled"] is True
    # SQLite 读回的 datetime 可能带 offset 也可能 naive，统一按 UTC 归一再比较
    nxt = datetime.fromisoformat(str(resumed["next_run_at"]).replace("Z", "+00:00"))
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=UTC)
    assert nxt > datetime.now(UTC) - timedelta(minutes=5)

    # run-now：执行中冲突 → 409
    monkeypatch1 = pytest.MonkeyPatch()
    monkeypatch1.setattr(svc, "execute_once", lambda task_id: asyncio.sleep(0, result=False))
    assert api.post(f"/api/cron-tasks/{task.id}/run-now", headers=owner["headers"]).status_code == 409
    monkeypatch1.undo()

    # 删除
    assert api.delete(f"/api/cron-tasks/{task.id}", headers=owner["headers"]).json()["ok"] is True
    assert db.query(AgentCronTask).filter(AgentCronTask.id == task.id).first() is None
    assert api.delete(f"/api/cron-tasks/{task.id}", headers=owner["headers"]).status_code == 404


def test_api_run_now_success(client, api, login_token, db, monkeypatch):
    from app.models.user import UserRole
    owner = login_token(role=UserRole.STUDENT)
    _svc_create(db, _args(), owner["user"])
    task = db.query(AgentCronTask).filter(AgentCronTask.user_id == owner["user"].id).first()

    monkeypatch.setattr(svc, "execute_once", lambda task_id: asyncio.sleep(0, result=True))
    assert api.post(f"/api/cron-tasks/{task.id}/run-now", headers=owner["headers"]).json()["ok"] is True


def test_api_requires_auth(client, api):
    assert api.get("/api/cron-tasks").status_code == 401
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: 新增 3 条 FAIL — 404 Not Found（路由未注册）

- [ ] **Step 3: 写 schemas** `backend/app/schemas/cron_task.py`

```python
from datetime import datetime

from pydantic import BaseModel


class CronTaskUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None


class CronTaskOut(BaseModel):
    id: int
    name: str
    prompt: str
    schedule_kind: str
    schedule_text: str
    hour: int | None = None
    minute: int | None = None
    weekday: int | None = None
    interval_hours: int | None = None
    enabled: bool
    conversation_id: int
    last_run_at: datetime | None = None
    next_run_at: datetime
```

- [ ] **Step 4: 写 API** `backend/app/api/cron_task.py`

```python
"""Agent 定时任务管理：学生查看/启停/删除/立即执行自己的任务。

创建不在 API 层暴露——创建走 agent 工具（聊天动嘴），管理页只管存量任务。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cron_task import AgentCronTask, CronScheduleKind
from app.models.user import User
from app.schemas.cron_task import CronTaskOut, CronTaskUpdate
from app.services import cron_task_service
from app.services.cron_task_service import describe_schedule

router = APIRouter(prefix="/api/cron-tasks", tags=["Agent定时任务"])


def _get_own_task(db: Session, task_id: int, user: User) -> AgentCronTask:
    task = db.query(AgentCronTask).filter(AgentCronTask.id == task_id).first()
    # 越权一律 404，不暴露他人任务的存在性
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def _serialize(task: AgentCronTask) -> dict:
    kind = task.schedule_kind
    return {
        "id": task.id,
        "name": task.name,
        "prompt": task.prompt,
        "schedule_kind": kind.value if isinstance(kind, CronScheduleKind) else str(kind),
        "schedule_text": describe_schedule(task),
        "hour": task.hour,
        "minute": task.minute,
        "weekday": task.weekday,
        "interval_hours": task.interval_hours,
        "enabled": task.enabled,
        "conversation_id": task.conversation_id,
        # 统一北京时间 ISO（带 +08:00）：SQLite 读回的是无偏移 UTC 裸值，直接透传会被前端 new Date 当本地时区解析（差 8 小时）
        "last_run_at": cron_task_service.to_beijing_iso(task.last_run_at) if task.last_run_at else None,
        "next_run_at": cron_task_service.to_beijing_iso(task.next_run_at),
    }


@router.get("", response_model=list[CronTaskOut])
def list_my_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(AgentCronTask)
        .filter(AgentCronTask.user_id == current_user.id)
        .order_by(AgentCronTask.created_at.desc())
        .all()
    )
    return [_serialize(t) for t in rows]


@router.put("/{task_id}", response_model=CronTaskOut)
def update_task(
    task_id: int,
    req: CronTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_own_task(db, task_id, current_user)
    if req.name is not None and req.name.strip():
        task.name = req.name.strip()[:100]
    if req.enabled is not None:
        task.enabled = req.enabled
        # 恢复时若 next_run_at 已过期则重算，不补跑暂停期间的旧账
        if req.enabled and cron_task_service._as_utc(task.next_run_at) <= datetime.now(timezone.utc):
            task.next_run_at = cron_task_service.compute_next_run(task)
    db.commit()
    db.refresh(task)
    return _serialize(task)


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_own_task(db, task_id, current_user)
    # 正在执行中的任务先拒绝删除：execute_once 收尾要对本行 UPDATE，先删会 StaleDataError
    if task.id in cron_task_service._running_ids:
        raise HTTPException(status_code=409, detail="任务正在执行中，请稍后再试")
    # 保留会话记录：历史执行结果学生还能在对话列表里看到
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.post("/{task_id}/run-now")
async def run_now(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_own_task(db, task_id, current_user)
    if not task.enabled:
        raise HTTPException(status_code=400, detail="任务已暂停，请先启用")
    was_running = task.id in cron_task_service._running_ids
    ok = await cron_task_service.execute_once(task.id)
    if not ok:
        # was_running：进入时就已有人在跑 → 409 忙；否则 False 即失败/不可用 → 502
        if was_running:
            raise HTTPException(status_code=409, detail="任务正在执行中，请稍后再试")
        raise HTTPException(status_code=502, detail="执行失败，请稍后查看通知")
    return {"ok": True}
```

- [ ] **Step 5: 注册路由** —— `backend/app/api/registry.py`：

(a) import 区加：`from app.api.cron_task import router as cron_task_router`
(b) `ROUTERS = [...]` 列表末尾（`]` 之前）加：`cron_task_router,`

- [ ] **Step 6: 跑测试确认通过**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/test_cron_task.py -v`
Expected: 19 passed

- [ ] **Step 7: 回归全量**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/ -q`
Expected: 全绿（新增迁移在 test.db 上自动执行；定时任务循环在 TESTING=1 下不启动）

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/cron_task.py backend/app/api/cron_task.py backend/app/api/registry.py backend/tests/test_cron_task.py
git commit -m "feat(cron): 定时任务管理 API（列表/启停/删除/立即执行，越权 404）"
```

---

### Task 6: 前端 API client 与管理子页

**Files:**
- Create: `frontend/src/api/cronTask.ts`
- Create: `frontend/src/components/agent/AgentCronPage.vue`

- [ ] **Step 1: API client** `frontend/src/api/cronTask.ts`

```ts
import request from '@/utils/request'

export interface CronTaskItem {
  id: number
  name: string
  prompt: string
  schedule_kind: 'daily' | 'weekly' | 'interval'
  schedule_text: string
  hour: number | null
  minute: number | null
  weekday: number | null
  interval_hours: number | null
  enabled: boolean
  conversation_id: number
  last_run_at: string | null
  next_run_at: string
}

export function listCronTasks() {
  return request.get<CronTaskItem[]>('/cron-tasks')
}

export function updateCronTask(id: number, data: { name?: string; enabled?: boolean }) {
  return request.put<CronTaskItem>(`/cron-tasks/${id}`, data)
}

export function deleteCronTask(id: number) {
  return request.delete(`/cron-tasks/${id}`)
}

export function runCronTaskNow(id: number) {
  return request.post(`/cron-tasks/${id}/run-now`)
}
```

- [ ] **Step 2: 管理子页** `frontend/src/components/agent/AgentCronPage.vue`（覆盖式子页，结构照抄 CampusSearchPage：Teleport + Transition(name="subpage") + 根元素 fixed inset:0，进出场动画统一走全局 `.subpage`，本页不自带）

```vue
<template>
  <Teleport to="body">
    <Transition name="subpage" :duration="320" @after-leave="emit('closed')">
      <div v-if="visible" class="acp-root" role="dialog" aria-modal="true" aria-label="定时任务">
        <header class="acp-head">
          <button type="button" class="acp-back" aria-label="返回" @click="close">
            <el-icon :size="22"><ArrowLeft /></el-icon>
          </button>
          <h1 class="acp-title">定时任务</h1>
          <span class="acp-head-space"></span>
        </header>

        <div class="acp-scroll">
          <el-empty v-if="!loading && tasks.length === 0" description="还没有定时任务">
            <p class="acp-empty-tip">在对话框跟我说「每天早上 8 点帮我汇总校园资讯」就能建一个</p>
          </el-empty>

          <div v-else class="acp-list">
            <div v-for="t in tasks" :key="t.id" class="acp-item" :class="{ disabled: !t.enabled }">
              <div class="acp-item-main" @click="openConversation(t)">
                <div class="acp-item-name">{{ t.name }}</div>
                <div class="acp-item-meta">
                  {{ t.schedule_text }}<template v-if="t.last_run_at"> · 上次 {{ fmtTime(t.last_run_at) }}</template>
                </div>
              </div>
              <div class="acp-item-ops">
                <el-button text size="small" type="primary" :loading="runningId === t.id" @click.stop="runNow(t)">立即执行</el-button>
                <el-switch :model-value="t.enabled" @change="(v: string | number | boolean) => toggle(t, Boolean(v))" />
                <el-button text size="small" type="danger" @click.stop="remove(t)">删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteCronTask, listCronTasks, runCronTaskNow, updateCronTask, type CronTaskItem,
} from '@/api/cronTask'

const emit = defineEmits<{ (e: 'closed'): void }>()
const router = useRouter()

/* 与 ArticleDetailPage / CampusSearchPage 同一套约定：父页 v-if 挂载即打开
   （onMounted 置 visible），close() 播退场动画，after-leave 才通知父页卸载。 */
const visible = ref(false)
const tasks = ref<CronTaskItem[]>([])
const loading = ref(false)
const runningId = ref<number | null>(null)

function close() {
  visible.value = false
}

async function load() {
  loading.value = true
  try {
    tasks.value = await listCronTasks()
  } catch { /* 列表拉取失败保持空态 */ } finally {
    loading.value = false
  }
}

async function toggle(t: CronTaskItem, enabled: boolean) {
  try {
    const updated = await updateCronTask(t.id, { enabled })
    Object.assign(t, updated)
    ElMessage.success(enabled ? '已恢复' : '已暂停')
  } catch {
    ElMessage.error('操作失败，请重试')
  }
}

async function remove(t: CronTaskItem) {
  try {
    await ElMessageBox.confirm(
      `删除后「${t.name}」不再自动执行，历史结果仍保留在会话里。`,
      '删除定时任务',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }
  try {
    await deleteCronTask(t.id)
    tasks.value = tasks.value.filter(x => x.id !== t.id)
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败，请重试')
  }
}

async function runNow(t: CronTaskItem) {
  runningId.value = t.id
  try {
    await runCronTaskNow(t.id)
    ElMessage.success('已触发，AI 正在执行，结果稍后送达会话')
    await load()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '执行失败，请稍后再试')
  } finally {
    runningId.value = null
  }
}

function openConversation(t: CronTaskItem) {
  close()
  router.push(`/student/agent?conv=${t.conversation_id}`)
}

function fmtTime(iso: string) {
  // 后端统一给北京时间 ISO（带 +08:00），new Date 解析后直接取本地字段即为正确展示
  const d = new Date(iso)
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/** 5xx/网络错误已由全局拦截器统一提示，这里只对 4xx 弹后端 detail，避免双 toast。 */
function toastBizError(e: unknown, fallback: string) {
  const status = (e as { response?: { status?: number } })?.response?.status
  if (status && status < 500) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || fallback)
  } else {
    console.error('cron task request failed', e)
  }
}

onMounted(() => {
  visible.value = true
  load()
})
</script>

<style scoped>
/* 定位照抄 .csp-root：全屏覆盖 + 独立层；动画由全局 .subpage keyframes 驱动 */
.acp-root {
  position: fixed;
  inset: 0;
  z-index: 2600;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.acp-head {
  display: flex;
  align-items: center;
  gap: 10px;
  /* viewport-fit=cover + fixed inset:0：刘海屏顶栏要避开状态栏（照抄 .csp-head） */
  padding: calc(8px + env(safe-area-inset-top, 0px)) 14px 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
.acp-back {
  display: flex;
  align-items: center;
  border: none;
  background: none;
  cursor: pointer;
  color: #333;
}
.acp-title {
  flex: 1;
  margin: 0;
  font-size: 16.5px;
  font-weight: 600;
  color: #222;
}
.acp-head-space { width: 34px; }
.acp-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  /* 底部避开 home indicator（照抄 .csp-scroll） */
  padding: 4px 16px calc(40px + env(safe-area-inset-bottom, 0px));
}
.acp-empty-tip {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.6;
}
.acp-list { display: flex; flex-direction: column; gap: 10px; }
.acp-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: #f7f8fa;
  border: 1px solid rgba(91, 141, 239, 0.08);
}
.acp-item.disabled { opacity: 0.55; }
.acp-item-main { flex: 1; min-width: 0; cursor: pointer; }
.acp-item-name {
  font-size: 14.5px;
  font-weight: 600;
  color: #2b2f36;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.acp-item-meta { margin-top: 3px; font-size: 12.5px; color: #8a9099; }
.acp-item-ops { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
</style>
```

- [ ] **Step 3: 类型检查/构建验证**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\frontend" && mkdir -p .tmpbuild && TMP="$PWD/.tmpbuild" TEMP="$PWD/.tmpbuild" TMPDIR="$PWD/.tmpbuild" npm run build`
Expected: 构建成功（AgentCronPage 暂未被引用，构建仍通过；被 ChatPanel 引用在 Task 7 接入）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/cronTask.ts frontend/src/components/agent/AgentCronPage.vue
git commit -m "feat(cron): 定时任务管理子页与 API client，覆盖式 subpage 动效"
```

---

### Task 7: ChatPanel 集成（顶栏入口 + ?conv= 直达）

**Files:**
- Modify: `frontend/src/components/agent/ChatPanel.vue`

- [ ] **Step 1: 模板——顶栏加时钟入口**。`mobile-header` 内、`<el-button ... @click="handlePhoneCall">` 之前插入（仅学生端显示；教师端 ChatPanel 复用同一组件，不给入口）：

```html
      <el-button
        v-if="props.role === 'student'"
        text circle class="menu-toggle"
        aria-label="定时任务"
        @click="cronVisible = true"
      >
        <el-icon :size="20"><Clock /></el-icon>
      </el-button>
```

- [ ] **Step 2: 模板——挂载子页**。根元素 `.chat-modern` 的闭合 `</div>` 之前（`</template>` 之前最后一个子元素位置）加：

```html
    <!-- Agent 定时任务管理子页：覆盖式整屏，仅学生端 -->
    <AgentCronPage v-if="cronVisible" @closed="cronVisible = false" />
```

- [ ] **Step 3: 脚本——imports 与状态**。

(a) `import { useRouter } from 'vue-router'` 改为：

```ts
import { useRouter, useRoute } from 'vue-router'
```

(b) icons import（`Promotion, Paperclip, ...` 那行）加入 `Clock`：

```ts
import {
  Promotion, Paperclip, Picture, Document, Microphone, Phone, CopyDocument, EditPen, ArrowDown, Close, Delete, Clock,
} from '@element-plus/icons-vue'
```

(c) `import MianCharacter from './MianCharacter.vue'` 之后加：

```ts
import AgentCronPage from './AgentCronPage.vue'
```

(d) `const router = useRouter()` 处加一行：

```ts
const router = useRouter()
const route = useRoute()
```

(e) `const loading = ref(false)` 附近加：

```ts
const cronVisible = ref(false)
```

- [ ] **Step 4: 脚本——onMounted 支持 ?conv= 直达**。`onMounted(() => {` 回调开头（`scrollToBottom(true)` 之前）插入（照抄 handleVoiceClose 的换会话三件套：fetchMessages → replaceMessages → setActive/fetchList）。**把加载逻辑抽成 `openConvFromQuery()` 函数，onMounted 与 `watch(() => route.query.conv, …)` 都调用**——子页 openConversation 在 /student/agent 本页内 push 时不会重挂载 ChatPanel，同路由推入必须靠 watch 生效：

```ts
  // 通知直达：/student/agent?conv=<id>（Agent 定时任务通知的 link），进入即打开对应会话
  const convParam = Number(route.query.conv)
  if (props.role === 'student' && Number.isFinite(convParam) && convParam > 0) {
    convStore.fetchMessages(convParam).then(() => {
      store.replaceMessages(
        convStore.messages.map(m => ({
          id: m.id.toString(),
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
        })),
      )
      convStore.setActive(convParam)
      convStore.fetchList()
    })
  }
```

- [ ] **Step 5: 构建验证**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\frontend" && mkdir -p .tmpbuild && TMP="$PWD/.tmpbuild" TEMP="$PWD/.tmpbuild" TMPDIR="$PWD/.tmpbuild" npm run build`
Expected: 构建成功，无 TS 报错

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/agent/ChatPanel.vue
git commit -m "feat(cron): 聊天顶栏定时任务入口与通知 ?conv= 直达会话"
```

---

### Task 8: 端到端手动验证

**Files:** 无代码改动（验证任务）

- [ ] **Step 1: 后端全量测试**

Run: `cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m pytest tests/ -q`
Expected: 全绿

- [ ] **Step 2: 起服务**

后端：`cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\backend" && python -m uvicorn app.main:app --port 8000`（启动即自动跑 alembic upgrade head）
前端：`cd "E:\studyScore\创意集市\WisPath_CampusMate_V2\frontend" && npm run dev`
浏览器打开 `http://localhost:5173/student`

- [ ] **Step 3: playwright 截图验证**（照既有配方，坑位齐全）：
  - 登录三坑：welcome 引导页需 init script 跳过；必须勾协议；账号输入框 placeholder 是「学号 / 工号」；种子账号 `2024001 / 123456`
  - 验证点 1：`/student` 聊天顶栏出现时钟图标，点击后 `AgentCronPage` 从右滑入整屏覆盖（ push 式，非卡片）
  - 验证点 2：空态文案与引导可见
  - 验证点 3：聊天里发「每天早上 8 点帮我汇总一下校园新鲜事」→ agent 复述确认 → 创建成功；子页列表出现该任务，周期显示「每天 08:00」
  - 验证点 4：对任务点「立即执行」→ 稍后消息中心出现通知，点击通知落到 `/student/agent?conv=<id>` 并展示会话内容
  - 补充观察（Task 7 质量审查给出）：
    - 深链进入任务会话后直接输入回复——注意当前 AgentPage 未传 `:conversation-id`，回复会**分叉进新会话**（既有行为被深链放大，属产品决策项，验证时记录现象即可）
    - 手造 `/student/agent?conv=999999`（不存在的会话）→ 应静默落到空会话视图，无报错 toast
    - 关闭动画 320ms 内再点时钟 → 点击被吞（兄弟子页同款既有契约，不算缺陷，记录即可）
    - 流式回复进行中点时钟 → 按钮应处于禁用态
  - 注意：ZCode 内置浏览器恒为 `prefers-reduced-motion: reduce`，滑入动画是否生效以用户本机浏览器为准，IAB 截图不能作为动效判据

- [ ] **Step 4: 收尾提交**（如有验证期的微调）

```bash
git add <微调的文件>
git commit -m "fix(cron): 端到端验证微调"
```
（无改动则跳过本步）
