"""我的作品集：项目经历（复用成长档案 projects）+ 证书荣誉 + 个人简历"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.certificate import Certificate, AwardLevel, CertStatus
from app.models.portfolio import StudentResume
from app.models.user import User
from app.schemas.portfolio import CertificateCreate, CertificateOut, ResumeCreate, ResumeOut

router = APIRouter(prefix="/api/portfolio", tags=["我的作品集"])


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_award_level(s: str | None):
    if not s:
        return None
    try:
        return AwardLevel(s)
    except ValueError:
        return None


# ==================== 证书荣誉 ====================

@router.get("/certificates", response_model=list[CertificateOut])
def list_certificates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Certificate).filter(
        Certificate.student_id == current_user.id
    ).order_by(Certificate.date.desc(), Certificate.id.desc()).all()


@router.post("/certificates", response_model=CertificateOut)
def create_certificate(
    req: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not req.title.strip():
        raise HTTPException(400, "证书名称不能为空")
    cert = Certificate(
        student_id=current_user.id,
        title=req.title.strip(),
        competition_name=req.competition_name,
        award_level=_parse_award_level(req.award_level),
        date=_parse_date(req.date),
        description=req.description,
        image_url=req.image_url,
        status=CertStatus.APPROVED,  # 学生自主维护，直接生效
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.put("/certificates/{cert_id}", response_model=CertificateOut)
def update_certificate(
    cert_id: int,
    req: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cert = db.query(Certificate).filter(
        Certificate.id == cert_id, Certificate.student_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(404, "证书不存在")
    data = req.model_dump(exclude_unset=True)
    if "date" in data:
        data["date"] = _parse_date(data.get("date"))
    if "award_level" in data:
        data["award_level"] = _parse_award_level(data.get("award_level"))
    if "title" in data and not str(data["title"]).strip():
        raise HTTPException(400, "证书名称不能为空")
    for k, v in data.items():
        setattr(cert, k, v)
    db.commit()
    db.refresh(cert)
    return cert


@router.delete("/certificates/{cert_id}")
def delete_certificate(cert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cert = db.query(Certificate).filter(
        Certificate.id == cert_id, Certificate.student_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(404, "证书不存在")
    db.delete(cert)
    db.commit()
    return {"message": "deleted"}


# ==================== 个人简历 ====================

@router.get("/resumes", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(StudentResume).filter(
        StudentResume.student_id == current_user.id
    ).order_by(StudentResume.created_at.desc()).all()


@router.post("/resumes", response_model=ResumeOut)
def create_resume(
    req: ResumeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not req.filename.strip() or not req.url.strip():
        raise HTTPException(400, "简历文件名与地址不能为空")
    has_current = db.query(StudentResume).filter(
        StudentResume.student_id == current_user.id, StudentResume.is_current == 1
    ).first()
    resume = StudentResume(
        student_id=current_user.id,
        filename=req.filename.strip(),
        url=req.url.strip(),
        file_size=req.file_size,
        is_current=1 if not has_current else 0,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.put("/resumes/{resume_id}/current", response_model=ResumeOut)
def set_current_resume(resume_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resume = db.query(StudentResume).filter(
        StudentResume.id == resume_id, StudentResume.student_id == current_user.id
    ).first()
    if not resume:
        raise HTTPException(404, "简历不存在")
    db.query(StudentResume).filter(StudentResume.student_id == current_user.id).update(
        {StudentResume.is_current: 0}
    )
    resume.is_current = 1
    db.commit()
    db.refresh(resume)
    return resume


@router.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resume = db.query(StudentResume).filter(
        StudentResume.id == resume_id, StudentResume.student_id == current_user.id
    ).first()
    if not resume:
        raise HTTPException(404, "简历不存在")
    was_current = resume.is_current == 1
    db.delete(resume)
    db.commit()
    if was_current:
        newest = db.query(StudentResume).filter(
            StudentResume.student_id == current_user.id
        ).order_by(StudentResume.created_at.desc()).first()
        if newest:
            newest.is_current = 1
            db.commit()
    return {"message": "deleted"}