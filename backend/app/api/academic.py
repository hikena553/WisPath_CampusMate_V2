from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.academic import Course, Grade, Exam
from app.models.user import User, UserRole
from app.schemas.academic import CourseOut, GradeOut, ExamOut

router = APIRouter(prefix="/api/academic", tags=["academic"])


@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    semester: str | None = Query(None, description="学期筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程列表 - 学生通过班级关联"""
    query = db.query(Course)

    if current_user.role == UserRole.ADMIN:
        pass  # 管理员可查看所有
    elif current_user.role == UserRole.TEACHER:
        # 教师: 查看其名下学生所在班级的课程
        student_class_ids = [
            s.class_group_id for s in
            db.query(User).filter(
                User.tutor_id == current_user.id,
                User.class_group_id.isnot(None),
            ).all()
        ]
        query = query.filter(Course.class_group_id.in_(student_class_ids))
    else:
        # 学生: 通过班级查看课程
        if not current_user.class_group_id:
            return []
        query = query.filter(Course.class_group_id == current_user.class_group_id)

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
