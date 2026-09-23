"""知识库公共检索接口（v3.0 实施文档 §6 接口规范）

面向全体登录用户开放 RAG 混合检索，支撑学生端"AI 资源空间"、
教师/管理端的检索能力复用。新增接口遵循统一约定：
- 携带 trace_id 便于链路追踪
- 参数显式校验（Query min_length/max_length）
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.knowledge_service import search_knowledge

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search")
def search_items(
    q: str = Query(..., min_length=1, max_length=100, description="检索关键词"),
    limit: int = Query(5, ge=1, le=20, description="返回条数上限"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RAG 知识库混合检索：问答对优先，文档分块兜底"""
    hits = search_knowledge(db, q.strip(), limit)
    return {
        "results": hits,
        "count": len(hits),
        "trace_id": f"kb-{uuid.uuid4().hex[:12]}",
    }