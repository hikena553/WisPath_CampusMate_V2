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
            # commit 后 expire_on_commit 会从 SQLite 读回 naive UTC 值，必须经 to_beijing_iso 补偏移
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
        "message": f"共 {len(rows)} 个定时任务",
    }
