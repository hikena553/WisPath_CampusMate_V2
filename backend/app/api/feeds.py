"""外部资讯中心：AI 论文 / 开源项目榜 / 智能体榜 / 权威要闻 / AI 行业 / 国产模型
数据源落库(feed_sources)，运行时动态管理（增删/启停）；抓取按库中启用的源动态执行。
"""
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.feed import ExternalFeedItem, FeedSource

router = APIRouter(prefix="/api/feeds", tags=["外部资讯"])

ALLOWED_TYPES = ("papers", "agents", "opensource", "news", "ai_news", "rankings", "cn_ai")
ALLOWED_KINDS = ("rss", "html", "arxiv", "github", "gitee", "lmarena")

_last_refresh: dict[str, float] = {}
REFRESH_COOLDOWN = 60  # 秒，冷却期内拒绝手动刷新，避免触发源站限流


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


def _src_to_dict(s: FeedSource) -> dict:
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
    }


@router.get("")
def list_feeds(
    source_type: str = Query("all", description="papers/agents/opensource/news/ai_news/rankings/cn_ai 或 all"),
    limit: int = Query(20, ge=1, le=50),
    q: str = Query("", max_length=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按分类返回最新外部资讯（新→旧）。"""
    query = db.query(ExternalFeedItem)
    if source_type in ALLOWED_TYPES:
        query = query.filter(ExternalFeedItem.source_type == source_type)
    elif source_type != "all":
        raise HTTPException(400, "不支持的资讯类型")
    kw = q.strip()
    if kw:
        like = f"%{kw}%"
        query = query.filter(ExternalFeedItem.title.like(like) | ExternalFeedItem.summary.like(like))
    rows = query.order_by(
        ExternalFeedItem.published_at.desc(),
        ExternalFeedItem.id.desc(),
    ).limit(limit).all()
    return [_item_to_dict(r) for r in rows]


@router.post("/refresh")
def refresh_feeds(
    source_type: str = Query("all", description="仅刷新某类，或 all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发抓取（60 秒冷却）。返回统计。"""
    key = source_type if source_type in ALLOWED_TYPES else "all"
    now = time.time()
    if now - _last_refresh.get(key, 0) < REFRESH_COOLDOWN:
        remain = int(REFRESH_COOLDOWN - (now - _last_refresh.get(key, 0)))
        raise HTTPException(429, f"刷新太频繁，请 {remain} 秒后再试")
    _last_refresh[key] = now

    from app.services.feed_ingest import ingest_all
    stats = ingest_all(only=key if key != "all" else None)
    return stats


# ==================== 数据源动态管理 ====================

@router.get("/sources")
def list_sources(
    source_type: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出所有资讯源（含启停状态），供前端管理。"""
    q = db.query(FeedSource).order_by(FeedSource.sort_order, FeedSource.id)
    if source_type in ALLOWED_TYPES:
        q = q.filter(FeedSource.source_type == source_type)
    return [_src_to_dict(s) for s in q.all()]


@router.post("/sources")
def create_source(
    body: FeedSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增自定义资讯源（rss/html 通用；API 类源由内置预设覆盖）。"""
    host = urlparse(body.url).hostname
    if not host:
        raise HTTPException(400, "URL 无效，缺少域名")
    dup = (db.query(FeedSource)
           .filter(FeedSource.kind == body.kind, FeedSource.url == body.url)
           .first())
    if dup:
        raise HTTPException(409, "相同 URL 已存在")
    src = FeedSource(
        name=body.name, kind=body.kind, source_type=body.source_type,
        url=body.url, query=body.query, base_url=body.base_url,
        filter_kw=body.filter_kw or [], date_only=body.date_only,
        per_page=body.per_page, is_builtin=False, enabled=True,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return _src_to_dict(src)


@router.patch("/sources/{source_id}")
def update_source(
    source_id: int,
    body: FeedSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启停 / 编辑资讯源。"""
    src = db.query(FeedSource).filter(FeedSource.id == source_id).first()
    if not src:
        raise HTTPException(404, "资讯源不存在")
    if body.name is not None:
        src.name = body.name
    if body.enabled is not None:
        src.enabled = body.enabled
    if body.url is not None:
        src.url = body.url
    if body.query is not None:
        src.query = body.query
    if body.base_url is not None:
        src.base_url = body.base_url
    if body.filter_kw is not None:
        src.filter_kw = body.filter_kw
    if body.date_only is not None:
        src.date_only = body.date_only
    if body.per_page is not None:
        src.per_page = body.per_page
    db.commit()
    db.refresh(src)
    return _src_to_dict(src)


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除资讯源（内置预设源仅可启停，不可删除）。"""
    src = db.query(FeedSource).filter(FeedSource.id == source_id).first()
    if not src:
        raise HTTPException(404, "资讯源不存在")
    if src.is_builtin:
        raise HTTPException(403, "内置预设源不可删除，可停用")
    db.delete(src)
    db.commit()
    return {"ok": True}