"""管理端资讯账号管理：/api/admin/media/accounts 的 CRUD 与手动发布。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.media_account import (
    MediaAccountCreate,
    MediaAccountOut,
    MediaAccountUpdate,
    MediaPublishResult,
)
from app.services import media_account_service

router = APIRouter(tags=["admin"])


@router.get("/media/accounts", response_model=list[MediaAccountOut])
def list_media_accounts(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return media_account_service.list_accounts(db)


@router.post("/media/accounts", response_model=MediaAccountOut)
def create_media_account(
    data: MediaAccountCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        return media_account_service.create_account(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/media/accounts/{account_id}", response_model=MediaAccountOut)
def update_media_account(
    account_id: int,
    data: MediaAccountUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    pair = media_account_service.get_account(db, account_id)
    if not pair:
        raise HTTPException(status_code=404, detail="资讯账号不存在")
    return media_account_service.update_account(db, pair[0], pair[1], data)


@router.delete("/media/accounts/{account_id}")
def delete_media_account(
    account_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    pair = media_account_service.get_account(db, account_id)
    if not pair:
        raise HTTPException(status_code=404, detail="资讯账号不存在")
    media_account_service.delete_account(db, pair[0], pair[1])
    return {"message": "deleted"}


@router.post("/media/accounts/{account_id}/publish", response_model=MediaPublishResult)
async def publish_media_digest(
    account_id: int,
    force: bool = False,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """手动发布今日汇总帖；force=True 时覆盖当天已发的汇总。"""
    pair = media_account_service.get_account(db, account_id)
    if not pair:
        raise HTTPException(status_code=404, detail="资讯账号不存在")
    account, account_user = pair
    if not account.is_enabled:
        raise HTTPException(status_code=400, detail="账号已停用，请先启用再发布")
    result = await media_account_service.publish_digest(db, account, account_user, force=force)
    return MediaPublishResult(**result)
