"""学习计划阶段 AI 服务：AI 拆解阶段（任务流关卡）+ 阶段成果评估打分。

LLM 不可用/超时/解析失败时回退到规则生成，保证功能可用。
"""
import json
import logging
import re
from datetime import date

from app.models.plan import StudyPlan, PlanStage, PlanTask, TaskStatus, StageStatus, TaskPriority
from app.services.llm_service import _get_llm_config, _get_client

logger = logging.getLogger(__name__)

_parse_json = None  # 延迟导入 llm_service 的解析函数，避免循环


def _parse_json_loose(text: str) -> dict | None:
    global _parse_json
    if _parse_json is None:
        from app.services.llm_service import _parse_json_loose as _pj
        _parse_json = _pj
    return _parse_json(text)


# ==================== AI 拆解阶段 ====================

async def ai_generate_stages(db, plan: StudyPlan, student_id: int) -> tuple[str, list[dict]]:
    """AI 拆解计划为阶段任务流。

    返回 (summary, stage_data_list)，stage_data 形如：
    {"title": ..., "goal": ..., "tasks": [{"title": ..., "description": ...}]}
    LLM 失败时回退规则拆解。
    """
    try:
        cfg = _get_llm_config()
        if not cfg["api_key"]:
            raise RuntimeError("no api key")
        client = _get_client()
        today = date.today()
        days_left = (plan.end_date - today).days if plan.end_date else None
        prompt = (
            f"学生有一个学习计划，请把它拆解为 3-6 个循序渐进的阶段（里程碑/关卡），用于闯关式任务流。\n"
            f"计划标题：{plan.title}\n"
            f"计划目标：{plan.objective or '未填写'}\n"
            f"周期：{plan.start_date} 至 {plan.end_date or '至今'}"
            + (f"（剩余 {days_left} 天）" if days_left is not None else "")
            + "\n"
            "要求：\n"
            "1. 阶段按完成目标的先后逻辑排列，每阶段给出简短标题（如'基础夯实'）与阶段目标 goal（说明本阶段要达成什么，40字内）\n"
            "2. 每个阶段给出 1-4 个具体任务（title + 简短 description），任务要可执行、可量化\n"
            "3. 总任务量要符合剩余时间，避免过重\n"
            '只输出 JSON：{"summary": "拆解思路(40字内)", "stages": [{"title": "...", "goal": "...", "tasks": [{"title": "...", "description": "..."}]}]}\n'
            "不要输出其他文字。"
        )
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "").strip()
        data = _parse_json_loose(text)
        if not data or not isinstance(data.get("stages"), list):
            raise RuntimeError("bad json")
        stages = []
        for s in data["stages"][:6]:
            title = str(s.get("title") or "").strip()
            if not title:
                continue
            tasks = []
            for t in (s.get("tasks") or [])[:4]:
                tt = str(t.get("title") or "").strip()
                if tt:
                    tasks.append({
                        "title": tt,
                        "description": str(t.get("description") or "").strip() or None,
                    })
            stages.append({
                "title": title[:100],
                "goal": str(s.get("goal") or "").strip()[:500] or None,
                "tasks": tasks,
            })
        if stages:
            return str(data.get("summary") or "已为你拆解为阶段任务流"), stages
        raise RuntimeError("empty stages")
    except Exception as e:
        logger.warning("AI 拆解阶段失败，回退规则拆解: %s", e)
        return _rule_generate_stages(plan)


def _rule_generate_stages(plan: StudyPlan) -> tuple[str, list[dict]]:
    """规则兜底：按周期长度拆 3-6 段，每段 2 个通用任务。"""
    total_days = 14
    if plan.end_date:
        total_days = max(7, (plan.end_date - plan.start_date).days)
    n = min(6, max(3, (total_days + 6) // 7))
    per = max(2, total_days // n)
    stages = []
    for i in range(1, n + 1):
        stages.append({
            "title": f"阶段 {i}：推进",
            "goal": f"完成本阶段的学习与练习（第 {(i - 1) * per + 1}~{i * per} 天）",
            "tasks": [
                {"title": f"阶段{i}基础学习", "description": "按计划目标完成本阶段核心知识学习并做笔记"},
                {"title": f"阶段{i}实践练习", "description": "完成配套练习/项目，检验阶段成果"},
            ],
        })
    return "已按周期为你拆解为阶段任务流（规则模式）", stages


# ==================== 阶段成果 AI 评估 ====================

async def ai_evaluate_stage(db, stage: PlanStage) -> tuple[int, str, str, str]:
    """AI 评估阶段成果：返回 (score, evaluation, weaknesses, suggestions)。

    LLM 失败时回退规则评估。
    """
    tasks = db.query(PlanTask).filter(PlanTask.stage_id == stage.id).all()
    plan = db.query(StudyPlan).filter(StudyPlan.id == stage.plan_id).first()
    task_lines = "\n".join(
        f"- 「{t.title}」状态={'已完成' if t.status == TaskStatus.DONE else '未完成'}"
        for t in tasks
    ) or "- 无"
    try:
        cfg = _get_llm_config()
        if not cfg["api_key"]:
            raise RuntimeError("no api key")
        client = _get_client()
        prompt = (
            "学生提交了学习计划中一个阶段的成果，请严格评估并给出改进建议。\n"
            f"计划目标：{plan.objective or plan.title if plan else ''}\n"
            f"阶段：{stage.title}\n"
            f"阶段目标：{stage.goal or '未填写'}\n"
            f"阶段任务：\n{task_lines}\n"
            f"学生提交的成果：{stage.submitted_result or ''}\n"
            '只输出 JSON：{"score": 0-100的整数, "evaluation": "综合评估(120字内)", "weaknesses": "不足与改进点(100字内)", "suggestions": "对后续阶段任务的调整建议(100字内)"}\n'
            "不要输出其他文字。score 要结合任务完成情况与成果质量合理打分。"
        )
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "").strip()
        data = _parse_json_loose(text)
        if not data:
            raise RuntimeError("bad json")
        try:
            score = max(0, min(100, int(float(data.get("score", 60)))))
        except (TypeError, ValueError):
            score = 60
        return (
            score,
            str(data.get("evaluation") or "").strip()[:500],
            str(data.get("weaknesses") or "").strip()[:500],
            str(data.get("suggestions") or "").strip()[:500],
        )
    except Exception as e:
        logger.warning("AI 评估阶段失败，回退规则评估: %s", e)
        return _rule_evaluate_stage(stage, tasks)


def _rule_evaluate_stage(stage: PlanStage, tasks: list) -> tuple[int, str, str, str]:
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    rate = round(done / total * 100) if total else 0
    score = min(100, 40 + rate // 2) if total else 70
    evaluation = (
        f"已收到阶段成果。阶段任务完成 {done}/{total}（{rate}%）。"
        if total else "已收到阶段成果。"
    )
    weaknesses = "任务完成度不足，建议补齐未完成项并复盘。" if rate < 100 else "成果与目标的对应说明不够具体，建议补充量化产出。"
    suggestions = "下一阶段先复习本阶段薄弱点，再推进新内容，保持每天固定学习时长。"
    return score, evaluation, weaknesses, suggestions


# ==================== 入库 ====================

def persist_generated_stages(db, plan: StudyPlan, stages: list[dict], student_id: int) -> list[PlanStage]:
    """把 AI 拆解结果写入 plan_stages + 对应任务；返回新建阶段列表。"""
    created = []
    for i, s in enumerate(stages):
        order = i
        st = PlanStage(
            plan_id=plan.id,
            title=s["title"],
            goal=s.get("goal"),
            order_index=order,
            status=StageStatus.LOCKED,
            ai_generated=True,
        )
        db.add(st)
        db.flush()
        for j, t in enumerate(s.get("tasks") or []):
            db.add(PlanTask(
                plan_id=plan.id,
                stage_id=st.id,
                title=t["title"],
                description=t.get("description"),
                priority=TaskPriority.MEDIUM,
                order_index=j,
            ))
        created.append(st)
    # 解锁第一个阶段
    if created:
        created[0].status = StageStatus.ACTIVE
    db.commit()
    for st in created:
        db.refresh(st)
    return created
