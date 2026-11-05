"""教学域 API：只读课表查询。

教师端前端只保留「我的课表」这一条教学线，因此这里也只提供课表的三种视角：
我的 / 按任课教师 / 按班级。课堂执行类能力（点名、作业、成绩录入、教学收件箱）
前端没有对应页面，已从后端下线，避免出现「接口在、入口无」的悬空能力。
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.academic import ClassGroup, College, Course, Major
from app.models.teaching import Attendance
from app.models.user import User, UserRole
from app.schemas.teaching import (
    ScheduleOut,
    ScheduleTeacherOut,
    ScheduleClassOut,
    TeachingCourseOut,
)
from app.services.teaching_scope import (
    default_semester,
    resolve_teacher_id,
    teacher_course_filter,
)

router = APIRouter(prefix="/api/teaching", tags=["teaching"])

_teacher_only = require_role(UserRole.TEACHER)


# ==============================================================
# 内部工具
# ==============================================================


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


# ══════════════════════════════════════════════════════════════════
# 我的课表（只读）
# ══════════════════════════════════════════════════════════════════

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
