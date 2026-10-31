"""管理端 · 系统监控与运维：项目基底监控（服务/数据库/后台任务/外部集成）
+ 全站功能模块注册表（对整个项目功能进行维护的统一入口）+ 维护动作（抓取/重建索引）。
"""
import logging
import platform
import sys
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db
from app.core.deps import require_role
from app.models.feed import ExternalFeedItem, FeedSource
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

# 进程启动时间：用于计算运行时长（监控「服务基底」存活情况）
_START_TS = time.time()

# 数据库监控：按表名统计行数，监控数据规模；异常表名/不可达时跳过
_MONITOR_TABLES = (
    "users", "documents", "document_chunks", "knowledge_base",
    "feed_sources", "external_feed_items", "conversations", "conversation_messages",
    "ai_dialog_summaries", "notifications", "feedback",
)


class MaintenanceBody(BaseModel):
    action: str  # refresh_feeds | reindex_knowledge


def _table_counts(db: Session) -> dict:
    counts: dict[str, int] = {}
    try:
        inspector = inspect(engine)
        names = set(inspector.get_table_names())
    except SQLAlchemyError:
        return counts
    for name in _MONITOR_TABLES:
        if name not in names:
            continue
        try:
            counts[name] = int(db.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar() or 0)
        except Exception:  # noqa: BLE001 - 单表统计失败不影响整体监控
            continue
    return counts


def _db_status(db: Session) -> dict:
    reachable = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        reachable = False
    safe_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
    return {
        "reachable": reachable,
        "dialect": engine.dialect.name,
        "target": safe_url,
        "table_counts": _table_counts(db),
    }


def _background_tasks() -> list[dict]:
    from app.tasks.periodic import PROACTIVE_INTERVAL_SECONDS, REFRESH_INTERVAL_SECONDS

    return [
        {"name": "外部资讯抓取", "interval_seconds": REFRESH_INTERVAL_SECONDS,
         "desc": "定时抓取论文/开源榜/智能体榜/权威要闻并入库"},
        {"name": "心情印象刷新", "interval_seconds": REFRESH_INTERVAL_SECONDS,
         "desc": "定时刷新学生心情印象数据"},
        {"name": "AI 主动触达", "interval_seconds": PROACTIVE_INTERVAL_SECONDS,
         "desc": "扫描全体学生，命中规则即落库站内通知"},
        {"name": "学习预警 pipeline", "interval_seconds": 3600,
         "desc": "每小时检查，按「每日一次」执行学习预警"},
    ]


def _feed_status(db: Session) -> dict:
    enabled = db.query(FeedSource).filter(FeedSource.enabled == True).count()  # noqa: E712
    total_sources = db.query(FeedSource).count()
    type_counts = dict(
        db.query(ExternalFeedItem.source_type, func.count(ExternalFeedItem.id))
        .group_by(ExternalFeedItem.source_type)
        .all()
    )
    latest = db.query(func.max(ExternalFeedItem.created_at)).scalar()
    return {
        "source_total": total_sources,
        "source_enabled": enabled,
        "item_total": db.query(ExternalFeedItem).count(),
        "type_counts": type_counts,
        "last_ingested_at": latest.isoformat() if latest else None,
    }


def _integrations(db: Session) -> dict:
    from app.services import knowledge_service

    cfg = knowledge_service.get_embedding_config(db)
    return {
        "llm_configured": bool((settings.llm_api_key or "").strip()),
        "embedding_configured": bool(cfg.get("configured")),
        "embedding_model": cfg.get("model") if cfg.get("configured") else None,
        "github_token_set": bool((settings.GITHUB_TOKEN or "").strip()),
        "gitee_token_set": bool((settings.GITEE_TOKEN or "").strip()),
        "sentry_configured": bool((settings.SENTRY_DSN or "").strip()),
    }


def _modules() -> list[dict]:
    """全站功能模块注册表：来自统一路由注册表（app.api.registry.ROUTERS）。"""
    from app.api.registry import ROUTERS

    out = []
    for r in ROUTERS:
        prefix = getattr(r, "prefix", "") or "/api"
        tags = getattr(r, "tags", []) or []
        routes = getattr(r, "routes", [])
        out.append({
            "prefix": prefix,
            "tags": list(tags),
            "route_count": len(routes),
        })
    out.sort(key=lambda m: m["prefix"])
    return out


@router.get("/system/overview")
def system_overview(
    request: Request,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """项目基底监控总览：服务 / 数据库 / 后台任务 / 外部数据 / 集成配置 / 功能模块。"""
    from app.services import knowledge_service

    uptime = int(time.time() - _START_TS)
    return {
        "service": {
            "status": "ok",
            "version": request.app.version,
            "env": settings.ENV,
            "log_level": settings.LOG_LEVEL,
            "python": sys.version.split()[0],
            "platform": f"{platform.system()} {platform.release()}",
            "uptime_seconds": uptime,
            "started_at": datetime.fromtimestamp(_START_TS, tz=timezone.utc).isoformat(),
            "server_time": datetime.now(timezone.utc).isoformat(),
        },
        "database": _db_status(db),
        "background_tasks": _background_tasks(),
        "feeds": _feed_status(db),
        "knowledge": knowledge_service.get_index_status(db),
        "integrations": _integrations(db),
        "modules": _modules(),
    }


@router.post("/system/maintenance")
def run_maintenance(
    body: MaintenanceBody,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """项目维护动作：手动触发外部资讯抓取 / 重建知识库向量索引。"""
    action = (body.action or "").strip()
    if action == "refresh_feeds":
        from app.services.feed_ingest import ingest_all

        stats = ingest_all()
        return {"action": action, "ok": True, "result": stats}
    if action == "reindex_knowledge":
        from app.services import knowledge_service

        result = knowledge_service.build_embeddings_for_missing(db)
        return {"action": action, "ok": not result.get("error"), "result": result}
    raise HTTPException(status_code=400, detail="不支持的维护动作")