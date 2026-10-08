"""AI 主动触达引擎（proactive 功能 A/B/C 的规则层）。

与旧版的区别：
1. 触发器不再要求「存在画像快照」——统一从 proactive_signals.gather_signals 取真实信号
   （课表/考试/成绩/待办/成长档案/请假/对话活跃度），快照存在时其画像字段作为补充；
2. 新增一批学生视角的真实规则（临考、不及格、即将上课、待办逾期、请假结果、成长档案断档）；
3. 修正按角色截断顺序：先按 target_role 过滤再排序截断，避免教师级动作挤掉学生可见动作；
4. 里程碑改为「跨越 25 分档位」判定（旧的 growth_score % 25 == 0 浮点取模几乎不可能命中）。

保留能力：S6 幂等（48h 查重）、全量评估防重入锁、事务化提交。
"""
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.crisis import AIDialogSummary
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.services.proactive_signals import StudentSignals, gather_signals

logger = logging.getLogger(__name__)

MAX_PER_STUDENT = 3
MILESTONE_STEP = 25


class ProactiveAction(BaseModel):
    trigger: str
    student_id: int
    priority: int
    action_type: str
    title: str
    content: str
    target_role: str


class BaseTrigger(ABC):
    @abstractmethod
    def evaluate(self, db: Session, student: User, signals: StudentSignals) -> ProactiveAction | None: ...


def _action(trigger: str, student: User, priority: int, action_type: str,
            title: str, content: str, target_role: str) -> ProactiveAction:
    return ProactiveAction(
        trigger=trigger, student_id=student.id, priority=priority,
        action_type=action_type, title=title, content=content, target_role=target_role,
    )


def _latest_crisis(db: Session, student_id: int):
    return db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).first()


_CRISIS_LEVEL_RISK = {"severe": 85.0, "moderate": 65.0, "mild": 40.0, "normal": 0.0}


# ═══════════════════════════════════════════════════════════
# 教师视角：危机升级 / 成绩下滑
# ═══════════════════════════════════════════════════════════

class CrisisEscalationTrigger(BaseTrigger):
    """心理风险升级。

    风险来源优先级：
    1. 画像快照的 psychological_risk（有快照时）；
    2. 无快照时，由最新一条未解除的危机记录等级推断（severe→85 / moderate→65 / mild→40）。

    保留旧行为：危机记录已解除则不再升级（避免对已处理事件反复打扰导师）。
    """

    def evaluate(self, db, student, signals):
        latest = _latest_crisis(db, student.id)
        risk = signals.risk_score
        if risk is None:
            if not latest or latest.resolved:
                return None
            risk = _CRISIS_LEVEL_RISK.get(latest.level.value, 0.0)
        elif latest is not None and latest.resolved:
            return None
        if risk is None:
            return None
        if risk > 75:
            return _action(
                "crisis_escalation", student, 90, "escalation",
                f"高危预警：{student.name}",
                f"心理风险评分 {int(risk)}，建议立即联系辅导员并跟进干预",
                "teacher",
            )
        if risk > 50:
            return _action(
                "crisis_escalation", student, 70, "notification",
                f"注意：{student.name} 的心理状态变化",
                f"心理风险评分 {int(risk)}，请关注学生状态",
                "teacher",
            )
        return None


class GradeDropTrigger(BaseTrigger):
    """学业下滑（教师视角）：成绩轨迹下降，且学业分偏低（无快照时按最新均绩 < 2.0 兜底）"""

    def evaluate(self, db, student, signals):
        if signals.grade_trajectory != "declining":
            return None
        low_academic = signals.academic_score is not None and signals.academic_score < 50
        low_gpa = signals.latest_gpa is not None and signals.latest_gpa < 2.0
        if not (low_academic or low_gpa):
            return None
        detail = (
            f"学业评分 {round(signals.academic_score)}"
            if low_academic
            else f"最新学期均绩 {signals.latest_gpa}"
        )
        return _action(
            "grade_drop", student, 60, "notification",
            f"学业关注：{student.name}",
            f"{detail}，成绩呈下降趋势，建议提供学业支持",
            "teacher",
        )


# ═══════════════════════════════════════════════════════════
# 学生视角：考试 / 成绩 / 课程 / 待办 / 请假 / 活跃度 / 成长档案 / 里程碑
# ═══════════════════════════════════════════════════════════

class ExamSoonTrigger(BaseTrigger):
    """临近期末考试提醒：3 天内高优先级，7 天内一般优先级"""

    def evaluate(self, db, student, signals):
        if not signals.upcoming_exams:
            return None
        nearest = signals.upcoming_exams[0]
        days = nearest["days_left"]
        when = "今天" if days == 0 else "明天" if days == 1 else f"{days} 天后"
        where = f"，地点 {nearest['location']}" if nearest["location"] else ""
        priority = 78 if days <= 3 else 62
        more = f"（共 {len(signals.upcoming_exams)} 场考试在 7 天内）" if len(signals.upcoming_exams) > 1 else ""
        return _action(
            "exam_soon", student, priority, "system_message",
            "临近考试提醒",
            f"{when}考《{nearest['course_name']}》{nearest['start_time']}{where}，记得提前复习{more}",
            "student",
        )


class GradeRiskTrigger(BaseTrigger):
    """成绩风险（学生视角）：最新学期有不及格，或均绩明显下滑"""

    def evaluate(self, db, student, signals):
        if signals.failing_courses:
            names = "、".join(f"《{c['course_name']}》" for c in signals.failing_courses[:2])
            extra = f"等 {len(signals.failing_courses)} 门" if len(signals.failing_courses) > 1 else ""
            return _action(
                "grade_risk", student, 68, "system_message",
                "成绩需要关注",
                f"{names}{extra}未及格，建议尽快联系老师了解补考/重修安排",
                "student",
            )
        if signals.grade_trajectory == "declining" and signals.latest_gpa is not None:
            return _action(
                "grade_risk", student, 55, "system_message",
                "绩点有所下滑",
                f"最新学期均绩 {signals.latest_gpa}"
                + (f"（上一学期 {signals.prev_gpa}）" if signals.prev_gpa is not None else "")
                + "，可以找我做一次学情分析",
                "student",
            )
        return None


class UpcomingCourseTrigger(BaseTrigger):
    """即将上课提醒：90 分钟内出发提示；否则当天仍有课时给一条轻提示"""

    def evaluate(self, db, student, signals):
        course = signals.next_course
        if course is None:
            return None
        minutes_left = signals.next_course_minutes_left or 0
        place = f"，地点 {course.location}" if course.location else ""
        if minutes_left <= 90:
            return _action(
                "class_soon", student, 70, "system_message",
                "下一节课快开始了",
                f"还有 {minutes_left} 分钟上课：{course.start_time}《{course.name}》{place}",
                "student",
            )
        remaining = len([c for c in signals.today_courses if c.start_minutes >= signals.now_minutes])
        return _action(
            "class_today", student, 32, "system_message",
            "今日课程安排",
            f"今天还有 {remaining} 节课，下一节 {course.start_time}《{course.name}》{place}",
            "student",
        )


class TodoOverdueTrigger(BaseTrigger):
    """学习计划待办逾期提醒"""

    def evaluate(self, db, student, signals):
        if not signals.overdue_tasks:
            return None
        top = signals.overdue_tasks[0]
        title = f"有 {len(signals.overdue_tasks)} 项待办已逾期" if len(signals.overdue_tasks) > 1 else "有一项待办已逾期"
        due = top["due_date"].strftime("%m-%d") if top["due_date"] else ""
        return _action(
            "todo_overdue", student, 62, "system_message",
            title,
            f"《{top['title']}》已逾期 {top['days_overdue']} 天（截止 {due}），建议今天先处理",
            "student",
        )


class LeaveStatusTrigger(BaseTrigger):
    """请假：待审批提醒 / 近 7 天审批结果通知"""

    def evaluate(self, db, student, signals):
        if signals.pending_leaves:
            return _action(
                "leave_pending", student, 45, "system_message",
                "请假申请审批中",
                f"你有 {signals.pending_leaves} 条请假申请等待导师审批，结果出来我会第一时间告诉你",
                "student",
            )
        if signals.recent_leave_results:
            latest = signals.recent_leave_results[0]
            period = f"{latest['start_date']}~{latest['end_date']}"
            if latest["status"] == "approved":
                return _action(
                    "leave_result", student, 55, "system_message",
                    "请假已通过",
                    f"你 {period} 的请假申请已通过，记得课后补齐学习进度",
                    "student",
                )
            reason = f"：{latest['reject_reason']}" if latest["reject_reason"] else ""
            return _action(
                "leave_result", student, 55, "system_message",
                "请假未通过",
                f"你 {period} 的请假申请未通过{reason}，可以找我一起看看怎么调整",
                "student",
            )
        return None


class InactivityTrigger(BaseTrigger):
    """久未互动关怀（无画像快照时由对话记录直接计算）"""

    def evaluate(self, db, student, signals):
        days = signals.inactive_days
        if days is None or days <= 14:
            return None
        return _action(
            "prolonged_inactivity", student, 50, "system_message",
            "好久不见",
            f"同学你好，你已经 {days} 天没有来找我聊天了。最近过得怎么样？有什么需要帮忙的吗？",
            "student",
        )


class GrowthRecordGapTrigger(BaseTrigger):
    """成长档案断档：从未记录 / 超过 30 天未更新，引导完善档案"""

    def evaluate(self, db, student, signals):
        if signals.record_count == 0:
            return _action(
                "growth_record_gap", student, 26, "system_message",
                "完善你的成长档案",
                "还没有成长记录，记录一条荣誉/竞赛/实践，AI 画像和成长指数会更准",
                "student",
            )
        days = signals.days_since_record
        if days is not None and days > 30:
            return _action(
                "growth_record_gap", student, 30, "system_message",
                "好久没更新成长档案了",
                f"上次记录已经是 {days} 天前，把最近的收获记下来吧",
                "student",
            )
        return None


class MilestoneTrigger(BaseTrigger):
    """成长里程碑：跨越 25 分档位（快照存在时才评估）

    旧实现用 growth_score % 25 == 0，浮点分几乎不可能命中，等于永不触发。
    """

    def evaluate(self, db, student, signals):
        growth = signals.growth_score
        if growth is None or growth <= 0:
            return None
        current_step = int(growth // MILESTONE_STEP)
        if signals.prev_growth_score is not None:
            prev_step = int(signals.prev_growth_score // MILESTONE_STEP)
            reached = current_step > prev_step and current_step > 0
        else:
            # 只有一条快照时退化为"接近档位"判定（±1.5 分容差）
            reached = current_step > 0 and abs(growth - current_step * MILESTONE_STEP) < 1.5
        if not reached:
            return None
        return _action(
            "milestone_reached", student, 40, "system_message",
            "成长里程碑",
            f"恭喜！你的成长评分已经达到 {int(growth)} 分！继续保持，未来可期！",
            "student",
        )


TRIGGERS: list[BaseTrigger] = [
    CrisisEscalationTrigger(),
    ExamSoonTrigger(),
    GradeRiskTrigger(),
    UpcomingCourseTrigger(),
    TodoOverdueTrigger(),
    GradeDropTrigger(),
    LeaveStatusTrigger(),
    InactivityTrigger(),
    MilestoneTrigger(),
    GrowthRecordGapTrigger(),
]

# ============ S6 幂等控制 ============
_DEDUP_WINDOW_HOURS = 48  # 通知查重窗口：48h 内同款通知不重复下发
_evaluate_lock = threading.Lock()  # 全量评估防重入锁


def _notification_exists(db: Session, user_id: int, title: str) -> bool:
    """48h 窗口内是否已存在 user_id + title 同款通知（S6 幂等查重）

    时间口径：Notification.created_at 由 default=datetime.now 写入本地 naive 时间，
    因此窗口也用本地 naive now，避免时区偏移导致查重失效。
    """
    cutoff = datetime.now() - timedelta(hours=_DEDUP_WINDOW_HOURS)
    return db.query(Notification.id).filter(
        Notification.user_id == user_id,
        Notification.title == title,
        Notification.created_at >= cutoff,
    ).first() is not None


def evaluate_student(db: Session, student: User, target_role: str | None = None) -> list[ProactiveAction]:
    """评估一名学生的主动触达动作。

    target_role：仅保留指定受众的动作（"student" / "teacher"）。
    必须先按受众过滤再排序截断——否则教师级高危动作会挤占学生可见名额，
    接口按角色过滤后就什么都不剩。
    教师视角只走轻量信号采集（画像 + 成绩），避免管理员遍历全体学生时放大成 N×8 次查询。
    """
    signals = gather_signals(db, student, full=(target_role != "teacher"))

    actions: list[ProactiveAction] = []
    for trigger in TRIGGERS:
        try:
            action = trigger.evaluate(db, student, signals)
            if action and (target_role is None or action.target_role == target_role):
                actions.append(action)
        except Exception:
            logger.exception("触发器 %s 评估失败 (student=%s)", trigger.__class__.__name__, student.id)

    actions.sort(key=lambda a: a.priority, reverse=True)
    return actions[:MAX_PER_STUDENT]


def execute_action(db: Session, action: ProactiveAction) -> bool:
    """落库一条主动触达动作：命中 48h 查重窗口的直接跳过。

    返回 True 表示本次实际产生通知；commit 由调用方统一控制（学生级事务）。
    """
    if action.action_type in ("notification", "escalation"):
        # 通知/高危升级：均触达目标教师（升级类必须真实下发，不能只评估不落库）
        if action.target_role == "teacher":
            tutors = db.query(User).filter(
                User.role == UserRole.TEACHER,
                User.id.in_(
                    db.query(User.tutor_id).filter(User.id == action.student_id)
                ),
            ).all()
            created = False
            for tutor in tutors:
                if _notification_exists(db, tutor.id, action.title):
                    logger.info("[主动触达] 48h 内重复通知已跳过 user_id=%s title=%s", tutor.id, action.title)
                    continue
                notif = Notification(
                    user_id=tutor.id,
                    title=action.title,
                    content=action.content,
                    type="system",
                )
                db.add(notif)
                created = True
            return created
    elif action.action_type == "system_message":
        if _notification_exists(db, action.student_id, action.title):
            logger.info("[主动触达] 48h 内重复通知已跳过 user_id=%s title=%s", action.student_id, action.title)
            return False
        notif = Notification(
            user_id=action.student_id,
            title=action.title,
            content=action.content,
            type="system",
        )
        db.add(notif)
        return True
    return False


def evaluate_all():
    """全量评估并落库（S6 幂等）。

    - 防重入：模块锁非阻塞获取，已有任务在跑则直接返回；
    - 事务化：每个学生的全部动作单事务提交，失败整体回滚；
    - 容错：单学生失败不影响其他学生。
    """
    if not _evaluate_lock.acquire(blocking=False):
        logger.info("[主动触达] 已有任务在执行，本次跳过")
        return
    db = SessionLocal()
    try:
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        written_students = 0
        for student in students:
            try:
                actions = evaluate_student(db, student)
                if not actions:
                    continue
                created_any = False
                for action in actions:
                    if execute_action(db, action):
                        created_any = True
                        logger.info("[主动触达] %s -> %s(%s): %s", action.trigger, student.name, student.username, action.title)
                if created_any:
                    db.commit()
                    written_students += 1
            except Exception:
                db.rollback()
                logger.exception("[主动触达] 学生 %s 的动作处理失败，已整体回滚", student.id)
        logger.info("[主动触达] 本轮完成，%d 名学生产生新通知", written_students)
    finally:
        db.close()
        _evaluate_lock.release()