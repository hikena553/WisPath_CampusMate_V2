"""学习计划模块（学习计划管理 / 任务管理 / 打卡闭环 / 数字赋能增强）

- 计划 CRUD：主题、周期(起止日期)、目标、阶段，可挂在长期目标下
- 任务 CRUD：标题、说明、截止时间、优先级；状态流转 待办→进行中→已完成
- 打卡闭环：任务打卡记录时长、连续打卡 streak、今日任务视图
- 数字赋能：完成率/进度计算、AI 顺延/重排建议、逾期/到期站内提醒、长期目标建联
"""
from datetime import date, timedelta, datetime, timezone
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.plan import (GrowthGoal, StudyPlan, PlanTask, PlanCheckin, PlanStage,
                             GoalStatus, PlanStatus, TaskStatus, StageStatus)
from app.schemas.plan import (
    GrowthGoalCreate, GrowthGoalUpdate, GrowthGoalOut,
    StudyPlanCreate, StudyPlanUpdate, StudyPlanOut,
    PlanTaskCreate, PlanTaskUpdate, PlanTaskOut,
    PlanStageCreate, PlanStageUpdate, PlanStageOut,
    StageSubmitRequest, StageSubmitOut, StageGenerateOut,
    CheckinCreate, CheckinOut, StreakOut, TodayTaskOut,
    AISuggestOut, AISuggestItem,
)
from app.api.notification import create_notification
from app.models.notification import NotificationType
from app.services.llm_service import _get_llm_config, _get_client
from app.services.plan_stage_service import (
    ai_generate_stages, ai_evaluate_stage, persist_generated_stages,
)

router = APIRouter(prefix="/api/plan", tags=["学习计划"])


def _parse_date(d: str | None) -> date | None:
    if not d:
        return None
    return datetime.strptime(d, "%Y-%m-%d").date()


def _plan_state(plan: StudyPlan, today: date) -> tuple[str, int]:
    """返回 (显示状态, 逾期未完成任务数)"""
    tasks = PlanTask.query  # placeholder, 不用
    return plan.status.value, 0


def _serialize_plan(db: Session, p: StudyPlan, today: date | None = None) -> StudyPlanOut:
    today = today or date.today()
    tasks = db.query(PlanTask).filter(PlanTask.plan_id == p.id).all()
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    overdue = sum(
        1 for t in tasks
        if t.status != TaskStatus.DONE and t.due_date and t.due_date < today
    )
    rate = round(done / total * 100) if total else 0
    goal_title = None
    if p.goal_id:
        goal = db.query(GrowthGoal).filter(GrowthGoal.id == p.goal_id).first()
        goal_title = goal.title if goal else None
    checkin_days = db.query(PlanCheckin).filter(
        PlanCheckin.plan_id == p.id,
        PlanCheckin.student_id == p.student_id,
    ).count()
    return StudyPlanOut(
        id=p.id, student_id=p.student_id, goal_id=p.goal_id, title=p.title,
        objective=p.objective, stage=p.stage, start_date=p.start_date,
        end_date=p.end_date, status=p.status.value, created_at=p.created_at,
        task_total=total, task_done=done, done_rate=rate, overdue=overdue,
        goal_title=goal_title, checkin_days=checkin_days,
    )


# ==================== 长期目标 ====================

@router.get("/goals", response_model=list[GrowthGoalOut])
def list_goals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goals = db.query(GrowthGoal).filter(
        GrowthGoal.student_id == current_user.id,
        GrowthGoal.status != GoalStatus.PAUSED,
    ).order_by(GrowthGoal.created_at.desc()).all()
    result = []
    for g in goals:
        plan_count = db.query(StudyPlan).filter(
            StudyPlan.goal_id == g.id,
            StudyPlan.student_id == current_user.id,
        ).count()
        out = GrowthGoalOut.model_validate(g)
        out.plan_count = plan_count
        result.append(out)
    return result


@router.post("/goals", response_model=GrowthGoalOut)
def create_goal(req: GrowthGoalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal = GrowthGoal(
        student_id=current_user.id,
        goal_type=req.goal_type,
        title=req.title.strip(),
        target_date=_parse_date(req.target_date),
        note=req.note,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return GrowthGoalOut.model_validate(goal)


@router.put("/goals/{goal_id}", response_model=GrowthGoalOut)
def update_goal(goal_id: int, req: GrowthGoalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal = db.query(GrowthGoal).filter(
        GrowthGoal.id == goal_id, GrowthGoal.student_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(404, "目标不存在")
    data = req.model_dump(exclude_unset=True)
    if "target_date" in data:
        data["target_date"] = _parse_date(data["target_date"])
    for k, v in data.items():
        if v is not None:
            setattr(goal, k, v)
    db.commit()
    db.refresh(goal)
    return GrowthGoalOut.model_validate(goal)


@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal = db.query(GrowthGoal).filter(
        GrowthGoal.id == goal_id, GrowthGoal.student_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(404, "目标不存在")
    # 解绑关联计划
    db.query(StudyPlan).filter(StudyPlan.goal_id == goal_id).update({StudyPlan.goal_id: None})
    db.delete(goal)
    db.commit()
    return {"message": "deleted"}


# ==================== 学习计划 ====================

@router.get("/plans", response_model=list[StudyPlanOut])
def list_plans(
    status: str | None = Query(None, description="active/completed/expired"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    query = db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id)
    plans = query.order_by(StudyPlan.created_at.desc()).all()

    def _visible(p: StudyPlan) -> bool:
        st = p.status.value
        if st == "completed":
            return status == "completed"
        # 逾期的定义：结束日期已过且未完成
        expired = p.end_date is not None and p.end_date < today
        if status == "expired":
            return expired
        if status == "active":
            return not expired
        return True

    filtered = [p for p in plans if _visible(p)]
    return [_serialize_plan(db, p, today) for p in filtered]


@router.post("/plans", response_model=StudyPlanOut)
def create_plan(req: StudyPlanCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = StudyPlan(
        student_id=current_user.id,
        goal_id=req.goal_id,
        title=req.title.strip(),
        objective=req.objective,
        stage=req.stage,
        start_date=_parse_date(req.start_date) or date.today(),
        end_date=_parse_date(req.end_date),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_plan(db, plan)


@router.put("/plans/{plan_id}", response_model=StudyPlanOut)
def update_plan(plan_id: int, req: StudyPlanUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(
        StudyPlan.id == plan_id, StudyPlan.student_id == current_user.id
    ).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    data = req.model_dump(exclude_unset=True)
    for k in ("start_date", "end_date"):
        if k in data:
            data[k] = _parse_date(data[k])
    for k, v in data.items():
        if v is not None:
            setattr(plan, k, v)
    # 依赖任务全部完成时自动置为已完成
    if plan.status != PlanStatus.COMPLETED:
        tasks = db.query(PlanTask).filter(PlanTask.plan_id == plan.id).all()
        if tasks and all(t.status == TaskStatus.DONE for t in tasks):
            plan.status = PlanStatus.COMPLETED
    db.commit()
    db.refresh(plan)
    return _serialize_plan(db, plan)


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(
        StudyPlan.id == plan_id, StudyPlan.student_id == current_user.id
    ).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    # 先删打卡（含任务关联打卡，解除外键约束），再删任务/阶段，最后删计划
    db.query(PlanCheckin).filter(PlanCheckin.plan_id == plan_id).delete(synchronize_session=False)
    db.query(PlanTask).filter(PlanTask.plan_id == plan_id).delete(synchronize_session=False)
    db.query(PlanStage).filter(PlanStage.plan_id == plan_id).delete(synchronize_session=False)
    db.delete(plan)
    db.commit()
    return {"message": "deleted"}


# ==================== 计划任务 ====================

@router.get("/tasks", response_model=list[PlanTaskOut])
def list_tasks(
    plan_id: int | None = Query(None),
    status: str | None = Query(None, description="todo/doing/done"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(PlanTask).join(StudyPlan, StudyPlan.id == PlanTask.plan_id).filter(
        StudyPlan.student_id == current_user.id
    )
    if plan_id:
        query = query.filter(PlanTask.plan_id == plan_id)
    if status:
        query = query.filter(PlanTask.status == status)
    tasks = query.order_by(PlanTask.order_index.asc(), PlanTask.created_at.asc()).all()
    plan_titles = {p.id: p.title for p in db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id).all()}
    checked_task_ids = {
        c.task_id for c in db.query(PlanCheckin).filter(
            PlanCheckin.student_id == current_user.id,
            PlanCheckin.check_date == date.today(),
        ).all() if c.task_id
    }
    result = []
    for t in tasks:
        out = PlanTaskOut.model_validate(t)
        out.plan_title = plan_titles.get(t.plan_id, "")
        out.checked_today = t.id in checked_task_ids
        result.append(out)
    return result


@router.post("/tasks", response_model=PlanTaskOut)
def create_task(req: PlanTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == req.plan_id, StudyPlan.student_id == current_user.id).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    if req.stage_id:
        stage = db.query(PlanStage).filter(PlanStage.id == req.stage_id, PlanStage.plan_id == req.plan_id).first()
        if not stage:
            raise HTTPException(404, "阶段不存在")
    task = PlanTask(
        plan_id=req.plan_id,
        stage_id=req.stage_id,
        title=req.title.strip(),
        description=req.description,
        due_date=_parse_date(req.due_date),
        priority=req.priority,
        order_index=req.order_index,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    out = PlanTaskOut.model_validate(task)
    out.plan_title = plan.title
    return out


@router.put("/tasks/{task_id}", response_model=PlanTaskOut)
def update_task(task_id: int, req: PlanTaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(PlanTask).join(StudyPlan, StudyPlan.id == PlanTask.plan_id).filter(
        PlanTask.id == task_id, StudyPlan.student_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    data = req.model_dump(exclude_unset=True)
    if "due_date" in data:
        data["due_date"] = _parse_date(data["due_date"])
    if "stage_id" in data and data["stage_id"] is not None:
        stage = db.query(PlanStage).filter(PlanStage.id == data["stage_id"], PlanStage.plan_id == task.plan_id).first()
        if not stage:
            raise HTTPException(404, "阶段不存在")
    old_status = task.status
    for k, v in data.items():
        if v is not None:
            setattr(task, k, v)
    # 状态流转：完成时自动打卡（默认 30 分钟占位，用户后可补记）
    if task.status == TaskStatus.DONE and old_status != TaskStatus.DONE:
        exists = db.query(PlanCheckin).filter(
            PlanCheckin.task_id == task.id,
            PlanCheckin.check_date == date.today(),
        ).first()
        if not exists:
            db.add(PlanCheckin(
                student_id=current_user.id,
                plan_id=task.plan_id,
                task_id=task.id,
                check_date=date.today(),
                minutes=30,
                note="完成任务自动打卡",
            ))
    db.commit()
    db.refresh(task)
    out = PlanTaskOut.model_validate(task)
    plan = db.query(StudyPlan).filter(StudyPlan.id == task.plan_id).first()
    out.plan_title = plan.title if plan else ""
    return out


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(PlanTask).join(StudyPlan, StudyPlan.id == PlanTask.plan_id).filter(
        PlanTask.id == task_id, StudyPlan.student_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    db.query(PlanCheckin).filter(PlanCheckin.task_id == task.id).delete(synchronize_session=False)
    db.delete(task)
    db.commit()
    return {"message": "deleted"}


# ==================== 打卡闭环 ====================

@router.post("/checkin", response_model=CheckinOut)
def create_checkin(req: CheckinCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == req.plan_id, StudyPlan.student_id == current_user.id).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    today = date.today()
    cin = PlanCheckin(
        student_id=current_user.id,
        plan_id=req.plan_id,
        task_id=req.task_id,
        check_date=today,
        minutes=max(1, min(req.minutes, 600)),
        note=req.note,
    )
    db.add(cin)
    # 关联任务则同步流转为已完成
    if req.task_id:
        task = db.query(PlanTask).filter(PlanTask.id == req.task_id, PlanTask.plan_id == req.plan_id).first()
        if task and task.status != TaskStatus.DONE:
            task.status = TaskStatus.DONE
    db.commit()
    db.refresh(cin)
    out = CheckinOut.model_validate(cin)
    out.plan_title = plan.title
    return out


@router.get("/checkins", response_model=list[CheckinOut])
def list_checkins(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(PlanCheckin).filter(PlanCheckin.student_id == current_user.id).order_by(
        PlanCheckin.check_date.desc()
    ).limit(90).all()
    plans = {p.id: p.title for p in db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id).all()}
    result = []
    for c in items:
        out = CheckinOut.model_validate(c)
        out.plan_title = plans.get(c.plan_id, "")
        result.append(out)
    return result


@router.get("/streak", response_model=StreakOut)
def get_streak(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    days = {c.check_date for c in db.query(PlanCheckin).filter(PlanCheckin.student_id == current_user.id).all()}
    today = date.today()

    # 当前连续：从今天（或昨天，若今天未打卡）往前数
    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)

    # 最长连续
    longest = 0
    run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        longest = max(longest, run)
        prev = d

    # 最近 7 天记录
    week = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    return StreakOut(
        current=current,
        longest=longest,
        today_checked=today in days,
        days=[d.isoformat() for d in sorted(days)],
    )


# ==================== 今日任务视图 ====================

@router.get("/today", response_model=list[TodayTaskOut])
def get_today(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date.today()
    plans = {p.id: p for p in db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id).all()}
    tasks = db.query(PlanTask).join(StudyPlan, StudyPlan.id == PlanTask.plan_id).filter(
        StudyPlan.student_id == current_user.id,
        PlanTask.status != TaskStatus.DONE,
    ).all()
    # 今天到期或逾期未完成 + 高优先级未完成
    due_today = [t for t in tasks if t.due_date and t.due_date <= today]
    no_due_high = [t for t in tasks if not t.due_date and t.priority.value == "high"]
    merged: dict[int, PlanTask] = {}
    for t in due_today + no_due_high:
        merged[t.id] = t
    checked_task_ids = {
        c.task_id for c in db.query(PlanCheckin).filter(
            PlanCheckin.student_id == current_user.id,
            PlanCheckin.check_date == today,
        ).all() if c.task_id
    }
    result = []
    for t in merged.values():
        p = plans.get(t.plan_id)
        result.append(TodayTaskOut(
            task_id=t.id,
            title=t.title,
            due_date=t.due_date,
            priority=t.priority.value,
            status=t.status.value,
            plan_id=t.plan_id,
            plan_title=p.title if p else "",
            checked_today=t.id in checked_task_ids,
        ))
    result.sort(key=lambda x: (x.due_date is None, x.due_date or date.max))
    return result


# ==================== 阶段任务流（闯关式进度 + AI 拆解/评估） ====================

def _serialize_stage(db: Session, s: PlanStage) -> PlanStageOut:
    tasks = db.query(PlanTask).filter(PlanTask.stage_id == s.id).all()
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    out = PlanStageOut.model_validate(s)
    out.task_total = total
    out.task_done = done
    out.done_rate = round(done / total * 100) if total else 0
    return out


def _get_plan_or_404(db: Session, student_id: int, plan_id: int) -> StudyPlan:
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.student_id == student_id).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    return plan


def _unlock_next_stage(db: Session, plan_id: int, current_order: int) -> None:
    """完成当前阶段后，解锁顺序上的下一个阶段（若有）。"""
    nxt = db.query(PlanStage).filter(
        PlanStage.plan_id == plan_id,
        PlanStage.order_index > current_order,
        PlanStage.status.in_([StageStatus.LOCKED, StageStatus.ACTIVE]),
    ).order_by(PlanStage.order_index.asc()).first()
    if nxt and nxt.status == StageStatus.LOCKED:
        nxt.status = StageStatus.ACTIVE


def _auto_complete_plan(db: Session, plan: StudyPlan) -> None:
    stages = db.query(PlanStage).filter(PlanStage.plan_id == plan.id).all()
    if stages and all(s.status == StageStatus.DONE for s in stages):
        plan.status = PlanStatus.COMPLETED


@router.get("/plans/{plan_id}/stages", response_model=list[PlanStageOut])
def list_stages(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """阶段任务流列表（按顺序）。"""
    _get_plan_or_404(db, current_user.id, plan_id)
    stages = db.query(PlanStage).filter(PlanStage.plan_id == plan_id).order_by(PlanStage.order_index.asc()).all()
    return [_serialize_stage(db, s) for s in stages]


@router.post("/plans/{plan_id}/stages/ai-generate", response_model=StageGenerateOut)
async def ai_generate_plan_stages(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """AI 推理出完成计划的小阶段目标（闯关阶段 + 每阶段任务）。"""
    plan = _get_plan_or_404(db, current_user.id, plan_id)
    existing = db.query(PlanStage).filter(PlanStage.plan_id == plan_id).count()
    if existing > 0:
        raise HTTPException(409, "该计划已有阶段，可继续手动添加或直接闯关")
    summary, stage_data = await ai_generate_stages(db, plan, current_user.id)
    created = persist_generated_stages(db, plan, stage_data, current_user.id)
    return StageGenerateOut(summary=summary, stages=[_serialize_stage(db, s) for s in created])


@router.post("/plans/{plan_id}/stages", response_model=PlanStageOut)
def create_stage(req: PlanStageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """手动添加阶段。"""
    plan = _get_plan_or_404(db, current_user.id, req.plan_id)
    max_order = db.query(PlanStage).filter(PlanStage.plan_id == plan.id).order_by(PlanStage.order_index.desc()).first()
    order = (max_order.order_index + 1) if max_order else 0
    # 无任何 active/done 阶段时，新阶段自动激活
    has_progress = db.query(PlanStage).filter(
        PlanStage.plan_id == plan.id,
        PlanStage.status.in_([StageStatus.ACTIVE, StageStatus.SUBMITTED, StageStatus.DONE]),
    ).count() > 0
    st = PlanStage(
        plan_id=plan.id,
        title=req.title.strip(),
        goal=req.goal,
        order_index=order,
        status=StageStatus.LOCKED if has_progress else StageStatus.ACTIVE,
        ai_generated=False,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return _serialize_stage(db, st)


@router.put("/stages/{stage_id}", response_model=PlanStageOut)
def update_stage(stage_id: int, req: PlanStageUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """编辑阶段 / 状态流转（含解锁下一阶段）。"""
    stage = db.query(PlanStage).join(StudyPlan, StudyPlan.id == PlanStage.plan_id).filter(
        PlanStage.id == stage_id, StudyPlan.student_id == current_user.id
    ).first()
    if not stage:
        raise HTTPException(404, "阶段不存在")
    data = req.model_dump(exclude_unset=True)
    old_status = stage.status
    for k, v in data.items():
        if v is not None:
            setattr(stage, k, v)
    if stage.status == StageStatus.DONE and old_status != StageStatus.DONE:
        _unlock_next_stage(db, stage.plan_id, stage.order_index)
        plan = db.query(StudyPlan).filter(StudyPlan.id == stage.plan_id).first()
        if plan:
            _auto_complete_plan(db, plan)
    db.commit()
    db.refresh(stage)
    return _serialize_stage(db, stage)


@router.delete("/stages/{stage_id}")
def delete_stage(stage_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """删除阶段（其下任务一并删除）。"""
    stage = db.query(PlanStage).join(StudyPlan, StudyPlan.id == PlanStage.plan_id).filter(
        PlanStage.id == stage_id, StudyPlan.student_id == current_user.id
    ).first()
    if not stage:
        raise HTTPException(404, "阶段不存在")
    db.query(PlanTask).filter(PlanTask.stage_id == stage.id).delete(synchronize_session=False)
    db.delete(stage)
    db.commit()
    return {"message": "deleted"}


@router.post("/stages/{stage_id}/submit", response_model=StageSubmitOut)
async def submit_stage(stage_id: int, req: StageSubmitRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """提交阶段成果 -> AI 评估打分、综合分析、指出不足、给出后续任务建议。"""
    if not req.result or not req.result.strip():
        raise HTTPException(400, "请填写阶段成果说明")
    stage = db.query(PlanStage).join(StudyPlan, StudyPlan.id == PlanStage.plan_id).filter(
        PlanStage.id == stage_id, StudyPlan.student_id == current_user.id
    ).first()
    if not stage:
        raise HTTPException(404, "阶段不存在")
    if stage.status == StageStatus.DONE:
        raise HTTPException(400, "该阶段已完成，无需重复提交")
    stage.submitted_result = req.result.strip()[:3000]
    stage.submitted_at = datetime.now(timezone.utc)
    if stage.status == StageStatus.LOCKED:
        stage.status = StageStatus.ACTIVE
    score, evaluation, weaknesses, suggestions = await ai_evaluate_stage(db, stage)
    stage.score = score
    stage.evaluation = evaluation
    stage.weaknesses = weaknesses
    stage.suggestions = suggestions
    stage.status = StageStatus.SUBMITTED
    db.commit()
    db.refresh(stage)
    return StageSubmitOut(
        id=stage.id, status=stage.status.value,
        score=stage.score, evaluation=stage.evaluation,
        weaknesses=stage.weaknesses, suggestions=stage.suggestions,
    )


# ==================== 数字赋能：AI 顺延/重排建议 ====================

async def _gen_suggest_by_llm(db: Session, plans: list, tasks: list, today: date) -> AISuggestOut:
    """LLM 生成顺延/重排建议；失败时回退规则"""
    try:
        cfg = _get_llm_config()
        if not cfg["api_key"]:
            raise RuntimeError("no api key")
        client = _get_client()
        plan_lines = "\n".join(
            f"- 计划[{p.id}] {p.title}（{p.start_date} ~ {p.end_date or '至今'}，预算剩余 {max(0, (p.end_date - today).days) if p.end_date else '—'} 天）"
            for p in plans
        )
        task_lines = "\n".join(
            f"- 任务[{t.id}] 「{t.title}」截止 {t.due_date or '未定'} 状态={t.status.value} 优先级={t.priority.value}"
            for t in tasks
        )
        prompt = (
            f"今天是 {today.isoformat()}。学生有以下学习计划与未完成/未开始任务：\n{plan_lines}\n{task_lines}\n"
            "请以 JSON 输出顺延与重排建议：{\"summary\": \"总体建议(60字内)\", \"items\": [{\"task_id\": 数字, \"suggest\": \"针对该任务的一句建议(40字内)\"}]}。"
            "只对未完成任务给出建议，任务ID必须来自上面列表。不要输出其他内容。"
        )
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )
        text = (resp.choices[0].message.content or "").strip()
        import json, re
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise RuntimeError("no json")
        data = json.loads(m.group(0))
        items = [AISuggestItem(task_id=i.get("task_id"), title="", suggest=i.get("suggest", "")) for i in data.get("items", [])]
        texts = {str(t.id): t for t in tasks}
        for it in items:
            t = texts.get(str(it.task_id))
            if t:
                it.title = t.title
                it.due_date = t.due_date
                it.status = t.status.value
        return AISuggestOut(summary=data.get("summary", ""), items=[i for i in items if i.task_id])
    except Exception:
        return _gen_suggest_by_rule(plans, tasks, today)


def _gen_suggest_by_rule(plans: list, tasks: list, today: date) -> AISuggestOut:
    summary = "根据当前进度，建议优先处理临近截止的高优先级任务；逾期任务顺延至最近空闲日，避免堆积。"
    items = []
    for t in sorted(tasks, key=lambda x: (x.due_date or date.max)):
        if t.status == TaskStatus.DONE:
            continue
        if t.due_date and t.due_date < today:
            items.append(AISuggestItem(
                task_id=t.id, title=t.title, due_date=t.due_date, status=t.status.value,
                suggest=f"已逾期 {abs((t.due_date - today).days)} 天，建议顺延至 {today + timedelta(days=2)} 并拆分小步完成",
            ))
        elif t.due_date and t.due_date <= today + timedelta(days=3):
            items.append(AISuggestItem(
                task_id=t.id, title=t.title, due_date=t.due_date, status=t.status.value,
                suggest="3 天内到期，建议今天起每天推进 25 分钟，按番茄钟拆解",
            ))
        elif t.priority.value == "high":
            items.append(AISuggestItem(
                task_id=t.id, title=t.title, due_date=t.due_date, status=t.status.value,
                suggest="高优先级任务，建议排在每日清单首位，先完成再处理其他",
            ))
    return AISuggestOut(summary=summary, items=items)


@router.post("/ai-suggest", response_model=AISuggestOut)
async def ai_suggest(
    plan_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id)
    if plan_id:
        query = query.filter(StudyPlan.id == plan_id)
    plans = query.all()
    task_query = db.query(PlanTask).join(StudyPlan, StudyPlan.id == PlanTask.plan_id).filter(
        StudyPlan.student_id == current_user.id
    )
    if plan_id:
        task_query = task_query.filter(PlanTask.plan_id == plan_id)
    tasks = task_query.all()
    if not tasks:
        return AISuggestOut(summary="当前没有待处理任务，先去创建学习计划吧", items=[])
    return await _gen_suggest_by_llm(db, plans, tasks, date.today())


# ==================== 站内提醒（逾期/到期） ====================

@router.get("/reminders")
def plan_reminders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """检查逾期任务/到期计划，生成站内通知，返回本次触发列表"""
    today = date.today()
    triggered = []
    plans = db.query(StudyPlan).filter(
        StudyPlan.student_id == current_user.id,
        StudyPlan.status != PlanStatus.COMPLETED,
    ).all()
    for p in plans:
        # 计划到期提醒
        if p.end_date and p.end_date == today + timedelta(days=1):
            triggered.append(f"计划《{p.title}》将于明天到期，请检查任务完成情况")
            create_notification(db, current_user.id, "计划即将到期",
                                f"学习计划《{p.title}》将于 {p.end_date} 到期，记得提交阶段成果。",
                                NotificationType.SYSTEM, link="/student/plan", related_id=p.id)
        if p.end_date and p.end_date < today and p.status == PlanStatus.ACTIVE:
            # 已逾期的计划若任务全部完成则置为完成
            tasks = db.query(PlanTask).filter(PlanTask.plan_id == p.id).all()
            if tasks and all(t.status == TaskStatus.DONE for t in tasks):
                p.status = PlanStatus.COMPLETED
                db.commit()
            else:
                triggered.append(f"计划《{p.title}》已到期但仍有任务未完成")
                create_notification(db, current_user.id, "计划已到期",
                                    f"学习计划《{p.title}》已到期，还有任务未完成，点击查看或用 AI 顺延建议重新排期。",
                                    NotificationType.SYSTEM, link="/student/plan", related_id=p.id)
        # 任务逾期提醒（同日去重：每天最多提醒一次）
        overdue_tasks = db.query(PlanTask).filter(
            PlanTask.plan_id == p.id,
            PlanTask.status != TaskStatus.DONE,
            PlanTask.due_date.isnot(None),
            PlanTask.due_date < today,
        ).all()
        for t in overdue_tasks:
            existed = db.query(PlanCheckin).filter(
                PlanCheckin.task_id == t.id,
                PlanCheckin.check_date == today,
            ).first()
            if not existed:
                triggered.append(f"任务「{t.title}」已逾期 {abs((t.due_date - today).days)} 天")
                create_notification(db, current_user.id, "任务逾期提醒",
                                    f"任务「{t.title}」（{p.title}）已逾期，建议使用 AI 顺延重新排期。",
                                    NotificationType.SYSTEM, link="/student/plan", related_id=t.id)
    db.commit()
    return {"triggered": triggered, "count": len(triggered)}


# ==================== 计划洞察（供成长页） ====================

@router.get("/insights")
def plan_insights(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plans = db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id).all()
    total_plans = len(plans)
    completed_plans = sum(1 for p in plans if p.status == PlanStatus.COMPLETED)
    active_plans = sum(1 for p in plans if p.status == PlanStatus.ACTIVE)
    today = date.today()
    expired_plans = sum(
        1 for p in plans
        if p.status == PlanStatus.ACTIVE and p.end_date and p.end_date < today
    )
    task_total = task_done = 0
    for p in plans:
        tasks = db.query(PlanTask).filter(PlanTask.plan_id == p.id).all()
        task_total += len(tasks)
        task_done += sum(1 for t in tasks if t.status == TaskStatus.DONE)
    checkin_total = db.query(PlanCheckin).filter(PlanCheckin.student_id == current_user.id).count()
    minutes_total = sum(
        c.minutes for c in db.query(PlanCheckin).filter(PlanCheckin.student_id == current_user.id).all()
    )
    risk = []
    if expired_plans > 0:
        risk.append(f"有 {expired_plans} 个计划已逾期，建议尽快收尾或调用 AI 顺延")
    if active_plans and task_total > 0 and task_done / task_total < 0.3:
        risk.append("整体任务完成率低于 30%，注意节奏，避免计划堆积")
    if not active_plans and not completed_plans:
        risk.append("还没有进行中的学习计划，建议从一个小目标开始")
    return {
        "total_plans": total_plans,
        "completed_plans": completed_plans,
        "active_plans": active_plans,
        "expired_plans": expired_plans,
        "task_total": task_total,
        "task_done": task_done,
        "done_rate": round(task_done / task_total * 100) if task_total else 0,
        "checkin_total": checkin_total,
        "minutes_total": minutes_total,
        "risk": risk,
    }