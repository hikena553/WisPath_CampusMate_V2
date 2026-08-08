from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.lost_found import LostFoundItem, LostFoundComment, ItemType, ItemStatus
from app.models.user import User, UserRole
from app.schemas.lost_found import (
    LostFoundItemCreate,
    LostFoundItemOut,
    LostFoundCommentCreate,
    LostFoundCommentOut,
    LostFoundStatusUpdate,
)

router = APIRouter(prefix="/api/lost-found", tags=["失物招领"])


def _item_out(db: Session, item: LostFoundItem, with_comments: bool = False) -> LostFoundItemOut:
    user = db.query(User).filter(User.id == item.user_id).first()
    comments = None
    if with_comments:
        rows = db.query(LostFoundComment).filter(LostFoundComment.item_id == item.id).order_by(LostFoundComment.created_at.asc()).all()
        comments = []
        for c in rows:
            cu = db.query(User).filter(User.id == c.user_id).first()
            comments.append(LostFoundCommentOut(
                id=c.id,
                item_id=c.item_id,
                user_id=c.user_id,
                user_name=cu.name if cu else None,
                content=c.content,
                created_at=c.created_at,
            ))
    return LostFoundItemOut(
        id=item.id,
        user_id=item.user_id,
        user_name=user.name if user else None,
        type=item.type.value if isinstance(item.type, ItemType) else str(item.type),
        title=item.title,
        description=item.description or "",
        location=item.location or "",
        contact=item.contact or "",
        image_url=item.image_url,
        status=item.status.value if isinstance(item.status, ItemStatus) else str(item.status),
        created_at=item.created_at,
        comments=comments,
    )


@router.get("/items", response_model=list[LostFoundItemOut])
def list_items(
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(LostFoundItem)
    if type:
        query = query.filter(LostFoundItem.type == type)
    if status:
        query = query.filter(LostFoundItem.status == status)
    items = query.order_by(LostFoundItem.created_at.desc()).all()
    return [_item_out(db, it) for it in items]


@router.get("/items/{item_id}", response_model=LostFoundItemOut)
def get_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    return _item_out(db, item, with_comments=True)


@router.post("/items", response_model=LostFoundItemOut)
def create_item(req: LostFoundItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.type not in [t.value for t in ItemType]:
        raise HTTPException(status_code=400, detail="类型必须为 lost 或 found")
    item = LostFoundItem(
        user_id=user.id,
        type=ItemType(req.type),
        title=req.title,
        description=req.description,
        location=req.location,
        contact=req.contact,
        image_url=req.image_url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_out(db, item, with_comments=True)


@router.put("/items/{item_id}/status", response_model=LostFoundItemOut)
def update_status(
    item_id: int,
    req: LostFoundStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    if user.role != UserRole.ADMIN and item.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    if req.status not in [s.value for s in ItemStatus]:
        raise HTTPException(status_code=400, detail="状态不合法")
    item.status = ItemStatus(req.status)
    db.commit()
    db.refresh(item)
    return _item_out(db, item, with_comments=True)


@router.delete("/items/{item_id}")
def delete_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    if user.role != UserRole.ADMIN and item.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权删除")
    db.query(LostFoundComment).filter(LostFoundComment.item_id == item.id).delete()
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


@router.post("/items/{item_id}/comments", response_model=LostFoundCommentOut)
def create_comment(
    item_id: int,
    req: LostFoundCommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="留言内容不能为空")
    comment = LostFoundComment(item_id=item_id, user_id=user.id, content=req.content.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return LostFoundCommentOut(
        id=comment.id,
        item_id=comment.item_id,
        user_id=comment.user_id,
        user_name=user.name,
        content=comment.content,
        created_at=comment.created_at,
    )
