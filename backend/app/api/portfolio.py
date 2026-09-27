"""我的作品集 API：项目经历（复用成长档案 projects）+ 证书荣誉 + 个人简历。仅 HTTP 语义，业务下沉 services。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.portfolio import CertificateCreate, CertificateOut, ResumeCreate, ResumeOut
from app.services import portfolio_service

router = APIRouter(prefix="/api/portfolio", tags=["我的作品集"])


# ==================== 证书荣誉 ====================

@router.get("/certificates", response_model=list[CertificateOut])
def list_certificates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.list_certificates(db, current_user)


@router.post("/certificates", response_model=CertificateOut)
def create_certificate(
    req: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return portfolio_service.create_certificate(db, current_user, req)


@router.put("/certificates/{cert_id}", response_model=CertificateOut)
def update_certificate(
    cert_id: int,
    req: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return portfolio_service.update_certificate(db, current_user, cert_id, req)


@router.delete("/certificates/{cert_id}")
def delete_certificate(cert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.delete_certificate(db, current_user, cert_id)


# ==================== 个人简历 ====================

@router.get("/resumes", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.list_resumes(db, current_user)


@router.post("/resumes", response_model=ResumeOut)
def create_resume(
    req: ResumeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return portfolio_service.create_resume(db, current_user, req)


@router.put("/resumes/{resume_id}/current", response_model=ResumeOut)
def set_current_resume(resume_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.set_current_resume(db, current_user, resume_id)


@router.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.delete_resume(db, current_user, resume_id)