"""学习计划/成长画像工具 handlers：计划概览、闯关关卡、关卡成果 AI 评估、成长画像。"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.growth import GrowthRecord
from app.models.plan import (
    GoalStatus,
    GrowthGoal,
    PlanCheckin,
    PlanStage,
    PlanStatus,
    PlanTask,
    StageStatus,
    StudyPlan,
    TaskStatus,
)
from app.models.user import User
from app.utils.enum_helpers import safe_enum_str




# ============ 学习计划 / 作品集 / 社区 / 资源 / 成长画像工具 ============

_TASK_STATUS_NAMES = {"todo": "待办", "doing": "进行中", "done": "已完成"}
_TASK_PRIORITY_NAMES = {"high": "高", "medium": "中", "low": "低"}


def _query_plan_overview(db: Session, args: dict, user: User) -> dict:
    today = date.today()
    goals = db.query(GrowthGoal).filter(
        GrowthGoal.student_id == user.id, GrowthGoal.status == GoalStatus.ACTIVE
    ).order_by(GrowthGoal.created_at.desc()).all()
    plans = db.query(StudyPlan).filter(
        StudyPlan.student_id == user.id, StudyPlan.status == PlanStatus.ACTIVE
    ).order_by(StudyPlan.created_at.desc()).limit(20).all()

    plan_list = []
    for p in plans:
        tasks = db.query(PlanTask).filter(PlanTask.plan_id == p.id).all()
        done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        plan_list.append({
            "id": p.id,
            "title": p.title,
            "objective": p.objective or "",
            "stage": p.stage or "",
            "start_date": str(p.start_date),
            "end_date": str(p.end_date) if p.end_date else "",
            "task_total": len(tasks),
            "task_done": done,
            "done_rate": round(done * 100 / len(tasks)) if tasks else 0,
        })

    today_tasks = db.query(PlanTask).join(StudyPlan, StudyPlan.id == PlanTask.plan_id).filter(
        StudyPlan.student_id == user.id,
        PlanTask.due_date == today,
        PlanTask.status != TaskStatus.DONE,
    ).order_by(PlanTask.priority).all()
    today_checked = db.query(PlanCheckin).filter(
        PlanCheckin.student_id == user.id, PlanCheckin.check_date == today
    ).first() is not None

    streak = 0
    d = today
    while True:
        cur = db.query(PlanCheckin).filter(PlanCheckin.student_id == user.id, PlanCheckin.check_date == d).first()
        if not cur:
            break
        streak += 1
        d = d - timedelta(days=1)

    goals_data = [{"id": g.id, "goal_type": g.goal_type, "title": g.title, "progress": g.progress,
                   "target_date": str(g.target_date) if g.target_date else ""} for g in goals]
    tasks_data = [{"id": t.id, "plan_id": t.plan_id, "title": t.title, "due_date": str(t.due_date),
                   "priority": _TASK_PRIORITY_NAMES.get(safe_enum_str(t.priority, ""), "中")} for t in today_tasks]

    msg = f"进行中的计划 {len(plan_list)} 个，长期目标 {len(goals_data)} 个，今日待办 {len(tasks_data)} 项"
    if today_checked:
        msg += f"，今日已打卡（连续 {streak} 天）"
    else:
        msg += "，今日尚未打卡"
    return {
        "message": msg,
        "goals": goals_data,
        "plans": plan_list,
        "today_tasks": tasks_data,
        "checked_today": today_checked,
        "streak_days": streak,
    }


_STAGE_STATUS_NAMES = {"locked": "未解锁", "active": "进行中", "submitted": "待确认", "done": "已完成"}


def _query_plan_stages(db: Session, args: dict, user: User) -> dict:
    """查询计划的闯关关卡（阶段任务流）"""
    plan_id = args.get("plan_id")
    query = db.query(StudyPlan).filter(
        StudyPlan.student_id == user.id,
        StudyPlan.status == PlanStatus.ACTIVE,
    )
    if plan_id:
        query = query.filter(StudyPlan.id == int(plan_id))
    plans = query.order_by(StudyPlan.created_at.desc()).all()
    if not plans:
        return {"message": "暂无进行中的学习计划", "plans": []}

    result_plans = []
    for p in plans:
        stages = db.query(PlanStage).filter(PlanStage.plan_id == p.id).order_by(PlanStage.order_index.asc()).all()
        stage_list = []
        for s in stages:
            tasks = db.query(PlanTask).filter(PlanTask.stage_id == s.id).all()
            done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
            key = safe_enum_str(s.status, "locked")
            stage_list.append({
                "id": s.id,
                "title": s.title,
                "goal": s.goal or "",
                "status": _STAGE_STATUS_NAMES.get(key, key),
                "status_key": key,
                "score": s.score,
                "evaluation": s.evaluation or "",
                "weaknesses": s.weaknesses or "",
                "suggestions": s.suggestions or "",
                "submitted_result": s.submitted_result or "",
                "task_total": len(tasks),
                "task_done": done,
                "done_rate": round(done * 100 / len(tasks)) if tasks else 0,
            })
        result_plans.append({"id": p.id, "title": p.title, "stages": stage_list})
    return {"message": f"查询到 {len(result_plans)} 个计划的关卡任务流", "plans": result_plans}


async def _submit_plan_stage(db: Session, args: dict, user: User) -> dict:
    """提交关卡成果 -> AI 评估打分、指出不足、给出后续建议"""
    from app.services.plan_stage_service import ai_evaluate_stage
    stage_id = args.get("stage_id")
    result_text = str(args.get("result") or "").strip()
    if not stage_id:
        return {"error": "缺少关卡ID（stage_id）"}
    if not result_text:
        return {"error": "请填写阶段成果说明"}
    stage = db.query(PlanStage).join(StudyPlan, StudyPlan.id == PlanStage.plan_id).filter(
        PlanStage.id == int(stage_id), StudyPlan.student_id == user.id
    ).first()
    if not stage:
        return {"error": "关卡不存在或不属于当前学生"}
    if safe_enum_str(stage.status, "") == "done":
        return {"error": "该关卡已完成，无需重复提交"}
    stage.submitted_result = result_text[:3000]
    stage.submitted_at = datetime.now(timezone.utc)
    if safe_enum_str(stage.status, "") == "locked":
        stage.status = StageStatus.ACTIVE
    score, evaluation, weaknesses, suggestions = await ai_evaluate_stage(db, stage)
    stage.score = score
    stage.evaluation = evaluation
    stage.weaknesses = weaknesses
    stage.suggestions = suggestions
    stage.status = StageStatus.SUBMITTED
    db.commit()
    return {
        "message": f"✅ 已提交关卡「{stage.title}」成果，AI 评分 {score} 分",
        "stage_id": stage.id,
        "status": "submitted",
        "score": score,
        "evaluation": evaluation,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
    }


# ============ 成长画像工具 ============


def _query_profile_overview(db: Session, args: dict, user: User) -> dict:
    skills_data = user.skills_json or {"skills": [], "interests": []}
    skills = [s["name"] if isinstance(s, dict) else str(s) for s in skills_data.get("skills", [])]
    interests = [str(i) for i in skills_data.get("interests", [])]

    goals = db.query(GrowthGoal).filter(
        GrowthGoal.student_id == user.id, GrowthGoal.status == GoalStatus.ACTIVE
    ).order_by(GrowthGoal.created_at.desc()).limit(10).all()
    goals_data = [{"goal_type": g.goal_type, "title": g.title, "progress": g.progress,
                   "target_date": str(g.target_date) if g.target_date else ""} for g in goals]

    record_count = db.query(GrowthRecord).filter(GrowthRecord.student_id == user.id).count()
    today = date.today()
    checkin_30d = db.query(PlanCheckin).filter(
        PlanCheckin.student_id == user.id, PlanCheckin.check_date >= today - timedelta(days=30)
    ).count()
    return {
        "message": f"画像：技能 {len(skills)} 项、兴趣 {len(interests)} 项、长期目标 {len(goals_data)} 个、成长记录 {record_count} 条、近30天打卡 {checkin_30d} 天",
        "skills": skills,
        "interests": interests,
        "goals": goals_data,
        "growth_record_count": record_count,
        "checkin_last_30d": checkin_30d,
    }
