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
        if was_running:
            # 调度循环/另一次 run-now 已占坑（_running_ids 去重）
            raise HTTPException(status_code=409, detail="任务正在执行中，请稍后再试")
        raise HTTPException(status_code=502, detail="执行失败，请稍后查看通知")
    return {"ok": True}
