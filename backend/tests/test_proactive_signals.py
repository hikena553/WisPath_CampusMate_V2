"""AI 主动发现改造（A 真实信号 / B 学生视角规则 / C LLM 洞察）的测试。

覆盖点：
1. A：无画像快照时，也能从业务表（课表/考试/成绩/待办）采集到真实信号；
2. B：学生视角规则在无快照下命中；按受众过滤先于截断（教师级动作不挤占学生名额）；
       即将上课提醒按时距分档；里程碑按"跨越 25 分档位"判定；
3. C：LLM 洞察生成成功即写缓存、二次直接命中；未配置 LLM / 异常 / 超时静默降级为 None；
       并发同一批动作共享同一次在途生成（in-flight 合并）；
4. 接口层：/api/agent/proactive 与 /api/agent/proactive/insight 的角色可见性；
5. 回归：画像引擎的行为模式检测在 naive 库内时间下不再抛 TypeError。

时间口径（**本文件最关键的部分**）：
    de87583 的 `gather_signals(db, student, full=True)` 不接受 now 参数，内部直接调用
    `date.today()` / `datetime.now()`，因此只能冻结「模块看到的时钟」——
    proactive_signals 里是 `from datetime import date, datetime, ...`，
    用 monkeypatch 替换该模块的 `date` / `datetime` 两个属性即可（见 frozen_now fixture）。
    造数据必须使用同一口径（FROZEN_DATE 及其偏移量），否则断言会随真实运行日期漂移：
    旧版用例把 `FIXED_NOW = datetime(2026, 10, 8, 8, 0)` 只喂给 now= 参数，
    数据却用 `date.today()` 生成，于是只在运行日恰为 2026-10-08 时才是绿的。

    冻结时刻取「周四 08:00」这一常量，与真实运行日期无关；08:00 早于用例课程的 14:10，
    便于断言 next_course 命中该课。实测：把 FROZEN_NOW 换成另一个日期（同为 08:00）
    整套用例仍然全绿，即断言不依赖真实系统日期。
"""
import asyncio
from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.models.academic import ClassGroup, Course, Exam, Grade, Major
from app.models.conversation import Conversation
from app.models.plan import PlanTask, StudyPlan, TaskStatus
from app.models.profile import StudentProfileSnapshot
from app.models.user import UserRole
from app.services import proactive_engine, proactive_insight, proactive_signals
from app.services.proactive_signals import CourseInfo, StudentSignals

# ── 冻结时钟（与真实运行日期无关） ────────────────────────────────────────
FROZEN_NOW = datetime(2026, 1, 6, 8, 0)      # 周四 08:00
FROZEN_DATE = FROZEN_NOW.date()
FROZEN_NOW_MINUTES = FROZEN_NOW.hour * 60 + FROZEN_NOW.minute   # 480
FROZEN_SEMESTER = "2026-2027-1"
TEST_COURSE_START_MINUTES = 850                # 第 5 节 14:10


class _FrozenDateTime(datetime):
    """只接管 now()，返回值仍是普通 datetime（避免子类语义渗进业务计算）。"""

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return FROZEN_NOW
        return FROZEN_NOW.replace(tzinfo=timezone.utc).astimezone(tz)


class _FrozenDate(date):
    """只接管 today()。"""

    @classmethod
    def today(cls):
        return FROZEN_DATE


@pytest.fixture()
def frozen_now(monkeypatch):
    """冻结 proactive_signals 模块看到的时钟，返回冻结时刻。

    新实现拿不到 now 注入口，造数据（考试日期/待办截止日/课程星期几）必须与这里
    口径一致，否则断言随真实日期漂移。
    """
    monkeypatch.setattr(proactive_signals, "datetime", _FrozenDateTime)
    monkeypatch.setattr(proactive_signals, "date", _FrozenDate)
    return FROZEN_NOW


@pytest.fixture(autouse=True)
def _clear_insight_cache():
    """洞察缓存是模块级 + TTL 30 分钟，用例间必须清空，否则相互污染。

    同时清掉在途任务表（超时用例里 shield 出去的任务会活到事件循环关闭）。
    """
    proactive_insight.clear_cache()
    proactive_insight._inflight.clear()
    yield
    proactive_insight.clear_cache()
    proactive_insight._inflight.clear()


# ═══════════════════════════════════════════════════════════
# 数据构造辅助（一律使用冻结日期）
# ═══════════════════════════════════════════════════════════

def _add_exam(db, student_id: int, *, days_left: int = 1, name: str = "测试考试"):
    db.add(Exam(
        student_id=student_id,
        course_name=name,
        exam_date=FROZEN_DATE + timedelta(days=days_left),
        start_time=time(9, 0),
        end_time=time(11, 0),
        location="测试楼201",
    ))


def _add_failing_grade(db, student_id: int, *, semester: str = FROZEN_SEMESTER):
    db.add(Grade(
        student_id=student_id,
        course_name="测试不及格课程",
        score=48,
        credit=3,
        gpa=1.0,
        semester=semester,
    ))


def _add_overdue_task(db, student_id: int, *, days_overdue: int = 3):
    plan = StudyPlan(
        student_id=student_id,
        title="测试学习计划",
        start_date=FROZEN_DATE - timedelta(days=10),
    )
    db.add(plan)
    db.flush()
    db.add(PlanTask(
        plan_id=plan.id,
        title="测试逾期任务",
        due_date=FROZEN_DATE - timedelta(days=days_overdue),
        status=TaskStatus.TODO,
    ))
    return plan


def _delete_plan(db, plan) -> None:
    db.query(PlanTask).filter(PlanTask.plan_id == plan.id).delete()
    db.query(StudyPlan).filter(StudyPlan.id == plan.id).delete()
    db.commit()


def _attach_own_class(db, stu, *, name: str = "信号测试课"):
    """给学生挂一个独立班级 + 一门当天课程，返回 (class_group, course)。

    独立班级让 today_courses 只含本用例的课，断言不必迁就种子班级的课表。
    """
    major = db.query(Major).first()
    assert major is not None, "种子数据缺少专业"
    cg = ClassGroup(major_id=major.id, grade=2024, name=f"主动信号测试班{stu.id}")
    db.add(cg)
    db.flush()

    course = Course(
        class_group_id=cg.id,
        name=name,
        teacher="测试老师",
        location="测试楼101",
        day_of_week=FROZEN_NOW.isoweekday(),   # 必须与冻结时钟同一天，否则采集不到
        start_period=5,
        end_period=6,
        week_start=1,
        week_end=16,
        semester=FROZEN_SEMESTER,
        credit=2,
    )
    db.add(course)
    db.flush()

    stu.class_group_id = cg.id
    db.flush()
    return cg, course


def _detach_own_class(db, stu, cg) -> None:
    db.query(Course).filter(Course.class_group_id == cg.id).delete()
    db.flush()
    stu.class_group_id = None
    db.flush()
    db.query(ClassGroup).filter(ClassGroup.id == cg.id).delete()
    db.commit()


# ═══════════════════════════════════════════════════════════
# A：真实信号采集（不依赖画像快照）
# ═══════════════════════════════════════════════════════════

def test_gather_signals_from_tables_without_snapshot(db, make_user, frozen_now):
    """无快照时课程/考试/成绩/待办信号照常可用（这是此前恒为空的根因）"""
    # 冻结自检：模块内时钟必须就是冻结时刻，否则后面的 days_left/days_overdue 都会漂
    assert proactive_signals.datetime.now() == frozen_now
    assert proactive_signals.date.today() == FROZEN_DATE

    stu = make_user()
    cg, course = _attach_own_class(db, stu)
    plan = _add_overdue_task(db, stu.id)
    _add_exam(db, stu.id, days_left=2, name="信号测试考试")
    _add_failing_grade(db, stu.id, semester=FROZEN_SEMESTER)
    db.commit()

    try:
        signals = proactive_signals.gather_signals(db, stu)
        assert signals.has_snapshot is False

        # 课表：按冻结时钟的星期几命中当天课程，节次映射为真实时间
        assert [c.name for c in signals.today_courses] == ["信号测试课"]
        my_course = signals.today_courses[0]
        assert my_course.start_time == "14:10"
        assert my_course.start_minutes == TEST_COURSE_START_MINUTES
        assert my_course.location == "测试楼101"
        assert signals.now_minutes == FROZEN_NOW_MINUTES

        # next_course：当天第一节尚未开始的课（严格晚于当前时刻）
        assert signals.next_course is not None
        assert signals.next_course.name == "信号测试课"
        # 距上课分钟数必须由冻结时刻推导，不能写死（写死 370 只在 FROZEN_NOW 恰为 08:00 时成立）
        assert signals.next_course_minutes_left == TEST_COURSE_START_MINUTES - FROZEN_NOW_MINUTES

        # 考试：7 天窗口内的 days_left 用同一冻结日期计算
        assert [e["days_left"] for e in signals.upcoming_exams] == [2]
        assert signals.upcoming_exams[0]["exam_date"] == FROZEN_DATE + timedelta(days=2)
        assert signals.upcoming_exams[0]["start_time"] == "09:00"

        # 成绩：最新学期均绩 + 不及格课程（只有一个学期时无法判轨迹）
        assert signals.latest_gpa == 1.0
        assert signals.prev_gpa is None
        assert signals.grade_trajectory is None
        assert [g["course_name"] for g in signals.failing_courses] == ["测试不及格课程"]

        # 待办：逾期天数同样按冻结日期算
        assert len(signals.overdue_tasks) == 1
        assert signals.overdue_tasks[0]["days_overdue"] == 3
        assert signals.overdue_tasks[0]["due_date"] == FROZEN_DATE - timedelta(days=3)
    finally:
        _delete_plan(db, plan)
        _detach_own_class(db, stu, cg)
        db.query(Exam).filter(Exam.student_id == stu.id).delete()
        db.query(Grade).filter(Grade.student_id == stu.id).delete()
        db.commit()


# ═══════════════════════════════════════════════════════════
# B：学生视角规则
# ═══════════════════════════════════════════════════════════

def test_student_actions_fire_without_snapshot(db, make_user, frozen_now):
    """无画像快照时，临考 / 不及格 / 待办逾期也能产生学生可见动作"""
    stu = make_user()
    _add_exam(db, stu.id, days_left=1)
    _add_failing_grade(db, stu.id)
    db.commit()

    try:
        actions = proactive_engine.evaluate_student(db, stu, target_role="student")
        triggers = [a.trigger for a in actions]
        assert "exam_soon" in triggers
        assert "grade_risk" in triggers
        assert all(a.target_role == "student" for a in actions)
        assert len(actions) <= proactive_engine.MAX_PER_STUDENT
        # 排序契约：优先级降序
        priorities = [a.priority for a in actions]
        assert priorities == sorted(priorities, reverse=True)
    finally:
        db.query(Exam).filter(Exam.student_id == stu.id).delete()
        db.query(Grade).filter(Grade.student_id == stu.id).delete()
        db.commit()


def test_overdue_task_action_without_snapshot(db, make_user, frozen_now):
    """逾期天数按冻结日期计算，无快照也能命中待办逾期提醒"""
    stu = make_user()
    plan = _add_overdue_task(db, stu.id)
    db.commit()

    try:
        actions = proactive_engine.evaluate_student(db, stu, target_role="student")
        overdue = [a for a in actions if a.trigger == "todo_overdue"]
        assert overdue, "无快照时待办逾期未命中"
        assert "已逾期 3 天" in overdue[0].content
        assert overdue[0].target_role == "student"
    finally:
        _delete_plan(db, plan)


def test_teacher_actions_do_not_crowd_out_student_actions(db, make_user, frozen_now):
    """按受众过滤必须先于截断：危机动作（priority 90，教师级）不能挤掉学生可见动作"""
    stu = make_user()
    db.add(StudentProfileSnapshot(
        student_id=stu.id, snapshot_date=FROZEN_DATE, psychological_risk=88.0,
    ))
    _add_exam(db, stu.id, days_left=1)
    _add_failing_grade(db, stu.id)
    plan = _add_overdue_task(db, stu.id)
    db.commit()

    try:
        student_actions = proactive_engine.evaluate_student(db, stu, target_role="student")
        teacher_actions = proactive_engine.evaluate_student(db, stu, target_role="teacher")

        assert [a.trigger for a in teacher_actions] == ["crisis_escalation"]
        assert teacher_actions[0].priority == 90
        # 学生名额被三个学生级动作占满（78/68/62），危机动作不参与竞争
        assert len(student_actions) == proactive_engine.MAX_PER_STUDENT
        assert [a.trigger for a in student_actions] == ["exam_soon", "grade_risk", "todo_overdue"]
        assert all(a.target_role == "student" for a in student_actions)
    finally:
        _delete_plan(db, plan)
        db.query(Exam).filter(Exam.student_id == stu.id).delete()
        db.query(Grade).filter(Grade.student_id == stu.id).delete()
        db.query(StudentProfileSnapshot).filter(StudentProfileSnapshot.student_id == stu.id).delete()
        db.commit()


def test_upcoming_course_trigger_priority_by_minutes(db, make_user):
    """即将上课：距上课 ≤90 分钟为高优先级提醒，否则当天轻提示"""
    stu = make_user()
    course = CourseInfo(
        name="Web前端开发", location="安州实验楼301",
        start_period=5, end_period=6,
        start_time="14:10", start_minutes=TEST_COURSE_START_MINUTES,
    )

    # 13:30 -> 距 14:10 还有 40 分钟
    soon = StudentSignals(
        now_minutes=13 * 60 + 30,
        today_courses=[course],
        next_course=course,
        next_course_minutes_left=40,
    )
    action = proactive_engine.UpcomingCourseTrigger().evaluate(db, stu, soon)
    assert action is not None
    assert action.trigger == "class_soon" and action.priority == 70
    assert "40 分钟" in action.content
    assert "安州实验楼301" in action.content

    # 08:00 -> 距上课 370 分钟，退化为当天轻提示
    later = StudentSignals(
        now_minutes=FROZEN_NOW_MINUTES,
        today_courses=[course],
        next_course=course,
        next_course_minutes_left=TEST_COURSE_START_MINUTES - FROZEN_NOW_MINUTES,
    )
    action2 = proactive_engine.UpcomingCourseTrigger().evaluate(db, stu, later)
    assert action2 is not None
    assert action2.trigger == "class_today" and action2.priority == 32
    assert "14:10" in action2.content
    assert "今天还有 1 节课" in action2.content


def test_milestone_only_on_step_crossing(db, make_user, frozen_now):
    """里程碑：跨越 25 分档位才触发（旧的 % 25 == 0 判定几乎永不命中）"""
    crossed = make_user()
    db.add(StudentProfileSnapshot(
        student_id=crossed.id, snapshot_date=FROZEN_DATE - timedelta(days=1), growth_score=24.0))
    db.add(StudentProfileSnapshot(
        student_id=crossed.id, snapshot_date=FROZEN_DATE, growth_score=26.0))

    same_step = make_user()
    db.add(StudentProfileSnapshot(
        student_id=same_step.id, snapshot_date=FROZEN_DATE - timedelta(days=1), growth_score=51.0))
    db.add(StudentProfileSnapshot(
        student_id=same_step.id, snapshot_date=FROZEN_DATE, growth_score=53.0))
    db.commit()

    crossed_actions = proactive_engine.evaluate_student(db, crossed)
    same_actions = proactive_engine.evaluate_student(db, same_step)

    assert "milestone_reached" in [a.trigger for a in crossed_actions]
    assert "milestone_reached" not in [a.trigger for a in same_actions]

    milestone = next(a for a in crossed_actions if a.trigger == "milestone_reached")
    assert milestone.priority == 40
    assert milestone.target_role == "student"


def test_crisis_inferred_from_dialog_without_snapshot(db, make_user):
    """无快照时，未解除的严重危机记录也能推断出教师级高危动作"""
    from app.models.crisis import AIDialogSummary, CrisisLevel

    stu = make_user()
    db.add(AIDialogSummary(
        student_id=stu.id, summary="测试危机摘要", level=CrisisLevel.SEVERE, resolved=False,
    ))
    db.commit()

    teacher_actions = proactive_engine.evaluate_student(db, stu, target_role="teacher")
    assert [a.trigger for a in teacher_actions] == ["crisis_escalation"]
    assert teacher_actions[0].priority == 90
    assert teacher_actions[0].target_role == "teacher"


# ═══════════════════════════════════════════════════════════
# C：LLM 洞察
# ═══════════════════════════════════════════════════════════

def _action(stu, trigger: str = "exam_soon", title: str = "临近考试提醒") -> proactive_engine.ProactiveAction:
    return proactive_engine.ProactiveAction(
        trigger=trigger, student_id=stu.id, priority=78, action_type="system_message",
        title=title, content="明天考《测试考试》09:00", target_role="student",
    )


def test_generate_insight_caches_result(monkeypatch, db, make_user):
    """生成成功即写缓存；二次调用直接命中不再打模型；文案按实现在返回前清洗"""
    stu = make_user()
    actions = [_action(stu)]
    calls = {"n": 0}

    async def _fake_complete(prompt, **kwargs):
        calls["n"] += 1
        assert "临近考试提醒" in prompt          # 动作标题进了 prompt
        assert stu.name in prompt                # 学生姓名进了 prompt
        return "明天有考试，今晚把重点过一遍。"

    monkeypatch.setattr(proactive_insight, "complete", _fake_complete)
    text = asyncio.run(proactive_insight.generate_insight(stu, actions))
    assert text == "明天有考试，今晚把重点过一遍。"
    assert calls["n"] == 1

    # 二次调用命中缓存，不再打模型
    async def _should_not_call(prompt, **kwargs):
        calls["n"] += 1
        return "不应被调用"

    monkeypatch.setattr(proactive_insight, "complete", _should_not_call)
    again = asyncio.run(proactive_insight.generate_insight(stu, actions))
    assert again == "明天有考试，今晚把重点过一遍。"
    assert calls["n"] == 1
    assert proactive_insight.get_cached_insight(stu, actions) == "明天有考试，今晚把重点过一遍。"

    # 新实现的清洗契约：去首尾引号 + 超长截断到 MAX_INSIGHT_CHARS * 2（注意不是 * 1）
    long_actions = [_action(stu, trigger="grade_risk", title="成绩需要关注")]

    async def _long_complete(prompt, **kwargs):
        return '"' + "长" * 200 + '"'

    monkeypatch.setattr(proactive_insight, "complete", _long_complete)
    long_text = asyncio.run(proactive_insight.generate_insight(stu, long_actions))
    assert long_text is not None
    assert not long_text.startswith('"') and not long_text.endswith('"')
    assert len(long_text) == proactive_insight.MAX_INSIGHT_CHARS * 2
    assert proactive_insight.get_cached_insight(stu, long_actions) == long_text


def test_generate_insight_degrades_without_llm(monkeypatch, db, make_user):
    """LLM 不可用（未配 Key / 异常 / 超时）时静默降级为 None，绝不抛错给接口"""
    stu = make_user()
    actions = [_action(stu, trigger="grade_risk", title="成绩需要关注")]

    async def _raise(prompt, **kwargs):
        raise RuntimeError("LLM 未配置 API Key")

    monkeypatch.setattr(proactive_insight, "complete", _raise)
    assert asyncio.run(proactive_insight.generate_insight(stu, actions)) is None
    assert proactive_insight.get_cached_insight(stu, actions) is None

    # 超时同样降级（INSIGHT_TIMEOUT_SECONDS 默认 8s，这里缩短以免拖慢用例）
    async def _hang(prompt, **kwargs):
        await asyncio.sleep(1)
        return "不该等到这句"

    monkeypatch.setattr(proactive_insight, "complete", _hang)
    monkeypatch.setattr(proactive_insight, "INSIGHT_TIMEOUT_SECONDS", 0.05)

    async def _run_until_timeout():
        # wait_for 只取消 shield 那一层，被留存的在途任务必须在同一个事件循环内收尾，
        # 否则循环关闭时 asyncio 会打出 "Future exception was never retrieved" 噪声日志
        result = await proactive_insight.generate_insight(stu, actions)
        for task in list(proactive_insight._inflight.values()):
            task.cancel()
        return result

    assert asyncio.run(_run_until_timeout()) is None
    assert proactive_insight.get_cached_insight(stu, actions) is None


def test_generate_insight_joins_inflight_generation(monkeypatch, db, make_user):
    """并发同一批动作时共享同一次模型请求（新实现：_inflight + asyncio.shield 合并）"""
    stu = make_user()
    actions = [_action(stu, trigger="class_soon", title="下一节课快开始了")]
    calls = {"n": 0}

    async def _slow_complete(prompt, **kwargs):
        calls["n"] += 1
        await asyncio.sleep(0.2)
        return "十分钟后上课，别迟到。"

    monkeypatch.setattr(proactive_insight, "complete", _slow_complete)

    async def _concurrent():
        return await asyncio.gather(
            proactive_insight.generate_insight(stu, actions),
            proactive_insight.generate_insight(stu, actions),
        )

    first, second = asyncio.run(_concurrent())
    assert first == "十分钟后上课，别迟到。"
    assert second == first
    assert calls["n"] == 1


# ═══════════════════════════════════════════════════════════
# 接口层
# ═══════════════════════════════════════════════════════════

def test_proactive_api_returns_student_actions(client, db, login_token, frozen_now):
    auth = login_token()
    stu = auth["user"]
    _add_exam(db, stu.id, days_left=2, name="接口测试考试")
    db.commit()

    try:
        resp = client.get("/api/agent/proactive", headers=auth["headers"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body["actions"], list)
        assert "insight" in body
        assert any(a["trigger"] == "exam_soon" for a in body["actions"])
        assert all(a["target_role"] == "student" for a in body["actions"])
    finally:
        db.query(Exam).filter(Exam.student_id == stu.id).delete()
        db.commit()


def test_proactive_insight_endpoint(client, db, login_token, monkeypatch, frozen_now):
    auth = login_token()
    stu = auth["user"]
    _add_exam(db, stu.id, days_left=2, name="接口洞察考试")
    db.commit()

    async def _fake_complete(prompt, **kwargs):
        return "接口返回的洞察文案"

    monkeypatch.setattr(proactive_insight, "complete", _fake_complete)
    try:
        resp = client.get("/api/agent/proactive/insight", headers=auth["headers"])
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"insight": "接口返回的洞察文案", "cached": False}

        # 同一批动作第二次请求直接命中 30 分钟缓存
        again = client.get("/api/agent/proactive/insight", headers=auth["headers"])
        assert again.status_code == 200, again.text
        assert again.json() == {"insight": "接口返回的洞察文案", "cached": True}
    finally:
        db.query(Exam).filter(Exam.student_id == stu.id).delete()
        db.commit()


def test_proactive_insight_endpoint_for_teacher_returns_null(client, login_token):
    """非学生角色不生成洞察（教师端卡片不需要）"""
    auth = login_token(role=UserRole.TEACHER)
    resp = client.get("/api/agent/proactive/insight", headers=auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["insight"] is None


# ═══════════════════════════════════════════════════════════
# 回归：画像引擎行为模式检测的时区安全
# ═══════════════════════════════════════════════════════════

def test_behavioral_patterns_with_naive_db_timestamp(db, make_user):
    """库内 DateTime 读出来是 naive，与 aware now 相减曾抛 TypeError，
    导致管理员刷新画像整批静默失败（快照永远生不出来）。"""
    from app.services.student_profile_engine import _detect_behavioral_patterns

    stu = make_user()
    db.add(Conversation(user_id=stu.id, title="时区回归会话"))
    db.commit()

    patterns = _detect_behavioral_patterns(db, stu.id)
    assert "inactive_days" in patterns
    assert patterns["inactive_days"] == 0  # 刚创建的会话，0 天未互动