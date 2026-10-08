"""AI 学情助手：读学情数据底座聚合成风险画像 → 调 LLM 生成辅导建议。

规划硬约束：
- 建议必须可溯源：结论只能来自 profile.evidence，不给无据结论；
- LLM 调用失败要有降级文案（返回规则化建议），保证教师端可用；
- 结果可一键转 TeacherTask，形成「画像 → 建议 → 执行」闭环。
"""
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.care_record import CareRecord
from app.models.crisis import AIDialogSummary
from app.models.growth import GrowthRecord
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.teacher_task import TaskSourceType, TaskStatus, TeacherTask
from app.models.user import User
from app.services import learning_event_service, teacher_task_service

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 30


def _safe_enum(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def build_profile(db: Session, student_id: int, days: int = DEFAULT_WINDOW_DAYS) -> dict:
    """构建可溯源的风险画像：每条指标都带 evidence，结论有据可查。"""
    since_dt = datetime.now() - timedelta(days=days)
    since_date = date.today() - timedelta(days=days)

    # ① 学情事件底座
    learning = learning_event_service.aggregate(db, student_id, days=days)

    # ② 请假（窗口内非驳回）
    leave_total = (
        db.query(func.count(LeaveRequest.id))
        .filter(
            LeaveRequest.student_id == student_id,
            LeaveRequest.created_at >= since_dt,
            LeaveRequest.status != LeaveStatus.REJECTED,
        )
        .scalar()
        or 0
    )
    leave_pending = (
        db.query(func.count(LeaveRequest.id))
        .filter(LeaveRequest.student_id == student_id, LeaveRequest.status == LeaveStatus.PENDING)
        .scalar()
        or 0
    )

    # ③ 危机预警（最新未处理）
    latest_crisis = (
        db.query(AIDialogSummary)
        .filter(AIDialogSummary.student_id == student_id)
        .order_by(AIDialogSummary.created_at.desc())
        .first()
    )
    crisis_level = _safe_enum(latest_crisis.level) if latest_crisis else ""
    crisis_unresolved = bool(latest_crisis and not latest_crisis.resolved)

    # ④ 关怀侧写与成长记录
    care_total = (
        db.query(func.count(CareRecord.id))
        .filter(
            CareRecord.student_id == student_id,
            CareRecord.is_deleted.is_(False),
            CareRecord.created_at >= since_dt,
        )
        .scalar()
        or 0
    )
    growth_total = (
        db.query(func.count(GrowthRecord.id))
        .filter(GrowthRecord.student_id == student_id)
        .scalar()
        or 0
    )

    # ⑤ 未办结跟进任务
    open_tasks = (
        db.query(func.count(TeacherTask.id))
        .filter(
            TeacherTask.student_id == student_id,
            TeacherTask.status.in_([TaskStatus.PENDING, TaskStatus.CONTACTED, TaskStatus.CARED]),
        )
        .scalar()
        or 0
    )

    evidence = [
        {"source": "learning_events", "label": f"近{days}天学情事件数", "value": learning["total"]},
        {"source": "leave", "label": f"近{days}天请假次数", "value": int(leave_total)},
        {"source": "leave", "label": "待审批请假", "value": int(leave_pending)},
        {"source": "crisis", "label": "最新预警等级", "value": crisis_level or "无"},
        {"source": "care_record", "label": f"近{days}天关怀侧写", "value": int(care_total)},
        {"source": "growth", "label": "成长记录总数", "value": int(growth_total)},
        {"source": "teacher_task", "label": "未办结跟进任务", "value": int(open_tasks)},
    ]

    # 风险等级：完全由上面的事实推导，避免无据结论
    risk_level = "low"
    reasons: list[str] = []
    if crisis_unresolved and crisis_level in ("moderate", "severe"):
        risk_level = "high" if crisis_level == "severe" else "medium"
        reasons.append(f"存在未处理的{crisis_level}危机预警")
    if int(leave_total) >= 3:
        risk_level = "high"
        reasons.append(f"近{days}天请假 {int(leave_total)} 次")
    elif int(leave_total) == 2 and risk_level == "low":
        risk_level = "medium"
        reasons.append(f"近{days}天请假 {int(leave_total)} 次")
    if learning["total"] == 0:
        reasons.append(f"近{days}天无学情事件")
    if int(open_tasks) >= 3 and risk_level == "low":
        risk_level = "medium"
        reasons.append(f"未办结跟进任务 {int(open_tasks)} 条")

    return {
        "student_id": student_id,
        "days": days,
        "risk_level": risk_level,
        "risk_reasons": reasons,
        "metrics": {
            "learning_total": learning["total"],
            "leave_total": int(leave_total),
            "leave_pending": int(leave_pending),
            "crisis_level": crisis_level,
            "care_total": int(care_total),
            "growth_total": int(growth_total),
            "open_tasks": int(open_tasks),
        },
        "by_verb": learning["by_verb"],
        "by_object": learning["by_object"],
        "recent_events": learning["recent"][:10],
        "evidence": evidence,
        "generated_at": datetime.now().isoformat(),
    }


def _fallback_advice(profile: dict, student_name: str) -> str:
    """LLM 不可用时的降级建议：直接由画像事实拼装，保证有据可依。"""
    m = profile["metrics"]
    lines = [f"{student_name}当前风险等级：{profile['risk_level']}。"]
    if profile["risk_reasons"]:
        lines.append("主要依据：" + "；".join(profile["risk_reasons"]) + "。")
    else:
        lines.append(f"近{profile['days']}天未发现明显异常。")
    if m["leave_total"] >= 3:
        lines.append("建议：约谈学生了解请假原因，必要时联系家长。")
    if m["crisis_level"] in ("moderate", "severe"):
        lines.append("建议：尽快安排谈心，按危机干预流程处置并记录。")
    if m["learning_total"] == 0:
        lines.append("建议：主动发起一次学情沟通，恢复数据触达。")
    if m["open_tasks"] > 0:
        lines.append(f"提示：还有 {m['open_tasks']} 条跟进任务未办结。")
    return "".join(lines)


async def generate_advice(profile: dict, student_name: str) -> tuple[str, bool, str]:
    """调用 LLM 生成辅导建议。返回 (建议, 是否降级, 降级原因)。"""
    from app.services.llm_service import _get_client, _get_llm_config

    facts = "\n".join(f"- {e['label']}：{e['value']}" for e in profile["evidence"])
    prompt = (
        f"你是高校辅导员的工作助手。请基于以下**已核实事实**，为辅导员生成对学生「{student_name}」的辅导建议。\n\n"
        f"事实清单：\n{facts}\n\n"
        f"系统判定风险等级：{profile['risk_level']}；依据：{'；'.join(profile['risk_reasons']) or '无'}\n\n"
        "要求：\n"
        "1. 只能使用上述事实，不得编造任何未给出的信息；\n"
        "2. 用 3 条以内的要点给出可执行动作（先做什么、再做什么）；\n"
        "3. 控制在 150 字以内，纯文本，不要 Markdown 标记。"
    )

    config = _get_llm_config()
    if not config.get("api_key"):
        return _fallback_advice(profile, student_name), True, "未配置 LLM API Key"

    try:
        resp = await _get_client().chat.completions.create(
            model=config.get("agent_model") or config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return _fallback_advice(profile, student_name), True, "模型返回为空"
        return text, False, ""
    except Exception as exc:
        logger.warning("学情建议生成失败，降级为规则建议: %s", exc)
        return _fallback_advice(profile, student_name), True, f"模型调用失败: {exc}"


async def get_insight(db: Session, student_id: int, days: int = DEFAULT_WINDOW_DAYS) -> dict:
    student = db.query(User).filter(User.id == student_id).first()
    name = student.name if student else "该学生"
    profile = build_profile(db, student_id, days=days)
    advice, degraded, reason = await generate_advice(profile, name)
    return {
        "student_id": student_id,
        "student_name": name,
        "profile": profile,
        "advice": advice,
        "degraded": degraded,
        "degrade_reason": reason,
    }


def to_task(db: Session, *, teacher_id: int, student_id: int, advice: str, risk_level: str = "low") -> TeacherTask:
    """一键转跟进任务（画像 → 执行 闭环）。"""
    return teacher_task_service.create_task(
        db,
        teacher_id=teacher_id,
        title=f"学情跟进：{_student_name(db, student_id)}",
        detail=advice,
        student_id=student_id,
        due_at=date.today() + timedelta(days=3 if risk_level != "high" else 1),
        source_type=TaskSourceType.CARE_PLAN,
        source_id=student_id,
    )


def _student_name(db: Session, student_id: int) -> str:
    row = db.execute(select(User.name).where(User.id == student_id)).first()
    return row[0] if row else "该学生"