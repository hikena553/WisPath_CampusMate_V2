from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.models.academic import College, Major, ClassGroup
from app.schemas.organization import (
    CollegeCreate, CollegeOut,
    MajorCreate, MajorOut,
    ClassGroupCreate, ClassGroupOut,
)

router = APIRouter(prefix="/api/admin", tags=["组织架构管理"])


# ─── 学院 ───────────────────────────────────────────────────

@router.get("/colleges", response_model=list[CollegeOut])
def list_colleges(db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    return db.query(College).order_by(College.id).all()


@router.post("/colleges", response_model=CollegeOut)
def create_college(data: CollegeCreate, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    if db.query(College).filter(College.name == data.name).first():
        raise HTTPException(400, "学院名称已存在")
    if db.query(College).filter(College.code == data.code).first():
        raise HTTPException(400, "学院代码已存在")
    obj = College(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/colleges/{college_id}", response_model=CollegeOut)
def update_college(college_id: int, data: CollegeCreate, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    obj = db.query(College).get(college_id)
    if not obj:
        raise HTTPException(404, "学院不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/colleges/{college_id}")
def delete_college(college_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    obj = db.query(College).get(college_id)
    if not obj:
        raise HTTPException(404, "学院不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ─── 专业 ───────────────────────────────────────────────────

@router.get("/majors", response_model=list[MajorOut])
def list_majors(
    college_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    q = db.query(Major)
    if college_id:
        q = q.filter(Major.college_id == college_id)
    rows = q.order_by(Major.id).all()
    result = []
    for m in rows:
        out = MajorOut.model_validate(m)
        out.college_name = m.college.name if m.college else None
        result.append(out)
    return result


@router.post("/majors", response_model=MajorOut)
def create_major(data: MajorCreate, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    if not db.query(College).get(data.college_id):
        raise HTTPException(400, "所属学院不存在")
    obj = Major(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    out = MajorOut.model_validate(obj)
    out.college_name = obj.college.name if obj.college else None
    return out


@router.put("/majors/{major_id}", response_model=MajorOut)
def update_major(major_id: int, data: MajorCreate, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    obj = db.query(Major).get(major_id)
    if not obj:
        raise HTTPException(404, "专业不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    out = MajorOut.model_validate(obj)
    out.college_name = obj.college.name if obj.college else None
    return out


@router.delete("/majors/{major_id}")
def delete_major(major_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    obj = db.query(Major).get(major_id)
    if not obj:
        raise HTTPException(404, "专业不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ─── 班级 ───────────────────────────────────────────────────

@router.get("/class-groups", response_model=list[ClassGroupOut])
def list_class_groups(
    major_id: Optional[int] = None,
    college_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    q = db.query(ClassGroup)
    if major_id:
        q = q.filter(ClassGroup.major_id == major_id)
    elif college_id:
        major_ids = [m.id for m in db.query(Major).filter(Major.college_id == college_id).all()]
        q = q.filter(ClassGroup.major_id.in_(major_ids))
    rows = q.order_by(ClassGroup.grade.desc(), ClassGroup.id).all()
    result = []
    for cg in rows:
        out = ClassGroupOut.model_validate(cg)
        out.major_name = cg.major.name if cg.major else None
        out.college_name = cg.major.college.name if cg.major and cg.major.college else None
        result.append(out)
    return result


@router.post("/class-groups", response_model=ClassGroupOut)
def create_class_group(data: ClassGroupCreate, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    if not db.query(Major).get(data.major_id):
        raise HTTPException(400, "所属专业不存在")
    obj = ClassGroup(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    out = ClassGroupOut.model_validate(obj)
    out.major_name = obj.major.name if obj.major else None
    out.college_name = obj.major.college.name if obj.major and obj.major.college else None
    return out


@router.put("/class-groups/{cg_id}", response_model=ClassGroupOut)
def update_class_group(cg_id: int, data: ClassGroupCreate, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    obj = db.query(ClassGroup).get(cg_id)
    if not obj:
        raise HTTPException(404, "班级不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    out = ClassGroupOut.model_validate(obj)
    out.major_name = obj.major.name if obj.major else None
    out.college_name = obj.major.college.name if obj.major and obj.major.college else None
    return out


@router.delete("/class-groups/{cg_id}")
def delete_class_group(cg_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    obj = db.query(ClassGroup).get(cg_id)
    if not obj:
        raise HTTPException(404, "班级不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}
