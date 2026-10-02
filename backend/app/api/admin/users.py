from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from urllib.parse import quote

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import hash_password, generate_random_password
from app.models.user import User, UserRole
from app.models.crisis import AIDialogSummary
from app.schemas.admin import (
    TeacherCreate, TeacherOut, TeacherCreatedOut,
    StudentBriefOut, StudentUpdate, ImportResult,
)
from app.services.import_export_service import export_users, import_users
from app.services.scoring import calc_radar_score
from app.api.admin.common import PaginatedResponse

router = APIRouter(tags=["admin"])

# ========== 教师管理 ==========

@router.post("/teachers", response_model=TeacherCreatedOut)
def create_teacher(
    data: TeacherCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="工号已存在")

    initial_password = generate_random_password()
    teacher = User(
        username=data.username,
        name=data.name,
        role=UserRole.TEACHER,
        password_hash=hash_password(initial_password),
        college=data.college,
        title=data.title,
        department=data.department,
        gender=data.gender,
        phone=data.phone,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return TeacherCreatedOut(
        id=teacher.id, username=teacher.username, name=teacher.name,
        college=teacher.college, avatar=teacher.avatar,
        title=teacher.title, department=teacher.department,
        student_count=0,
        initial_password=initial_password,
    )


@router.get("/teachers", response_model=PaginatedResponse, summary="获取教师列表", description="分页获取教师列表，支持按姓名、工号、学院搜索")
def list_teachers(
    search: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """获取教师列表（分页）"""
    # #9 子查询：一次性聚合每位教师的学生数量
    from sqlalchemy import func as sa_func
    student_count_sub = (
        db.query(User.tutor_id, sa_func.count(User.id).label("cnt"))
        .filter(User.role == UserRole.STUDENT, User.tutor_id.isnot(None))
        .group_by(User.tutor_id)
        .subquery()
    )

    query = (
        db.query(User, sa_func.coalesce(student_count_sub.c.cnt, 0).label("student_count"))
        .outerjoin(student_count_sub, User.id == student_count_sub.c.tutor_id)
        .filter(User.role == UserRole.TEACHER)
    )
    if search:
        from app.services.knowledge_service import _escape_like
        safe = _escape_like(search)
        like = f"%{safe}%"
        query = query.filter(User.name.like(like, escape="\\") | User.username.like(like, escape="\\") | User.college.like(like, escape="\\"))

    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    rows = query.offset(start).limit(page_size).all()

    result = []
    for t, student_count in rows:
        result.append(TeacherOut(
            id=t.id,
            username=t.username,
            name=t.name,
            college=t.college,
            avatar=t.avatar,
            title=t.title,
            department=t.department,
            student_count=student_count,
        ))

    return PaginatedResponse(
        items=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/teachers/{teacher_id}/students", response_model=list[StudentBriefOut])
def get_teacher_students(
    teacher_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == UserRole.TEACHER).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")

    students = db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == teacher_id).all()
    result = []
    for s in students:
        score = calc_radar_score(db, s.id, s)
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == s.id
        ).order_by(AIDialogSummary.created_at.desc()).first()

        result.append(StudentBriefOut(
            id=s.id,
            username=s.username,
            name=s.name,
            college=s.college,
            avatar=s.avatar,
            score=score,
            crisis_level=latest_crisis.level.value if latest_crisis else None,
        ))
    return result


@router.delete("/teachers/batch")
def batch_delete_teachers(
    ids: list[int] = Body(..., embed=True),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """批量删除教师（注意：必须注册在 /teachers/{teacher_id} 之前，避免路由被吞）"""
    teachers = db.query(User).filter(User.id.in_(ids), User.role == UserRole.TEACHER).all()
    if not teachers:
        raise HTTPException(status_code=404, detail="未找到指定教师")

    deleted_names = []
    for t in teachers:
        db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == t.id).update(
            {"tutor_id": None}
        )
        deleted_names.append(t.name)
        db.delete(t)

    db.commit()
    return {"message": f"已删除 {len(deleted_names)} 名教师：{', '.join(deleted_names)}"}


@router.delete("/teachers/{teacher_id}")
def delete_teacher(
    teacher_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == UserRole.TEACHER).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")

    db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == teacher_id).update(
        {"tutor_id": None}
    )
    db.delete(teacher)
    db.commit()
    return {"message": f"已删除教师 {teacher.name}，其名下学生的辅导员已清空"}


# ========== 学生管理 ==========

@router.get("/students", response_model=PaginatedResponse, summary="获取学生列表", description="分页获取学生列表，支持按学号、姓名、学院、班级筛选")
def list_students(
    search: str | None = Query(None, description="搜索学号或姓名"),
    college: str | None = Query(None, description="学院筛选"),
    class_name: str | None = Query(None, description="班级筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """获取学生列表（分页）"""
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if search:
        from app.services.knowledge_service import _escape_like
        safe = _escape_like(search)
        like = f"%{safe}%"
        query = query.filter(User.name.like(like, escape="\\") | User.username.like(like, escape="\\"))
    if college:
        from app.services.knowledge_service import _escape_like
        safe_college = _escape_like(college)
        query = query.filter(User.college.like(f"%{safe_college}%", escape="\\"))
    if class_name:
        query = query.filter(User.class_name == class_name)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    students = query.offset(start).limit(page_size).all()

    # #10 批量查询：一次获取本页所有学生的最新危机记录
    student_ids = [s.id for s in students]
    latest_crisis_map: dict[int, str] = {}
    if student_ids:
        from sqlalchemy import func as sa_func
        crisis_sub = (
            db.query(
                AIDialogSummary.student_id,
                AIDialogSummary.level,
                sa_func.row_number().over(
                    partition_by=AIDialogSummary.student_id,
                    order_by=AIDialogSummary.created_at.desc()
                ).label("rn")
            )
            .filter(AIDialogSummary.student_id.in_(student_ids))
            .subquery()
        )
        crisis_rows = db.query(crisis_sub).filter(crisis_sub.c.rn == 1).all()
        latest_crisis_map = {r.student_id: r.level.value for r in crisis_rows}

    result = []
    for s in students:
        score = calc_radar_score(db, s.id, s)
        result.append(StudentBriefOut(
            id=s.id, username=s.username, name=s.name,
            college=s.college, class_name=s.class_name, avatar=s.avatar,
            score=score,
            crisis_level=latest_crisis_map.get(s.id),
        ))

    return PaginatedResponse(
        items=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/students/stats")
def student_stats(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    total = db.query(User).filter(User.role == UserRole.STUDENT).count()

    college_rows = db.query(User.college, func.count(User.id)).filter(
        User.role == UserRole.STUDENT, User.college.isnot(None)
    ).group_by(User.college).all()
    college_stats = [{"college": c, "count": n} for c, n in college_rows]

    crisis_sub = db.query(
        AIDialogSummary.student_id,
        AIDialogSummary.level,
        func.row_number().over(
            partition_by=AIDialogSummary.student_id,
            order_by=AIDialogSummary.created_at.desc()
        ).label("rn")
    ).subquery()

    crisis_counts = db.query(crisis_sub.c.level, func.count(crisis_sub.c.student_id)).filter(
        crisis_sub.c.rn == 1
    ).group_by(crisis_sub.c.level).all()
    crisis_stats = [{"level": level.value, "count": n} for level, n in crisis_counts]

    no_crisis = total - sum(n for _, n in crisis_counts)
    if no_crisis > 0:
        crisis_stats.append({"level": "none", "count": no_crisis})

    return {"total": total, "college_stats": college_stats, "crisis_stats": crisis_stats}


@router.put("/students/{student_id}", response_model=StudentBriefOut)
def update_student(
    student_id: int,
    data: StudentUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    for key, val in data.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(student, key, val)

    db.commit()
    db.refresh(student)

    score = calc_radar_score(db, student.id, student)
    latest_crisis = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student.id
    ).order_by(AIDialogSummary.created_at.desc()).first()

    return StudentBriefOut(
        id=student.id, username=student.username, name=student.name,
        college=student.college, class_name=student.class_name, avatar=student.avatar,
        score=score,
        crisis_level=latest_crisis.level.value if latest_crisis else None,
    )


# ========== 密码管理 ==========

@router.post("/reset-password/{user_id}")
def reset_password(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    new_password = generate_random_password()
    target.password_hash = hash_password(new_password)
    target.password_changed = False
    db.commit()
    return {
        "message": f"已重置 {target.name} 的密码",
        "initial_password": new_password,
        "hint": "初始密码仅在本次响应中返回，请管理员线下转交，用户首次登录后强制修改",
    }


# ========== 数据导入导出 ==========


# ========== 课程管理 ==========

@router.get("/export")
def export_data(
    role: str = Query(..., description="student 或 teacher"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="role 必须是 student 或 teacher")

    user_role = UserRole.STUDENT if role == "student" else UserRole.TEACHER
    data = export_users(db, user_role)

    filename = "学生数据.xlsx" if role == "student" else "教师数据.xlsx"
    # 使用 RFC 5987 编码处理中文文件名
    encoded_filename = quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.post("/import", response_model=ImportResult)
async def import_data(
    role: str = Query(..., description="student 或 teacher"),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="role 必须是 student 或 teacher")

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")

    content = await file.read()
    user_role = UserRole.STUDENT if role == "student" else UserRole.TEACHER
    result = import_users(db, user_role, content)
    return ImportResult(**result)
