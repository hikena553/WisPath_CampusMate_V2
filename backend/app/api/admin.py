from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from urllib.parse import quote
from typing import Any
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.campus import CampusFigure
from app.models.crisis import AIDialogSummary
from app.models.academic import Course, ClassGroup, Major, College
from app.schemas.admin import (
    KnowledgeItemCreate, KnowledgeItemUpdate, KnowledgeItemOut,
    DocumentOut, TeacherCreate, TeacherOut, StudentBriefOut, StudentUpdate, ImportResult,
)
from app.schemas.campus import CampusFigureOut, CampusFigureCreate, CampusFigureUpdate
from app.schemas.academic import CourseOut, CourseCreate
from app.services import knowledge_service
from app.services.import_export_service import export_users, import_users
from app.services.scoring import calc_radar_score

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ========== 分页响应模型 ==========
class PaginatedResponse(BaseModel):
    """通用分页响应模型"""
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========== 知识库管理 ==========

@router.get("/knowledge", response_model=PaginatedResponse, summary="获取知识库列表", description="分页获取知识库问答对列表，支持按分类和关键词筛选")
def list_knowledge(
    category: str | None = Query(None, description="分类筛选"),
    search: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """获取知识库列表（分页）"""
    query = knowledge_service.get_all_knowledge_items(db, category, search)
    total = len(query)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    items = query[start:end]

    return PaginatedResponse(
        items=[KnowledgeItemOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/knowledge", response_model=KnowledgeItemOut)
def create_knowledge(
    data: KnowledgeItemCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return knowledge_service.create_knowledge_item(db, data.category, data.question, data.answer, data.tags)


@router.put("/knowledge/{item_id}", response_model=KnowledgeItemOut)
def update_knowledge(
    item_id: int,
    data: KnowledgeItemUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    item = knowledge_service.update_knowledge_item(db, item_id, **data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="知识库条目不存在")
    return item


@router.delete("/knowledge/{item_id}")
def delete_knowledge(
    item_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if not knowledge_service.delete_knowledge_item(db, item_id):
        raise HTTPException(status_code=404, detail="知识库条目不存在")
    return {"message": "删除成功"}


@router.post("/knowledge/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    allowed_types = {"pdf", "docx", "txt"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 PDF/DOCX/TXT 格式")

    import os
    from pathlib import Path
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = knowledge_service.save_document(db, file.filename, ext, str(file_path), user.id)

    try:
        chunks = knowledge_service.parse_document(str(file_path), ext)
        if chunks:
            knowledge_service.save_chunks(db, doc.id, chunks)
        else:
            doc.status = "failed"
            db.commit()
            raise HTTPException(status_code=422, detail="文档解析失败：未能提取到有效内容")
    except HTTPException:
        raise
    except Exception as e:
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")

    return {"message": "上传成功", "document_id": doc.id, "chunk_count": len(chunks)}


@router.get("/knowledge/documents", response_model=list[DocumentOut])
def list_documents(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    docs = knowledge_service.get_all_documents(db)
    return [DocumentOut(
        id=d.id,
        filename=d.filename,
        file_type=d.file_type,
        status=d.status,
        chunk_count=d.chunk_count,
        created_at=d.created_at.isoformat() if d.created_at else None,
    ) for d in docs]


@router.delete("/knowledge/documents/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if not knowledge_service.delete_document(db, doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"message": "删除成功"}


# ========== 教师管理 ==========

@router.post("/teachers", response_model=TeacherOut)
def create_teacher(
    data: TeacherCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="工号已存在")

    teacher = User(
        username=data.username,
        name=data.name,
        role=UserRole.TEACHER,
        password_hash=hash_password("123456"),
        college=data.college,
        title=data.title,
        department=data.department,
        gender=data.gender,
        phone=data.phone,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return TeacherOut(
        id=teacher.id, username=teacher.username, name=teacher.name,
        college=teacher.college, avatar=teacher.avatar,
        title=teacher.title, department=teacher.department,
        student_count=0,
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
    query = db.query(User).filter(User.role == UserRole.TEACHER)
    if search:
        like = f"%{search}%"
        query = query.filter(User.name.like(like) | User.username.like(like) | User.college.like(like))

    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    teachers = query.offset(start).limit(page_size).all()

    result = []
    for t in teachers:
        student_count = db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == t.id).count()
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


@router.delete("/teachers/batch")
def batch_delete_teachers(
    ids: list[int] = Body(..., embed=True),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
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
        like = f"%{search}%"
        query = query.filter(User.name.like(like) | User.username.like(like))
    if college:
        query = query.filter(User.college.like(f"%{college}%"))
    if class_name:
        query = query.filter(User.class_name == class_name)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    students = query.offset(start).limit(page_size).all()

    result = []
    for s in students:
        score = calc_radar_score(db, s.id, s)
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == s.id
        ).order_by(AIDialogSummary.created_at.desc()).first()

        result.append(StudentBriefOut(
            id=s.id, username=s.username, name=s.name,
            college=s.college, class_name=s.class_name, avatar=s.avatar,
            score=score,
            crisis_level=latest_crisis.level.value if latest_crisis else None,
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

    target.password_hash = hash_password("123456")
    target.password_changed = False
    db.commit()
    return {"message": f"已将 {target.name} 的密码重置为 123456"}


# ========== 数据导入导出 ==========

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


# ========== 人物风采管理 ==========

@router.get("/figures", response_model=list[CampusFigureOut])
def list_figures(
    category: str | None = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(CampusFigure)
    if category:
        query = query.filter(CampusFigure.category == category)
    return query.all()


@router.post("/figures", response_model=CampusFigureOut)
def create_figure(
    data: CampusFigureCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    figure = CampusFigure(**data.model_dump())
    db.add(figure)
    db.commit()
    db.refresh(figure)
    return figure


@router.put("/figures/{figure_id}", response_model=CampusFigureOut)
def update_figure(
    figure_id: int,
    data: CampusFigureUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    figure = db.query(CampusFigure).filter(CampusFigure.id == figure_id).first()
    if not figure:
        raise HTTPException(status_code=404, detail="人物不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(figure, key, val)
    db.commit()
    db.refresh(figure)
    return figure


@router.delete("/figures/{figure_id}")
def delete_figure(
    figure_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    figure = db.query(CampusFigure).filter(CampusFigure.id == figure_id).first()
    if not figure:
        raise HTTPException(status_code=404, detail="人物不存在")
    db.delete(figure)
    db.commit()
    return {"message": "删除成功"}


# ========== 课程管理 ==========

@router.get("/courses", response_model=list[CourseOut])
def admin_list_courses(
    class_group_id: int | None = Query(None),
    semester: str | None = Query(None),
    college_id: int | None = Query(None),
    major_id: int | None = Query(None),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员获取课程列表，支持多级筛选"""
    q = db.query(Course)
    if class_group_id:
        q = q.filter(Course.class_group_id == class_group_id)
    elif major_id:
        cg_ids = [cg.id for cg in db.query(ClassGroup).filter(ClassGroup.major_id == major_id).all()]
        q = q.filter(Course.class_group_id.in_(cg_ids))
    elif college_id:
        major_ids = [m.id for m in db.query(Major).filter(Major.college_id == college_id).all()]
        cg_ids = [cg.id for cg in db.query(ClassGroup).filter(ClassGroup.major_id.in_(major_ids)).all()]
        q = q.filter(Course.class_group_id.in_(cg_ids))
    if semester:
        q = q.filter(Course.semester == semester)
    return q.order_by(Course.day_of_week, Course.start_period).all()


@router.post("/courses", response_model=CourseOut)
def admin_create_course(
    data: CourseCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员新增课程"""
    cg = db.query(ClassGroup).get(data.class_group_id)
    if not cg:
        raise HTTPException(400, "班级不存在")
    # 检测时间冲突
    conflict = db.query(Course).filter(
        Course.class_group_id == data.class_group_id,
        Course.semester == data.semester,
        Course.day_of_week == data.day_of_week,
        Course.start_period <= data.end_period,
        Course.end_period >= data.start_period,
    ).first()
    if conflict:
        raise HTTPException(400, f"时间冲突：与课程「{conflict.name}」(第{conflict.start_period}-{conflict.end_period}节)重叠")
    obj = Course(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/courses/{course_id}", response_model=CourseOut)
def admin_update_course(
    course_id: int,
    data: CourseCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员修改课程"""
    obj = db.query(Course).get(course_id)
    if not obj:
        raise HTTPException(404, "课程不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/courses/{course_id}")
def admin_delete_course(
    course_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员删除课程"""
    obj = db.query(Course).get(course_id)
    if not obj:
        raise HTTPException(404, "课程不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.delete("/courses/batch")
def admin_batch_delete_courses(
    ids: list[int] = Body(..., embed=True),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员批量删除课程"""
    count = db.query(Course).filter(Course.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted": count}
