"""管理端 · 绵小城 AI 资讯站图谱接口。

三级结构：资讯站（根节点）→ 资讯账号 → 资讯源连接线。
画布上的连接线可以随时断开/重连，断开只影响内容投递与社区展示，不删除任何内容。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.media_account import (
    MediaSourceLinkCreate,
    MediaSourceLinkUpdate,
    MediaStationLinkToggle,
    MediaStationUpdate,
)
from app.services import media_account_service

router = APIRouter(tags=["admin"])


@router.get("/media/station")
def get_media_station(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """资讯站（画布根节点）配置：抓取间隔 / 每日汇总时刻 / 发帖模式 / 总开关。"""
    return media_account_service.get_station_settings(db)


@router.patch("/media/station")
def update_media_station(
    body: MediaStationUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return media_account_service.update_station_config(db, body)


@router.get("/media/graph")
def get_media_graph(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """画布全量数据：资讯站 + 账号（含连接线）+ 可连接资讯源。"""
    return media_account_service.build_graph(db)


@router.patch("/media/accounts/{account_id}/station-link")
def toggle_station_link(
    account_id: int,
    body: MediaStationLinkToggle,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """接入 / 断开「资讯站 ↔ 资讯账号」连接线（不删除账号内容）。"""
    pair = media_account_service.get_account(db, account_id)
    if not pair:
        raise HTTPException(status_code=404, detail="资讯账号不存在")
    return media_account_service.set_station_connected(db, pair[0], body.connected)


@router.post("/media/accounts/{account_id}/source-links")
def create_source_link(
    account_id: int,
    body: MediaSourceLinkCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """为账号连接一个资讯源（连接名可自定义，默认取源名称）。"""
    pair = media_account_service.get_account(db, account_id)
    if not pair:
        raise HTTPException(status_code=404, detail="资讯账号不存在")
    try:
        return media_account_service.create_source_link(
            db, pair[0], body.feed_source_id, body.name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/media/source-links/{link_id}")
def update_source_link(
    link_id: int,
    body: MediaSourceLinkUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """重命名连接线 / 断开 / 重连（断开不删除资讯源与已抓取内容）。"""
    pair = media_account_service.get_source_link(db, link_id)
    if not pair:
        raise HTTPException(status_code=404, detail="连接线不存在")
    return media_account_service.update_source_link(db, pair[0], pair[1], body)


@router.delete("/media/source-links/{link_id}")
def delete_source_link(
    link_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """删除连接线本身，资讯源与内容保留，可在画布上重新连接。"""
    pair = media_account_service.get_source_link(db, link_id)
    if not pair:
        raise HTTPException(status_code=404, detail="连接线不存在")
    media_account_service.delete_source_link(db, pair[0])
    return {"message": "deleted"}
