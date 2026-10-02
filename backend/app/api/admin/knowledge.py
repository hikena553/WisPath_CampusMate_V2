from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import require_role
from app.core.crypto import encrypt_value
from app.models.user import User, UserRole
from app.schemas.admin import (
    KnowledgeItemCreate, KnowledgeItemUpdate, KnowledgeItemOut,
    DocumentOut,
)
from app.services import knowledge_service
from app.api.admin.common import PaginatedResponse, _xqe_get, _xqe_set

router = APIRouter(tags=["admin"])

# ========== 知识库管理 ==========

@router.get("/knowledge", response_model=PaginatedResponse, summary="获取知识库列表", description="分页获取知识库问答对列表，支持按分类和关键词筛选")
def list_knowledge(
    category: str | None = Query(None, description="分类筛选"),
    search: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """获取知识库列表（分页）"""
    query = knowledge_service.get_all_knowledge_items(db, category, search)
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    items = query.offset(start).limit(page_size).all()

    return PaginatedResponse(
        items=[KnowledgeItemOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/knowledge", response_model=KnowledgeItemOut)
def create_knowledge(
    data: KnowledgeItemCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return knowledge_service.create_knowledge_item(db, data.category, data.question, data.answer, data.tags)


@router.put("/knowledge/{item_id}", response_model=KnowledgeItemOut)
def update_knowledge(
    item_id: int,
    data: KnowledgeItemUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    item = knowledge_service.update_knowledge_item(db, item_id, **data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="知识库条目不存在")
    return item


@router.delete("/knowledge/{item_id}")
def delete_knowledge(
    item_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if not knowledge_service.delete_knowledge_item(db, item_id):
        raise HTTPException(status_code=404, detail="知识库条目不存在")
    return {"message": "删除成功"}


@router.post("/knowledge/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    allowed_types = {"pdf", "docx", "txt"}
    filename = file.filename or "unnamed"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 PDF/DOCX/TXT 格式")

    import os
    from pathlib import Path
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # #6 路径清洗：只保留文件名部分，防止路径穿越
    safe_name = Path(filename).name
    file_path = upload_dir / safe_name

    # #7 大小限制：10MB
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超过 10MB 限制")

    with open(file_path, "wb") as f:
        f.write(content)

    doc = knowledge_service.save_document(db, file.filename, ext, str(file_path), user.id)

    try:
        chunks = knowledge_service.parse_document(str(file_path), ext)
        if chunks:
            knowledge_service.save_chunks(db, doc.id, chunks)
        else:
            doc.status = "failed"
            db.commit()
            raise HTTPException(status_code=422, detail="文档解析失败：未能提取到有效内容")
    except HTTPException:
        raise
    except Exception as e:
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")

    return {"message": "上传成功", "document_id": doc.id, "chunk_count": len(chunks)}


@router.get("/knowledge/documents", response_model=list[DocumentOut])
def list_documents(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    docs = knowledge_service.get_all_documents(db)
    embedded_counts = knowledge_service.get_embedded_counts(db, [d.id for d in docs])
    return [DocumentOut(
        id=d.id,
        filename=d.filename,
        file_type=d.file_type,
        status=d.status,
        chunk_count=d.chunk_count,
        embedded_count=embedded_counts.get(d.id, 0),
        created_at=d.created_at.isoformat() if d.created_at else None,
    ) for d in docs]


@router.post("/knowledge/reindex")
def reindex_knowledge(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """为知识库文档分块重建向量索引（幂等：仅处理缺少向量的分块）"""
    result = knowledge_service.build_embeddings_for_missing(db)
    model = knowledge_service.get_embedding_model(db)
    return {
        "message": "向量索引重建完成" if not result["error"] else "向量索引重建失败",
        "model": model,
        **{k: v for k, v in result.items()},
    }


@router.get("/knowledge/index-status")
def knowledge_index_status(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """知识库检索模型与向量索引状态（分词模型/向量模型/索引覆盖率）"""
    return knowledge_service.get_index_status(db)


class EmbeddingConfigOut(BaseModel):
    model: str = ""
    base_url: str = ""
    api_key_set: bool = False
    configured: bool = False
    using_env_fallback: bool = False
    hint: str = ""


class EmbeddingConfigBody(BaseModel):
    model: str = ""          # 空串 = 使用默认 text-embedding-v3
    base_url: str = ""       # 空串 = 沿用环境变量 LLM_BASE_URL
    api_key: str = ""        # 明文，非空时加密存储


@router.get("/knowledge/embedding-config", response_model=EmbeddingConfigOut)
def embedding_get_config(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """读取向量模型配置（密钥仅返回是否已设置；显示是否回退环境变量）"""
    from app.core.config import settings

    model = _xqe_get(db, "embedding_model", "") or ""
    base = _xqe_get(db, "embedding_base_url", "") or ""
    api_key = _xqe_get(db, "embedding_api_key", "") or ""
    env_key = (settings.DASHSCOPE_API_KEY or settings.LLM_API_KEY or "").strip()
    env_base = (settings.LLM_BASE_URL or "").strip().rstrip("/")

    using_fallback = (not base or not api_key) and bool(env_key and env_base)
    effective_base = base or env_base
    effective_model = model or "text-embedding-v3"
    return EmbeddingConfigOut(
        model=effective_model,
        base_url=effective_base or "",
        api_key_set=bool(api_key or env_key),
        configured=bool((api_key or env_key) and (base or env_base)),
        using_env_fallback=using_fallback,
        hint=(
            "当前使用环境变量配置（DASHSCOPE_API_KEY / LLM_BASE_URL）"
            if using_fallback
            else ("请在下方填写模型名、接口地址与密钥" if not api_key else "配置已保存")
        ),
    )


@router.post("/knowledge/embedding-config", response_model=EmbeddingConfigOut)
def embedding_save_config(
    data: EmbeddingConfigBody,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """保存向量模型配置（模型名/接口地址/API 密钥，密钥加密存储）"""
    model = data.model.strip()
    if model:
        _xqe_set(db, "embedding_model", model)
    base = data.base_url.strip().rstrip("/")
    if base:
        if not base.startswith(("http://", "https://")):
            raise HTTPException(400, "接口地址需以 http:// 或 https:// 开头")
        _xqe_set(db, "embedding_base_url", base)
    if data.api_key.strip():
        _xqe_set(db, "embedding_api_key", encrypt_value(data.api_key.strip()))

    db.commit()
    return embedding_get_config(user=user, db=db)


@router.delete("/knowledge/documents/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if not knowledge_service.delete_document(db, doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"message": "删除成功"}
