"""课程授课教师的解析与查询（教学域共用的唯一入口）。

为什么单独成模块
----------------
``courses`` 表里授课教师有两条表达：结构化的 ``teacher_id`` 和历史沿用的
``teacher`` 姓名字符串。如果每个调用方各写一遍匹配逻辑，「教师看自己的课」
在不同接口里会得到不同结果——这比没有这个功能更难排查。所以：

- **写**：一律走 :func:`resolve_teacher_id`，按姓名反查账号并回写 ``teacher_id``；
- **读**：一律走 :func:`teacher_course_filter`，包含姓名兜底条件。

兜底条件（``teacher_id IS NULL AND teacher == 我的姓名``）只在历史数据未回填时
生效。回填覆盖率达标后可整体删除，调用方无需改动。
"""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.academic import Course
from app.models.user import User, UserRole


def resolve_teacher_id(db: Session, name: str | None) -> int | None:
    """姓名 → 教师账号 id。

    只在「姓名唯一命中且角色为教师」时返回 id，其余一律返回 None：
    同名教师、姓名为空、账号尚未创建都属于无法确定的情况，猜错比空着更糟——
    空着只影响本人的课表完整性，猜错会把课挂到别人名下。
    """
    if not name or not name.strip():
        return None
    rows = (
        db.query(User.id)
        .filter(User.role == UserRole.TEACHER, User.name == name.strip())
        .limit(2)
        .all()
    )
    return rows[0][0] if len(rows) == 1 else None


def teacher_course_filter(teacher: User):
    """构造「这位老师的课」的 SQL 条件（含历史姓名兜底）。"""
    conditions = [Course.teacher_id == teacher.id]
    if teacher.name:
        conditions.append(
            (Course.teacher_id.is_(None)) & (Course.teacher == teacher.name)
        )
    return or_(*conditions)


def is_my_course(course: Course, teacher: User) -> bool:
    """单条课程的归属判定，用于写入前的权限校验（与上面的过滤条件同源）。"""
    if course.teacher_id is not None:
        return course.teacher_id == teacher.id
    return bool(teacher.name) and course.teacher == teacher.name


def my_courses(db: Session, teacher: User, semester: str | None = None) -> list[Course]:
    """这位老师教的全部课程，按周次与节次排序。"""
    query = db.query(Course).filter(teacher_course_filter(teacher))
    if semester:
        query = query.filter(Course.semester == semester)
    return query.order_by(Course.day_of_week, Course.start_period).all()


def default_semester(db: Session) -> str | None:
    """当前应展示的学期：优先用最新一条课程数据的学期。

    没有独立的「当前学期」标记，用「最新学期值」做默认值最贴近实际：
    教务导入时总是先导新学期，最新的一定是当前学期。
    """
    row = (
        db.query(Course.semester)
        .filter(Course.semester.isnot(None), Course.semester != "")
        .order_by(Course.semester.desc())
        .first()
    )
    return row[0] if row else None
