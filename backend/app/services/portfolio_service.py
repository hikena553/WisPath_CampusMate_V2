"""我的作品集业务逻辑：证书荣誉 CRUD + 简历 CRUD/设当前，屏蔽 ORM 细节。"""
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, AwardLevel, CertStatus
from app.models.portfolio import StudentResume
from app.models.user import User
from app.schemas.portfolio import CertificateCreate, CertificateOut, ResumeCreate, ResumeOut


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

def list_certificates(db: Session, current_user: User) -> list[CertificateOut]:
    return (
        db.query(Certificate)
        .filter(Certificate.student_id == current_user.id)
        .order_by(Certificate.date.desc(), Certificate.id.desc())
        .all()
    )


def create_certificate(db: Session, current_user: User, req: CertificateCreate) -> CertificateOut:
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


def update_certificate(
    db: Session, current_user: User, cert_id: int, req: CertificateCreate
) -> CertificateOut:
    cert = (
        db.query(Certificate)
        .filter(Certificate.id == cert_id, Certificate.student_id == current_user.id)
        .first()
    )
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


def delete_certificate(db: Session, current_user: User, cert_id: int) -> dict:
    cert = (
        db.query(Certificate)
        .filter(Certificate.id == cert_id, Certificate.student_id == current_user.id)
        .first()
    )
    if not cert:
        raise HTTPException(404, "证书不存在")
    db.delete(cert)
    db.commit()
    return {"message": "deleted"}


# ==================== 个人简历 ====================

def list_resumes(db: Session, current_user: User) -> list[ResumeOut]:
    return (
        db.query(StudentResume)
        .filter(StudentResume.student_id == current_user.id)
        .order_by(StudentResume.created_at.desc())
        .all()
    )


def create_resume(db: Session, current_user: User, req: ResumeCreate) -> ResumeOut:
    if not req.filename.strip() or not req.url.strip():
        raise HTTPException(400, "简历文件名与地址不能为空")
    has_current = (
        db.query(StudentResume)
        .filter(StudentResume.student_id == current_user.id, StudentResume.is_current == 1)
        .first()
    )
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


def set_current_resume(db: Session, current_user: User, resume_id: int) -> ResumeOut:
    resume = (
        db.query(StudentResume)
        .filter(StudentResume.id == resume_id, StudentResume.student_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(404, "简历不存在")
    db.query(StudentResume).filter(StudentResume.student_id == current_user.id).update(
        {StudentResume.is_current: 0}
    )
    resume.is_current = 1
    db.commit()
    db.refresh(resume)
    return resume


def delete_resume(db: Session, current_user: User, resume_id: int) -> dict:
    resume = (
        db.query(StudentResume)
        .filter(StudentResume.id == resume_id, StudentResume.student_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(404, "简历不存在")
    was_current = resume.is_current == 1
    db.delete(resume)
    db.commit()
    if was_current:
        newest = (
            db.query(StudentResume)
            .filter(StudentResume.student_id == current_user.id)
            .order_by(StudentResume.created_at.desc())
            .first()
        )
        if newest:
            newest.is_current = 1
            db.commit()
    return {"message": "deleted"}