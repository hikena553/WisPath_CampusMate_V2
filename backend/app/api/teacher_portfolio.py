"""教师成长档案接口：工作案例 / 荣誉 / 培训研修 / 研究成果，含成长报告导出数据。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.teacher_portfolio import (
    PortfolioItemCreate,
    PortfolioItemOut,
    PortfolioItemUpdate,
    PortfolioReport,
)
from app.services import teacher_portfolio_service, learning_event_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teacher-portfolio", tags=["teacher-portfolio"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/report", response_model=PortfolioReport)
def get_report(user: User = Depends(_teacher_only), db: Session = Depends(get_db)):
    """成长报告数据（前端复用打印方案导出）。"""
    return teacher_portfolio_service.report(db, user.id)


@router.get("", response_model=list[PortfolioItemOut])
def list_items(
    item_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    items, _ = teacher_portfolio_service.list_items(
        db, user.id, item_type=item_type, limit=limit, offset=offset
    )
    return items


@router.post("", response_model=PortfolioItemOut)
def create_item(
    payload: PortfolioItemCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    item = teacher_portfolio_service.create_item(
        db,
        teacher_id=user.id,
        title=payload.title,
        item_type=payload.item_type,
        evidence=[e.model_dump() for e in payload.evidence],
        reflection=payload.reflection,
        occurred_on=payload.occurred_on,
        visibility=payload.visibility,
    )
    # 学情数据底座：单点写入（旁路，失败不影响主流程）
    learning_event_service.emit(
        db,
        actor_id=user.id,
        verb="portfolio.create",
        object_type="portfolio_item",
        object_id=item.id,
        context={"item_type": payload.item_type},
    )
    db.commit()
    return teacher_portfolio_service.serialize(item)


@router.patch("/{item_id}", response_model=PortfolioItemOut)
def update_item(
    item_id: int,
    payload: PortfolioItemUpdate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    item = teacher_portfolio_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="档案条目不存在")
    if user.role != UserRole.ADMIN and item.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能修改本人的成长档案")

    data = payload.model_dump(exclude_unset=True)
    if "evidence" in data and data["evidence"] is not None:
        data["evidence"] = [
            e.model_dump() if hasattr(e, "model_dump") else e for e in data["evidence"]
        ]
    teacher_portfolio_service.update_item(db, item, data)
    return teacher_portfolio_service.serialize(item)


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    item = teacher_portfolio_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="档案条目不存在")
    if user.role != UserRole.ADMIN and item.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能删除本人的成长档案")
    teacher_portfolio_service.soft_delete(db, item)
    return {"message": "已删除"}