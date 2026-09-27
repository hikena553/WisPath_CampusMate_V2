"""材料档案 API：学生上传并归档个人材料（证件/证明/成绩单/学籍等）。仅 HTTP 语义，业务下沉 services。"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.material import MaterialCreate, MaterialOut, MaterialReview
from app.services import material_service

router = APIRouter(prefix="/api/materials", tags=["材料档案"])


@router.post("", response_model=MaterialOut)
def create_material(
    req: MaterialCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return material_service.create_material(db, user, req)


@router.get("", response_model=list[MaterialOut])
def list_materials(
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return material_service.list_materials(db, user, status)


@router.get("/{material_id}", response_model=MaterialOut)
def get_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return material_service.get_material(db, user, material_id)


@router.delete("/{material_id}")
def delete_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return material_service.delete_material(db, user, material_id)