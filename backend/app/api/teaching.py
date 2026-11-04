"""教学域 API：我的课表 / 课堂考勤 / 作业 / 成绩。

这一组接口是教师端「教学」这条线唯一的入口，服务三种人：

- **任课教师**：看自己的课表、点名、布置作业、录成绩；
- **辅导员**：看「我带的学生在这门课上怎么样」（听课评课与学业预警的依据）；
- **管理员**：查看全量（复用管理端接口，这里只做教师视角）。

三条「一气呵成」的链路在这里落地，它们不是三个按钮，而是同一条数据流：

1. 点名 → 缺勤（未批假）→ 自动建 ``TeacherTask(follow_up)`` → 教师办结时写关怀记录；
2. 作业 → 未交/逾期 → 提成待办 → 与考勤缺勤在学生画像里合并成「学业风险」；
3. 成绩录入 → 低于警戒线 → 自动 ``CareEvent(academic)`` + 待办 → AI 洞察的「建议联系」。

所有写操作都会落 ``LearningEvent``（旁路，失败不影响主流程），
让「我的育人成长」与「学生画像」共用同一份行为数据。
"""
from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.academic import ClassGroup, College, Course, Grade, Major
from app.models.care_center import CareEvent, CareEventType
from app.models.care_record import CareRecord
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.teacher_task import TaskPriority, TaskSourceType, TaskStatus, TeacherTask
from app.models.teaching import (
    Attendance,
    AttendanceStatus,
    Homework,
    HomeworkStatus,
    HomeworkSubmission,
    SubmissionStatus,
)
from app.models.user import User, UserRole
from app.schemas.teaching import (
    AttendanceMarkIn,
    AttendanceMarkResult,
    AttendanceRosterItem,
    AttendanceRosterOut,
    AttendanceStatRow,
    AttendanceStatsOut,
    CourseGradeOut,
    CourseGradeRow,
    GradeImportIn,
    GradeImportResult,
    GradeIn,
    HomeworkCreate,
    HomeworkDetailOut,
    HomeworkOut,
    ScheduleOut,
    ScheduleTeacherOut,
    ScheduleClassOut,
    SubmissionOut,
    TeachingCourseOut,
    TeachingInboxItem,
    TeachingInboxOut,
    TeachingOverviewOut,
)
from app.services import learning_event_service as les
from app.services import teacher_task_service as tts
from app.services.teaching_scope import (
    default_semester,
    is_my_course,
    my_courses,
    resolve_teacher_id,
    teacher_course_filter,
)

router = APIRouter(prefix="/api/teaching", tags=["teaching"])

_teacher_only = require_role(UserRole.TEACHER)

#: 成绩警戒线：低于该分数自动生成学业预警（与 ``alert_pipeline`` 的阈值口径一致）
GRADE_ALERT_LINE = 60.0

#: 主要课程所属班级的学生名单缓存键（(class_group_id) -> [User]），单次请求内复用
_STATUS_CN = {
    AttendanceStatus.PRESENT: "present",
    AttendanceStatus.LATE: "late",
    AttendanceStatus.ABSENT: "absent",
    AttendanceStatus.LEAVE: "leave",
    AttendanceStatus.EXCUSED: "excused",
}


# ══════════════════════════════════════════════════════════════════
# 内部工具
# ══════════════════════════════════════════════════════════════════


def _week_of_semester(semester: str | None) -> tuple[int | None, str]:
    """推算教学周：以 9 月 1 日 / 2 月 20 日作为学期起点。

    学校并未维护「学期开始日」字段，这里按国内高校通行校历估算，仅供界面提示
    「第 N 教学周」，不参与任何判定——估算错一两天不会影响业务，但能立刻让
    教师端有「开学第几周」的时间感。
    """
    if not semester:
        return None, ""
    try:
        year = int(str(semester).split("-")[0])
        term = int(str(semester).split("-")[-1])
    except (ValueError, IndexError):
        return None, ""
    start = date(year, 9, 1) if term == 1 else date(year + 1, 2, 20)
    today = date.today()
    week = (today - start).days // 7 + 1
    if week < 0:
        week = 0
    return week, f"{start.isoformat()} 起"


def _class_meta(db: Session, class_ids: set[int]) -> dict[int, tuple[str, str]]:
    """班级 id → (班级名称, 学院名称)。一次查完，避免逐课循环查询。"""
    if not class_ids:
        return {}
    rows = (
        db.query(ClassGroup.id, ClassGroup.name, College.name)
        .outerjoin(Major, ClassGroup.major_id == Major.id)
        .outerjoin(College, Major.college_id == College.id)
        .filter(ClassGroup.id.in_(class_ids))
        .all()
    )
    return {r[0]: (r[1] or "", r[2] or "") for r in rows}


def _class_student_counts(db: Session, class_ids: set[int]) -> dict[int, int]:
    if not class_ids:
        return {}
    rows = (
        db.query(User.class_group_id, func.count(User.id))
        .filter(User.role == UserRole.STUDENT, User.class_group_id.in_(class_ids))
        .group_by(User.class_group_id)
        .all()
    )
    return {r[0]: int(r[1]) for r in rows}


def _attendance_sessions(db: Session, course_ids: list[int], semester: str | None) -> dict[int, int]:
    """每门课已点名课次数（按「日期 + 起始节次」去重）。"""
    if not course_ids:
        return {}
    q = db.query(
        Attendance.course_id,
        func.count(func.distinct(Attendance.attend_date)),
    ).filter(Attendance.course_id.in_(course_ids))
    if semester:
        q = q.join(Course, Course.id == Attendance.course_id).filter(Course.semester == semester)
    return {r[0]: int(r[1]) for r in q.group_by(Attendance.course_id).all()}


def _to_course_out(
    db: Session,
    courses: list[Course],
    *,
    semester: str | None = None,
    meta: dict[int, tuple[str, str]] | None = None,
    counts: dict[int, int] | None = None,
    sessions: dict[int, int] | None = None,
) -> list[TeachingCourseOut]:
    if not courses:
        return []
    class_ids = {c.class_group_id for c in courses if c.class_group_id}
    meta = meta if meta is not None else _class_meta(db, class_ids)
    counts = counts if counts is not None else _class_student_counts(db, class_ids)
    sessions = sessions if sessions is not None else _attendance_sessions(db, [c.id for c in courses], semester)
    out: list[TeachingCourseOut] = []
    for c in courses:
        cls_name, col_name = meta.get(c.class_group_id, ("", ""))
        out.append(
            TeachingCourseOut(
                id=c.id,
                name=c.name,
                class_group_id=c.class_group_id,
                class_name=cls_name,
                college_name=col_name,
                teacher=c.teacher or "",
                teacher_id=c.teacher_id,
                location=c.location or "",
                day_of_week=c.day_of_week,
                start_period=c.start_period,
                end_period=c.end_period,
                week_start=c.week_start,
                week_end=c.week_end,
                semester=c.semester,
                credit=c.credit,
                student_count=counts.get(c.class_group_id, 0),
                attendance_sessions=sessions.get(c.id, 0),
            )
        )
    return out


def _get_course(db: Session, course_id: int, teacher: User) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "课程不存在")
    if not is_my_course(course, teacher):
        raise HTTPException(403, "只能操作自己任教的课程")
    return course


def _class_students(db: Session, class_group_id: int | None) -> list[User]:
    if not class_group_id:
        return []
    return (
        db.query(User)
        .filter(User.role == UserRole.STUDENT, User.class_group_id == class_group_id)
        .order_by(User.name)
        .all()
    )


# ══════════════════════════════════════════════════════════════════
# 1. 我的课表
# ══════════════════════════════════════════════════════════════════


@router.get("/overview", response_model=TeachingOverviewOut)
def teaching_overview(
    semester: str | None = Query(None, description="留空则用最新学期"),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """我的教学总览：本周课表、今日课程、教学周、学生规模。"""
    semesters = [
        r[0]
        for r in db.query(Course.semester)
        .distinct()
        .order_by(Course.semester.desc())
        .all()
        if r[0]
    ]
    sem = semester or (semesters[0] if semesters else None)
    courses = my_courses(db, teacher, sem)
    out = _to_course_out(db, courses, semester=sem)

    today_wd = date.today().isoweekday()
    today_courses = [c for c in out if c.day_of_week == today_wd]

    # 育人 ∩ 教学：我既带着、我又教的那些学生。这是「育人 + 教学」定位最直接的体现，
    # 也是首页最值得讲的一个数字。
    tutoring_ids = {
        r[0] for r in db.query(User.id).filter(User.role == UserRole.STUDENT, User.tutor_id == teacher.id).all()
    }
    taught_class_ids = {c.class_group_id for c in courses if c.class_group_id}
    overlap = 0
    total_students = 0
    if taught_class_ids:
        rows = (
            db.query(User.id)
            .filter(User.role == UserRole.STUDENT, User.class_group_id.in_(taught_class_ids))
            .all()
        )
        total_students = len(rows)
        overlap = len({r[0] for r in rows} & tutoring_ids)

    week, week_range = _week_of_semester(sem)
    return TeachingOverviewOut(
        semester=sem,
        semesters=semesters,
        current_week=week,
        week_range=week_range,
        today_courses=today_courses,
        courses=out,
        today_course_count=len(today_courses),
        # 「本周课程数」= 本学期的课程条目数（每门课每周上一次），
        # 同一门课若一周排多次，课表里本来就是两行，也应当算两节
        week_course_count=len(out),
        total_student_count=total_students,
        overlap_student_count=overlap,
    )


# ══════════════════════════════════════════════════════════════════
# 2. 课堂考勤
# ══════════════════════════════════════════════════════════════════


def _approved_leave_map(
    db: Session, student_ids: list[int], on_date: date
) -> dict[int, int]:
    """当天已批假的请假单：student_id → leave_request_id。

    只认 ``APPROVED``：待审批的假不能算数，否则学生只要提交就能逃过点名。
    """
    if not student_ids:
        return {}
    rows = (
        db.query(LeaveRequest.student_id, LeaveRequest.id)
        .filter(
            LeaveRequest.student_id.in_(student_ids),
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= on_date,
            LeaveRequest.end_date >= on_date,
        )
        .all()
    )
    # 同一学生当天可能有多条，取 id 最大的那条作为核销依据即可（业务上等价）
    result: dict[int, int] = {}
    for sid, lid in rows:
        result[sid] = max(lid, result.get(sid, 0))
    return result


# ── 课表：按任课教师 / 按班级查看 ─────────────────────────────────
#
# 这两个接口解决的是「课表只能看自己的课」这个限制。
# 教师排课协调、找同事对接学生情况、班主任看本班所有任课教师，都需要跨教师视角。
# 只读：不返回任何可写入口，且不改变「我教的课」的权限口径。


@router.get("/teachers", response_model=list[ScheduleTeacherOut])
def schedule_teachers(
    semester: str | None = Query(None, description="留空则用最新学期"),
    keyword: str | None = Query(None, description="按姓名模糊搜索"),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """本学期开课教师清单（课表页「按任课教师」筛选器的数据源）。

    只返回本学期确有课程的教师，避免列出全量教师造成筛选器过长。
    ``is_me`` 用于前端把本人置顶或高亮。
    """
    sem = semester or default_semester(db)
    q = db.query(Course).filter(Course.semester == sem)
    if keyword:
        from app.services.knowledge_service import _escape_like

        q = q.filter(Course.teacher.like(f"%{_escape_like(keyword)}%", escape="\\"))
    rows = q.all()

    buckets: dict[str, dict] = {}
    for c in rows:
        name = (c.teacher or "").strip()
        if not name:
            continue
        b = buckets.setdefault(
            name,
            {"teacher_id": c.teacher_id, "name": name, "course_count": 0, "classes": set(), "students": 0},
        )
        b["course_count"] += 1
        if c.class_group_id:
            b["classes"].add(c.class_group_id)
        # 同一 teacher_id 优先保留非空值
        if b["teacher_id"] is None and c.teacher_id:
            b["teacher_id"] = c.teacher_id

    # 学生数按班级统计（同一教师多门课同班不重复计）
    all_class_ids: set[int] = set()
    for b in buckets.values():
        all_class_ids |= b["classes"]
    counts = _class_student_counts(db, all_class_ids) if all_class_ids else {}

    out: list[ScheduleTeacherOut] = []
    for b in buckets.values():
        out.append(
            ScheduleTeacherOut(
                teacher_id=b["teacher_id"],
                name=b["name"],
                course_count=b["course_count"],
                class_count=len(b["classes"]),
                student_count=sum(counts.get(cid, 0) for cid in b["classes"]),
                is_me=(b["teacher_id"] == teacher.id) or (b["name"] == teacher.name),
            )
        )
    out.sort(key=lambda x: (-x.is_me, -x.course_count, x.name))
    return out


@router.get("/classes", response_model=list[ScheduleClassOut])
def schedule_classes(
    semester: str | None = Query(None, description="留空则用最新学期"),
    keyword: str | None = Query(None, description="按班级名模糊搜索"),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """本学期有课的班级清单（课表页「按班级」筛选器 / 空选态引导卡片的数据源）。

    为什么不复用前端「从我的授课里反推班级」：那等于把「我教的班」当成「全校的班」，
    一个本学期没排课的教师会看到空清单，整页没有入口。课表是教务排定的公共数据，
    班级清单必须独立于「我教什么」。
    ``is_mine`` 只用于把本人任教的班级置顶，不代表任何权限。
    """
    sem = semester or default_semester(db)
    rows = (
        db.query(Course)
        .filter(Course.semester == sem, Course.class_group_id.isnot(None))
        .with_entities(Course.class_group_id, Course.teacher_id, Course.teacher)
        .all()
    )
    if not rows:
        return []

    mine: set[int] = set()
    for cid, tid, tname in rows:
        if tid == teacher.id or (tname or "").strip() == teacher.name:
            mine.add(cid)

    # 每班课程数
    cnt: dict[int, int] = {}
    for cid, _tid, _tn in rows:
        cnt[cid] = cnt.get(cid, 0) + 1

    class_ids = list(cnt.keys())
    q = (
        db.query(ClassGroup)
        .filter(ClassGroup.id.in_(class_ids))
        .with_entities(ClassGroup.id, ClassGroup.name, ClassGroup.major_id)
        .all()
    )
    if keyword:
        from app.services.knowledge_service import _escape_like

        kw = keyword.strip()
        q = [r for r in q if kw in (r[1] or "")]
    if not q:
        return []

    # ClassGroup 没有 college_id，学院要经 major → college 两跳拿到
    major_ids = {r[2] for r in q if r[2]}
    majors = (
        dict(db.query(Major.id, Major.college_id).filter(Major.id.in_(list(major_ids))).all())
        if major_ids
        else {}
    )
    college_ids = {cid for cid in majors.values() if cid}
    colleges = (
        dict(
            db.query(College.id, College.name)
            .filter(College.id.in_(list(college_ids)))
            .all()
        )
        if college_ids
        else {}
    )
    students = _class_student_counts(db, {r[0] for r in q})

    out = [
        ScheduleClassOut(
            class_group_id=cid,
            name=name or f"班级 {cid}",
            college_name=colleges.get(majors.get(major_id)),
            course_count=cnt.get(cid, 0),
            student_count=students.get(cid, 0),
            is_mine=cid in mine,
        )
        for cid, name, major_id in q
    ]
    out.sort(key=lambda x: (-x.is_mine, x.name))
    return out


@router.get("/schedule", response_model=ScheduleOut)
def schedule_view(
    semester: str | None = Query(None, description="留空则用最新学期"),
    teacher_name: str | None = Query(None, description="按任课教师姓名查看"),
    class_group_id: int | None = Query(None, description="按班级查看"),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """课表查询：支持「我的 / 按任课教师 / 按班级」三种视角，统一返回同构数据。

    三者的差异只在筛选条件，返回结构一致，前端一套渲染逻辑即可。
    注意：按教师/班级查看是**只读**视图，不会赋予该教师课程的录入权限。
    """
    semesters = [
        r[0]
        for r in db.query(Course.semester).distinct().order_by(Course.semester.desc()).all()
        if r[0]
    ]
    sem = semester or (semesters[0] if semesters else None)

    q = db.query(Course).filter(Course.semester == sem)
    if teacher_name:
        from app.services.knowledge_service import _escape_like

        q = q.filter(Course.teacher.like(f"%{_escape_like(teacher_name)}%", escape="\\"))
        # 同名优先精确匹到的那个人；仍按姓名，因为历史数据可能没有 teacher_id
        scope, label = "teacher", f"{teacher_name} 的课表"
    elif class_group_id:
        q = q.filter(Course.class_group_id == class_group_id)
        cls = db.get(ClassGroup, class_group_id)
        scope, label = "class", f"{cls.name if cls else '该班级'}的课表"
    else:
        q = q.filter(teacher_course_filter(teacher))
        scope, label = "mine", "我的课表"

    courses = q.order_by(Course.day_of_week, Course.start_period).all()
    out = _to_course_out(db, courses, semester=sem)

    today_wd = date.today().isoweekday()
    today_courses = [c for c in out if c.day_of_week == today_wd]

    return ScheduleOut(
        semester=sem,
        semesters=semesters,
        scope=scope,
        label=label,
        courses=out,
        today_courses=today_courses if scope == "mine" else today_courses,
        today_course_count=len(today_courses),
        week_course_count=len(out),
        total_student_count=sum(c.student_count for c in out),
    )


@router.get("/attendance/roster", response_model=AttendanceRosterOut)
def attendance_roster(
    course_id: int,
    attend_date: date | None = Query(None),
    period_start: int | None = Query(None),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """点名面板：某课某天的学生名单 + 状态预置。

    状态预置规则（这是「一气呵成」的第一环）：
    已点过 → 用记录值；未点过但有已批假 → ``leave``；其余 → ``present``。
    教师进来只需改那少数几个人的状态。
    """
    course = _get_course(db, course_id, teacher)
    day = attend_date or date.today()
    p_start = period_start if period_start is not None else course.start_period
    p_end = course.end_period if p_start == course.start_period else p_start

    students = _class_students(db, course.class_group_id)
    student_ids = [s.id for s in students]

    existing: dict[int, Attendance] = {}
    if student_ids:
        existing = {
            a.student_id: a
            for a in db.query(Attendance).filter(
                Attendance.course_id == course.id,
                Attendance.attend_date == day,
                Attendance.period_start == p_start,
                Attendance.student_id.in_(student_ids),
            ).all()
        }
    leaves = _approved_leave_map(db, student_ids, day)

    roster: list[AttendanceRosterItem] = []
    for s in students:
        rec = existing.get(s.id)
        if rec:
            status = _STATUS_CN.get(rec.status, "present")
            roster.append(
                AttendanceRosterItem(
                    student_id=s.id, name=s.name, username=s.username, avatar=s.avatar,
                    status=status, leave_request_id=rec.leave_request_id,
                    remark=rec.remark, auto_leave=rec.leave_request_id is not None,
                )
            )
        elif s.id in leaves:
            roster.append(
                AttendanceRosterItem(
                    student_id=s.id, name=s.name, username=s.username, avatar=s.avatar,
                    status="leave", leave_request_id=leaves[s.id], auto_leave=True,
                )
            )
        else:
            roster.append(
                AttendanceRosterItem(
                    student_id=s.id, name=s.name, username=s.username, avatar=s.avatar,
                )
            )

    recorded_dates = [
        r[0]
        for r in db.query(Attendance.attend_date)
        .filter(Attendance.course_id == course.id)
        .distinct()
        .order_by(Attendance.attend_date.desc())
        .limit(30)
        .all()
    ]

    return AttendanceRosterOut(
        course=_to_course_out(db, [course], semester=course.semester)[0],
        attend_date=day,
        period_start=p_start,
        period_end=p_end,
        roster=roster,
        recorded_dates=recorded_dates,
    )


@router.post("/attendance/mark", response_model=AttendanceMarkResult)
def attendance_mark(
    payload: AttendanceMarkIn,
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """提交点名。

    与请假核销的配合方式：无论教师选了什么，只要该生当天存在**已批准**的请假单，
    状态一律落成 ``leave`` 并记录 ``leave_request_id``。教师不需要知道谁请了假，
    也不存在「误把请假记成旷课」的可能——这是与主流产品拉开的第一个细节。

    缺勤（``absent``）会自动建一条 ``follow_up`` 待办（幂等：同一缺勤只建一次），
    教师办结时就能顺路写关怀记录，形成「点名 → 跟进 → 留痕」的一气呵成。
    """
    course = _get_course(db, payload.course_id, teacher)
    students = {s.id: s for s in _class_students(db, course.class_group_id)}
    valid_ids = [i.student_id for i in payload.items if i.student_id in students]
    leaves = _approved_leave_map(db, valid_ids, payload.attend_date)

    result = AttendanceMarkResult()
    now = datetime.now()

    for item in payload.items:
        if item.student_id not in students:
            continue
        status = AttendanceStatus.PRESENT
        if str(item.status) in {s.value for s in AttendanceStatus}:
            status = AttendanceStatus(item.status)

        leave_id = leaves.get(item.student_id)
        auto_leave = False
        if leave_id is not None:
            status = AttendanceStatus.LEAVE
            auto_leave = True

        rec = (
            db.query(Attendance)
            .filter(
                Attendance.course_id == course.id,
                Attendance.attend_date == payload.attend_date,
                Attendance.period_start == payload.period_start,
                Attendance.student_id == item.student_id,
            )
            .first()
        )
        if rec is None:
            rec = Attendance(
                course_id=course.id,
                class_group_id=course.class_group_id,
                teacher_id=teacher.id,
                student_id=item.student_id,
                attend_date=payload.attend_date,
                period_start=payload.period_start,
                period_end=payload.period_end or course.end_period,
            )
            db.add(rec)
        rec.status = status
        rec.leave_request_id = leave_id
        rec.remark = item.remark
        rec.recorded_by = teacher.id
        rec.updated_at = now
        result.saved += 1
        if auto_leave:
            result.auto_leave += 1

        if status == AttendanceStatus.PRESENT:
            result.present += 1
        elif status == AttendanceStatus.LATE:
            result.late += 1
        elif status == AttendanceStatus.ABSENT:
            result.absent += 1
            # 缺勤 → 待办：source_id 用考勤记录 id，幂等键天然唯一
            db.flush()
            if not rec.task_created:
                tts.create_task(
                    db,
                    teacher_id=teacher.id,
                    title=f"{students[item.student_id].name} · {course.name} 缺勤待跟进",
                    detail=(
                        f"{payload.attend_date.isoformat()} 第 {payload.period_start}-"
                        f"{payload.period_end or course.end_period} 节 未到课，且无有效请假。"
                        "建议联系本人确认原因，必要时通知家长。"
                    ),
                    student_id=item.student_id,
                    due_at=payload.attend_date + timedelta(days=1),
                    source_type=TaskSourceType.FOLLOW_UP,
                    source_id=rec.id,
                    priority="high",
                )
                rec.task_created = True
                result.tasks_created += 1
        elif status == AttendanceStatus.LEAVE:
            result.leave += 1
        else:
            result.excused += 1

    db.commit()

    # 学情底座：点名是教师行为，actor 记教师；对象是课程
    les.emit(
        actor_id=teacher.id,
        verb="attendance.mark",
        object_type="course",
        object_id=course.id,
        result={"date": payload.attend_date, "absent": result.absent, "leave": result.leave},
    )
    return result


@router.get("/attendance/stats", response_model=AttendanceStatsOut)
def attendance_stats(
    course_id: int,
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """出勤统计：按学生聚合出勤率与连续缺勤，用于发现「习惯性缺勤」个体。"""
    course = _get_course(db, course_id, teacher)
    students = _class_students(db, course.class_group_id)
    name_map = {s.id: s for s in students}

    records = (
        db.query(Attendance)
        .filter(Attendance.course_id == course.id)
        .order_by(Attendance.attend_date.desc(), Attendance.period_start.desc())
        .all()
    )
    sessions = len({(r.attend_date, r.period_start) for r in records})

    by_student: dict[int, list[Attendance]] = {}
    for r in records:
        by_student.setdefault(r.student_id, []).append(r)

    rows: list[AttendanceStatRow] = []
    for s in students:
        items = by_student.get(s.id, [])
        total = len(items)
        present = sum(1 for i in items if i.status == AttendanceStatus.PRESENT)
        late = sum(1 for i in items if i.status == AttendanceStatus.LATE)
        absent = sum(1 for i in items if i.status == AttendanceStatus.ABSENT)
        leave = sum(1 for i in items if i.status == AttendanceStatus.LEAVE)
        excused = sum(1 for i in items if i.status == AttendanceStatus.EXCUSED)
        # 出勤率口径：请假不算缺勤，只惩罚「未到且未请假」
        denominator = total - leave
        rate = (present + late + excused) / denominator * 100 if denominator > 0 else 0.0
        consecutive = 0
        for i in items:  # items 已按日期倒序
            if i.status == AttendanceStatus.ABSENT:
                consecutive += 1
            elif i.status == AttendanceStatus.LEAVE:
                continue  # 请假不打断也不累计
            else:
                break
        rows.append(
            AttendanceStatRow(
                student_id=s.id, name=s.name, username=s.username,
                total=total, present=present, late=late, absent=absent,
                leave=leave, excused=excused,
                rate=round(rate, 1), consecutive_absent=consecutive,
            )
        )

    rates = [r.rate for r in rows if r.total > 0]
    return AttendanceStatsOut(
        course=_to_course_out(db, [course], semester=course.semester)[0],
        sessions=sessions,
        student_count=len(name_map),
        avg_rate=round(sum(rates) / len(rates), 1) if rates else 0.0,
        rows=sorted(rows, key=lambda r: (r.rate, -r.consecutive_absent)),
    )


# ══════════════════════════════════════════════════════════════════
# 3. 作业
# ══════════════════════════════════════════════════════════════════


def _homework_out(db: Session, hw: Homework, course: Course | None = None, counts: dict | None = None) -> HomeworkOut:
    course = course or db.get(Course, hw.course_id)
    if counts is None:
        total_subs = (
            db.query(func.count(HomeworkSubmission.id))
            .filter(HomeworkSubmission.homework_id == hw.id)
            .scalar()
        ) or 0
        submitted = (
            db.query(func.count(HomeworkSubmission.id))
            .filter(
                HomeworkSubmission.homework_id == hw.id,
                HomeworkSubmission.status.in_(
                    [SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED, SubmissionStatus.LATE]
                ),
            )
            .scalar()
        ) or 0
        graded = (
            db.query(func.count(HomeworkSubmission.id))
            .filter(
                HomeworkSubmission.homework_id == hw.id,
                HomeworkSubmission.status == SubmissionStatus.GRADED,
            )
            .scalar()
        ) or 0
        counts = {"total": total_subs, "submitted": submitted, "graded": graded}
    student_count = (
        db.query(func.count(User.id))
        .filter(User.role == UserRole.STUDENT, User.class_group_id == course.class_group_id)
        .scalar()
        if course and course.class_group_id
        else 0
    ) or 0
    overdue = 0
    if hw.due_at and hw.status == HomeworkStatus.PUBLISHED:
        overdue = max(student_count - counts["submitted"], 0)
    return HomeworkOut(
        id=hw.id,
        course_id=hw.course_id,
        course_name=course.name if course else "",
        class_group_id=hw.class_group_id,
        title=hw.title,
        content=hw.content,
        attachment_url=hw.attachment_url,
        due_at=hw.due_at,
        total_score=hw.total_score,
        status=hw.status.value if hasattr(hw.status, "value") else str(hw.status),
        submitted_count=counts["submitted"],
        graded_count=counts["graded"],
        student_count=student_count,
        created_at=hw.created_at,
        overdue_count=overdue,
    )


@router.get("/homeworks", response_model=list[HomeworkOut])
def list_homeworks(
    course_id: int | None = Query(None),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """我布置的作业（可按课程过滤），含提交/批改进度。"""
    q = db.query(Homework).filter(Homework.teacher_id == teacher.id, Homework.is_deleted.is_(False))
    if course_id:
        q = q.filter(Homework.course_id == course_id)
    rows = q.order_by(Homework.created_at.desc()).limit(200).all()
    course_ids = {h.course_id for h in rows}
    courses = {c.id: c for c in db.query(Course).filter(Course.id.in_(course_ids)).all()} if course_ids else {}
    return [_homework_out(db, h, courses.get(h.course_id)) for h in rows]


@router.post("/homeworks", response_model=HomeworkOut)
def create_homework(
    payload: HomeworkCreate,
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """布置作业。

    同时把「所有学生」都预置成 ``pending`` 提交记录，好处是：
    未交名单不需要前端算差集，教师一进详情页就能看到谁没交，
    也能直接按 ``status=pending`` 生成催交待办。
    """
    course = _get_course(db, payload.course_id, teacher)
    hw = Homework(
        course_id=course.id,
        class_group_id=course.class_group_id,
        teacher_id=teacher.id,
        title=payload.title,
        content=payload.content,
        attachment_url=payload.attachment_url,
        due_at=payload.due_at,
        total_score=payload.total_score,
        status=HomeworkStatus.PUBLISHED,
    )
    db.add(hw)
    db.flush()

    for s in _class_students(db, course.class_group_id):
        db.add(
            HomeworkSubmission(
                homework_id=hw.id,
                student_id=s.id,
                status=SubmissionStatus.PENDING,
            )
        )
    db.commit()
    db.refresh(hw)

    les.emit(
        actor_id=teacher.id,
        verb="homework.publish",
        object_type="homework",
        object_id=hw.id,
        result={"course": course.name, "title": hw.title},
    )
    return _homework_out(db, hw, course)


@router.get("/homeworks/{homework_id}", response_model=HomeworkDetailOut)
def homework_detail(
    homework_id: int,
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    hw = db.get(Homework, homework_id)
    if not hw or hw.is_deleted:
        raise HTTPException(404, "作业不存在")
    course = _get_course(db, hw.course_id, teacher)

    subs = (
        db.query(HomeworkSubmission, User)
        .join(User, User.id == HomeworkSubmission.student_id)
        .filter(HomeworkSubmission.homework_id == hw.id)
        .order_by(User.name)
        .all()
    )
    out = [
        SubmissionOut(
            student_id=u.id, name=u.name, username=u.username,
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
            content=s.content, attachment_url=s.attachment_url,
            score=s.score, comment=s.comment,
            submitted_at=s.submitted_at, graded_at=s.graded_at,
        )
        for s, u in subs
    ]
    counts = {
        "total": len(subs),
        "submitted": sum(1 for s, _ in subs if s.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED, SubmissionStatus.LATE)),
        "graded": sum(1 for s, _ in subs if s.status == SubmissionStatus.GRADED),
    }
    return HomeworkDetailOut(homework=_homework_out(db, hw, course, counts), submissions=out)


@router.post("/homeworks/{homework_id}/grade", response_model=HomeworkOut)
def grade_homework(
    homework_id: int,
    payload: GradeIn,
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """批量批改（分数 + 评语）。只处理本次提交的学生，其余保持原状。"""
    hw = db.get(Homework, homework_id)
    if not hw or hw.is_deleted:
        raise HTTPException(404, "作业不存在")
    course = _get_course(db, hw.course_id, teacher)

    ids = [i.student_id for i in payload.items]
    subs: dict[int, HomeworkSubmission] = {}
    if ids:
        subs = {
            s.student_id: s
            for s in db.query(HomeworkSubmission).filter(
                HomeworkSubmission.homework_id == hw.id,
                HomeworkSubmission.student_id.in_(ids),
            ).all()
        }

    now = datetime.now()
    for item in payload.items:
        sub = subs.get(item.student_id)
        if not sub:
            continue
        sub.score = item.score
        sub.comment = item.comment
        sub.graded_at = now
        sub.graded_by = teacher.id
        # 未提交也允许打分（比如课堂表现分），但状态不改，避免「未交」被抹掉
        if sub.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.LATE):
            sub.status = SubmissionStatus.GRADED
    db.commit()
    db.refresh(hw)

    les.emit(
        actor_id=teacher.id,
        verb="homework.grade",
        object_type="homework",
        object_id=hw.id,
        result={"graded": len(ids)},
    )
    return _homework_out(db, hw, course)


@router.post("/homeworks/{homework_id}/remind", response_model=dict)
def remind_homework(
    homework_id: int,
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """催交：给每个未交学生建一条待办。

    这是「作业 → 待办 → 关怀」链路的中间环。幂等键用 ``homework.id``
    无法区分学生，所以这里用 ``rule_code`` 加学生维度做业务去重。
    """
    hw = db.get(Homework, homework_id)
    if not hw or hw.is_deleted:
        raise HTTPException(404, "作业不存在")
    course = _get_course(db, hw.course_id, teacher)

    pending = (
        db.query(HomeworkSubmission, User)
        .join(User, User.id == HomeworkSubmission.student_id)
        .filter(
            HomeworkSubmission.homework_id == hw.id,
            HomeworkSubmission.status == SubmissionStatus.PENDING,
        )
        .all()
    )
    created = 0
    for _sub, stu in pending:
        rule_code = f"hw_{hw.id}_s{stu.id}"
        exists = (
            db.query(TeacherTask)
            .filter(TeacherTask.teacher_id == teacher.id, TeacherTask.rule_code == rule_code)
            .first()
        )
        if exists:
            continue
        tts.create_task(
            db,
            teacher_id=teacher.id,
            title=f"{stu.name} · {course.name} 未交「{hw.title}」",
            detail="作业已截止仍未提交，建议提醒本人并确认是否有学业困难。",
            student_id=stu.id,
            due_at=date.today() + timedelta(days=2),
            source_type=TaskSourceType.FOLLOW_UP,
            rule_code=rule_code,
            priority="mid",
        )
        created += 1
    return {"created": created, "pending": len(pending)}


# ══════════════════════════════════════════════════════════════════
# 4. 成绩
# ══════════════════════════════════════════════════════════════════


def _level_of(score: float | None) -> str:
    if score is None:
        return "no_grade"
    if score >= 90:
        return "excellent"
    if score >= 80:
        return "good"
    if score >= 60:
        return "pass"
    return "fail"


@router.get("/grades/{course_id}", response_model=CourseGradeOut)
def course_grades(
    course_id: int,
    semester: str | None = Query(None),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """某门课的成绩分析：均分、及格率、分布、逐个学生的相对位置。

    ``Grade`` 表以 ``course_name`` 关联（历史设计，无 course_id），所以这里按
    「课程名 + 学期 + 班级学生」三者同时匹配——课程名在本校课程表里是唯一的，
    跨班级同名课不会串（因为学生 id 集合已按班级限定）。
    """
    course = _get_course(db, course_id, teacher)
    sem = semester or course.semester

    students = _class_students(db, course.class_group_id)
    sids = [s.id for s in students]
    grades: dict[int, Grade] = {}
    if sids:
        grades = {
            g.student_id: g
            for g in db.query(Grade).filter(
                Grade.student_id.in_(sids),
                Grade.course_name == course.name,
                Grade.semester == sem,
            ).all()
        }

    # 已被辅导员关怀覆盖的学生：避免「系统又提示联系一遍」
    cared_ids: set[int] = set()
    if sids:
        cared_ids = {
            r[0]
            for r in db.query(CareEvent.student_id)
            .filter(CareEvent.teacher_id == teacher.id, CareEvent.student_id.in_(sids))
            .all()
        }

    scores = [g.score for g in grades.values() if g.score is not None]
    avg = round(statistics.mean(scores), 1) if scores else None
    median = round(statistics.median(scores), 1) if scores else None

    rows: list[CourseGradeRow] = []
    for s in students:
        g = grades.get(s.id)
        score = g.score if g else None
        rows.append(
            CourseGradeRow(
                student_id=s.id, name=s.name, username=s.username,
                score=score,
                gpa=g.gpa if g else None,
                delta=round(score - avg, 1) if (score is not None and avg is not None) else None,
                level=_level_of(score),
                cared=s.id in cared_ids,
            )
        )
    rows.sort(key=lambda r: (r.score is None, r.score if r.score is not None else 0))

    dist = {"excellent": 0, "good": 0, "pass": 0, "fail": 0, "no_grade": 0}
    for r in rows:
        dist[r.level] = dist.get(r.level, 0) + 1
    graded = len(scores)

    return CourseGradeOut(
        course=_to_course_out(db, [course], semester=sem)[0],
        semester=sem,
        count=len(students),
        graded=graded,
        avg=avg,
        median=median,
        max_score=max(scores) if scores else None,
        min_score=min(scores) if scores else None,
        pass_rate=round(sum(1 for x in scores if x >= 60) / graded * 100, 1) if graded else None,
        excellent_rate=round(sum(1 for x in scores if x >= 90) / graded * 100, 1) if graded else None,
        distribution=dist,
        rows=rows,
    )


@router.post("/grades", response_model=GradeImportResult)
def import_grades(
    payload: GradeImportIn,
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """录入 / 导入成绩。

    这是一气呵成的第四环：低于警戒线的成绩会立刻生成
    ``CareEvent(academic)`` 关怀事件 + 跟进待办，辅导员不需要再去「查看成绩 →
    判断 → 另外建事项」，因为数据落地的那一刻提醒已经就位。
    """
    course = _get_course(db, payload.course_id, teacher)
    sem = payload.semester or course.semester
    students = {s.username: s for s in _class_students(db, course.class_group_id)}

    result = GradeImportResult()
    for item in payload.items:
        stu = students.get(item.username)
        if not stu:
            result.skipped.append(item.username)
            continue
        existing = (
            db.query(Grade)
            .filter(
                Grade.student_id == stu.id,
                Grade.course_name == course.name,
                Grade.semester == sem,
            )
            .first()
        )
        credit = course.credit or 0
        # GPA 口径：60 分及格，绩点 = (分数-50)/10，60 以下记 0，与国内多数高校通行算法一致
        gpa = round(max((item.score - 50) / 10, 0), 2) if item.score >= 60 else 0.0
        if existing:
            existing.score = item.score
            existing.gpa = gpa
            existing.credit = credit
            result.updated += 1
        else:
            db.add(Grade(
                student_id=stu.id, course_name=course.name, score=item.score,
                credit=credit, gpa=gpa, semester=sem,
            ))
            result.created += 1

        if item.score < GRADE_ALERT_LINE:
            _raise_academic_alert(db, teacher, stu, course, item.score)
            result.alerted.append(stu.name)

    db.commit()
    les.emit(
        actor_id=teacher.id,
        verb="grade.import",
        object_type="course",
        object_id=course.id,
        result={"created": result.created, "updated": result.updated, "alerted": len(result.alerted)},
    )
    return result


def _raise_academic_alert(db: Session, teacher: User, stu: User, course: Course, score: float) -> None:
    """成绩不及格 → 关怀事件 + 待办（都做幂等，重复导入不会产生重复提醒）。"""
    title = f"{course.name} 成绩预警（{score:g} 分）"
    today = date.today()

    exists_event = (
        db.query(CareEvent)
        .filter(
            CareEvent.teacher_id == teacher.id,
            CareEvent.student_id == stu.id,
            CareEvent.event_type == CareEventType.ACADEMIC,
            CareEvent.title == title,
        )
        .first()
    )
    if not exists_event:
        db.add(CareEvent(
            teacher_id=teacher.id,
            student_id=stu.id,
            event_type=CareEventType.ACADEMIC,
            event_date=today,
            title=title,
            note=f"{course.name} 成绩 {score:g} 分，低于 {GRADE_ALERT_LINE:g} 分警戒线，建议安排学业辅导谈话。",
            auto_generated=True,
        ))

    tts.create_task(
        db,
        teacher_id=teacher.id,
        title=f"{stu.name} · {course.name} 成绩预警",
        detail=f"该生《{course.name}》成绩 {score:g} 分，已低于警戒线，建议联系本人了解学习困难并制定改进计划。",
        student_id=stu.id,
        due_at=today + timedelta(days=3),
        source_type=TaskSourceType.ALERT,
        rule_code=f"grade_low_{course.id}_s{stu.id}",
        priority="high",
    )


# ══════════════════════════════════════════════════════════════════
# 教学待办收件箱
# ══════════════════════════════════════════════════════════════════


@router.get("/inbox", response_model=TeachingInboxOut)
def teaching_inbox(
    semester: str | None = Query(None, description="留空则用最新学期"),
    teacher: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """教学页首屏「今天要做什么」：把四条链路的下一步聚合成一张列表。

    为什么单独做一个接口，而不是让前端调四个接口拼：

    1. 四类待办的**排序权重**必须统一，否则前端各排各的，同一件事在页面
       不同位置出现不同轻重；这里的顺序就是产品定义的重要性顺序——
       今天有课没点名 > 学业预警 > 待批作业 > 派生待办。
    2. 「点名没点」这件事**只有后端知道**：要拿今天的课 × 已有考勤记录做差集，
       前端逐课去问会产生 N 次请求。
    3. 每条都带 ``link`` 直达具体动作（不是回首页），这是「一气呵成」的接口级保证。
    """
    sem = semester or default_semester(db)
    courses = my_courses(db, teacher, sem)
    today = date.today()
    today_wd = today.isoweekday()
    teacher_id = resolve_teacher_id(teacher, None) or teacher.id

    class_ids = {c.class_group_id for c in courses if c.class_group_id}
    cls_names = {cid: meta[0] for cid, meta in _class_meta(db, class_ids).items()} if class_ids else {}

    items: list[TeachingInboxItem] = []

    # ── 1. 今天有课但还没点名 ──────────────────────────────────
    today_courses = [c for c in courses if c.day_of_week == today_wd]
    course_ids = [c.id for c in courses]
    marked_today: set[tuple[int, int]] = set()
    if course_ids:
        rows = (
            db.query(Attendance.course_id, Attendance.period_start)
            .filter(
                Attendance.course_id.in_(course_ids),
                Attendance.attend_date == today,
            )
            .distinct()
            .all()
        )
        marked_today = {(r[0], r[1]) for r in rows}

    unmarked = [c for c in today_courses if (c.id, c.start_period) not in marked_today]
    for c in unmarked:
        items.append(
            TeachingInboxItem(
                id=f"att-{c.id}-{c.start_period}",
                kind="attendance",
                priority="high",
                title=f"{c.name} 还没点名",
                desc=f"{cls_names.get(c.class_group_id, '')} · 第 {c.start_period}-{c.end_period} 节",
                link=f"/teacher/teaching?course={c.id}&tab=attendance",
                course_id=c.id,
                course_name=c.name,
                class_name=cls_names.get(c.class_group_id, ""),
                due_text="今天",
                action_text="去点名",
            )
        )

    # ── 2. 成绩低于警戒线的学业预警（来自成绩录入链路） ──────────
    alert_tasks = (
        db.query(TeacherTask)
        .filter(
            TeacherTask.teacher_id == teacher_id,
            TeacherTask.source_type == TaskSourceType.ALERT,
            TeacherTask.status.notin_([TaskStatus.DONE, TaskStatus.EXPIRED]),
        )
        .order_by(TeacherTask.due_at.asc())
        .limit(50)
        .all()
    )
    for t in alert_tasks:
        items.append(
            TeachingInboxItem(
                id=f"task-{t.id}",
                kind="alert",
                priority="high",
                title=t.title,
                desc=(t.detail or "")[:80],
                link=f"/teacher/tasks?open-task={t.id}",
                due_text=_due_text(t.due_at, today),
                action_text="去跟进",
                can_complete=False,
                task_id=t.id,
            )
        )

    # ── 3. 作业：待批 / 逾期未交 ───────────────────────────────
    pending_hw = 0
    if course_ids:
        hws = (
            db.query(Homework)
            .filter(
                Homework.course_id.in_(course_ids),
                Homework.is_deleted.is_(False),
                Homework.status == HomeworkStatus.PUBLISHED,
            )
            .order_by(Homework.due_at.asc())
            .limit(50)
            .all()
        )
        for hw in hws:
            counts = dict(
                db.query(HomeworkSubmission.status, func.count(HomeworkSubmission.id))
                .filter(HomeworkSubmission.homework_id == hw.id)
                .group_by(HomeworkSubmission.status)
                .all()
            )
            to_grade = (counts.get(SubmissionStatus.SUBMITTED, 0) or 0) + (
                counts.get(SubmissionStatus.LATE, 0) or 0
            )
            pending_hw += to_grade
            overdue_due = hw.due_at is not None and hw.due_at.date() < today
            if to_grade == 0 and not overdue_due:
                continue
            course = next((c for c in courses if c.id == hw.course_id), None)
            if to_grade > 0:
                title = f"{hw.title} 有 {to_grade} 份待批"
                desc = "学生已交，等你给反馈"
                action = "去批改"
            else:
                title = f"{hw.title} 已过截止"
                desc = "可以一键催交未提交的学生"
                action = "去催交"
            items.append(
                TeachingInboxItem(
                    id=f"hw-{hw.id}",
                    kind="homework",
                    priority="mid" if to_grade else "low",
                    title=title,
                    desc=f"{hw.course_id and (course.name if course else '')} · {desc}",
                    link=f"/teacher/teaching?course={hw.course_id}&tab=homework&hw={hw.id}",
                    course_id=hw.course_id,
                    course_name=course.name if course else "",
                    class_name=cls_names.get(course.class_group_id, "") if course else "",
                    due_text=_due_text(hw.due_at, today),
                    count=to_grade,
                    action_text=action,
                )
            )

    # ── 4. 教学链路派生待办（含管理员派单） ────────────────────
    # 管理员派单 source_type=admin，不带 course_id，教师端此前完全看不到；
    # 这里把它并进来，保证「上面派下来的事」和「我自己课上发生的事」在同一张清单里。
    other_tasks = (
        db.query(TeacherTask)
        .filter(
            TeacherTask.teacher_id == teacher_id,
            TeacherTask.source_type.in_([TaskSourceType.FOLLOW_UP, TaskSourceType.ADMIN, TaskSourceType.MANUAL]),
            TeacherTask.status.notin_([TaskStatus.DONE, TaskStatus.EXPIRED]),
        )
        .order_by(TeacherTask.due_at.is_(None), TeacherTask.due_at.asc())
        .limit(50)
        .all()
    )
    for t in other_tasks:
        is_admin = t.source_type == TaskSourceType.ADMIN
        items.append(
            TeachingInboxItem(
                id=f"task-{t.id}",
                kind="task",
                priority="high" if is_admin else "mid",
                title=t.title,
                desc=(t.detail or "")[:80] or ("管理员下发" if is_admin else "教学链路派生"),
                link=f"/teacher/tasks?open-task={t.id}",
                due_text=_due_text(t.due_at, today),
                action_text="去处理",
                can_complete=t.priority != TaskPriority.HIGH,
                task_id=t.id,
            )
        )

    # 排序：先按优先级，再按期限文本（今天 < 明天 < 其它），保证「今天要做的」浮到顶
    prio_rank = {"high": 0, "mid": 1, "low": 2}
    kind_rank = {"attendance": 0, "alert": 1, "homework": 2, "task": 3}
    items.sort(key=lambda i: (prio_rank.get(i.priority, 9), kind_rank.get(i.kind, 9)))

    return TeachingInboxOut(
        items=items[:30],
        unmarked_count=len(unmarked),
        pending_homework_count=pending_hw,
        grade_alert_count=sum(1 for i in items if i.kind == "alert"),
        task_count=sum(1 for i in items if i.kind == "task"),
        today_course_count=len(today_courses),
        generated_at=datetime.now().isoformat(),
    )


def _due_text(due_at, today: date) -> str:
    """期限的人话表述：今天 / 明天 / 已逾期 N 天 / 剩余 N 天。"""
    if not due_at:
        return ""
    d = due_at.date() if isinstance(due_at, datetime) else due_at
    delta = (d - today).days
    if delta == 0:
        return "今天到期"
    if delta == 1:
        return "明天到期"
    if delta < 0:
        return f"已逾期 {-delta} 天"
    return f"剩 {delta} 天"
