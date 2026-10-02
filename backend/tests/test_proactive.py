"""AI 主动触达引擎（p3_1）：四触发器命中规则 / 排序截断 / S6 幂等（查重+防重入）。

关键约束：StudentProfileSnapshot.snapshot_date 必填；AIDialogSummary 以
created_at 倒序取最新；execute_action 只 add 不 commit（提交由调用方控制）。
"""
from datetime import date

import pytest

from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.notification import Notification
from app.models.profile import StudentProfileSnapshot
from app.models.user import UserRole
from app.services import proactive_engine


def _add_profile(db, student_id, *, risk=0.0, academic=0.0, growth=0.0,
                 inactive_days=0, trajectory=None):
    snap = StudentProfileSnapshot(
        student_id=student_id,
        snapshot_date=date.today(),
        psychological_risk=risk,
        academic_score=academic,
        growth_score=growth,
        behavioral_patterns={
            **({"inactive_days": inactive_days} if inactive_days else {}),
            **({"grade_trajectory": trajectory} if trajectory else {}),
        },
    )
    db.add(snap)


def _add_crisis(db, student_id, *, level=CrisisLevel.MILD, resolved=False, summary="对话摘要"):
    c = AIDialogSummary(
        student_id=student_id,
        summary=summary,
        level=level,
        resolved=resolved,
    )
    db.add(c)


def _count_notifications(db, title: str) -> int:
    return db.query(Notification.id).filter(Notification.title == title).count()


def test_crisis_high_risk_escalation(db, make_user):
    stu = make_user()
    _add_profile(db, stu.id, risk=80.0)
    _add_crisis(db, stu.id, level=CrisisLevel.SEVERE)
    db.commit()

    actions = proactive_engine.evaluate_student(db, stu)
    assert actions and actions[0].trigger == "crisis_escalation"
    assert actions[0].priority == 90
    assert actions[0].action_type == "escalation"
    assert "高危预警" in actions[0].title
    assert actions[0].target_role == "teacher"


def test_crisis_mid_risk_notification(db, make_user):
    stu = make_user()
    _add_profile(db, stu.id, risk=60.0)
    _add_crisis(db, stu.id)
    db.commit()

    actions = proactive_engine.evaluate_student(db, stu)
    assert actions and actions[0].action_type == "notification"
    assert actions[0].priority == 70


def test_crisis_low_risk_or_resolved_no_action(db, make_user):
    stu_low = make_user()
    _add_profile(db, stu_low.id, risk=50.0)
    _add_crisis(db, stu_low.id)
    db.commit()
    assert proactive_engine.evaluate_student(db, stu_low) == []

    stu_resolved = make_user()
    _add_profile(db, stu_resolved.id, risk=90.0)
    _add_crisis(db, stu_resolved.id, resolved=True)
    db.commit()
    assert proactive_engine.evaluate_student(db, stu_resolved) == []


def test_inactivity_trigger(db, make_user):
    stu = make_user()
    _add_profile(db, stu.id, inactive_days=20)
    db.commit()

    actions = proactive_engine.evaluate_student(db, stu)
    assert actions and actions[0].trigger == "prolonged_inactivity"
    assert actions[0].priority == 50
    assert actions[0].target_role == "student"


def test_grade_drop_trigger_and_priority_sort(db, make_user):
    """成绩下滑 + 久未互动同时命中：按优先级降序且最多 3 条。"""
    stu = make_user()
    _add_profile(db, stu.id, academic=40.0, inactive_days=30, trajectory="declining")
    db.commit()

    actions = proactive_engine.evaluate_student(db, stu)
    assert [a.trigger for a in actions] == ["grade_drop", "prolonged_inactivity"]
    assert actions[0].priority >= actions[1].priority
    assert len(actions) <= 3


def test_milestone_trigger(db, make_user):
    stu = make_user()
    _add_profile(db, stu.id, growth=50.0)
    db.commit()

    actions = proactive_engine.evaluate_student(db, stu)
    assert actions and actions[0].trigger == "milestone_reached"
    assert actions[0].priority == 40
    assert actions[0].action_type == "system_message"


def test_execute_action_48h_dedup(db, make_user):
    """S6 查重：48h 内向同一用户下发同款通知只落一条。"""
    stu = make_user()
    action = proactive_engine.ProactiveAction(
        trigger="milestone_reached", student_id=stu.id, priority=40,
        action_type="system_message", title="成长里程碑",
        content="恭喜！你的成长评分已经达到 50 分！", target_role="student",
    )
    first = proactive_engine.execute_action(db, action)
    db.commit()
    second = proactive_engine.execute_action(db, action)
    db.commit()
    assert first is True
    assert second is False
    assert _count_notifications(db, "成长里程碑") == 1


def test_evaluate_all_idempotent(db, make_user):
    """S6 幂等：全量评估连续跑两轮，同款通知不重复落库。"""
    teacher = make_user(role=UserRole.TEACHER)
    stu = make_user(tutor_id=teacher.id)
    _add_profile(db, stu.id, risk=80.0, academic=40.0, inactive_days=20,
                 trajectory="declining")
    _add_crisis(db, stu.id, level=CrisisLevel.SEVERE)
    db.commit()
    title = f"高危预警：{stu.name}"

    proactive_engine.evaluate_all()
    after_first = _count_notifications(db, title)
    assert after_first == 1, "高危升级未下发教师通知"

    proactive_engine.evaluate_all()
    assert _count_notifications(db, title) == after_first


def test_evaluate_all_lock_prevents_reentry(db, make_user):
    """S6 防重入：模块锁被占用时 evaluate_all 直接跳过，不产生新通知。"""
    stu = make_user()
    _add_profile(db, stu.id, risk=80.0)
    _add_crisis(db, stu.id)
    db.commit()
    title = f"高危预警：{stu.name}"

    acquired = proactive_engine._evaluate_lock.acquire(blocking=False)
    assert acquired, "测试前置失败：无法获取引擎锁"
    try:
        proactive_engine.evaluate_all()
    finally:
        proactive_engine._evaluate_lock.release()

    assert _count_notifications(db, title) == 0