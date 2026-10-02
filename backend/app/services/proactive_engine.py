import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone, date, timedelta


from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.crisis import AIDialogSummary
from app.models.profile import StudentProfileSnapshot
from app.models.notification import Notification
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)


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
    def evaluate(self, db: Session, student: User, profile: StudentProfileSnapshot | None) -> ProactiveAction | None: ...


class CrisisEscalationTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == student.id
        ).order_by(AIDialogSummary.created_at.desc()).first()
        if not latest_crisis or latest_crisis.resolved:
            return None
        risk = profile.psychological_risk
        if risk > 75:
            return ProactiveAction(
                trigger="crisis_escalation", student_id=student.id, priority=90,
                action_type="escalation",
                title=f"高危预警：{student.name}",
                content=f"心理风险评分 {risk}，危机等级 {latest_crisis.level.value}，建议立即联系辅导员",
                target_role="teacher",
            )
        if risk > 50:
            return ProactiveAction(
                trigger="crisis_escalation", student_id=student.id, priority=70,
                action_type="notification",
                title=f"注意：{student.name} 的心理状态变化",
                content=f"心理风险评分 {risk}，请关注学生状态",
                target_role="teacher",
            )
        return None


class InactivityTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        patterns = profile.behavioral_patterns or {}
        inactive_days = patterns.get("inactive_days", 0)
        if inactive_days > 14:
            return ProactiveAction(
                trigger="prolonged_inactivity", student_id=student.id, priority=50,
                action_type="system_message",
                title="好久不见",
                content=f"同学你好，你已经 {inactive_days} 天没有来找我聊天了。最近过得怎么样？有什么需要帮忙的吗？",
                target_role="student",
            )
        return None


class GradeDropTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        patterns = profile.behavioral_patterns or {}
        if patterns.get("grade_trajectory") == "declining" and profile.academic_score < 50:
            return ProactiveAction(
                trigger="grade_drop", student_id=student.id, priority=60,
                action_type="notification",
                title=f"学业关注：{student.name}",
                content=f"学业评分 {profile.academic_score}，成绩呈下降趋势，建议提供学业支持",
                target_role="teacher",
            )
        return None


class MilestoneTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        if profile.growth_score > 0 and profile.growth_score % 25 == 0:
            return ProactiveAction(
                trigger="milestone_reached", student_id=student.id, priority=40,
                action_type="system_message",
                title="成长里程碑",
                content=f"恭喜！你的成长评分已经达到 {profile.growth_score} 分！继续保持，未来可期！",
                target_role="student",
            )
        return None


TRIGGERS: list[BaseTrigger] = [
    CrisisEscalationTrigger(),
    InactivityTrigger(),
    GradeDropTrigger(),
    MilestoneTrigger(),
]

# ============ S6 幂等控制 ============
_DEDUP_WINDOW_HOURS = 48  # 通知查重窗口：48h 内同款通知不重复下发
_evaluate_lock = threading.Lock()  # 全量评估防重入锁


def _notification_exists(db: Session, user_id: int, title: str) -> bool:
    """48h 窗口内是否已存在 user_id + title 同款通知（S6 幂等查重）"""
    cutoff = datetime.now() - timedelta(hours=_DEDUP_WINDOW_HOURS)
    return db.query(Notification.id).filter(
        Notification.user_id == user_id,
        Notification.title == title,
        Notification.created_at >= cutoff,
    ).first() is not None


def evaluate_student(db: Session, student: User) -> list[ProactiveAction]:
    profile = db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student.id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).first()

    actions = []
    for trigger in TRIGGERS:
        try:
            action = trigger.evaluate(db, student, profile)
            if action:
                actions.append(action)
        except Exception:
            logger.exception("触发器 %s 评估失败", trigger.__class__.__name__)

    actions.sort(key=lambda a: a.priority, reverse=True)
    max_per_student = 3
    return actions[:max_per_student]


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
