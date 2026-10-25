"""智能任务生成：把「评估后的待干预信号」聚合成教师待办，并落到对应日期。

信号来源（全部复用既有评估能力，不新增平行判定逻辑）：
1. 学情规则预警（频繁请假 / 近期学情沉默）—— alert_pipeline_service.scan_for_teacher；
2. 未闭环心理预警（中度及以上）—— crisis 的 AIDialogSummary；
3. AI 推荐联系名单（可选，由调用方传入 suggestions）。

设计要点：
- 每个信号都写入 due_at 与 remind_at，任务因此能直接出现在任务清单页的「日程视图」；
- 幂等：规则类按「规则+学生+当日」，预警类按 (source_type, source_id) 唯一键，重复点击不重复建。
"""
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.teacher_task import TaskPriority, TaskSourceType, TeacherTask
from app.models.user import User, UserRole
from app.services import alert_pipeline_service, teacher_task_service

logger = logging.getLogger(__name__)

# 未被闭环的中/重度预警才生成任务，避免轻度信号刷屏
_WATCH_LEVELS = (CrisisLevel.MODERATE, CrisisLevel.SEVERE)


def _teacher_student_ids(db: Session, teacher_id: int) -> list[int]:
    return [
        row[0]
        for row in db.query(User.id).filter(
            User.role == UserRole.STUDENT, User.tutor_id == teacher_id
        ).all()
    ]


def _crisis_tasks(db: Session, teacher_id: int, day: date) -> tuple[int, list[dict]]:
    """未闭环的心理预警 → 教师待办（截止/提醒落在明天，重度为高优先级）。"""
    student_ids = _teacher_student_ids(db, teacher_id)
    if not student_ids:
        return 0, []
    alerts = (
        db.query(AIDialogSummary)
        .filter(
            AIDialogSummary.student_id.in_(student_ids),
            AIDialogSummary.resolved.is_(False),
            AIDialogSummary.level.in_(_WATCH_LEVELS),
        )
        .all()
    )
    if not alerts:
        return 0, []

    names = {
        row[0]: row[1]
        for row in db.query(User.id, User.name).filter(User.id.in_({a.student_id for a in alerts})).all()
    }
    due = day + timedelta(days=1)

    created = 0
    items: list[dict] = []
    for alert in alerts:
        existing = (
            db.query(TeacherTask)
            .filter(
                TeacherTask.teacher_id == teacher_id,
                TeacherTask.source_type == TaskSourceType.ALERT,
                TeacherTask.source_id == alert.id,
            )
            .first()
        )
        if existing is not None:
            continue
        is_severe = alert.level == CrisisLevel.SEVERE
        name = names.get(alert.student_id, "该学生")
        teacher_task_service.create_task(
            db,
            teacher_id=teacher_id,
            title=f"心理预警跟进：{name}",
            detail=(alert.summary or "存在未闭环的心理预警，请及时跟进并记录处置")[:200],
            student_id=alert.student_id,
            due_at=due,
            remind_at=due,
            source_type=TaskSourceType.ALERT,
            source_id=alert.id,
            rule_code="crisis_open",
            priority=TaskPriority.HIGH if is_severe else TaskPriority.MID,
        )
        created += 1
        items.append({"student_id": alert.student_id, "student_name": name, "rule": "crisis_open"})
    return created, items


def auto_generate_for_teacher(
    db: Session,
    teacher_id: int,
    *,
    today: date | None = None,
    suggestions: list[dict] | None = None,
) -> dict:
    """执行一次「智能生成」：评估 → 建任务 → 返回本次新增明细。

    返回：{"created": n, "date": "YYYY-MM-DD", "breakdown": {...}, "items": [...]}
    """
    day = today or date.today()

    rule_result = alert_pipeline_service.scan_for_teacher(db, teacher_id, today=day)
    rule_created = int(rule_result.get("created") or 0)
    rule_items = rule_result.get("matched") or []

    crisis_created, crisis_items = _crisis_tasks(db, teacher_id, day)

    suggest_created = 0
    if suggestions:
        suggest_created = teacher_task_service.bulk_upsert_from_suggestions(db, teacher_id, suggestions)

    total = rule_created + crisis_created + suggest_created
    logger.info(
        "[TASK-AUTOGEN] teacher=%s rule=%s crisis=%s suggest=%s total=%s",
        teacher_id, rule_created, crisis_created, suggest_created, total,
    )
    return {
        "created": total,
        "date": day.isoformat(),
        "breakdown": {
            "rule": rule_created,
            "crisis": crisis_created,
            "suggest": suggest_created,
        },
        "items": list(rule_items) + list(crisis_items),
    }