from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.academic import Course, Grade, Exam
from app.models.user import User, UserRole
from app.schemas.academic import CourseOut, GradeOut, ExamOut
from app.services.teaching_scope import my_courses

router = APIRouter(prefix="/api/academic", tags=["academic"])


@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    semester: str | None = Query(None, description="学期筛选"),
    scope: str = Query(
        "all",
        description="教师视角：all=我带的班+我教的课 / taught=只我教的课 / tutored=只我带的学生所在班",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程列表。

    教师侧从 v3 起有两个不同口径，必须分清：

    - **我教的课**（``taught``）：``courses.teacher_id`` 指向我，这是教师端
      「我的教学」的数据源，也是课表里显示「任课教师」的依据；
    - **我带的班**（``tutored``）：``users.tutor_id`` 指向我的学生所在班级的课，
      同一门课可能由别的老师任教——这是「看学生上什么课」，不是「我要上什么课」。

    两者混在一起是旧实现的问题所在：教师打开课程列表看到的是全班的课，
    分不清哪门是自己的。默认 ``all`` 保留原有行为（首页班级图表依赖它）。
    """
    if current_user.role == UserRole.ADMIN:
        query = db.query(Course)
        if semester:
            query = query.filter(Course.semester == semester)
        return query.order_by(Course.day_of_week, Course.start_period).all()

    if current_user.role == UserRole.TEACHER:
        if scope == "taught":
            return my_courses(db, current_user, semester)

        student_class_ids = [
            s.class_group_id for s in
            db.query(User).filter(
                User.tutor_id == current_user.id,
                User.class_group_id.isnot(None),
            ).all()
        ]
        if scope == "tutored":
            if not student_class_ids:
                return []
            query = db.query(Course).filter(Course.class_group_id.in_(student_class_ids))
            if semester:
                query = query.filter(Course.semester == semester)
            return query.order_by(Course.day_of_week, Course.start_period).all()

        # all：并集。先取「我教的」，再补「我带班的班里的课」，按课程 id 去重
        mine = my_courses(db, current_user, semester)
        seen = {c.id for c in mine}
        merged = list(mine)
        if student_class_ids:
            query = db.query(Course).filter(Course.class_group_id.in_(student_class_ids))
            if semester:
                query = query.filter(Course.semester == semester)
            for c in query.order_by(Course.day_of_week, Course.start_period).all():
                if c.id not in seen:
                    seen.add(c.id)
                    merged.append(c)
        merged.sort(key=lambda c: (c.day_of_week, c.start_period))
        return merged

    # 学生: 通过班级查看课程
    if not current_user.class_group_id:
        return []
    query = db.query(Course).filter(Course.class_group_id == current_user.class_group_id)
    if semester:
        query = query.filter(Course.semester == semester)
    return query.order_by(Course.day_of_week, Course.start_period).all()


@router.get("/grades", response_model=list[GradeOut])
def list_grades(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Grade)

    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.TEACHER:
        student_ids = [s.id for s in db.query(User).filter(User.tutor_id == current_user.id).all()]
        query = query.filter(Grade.student_id.in_(student_ids))
    else:
        query = query.filter(Grade.student_id == current_user.id)

    if student_id:
        if current_user.role == UserRole.STUDENT and student_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问其他学生的数据")
        query = query.filter(Grade.student_id == student_id)

    return query.order_by(Grade.semester.desc()).all()


@router.get("/exams", response_model=list[ExamOut])
def list_exams(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Exam)

    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.TEACHER:
        student_ids = [s.id for s in db.query(User).filter(User.tutor_id == current_user.id).all()]
        query = query.filter(Exam.student_id.in_(student_ids))
    else:
        query = query.filter(Exam.student_id == current_user.id)

    if student_id:
        if current_user.role == UserRole.STUDENT and student_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问其他学生的数据")
        query = query.filter(Exam.student_id == student_id)

    return query.all()
