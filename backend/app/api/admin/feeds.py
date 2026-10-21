"""管理端 · 外部资讯统一管理（学生端订阅/爬取的外部数据源，由管理员统一查看与维护）。

覆盖：资讯源（feed_sources）增删改查与启停、资讯条目（external_feed_items）分页查看/删除、
手动触发抓取。学生端「AI 资源空间」订阅的外部数据源全部在此可见可控，形成管理闭环。
"""
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.admin.common import PaginatedResponse
from app.core.database import get_db
from app.core.deps import require_role
from app.models.feed import ExternalFeedItem, FeedSource
from app.models.user import User, UserRole
from app.services.feed_ingest import validate_source_url

router = APIRouter(tags=["admin"])

ALLOWED_TYPES = ("papers", "agents", "opensource", "news", "ai_news", "rankings", "cn_ai")
ALLOWED_KINDS = ("rss", "html", "arxiv", "github", "gitee", "lmarena")


class FeedSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    kind: str = Field(..., pattern="^(rss|html|arxiv|github|gitee|lmarena)$")
    source_type: str = Field(..., pattern="^(papers|agents|opensource|news|ai_news|rankings|cn_ai)$")
    url: str = Field(..., min_length=5, max_length=700)
    query: str | None = Field(None, max_length=500)
    base_url: str | None = Field(None, max_length=300)
    filter_kw: list[str] | None = None
    date_only: bool = False
    per_page: int = Field(10, ge=1, le=50)


class FeedSourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    enabled: bool | None = None
    url: str | None = Field(None, min_length=5, max_length=700)
    query: str | None = Field(None, max_length=500)
    base_url: str | None = Field(None, max_length=300)
    filter_kw: list[str] | None = None
    date_only: bool | None = None
    per_page: int | None = Field(None, ge=1, le=50)


class FeedItemUpdate(BaseModel):
    is_highlight: bool | None = None


def _src_to_dict(s: FeedSource, item_count: int, last_ingested_at) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "kind": s.kind,
        "source_type": s.source_type,
        "url": s.url,
        "query": s.query,
        "base_url": s.base_url,
        "filter_kw": s.filter_kw or [],
        "date_only": s.date_only,
        "per_page": s.per_page,
        "is_builtin": s.is_builtin,
        "enabled": s.enabled,
        "sort_order": s.sort_order,
        "item_count": item_count,
        "last_ingested_at": last_ingested_at.isoformat() if last_ingested_at else None,
    }


def _item_to_dict(it: ExternalFeedItem) -> dict:
    return {
        "id": it.id,
        "source_type": it.source_type,
        "feed_key": it.feed_key,
        "title": it.title,
        "summary": it.summary,
        "link": it.link,
        "author": it.author,
        "source_name": it.source_name,
        "is_highlight": it.is_highlight,
        "meta": it.meta or {},
        "published_at": it.published_at.isoformat() if it.published_at else None,
        "created_at": it.created_at.isoformat() if it.created_at else None,
    }


def _counts_by_key(db: Session) -> tuple[dict, dict, dict]:
    """一次性聚合：feed_key 维度条数、source_type 维度条数、feed_key 最近入库时间。"""
    key_counts = dict(
        db.query(ExternalFeedItem.feed_key, func.count(ExternalFeedItem.id))
        .group_by(ExternalFeedItem.feed_key)
        .all()
    )
    type_counts = dict(
        db.query(ExternalFeedItem.source_type, func.count(ExternalFeedItem.id))
        .group_by(ExternalFeedItem.source_type)
        .all()
    )
    last_seen = dict(
        db.query(ExternalFeedItem.feed_key, func.max(ExternalFeedItem.created_at))
        .group_by(ExternalFeedItem.feed_key)
        .all()
    )
    return key_counts, type_counts, last_seen


@router.get("/feeds/sources")
def list_feed_sources(
    source_type: str = Query("all"),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """列出全部资讯源（含启停状态、条目数、最近入库时间）。"""
    q = db.query(FeedSource).order_by(FeedSource.sort_order, FeedSource.id)
    if source_type in ALLOWED_TYPES:
        q = q.filter(FeedSource.source_type == source_type)
    sources = q.all()
    key_counts, type_counts, last_seen = _counts_by_key(db)

    out = []
    for s in sources:
        if s.feed_key:
            count = key_counts.get(s.feed_key, 0)
            last = last_seen.get(s.feed_key)
        else:
            count = type_counts.get(s.source_type, 0)
            last = None
        out.append(_src_to_dict(s, count, last))
    return out


@router.post("/feeds/sources")
def create_feed_source(
    body: FeedSourceCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """新增资讯源（RSS / 网页 / API 类）。"""
    if not urlparse(body.url).hostname:
        raise HTTPException(status_code=400, detail="URL 无效，缺少域名")
    try:
        validate_source_url(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    dup = (
        db.query(FeedSource)
        .filter(FeedSource.kind == body.kind, FeedSource.url == body.url)
        .first()
    )
    if dup:
        raise HTTPException(status_code=409, detail="相同地址的资讯源已存在")
    src = FeedSource(
        name=body.name, kind=body.kind, source_type=body.source_type,
        url=body.url, query=body.query, base_url=body.base_url,
        filter_kw=body.filter_kw or [], date_only=body.date_only,
        per_page=body.per_page, is_builtin=False, enabled=True,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return _src_to_dict(src, 0, None)


@router.patch("/feeds/sources/{source_id}")
def update_feed_source(
    source_id: int,
    body: FeedSourceUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """编辑 / 启停资讯源。"""
    src = db.query(FeedSource).filter(FeedSource.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="资讯源不存在")
    if body.url is not None:
        try:
            validate_source_url(body.url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(src, field, value)
    db.commit()
    db.refresh(src)
    key_counts, type_counts, last_seen = _counts_by_key(db)
    count = key_counts.get(src.feed_key, 0) if src.feed_key else type_counts.get(src.source_type, 0)
    return _src_to_dict(src, count, last_seen.get(src.feed_key))


@router.delete("/feeds/sources/{source_id}")
def delete_feed_source(
    source_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """删除资讯源（内置预设源仅可停用，不可删除）。"""
    src = db.query(FeedSource).filter(FeedSource.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="资讯源不存在")
    if src.is_builtin:
        raise HTTPException(status_code=403, detail="内置预设源不可删除，可停用")
    db.delete(src)
    db.commit()
    return {"ok": True, "message": f"已删除资讯源「{src.name}」"}


@router.get("/feeds/items", response_model=PaginatedResponse)
def list_feed_items(
    source_type: str = Query("all"),
    q: str = Query("", max_length=60),
    feed_key: str | None = Query(None, max_length=50),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """分页查看已抓取的外部资讯条目（支持分类 / 关键词 / 来源筛选）。"""
    query = db.query(ExternalFeedItem)
    if source_type in ALLOWED_TYPES:
        query = query.filter(ExternalFeedItem.source_type == source_type)
    elif source_type != "all":
        raise HTTPException(status_code=400, detail="不支持的资讯类型")
    if feed_key:
        query = query.filter(ExternalFeedItem.feed_key == feed_key)
    kw = q.strip()
    if kw:
        like = f"%{kw}%"
        query = query.filter(
            ExternalFeedItem.title.like(like) | ExternalFeedItem.summary.like(like)
        )

    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    rows = (
        query.order_by(ExternalFeedItem.published_at.desc(), ExternalFeedItem.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=[_item_to_dict(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/feeds/items/{item_id}")
def update_feed_item(
    item_id: int,
    body: FeedItemUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """标记 / 取消热点置顶。"""
    item = db.query(ExternalFeedItem).filter(ExternalFeedItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="资讯条目不存在")
    if body.is_highlight is not None:
        item.is_highlight = body.is_highlight
    db.commit()
    db.refresh(item)
    return _item_to_dict(item)


@router.delete("/feeds/items/{item_id}")
def delete_feed_item(
    item_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """删除单条外部资讯（下架不合适内容）。"""
    item = db.query(ExternalFeedItem).filter(ExternalFeedItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="资讯条目不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/feeds/refresh")
def refresh_feed_items(
    source_type: str = Query("all"),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """手动触发抓取（管理员运维入口，无冷却限制）。"""
    from app.services.feed_ingest import ingest_all

    only = source_type if source_type in ALLOWED_TYPES else None
    return ingest_all(only=only)