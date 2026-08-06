from collections import defaultdict
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.growth import GrowthRecord, StudentProject
from app.models.user import User, UserRole
from app.models.academic import Grade
from app.models.leave import LeaveRequest
from app.schemas.growth import GrowthRecordCreate, GrowthRecordOut, GrowthProfileOut, RadarDimension, MonthlyStat, GpaPoint, StudentProjectCreate, StudentProjectOut
from app.schemas.user import SkillsUpdate
from app.core.deps import get_current_user
from app.services.scoring import calc_radar_score, get_radar_dimensions, get_record_type_counts, TYPE_LABELS
from app.utils.enum_helpers import safe_enum_val

router = APIRouter(prefix="/api/growth", tags=["growth"])


def _parse_date(d: str | None) -> date | None:
    if not d:
        return None
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


@router.get("/profile", response_model=GrowthProfileOut)
def get_growth_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sid = current_user.id
    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == sid).all()
    skills_data = current_user.skills_json or {"skills": [], "interests": []}
    raw_skills = skills_data.get("skills", [])
    skills = [s["name"] if isinstance(s, dict) else s for s in raw_skills]
    interests = skills_data.get("interests", [])

    # 按类型统计
    type_counts = get_record_type_counts(records)
    stats_by_type = [{"name": TYPE_LABELS.get(k, k), "value": v} for k, v in type_counts.items()]

    # 月度趋势（最近12个月）
    monthly = defaultdict(lambda: defaultdict(int))
    for r in records:
        key = r.date.strftime("%Y-%m")
        t = safe_enum_val(r.type)
        monthly[key][t] += 1

    all_months = sorted(monthly.keys())[-12:] if monthly else []
    monthly_trend = []
    for m in all_months:
        for t, c in monthly[m].items():
            monthly_trend.append(MonthlyStat(month=m, count=c, type=t))

    # 雷达图维度（来自共享评分模块）
    raw_radar = get_radar_dimensions(db, sid, current_user)
    radar = [RadarDimension(**d) for d in raw_radar]
    n_records = len(records)
    n_skills = len(skills)
    total_score = calc_radar_score(db, sid, current_user)

    # GPA学期趋势
    grades = db.query(Grade).filter(Grade.student_id == sid).all()
    semester_gpa = defaultdict(list)
    for g in grades:
        semester_gpa[g.semester].append(g.gpa)
    gpa_trend = []
    for sem in sorted(semester_gpa.keys()):
        avg = round(sum(semester_gpa[sem]) / len(semester_gpa[sem]), 2)
        gpa_trend.append(GpaPoint(semester=sem, gpa=avg))

    return GrowthProfileOut(
        total_score=total_score,
        radar=radar,
        stats_by_type=stats_by_type,
        monthly_trend=monthly_trend,
        skills=skills,
        interests=interests,
        total_records=n_records,
        total_skills=n_skills,
        gpa_trend=gpa_trend,
    )


@router.get("/records", response_model=list[GrowthRecordOut])
def list_records(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(GrowthRecord)
    
    # 数据隔离
    if current_user.role == UserRole.ADMIN:
        pass  # 管理员可查看所有
    elif current_user.role == UserRole.TEACHER:
        # 教师只能查看自己名下学生的数据
        student_ids = [s.id for s in db.query(User).filter(User.tutor_id == current_user.id).all()]
        query = query.filter(GrowthRecord.student_id.in_(student_ids))
    else:
        # 学生只能查看自己的数据
        query = query.filter(GrowthRecord.student_id == current_user.id)
    
    # 如果指定了student_id，进一步检查权限
    if student_id:
        if current_user.role == UserRole.STUDENT and student_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问其他学生的数据")
        query = query.filter(GrowthRecord.student_id == student_id)
    
    return query.order_by(GrowthRecord.date.desc()).all()


@router.post("/records", response_model=GrowthRecordOut)
def create_record(req: GrowthRecordCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 学生只能为自己创建记录
    if current_user.role == UserRole.STUDENT:
        student_id = current_user.id
    else:
        # 教师和管理员可以为任何学生创建记录，但必须提供student_id
        if req.student_id is None:
            raise HTTPException(status_code=400, detail="教师和管理员必须提供student_id")
        student_id = req.student_id
    
    record_data = req.model_dump()
    record_data.pop('student_id', None)  # 移除student_id避免重复
    record = GrowthRecord(student_id=student_id, **record_data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(GrowthRecord).filter(GrowthRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # 数据隔离检查
    if current_user.role == UserRole.STUDENT and record.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除其他学生的记录")
    elif current_user.role == UserRole.TEACHER:
        # 教师只能删除自己名下学生的记录
        student = db.query(User).filter(User.id == record.student_id).first()
        if not student or student.tutor_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除非自己名下学生的记录")
    
    db.delete(record)
    db.commit()
    return {"message": "deleted"}


# ---- Project Showcase ----

@router.get("/projects", response_model=list[StudentProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(StudentProject).filter(
        StudentProject.student_id == current_user.id
    ).order_by(StudentProject.start_date.desc()).all()


@router.post("/projects", response_model=StudentProjectOut)
def create_project(req: StudentProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = req.model_dump()
    data["start_date"] = _parse_date(data["start_date"])
    data["end_date"] = _parse_date(data.get("end_date"))
    project = StudentProject(student_id=current_user.id, **data)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=StudentProjectOut)
def update_project(project_id: int, req: StudentProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(StudentProject).filter(
        StudentProject.id == project_id, StudentProject.student_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    data = req.model_dump()
    data["start_date"] = _parse_date(data["start_date"])
    data["end_date"] = _parse_date(data.get("end_date"))
    for k, v in data.items():
        setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(StudentProject).filter(
        StudentProject.id == project_id, StudentProject.student_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(project)
    db.commit()
    return {"message": "deleted"}


@router.put("/skills")
def update_skills(data: SkillsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current = user.skills_json or {"skills": [], "interests": []}
    current["skills"] = [{"name": s, "context": ""} for s in data.skills]
    current["interests"] = data.interests
    user.skills_json = current
    db.commit()
    return user.skills_json
