"""Agent 定时任务工具 handler：创建 / 列表。

执行与调度在 services/cron_task_service.py；这里只负责工具协议层：
参数校验结果转成工具载荷、上限校验、返回给 LLM 的结构化结果。
创建本身复用 cron_task_service.create_task（与手动新建接口同一实现）。
"""
from sqlalchemy.orm import Session

from app.models.cron_task import AgentCronTask, CronTaskSource
from app.models.user import User
from app.services.cron_task_service import (
    create_task,
    describe_schedule,
    to_beijing_iso,
)


def _create_cron_task(db: Session, args: dict, user: User) -> dict:
    task, err = create_task(
        db,
        user.id,
        name=args.get("name"),
        prompt=args.get("prompt"),
        args=args,
        source=CronTaskSource.CHAT,
    )
    if err or task is None:
        return {"success": False, "message": err or "创建失败，请稍后重试"}
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
