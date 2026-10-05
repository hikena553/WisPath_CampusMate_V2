"""预警 pipeline 服务：扫描学情事件 → 命中规则 → 生成 alert 待办 → 分配给教师。

约束（规划）：
- 幂等：同一规则 + 同一学生 + 同一自然日只生成一次；
- 规则可配置：默认规则内置，可通过 SystemSetting(learning_alert_rules) 覆盖，不硬编码；
- 每日一次：以 SystemSetting(learning_alert_last_run) 记录上次执行日期，重复触发自动跳过。
"""
import json
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.learning_event import LearningEvent
from app.models.setting import SystemSetting
from app.models.teacher_task import TaskSourceType, TeacherTask
from app.models.user import User, UserRole
from app.services import learning_event_service, teacher_task_service

logger = logging.getLogger(__name__)

RULES_KEY = "learning_alert_rules"
LAST_RUN_KEY = "learning_alert_last_run"

# 扫描候选窗口：近 90 天有学情事件的学生（避免全表扫描）
CANDIDATE_WINDOW_DAYS = 90

DEFAULT_RULES: list[dict] = [
    {
        "code": "leave_frequent",
        "name": "频繁请假",
        "verb": "leave.apply",
        "threshold": 3,
        "window_days": 30,
        "metric_label": "近 30 天请假次数",
        "due_in_days": 1,
    },
    {
        "code": "low_activity",
        "name": "近期学情沉默",
        "metric": "total_events",
        "threshold": 0,
        "window_days": 14,
        "baseline_days": 90,
        "metric_label": "近 14 天学情事件数",
        "due_in_days": 3,
    },
]


def _get_setting(db: Session, key: str) -> str | None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else None


def _set_setting(db: Session, key: str, value: str, description: str = "") -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value, description=description))
    db.commit()


def load_rules(db: Session) -> list[dict]:
    """读取规则：优先 SystemSetting 配置，缺省回退内置默认规则。"""
    raw = _get_setting(db, RULES_KEY)
    if not raw:
        return [dict(r) for r in DEFAULT_RULES]
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("预警规则配置解析失败，回退默认规则")
        return [dict(r) for r in DEFAULT_RULES]
    if not isinstance(data, list) or not data:
        return [dict(r) for r in DEFAULT_RULES]

    rules: list[dict] = []
    for item in data:
        if not isinstance(item, dict) or not item.get("code"):
            continue
        rules.append(
            {
                "code": str(item["code"]),
                "name": str(item.get("name") or item["code"]),
                "verb": item.get("verb"),
                "metric": item.get("metric"),
                "threshold": int(item.get("threshold", 1)),
                "window_days": int(item.get("window_days", 30)),
                "baseline_days": item.get("baseline_days"),
                "metric_label": str(item.get("metric_label") or ""),
                "due_in_days": int(item.get("due_in_days", 1)),
            }
        )
    return rules or [dict(r) for r in DEFAULT_RULES]


def _evaluate(db: Session, rule: dict, student_id: int) -> tuple[float, bool]:
    """返回 (指标值, 是否命中)。"""
    window = int(rule.get("window_days") or 30)

    if rule.get("verb"):
        value = learning_event_service.count_by_verb(db, student_id, str(rule["verb"]), window)
        return value, value >= int(rule.get("threshold", 1))

    if rule.get("metric") == "total_events":
        agg = learning_event_service.aggregate(db, student_id, days=window)
        value = float(agg["total"])
        matched = value <= int(rule.get("threshold", 0))
        baseline = rule.get("baseline_days")
        if matched and baseline:
            # 仅在「曾经活跃但近期沉默」时命中，避免对从未有事件的学生产生噪音
            base_agg = learning_event_service.aggregate(db, student_id, days=int(baseline))
            matched = base_agg["total"] > 0
        return value, matched

    return 0.0, False


def _already_created_today(
    db: Session, *, teacher_id: int, student_id: int, rule_code: str, day: date
) -> bool:
    day_start = datetime.combine(day, datetime.min.time())
    return (
        db.query(TeacherTask)
        .filter(
            TeacherTask.teacher_id == teacher_id,
            TeacherTask.source_type == TaskSourceType.ALERT,
            TeacherTask.student_id == student_id,
            TeacherTask.rule_code == rule_code,
            TeacherTask.created_at >= day_start,
        )
        .first()
        is not None
    )


def scan(
    db: Session,
    *,
    force: bool = False,
    today: date | None = None,
    rules: list[dict] | None = None,
) -> dict:
    """执行一次预警扫描。`force=True` 时忽略「每日一次」限制（手动触发场景）。"""
    day = today or date.today()
    day_iso = day.isoformat()

    if not force and _get_setting(db, LAST_RUN_KEY) == day_iso:
        return {"date": day_iso, "skipped": True, "reason": "今日已执行", "created": 0, "scanned": 0}

    active_rules = rules or load_rules(db)
    candidate_ids = learning_event_service.distinct_actors(db, days=CANDIDATE_WINDOW_DAYS)

    created = 0
    matched: list[dict] = []

    for student_id in candidate_ids:
        student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
        if not student or not student.tutor_id:
            continue  # 无辅导员则无处派单

        for rule in active_rules:
            value, hit = _evaluate(db, rule, student_id)
            if not hit:
                continue
            if _already_created_today(
                db,
                teacher_id=student.tutor_id,
                student_id=student_id,
                rule_code=rule["code"],
                day=day,
            ):
                continue

            label = rule.get("metric_label") or "指标"
            teacher_task_service.create_task(
                db,
                teacher_id=student.tutor_id,
                title=f"{rule['name']}：{student.name}",
                detail=f"{label}为 {value:g}，命中规则 {rule['code']}，请及时跟进",
                student_id=student_id,
                due_at=day + timedelta(days=int(rule.get("due_in_days", 1))),
                source_type=TaskSourceType.ALERT,
                # 不使用 source_id：避免与其它模块的 alert 任务争用唯一键
                source_id=None,
                rule_code=rule["code"],
            )
            created += 1
            matched.append({"student_id": student_id, "rule": rule["code"], "value": value})

    _set_setting(
        db,
        LAST_RUN_KEY,
        day_iso,
        description="预警 pipeline 上次执行日期（每日一次）",
    )
    logger.info("[ALERT-PIPELINE] date=%s scanned=%s created=%s", day_iso, len(candidate_ids), created)
    return {
        "date": day_iso,
        "skipped": False,
        "scanned": len(candidate_ids),
        "created": created,
        "matched": matched,
    }


def recent_alert_tasks(db: Session, teacher_id: int, days: int = 7, limit: int = 50) -> list[dict]:
    """近 N 天由预警 pipeline 生成的任务（供教师端查看）。"""
    since = datetime.now() - timedelta(days=days)
    rows = (
        db.query(TeacherTask)
        .filter(
            TeacherTask.teacher_id == teacher_id,
            TeacherTask.source_type == TaskSourceType.ALERT,
            TeacherTask.rule_code.isnot(None),
            TeacherTask.created_at >= since,
        )
        .order_by(TeacherTask.created_at.desc(), TeacherTask.id.desc())
        .limit(limit)
        .all()
    )
    return [teacher_task_service.serialize_one(db, t) for t in rows]


def count_events(db: Session, student_id: int, days: int = 30) -> int:
    """便捷统计（测试 / 调试用）。"""
    return int(
        db.query(LearningEvent)
        .filter(
            LearningEvent.actor_id == student_id,
            LearningEvent.occurred_at >= datetime.now() - timedelta(days=days),
        )
        .count()
    )