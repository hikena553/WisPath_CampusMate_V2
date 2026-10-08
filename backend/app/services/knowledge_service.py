"""知识库服务：文档解析、分块、中文分词检索与向量语义检索

v4.0 升级：
- 使用 jieba 中文分词器进行查询分词（未安装时自动回退空白切分）
- 可选启用千问 MaaS 向量模型（默认 qwen3.7-text-embedding，1024 维）对文档分块建立向量索引，
  检索时执行「关键词检索 + 向量语义检索」的混合排序
- search_knowledge 返回 (results, meta)，meta 中携带检索引擎/分词/向量模型信息，
  供管理端页面展示「检索或向量分词的模型」
"""
import json
import logging
import os
import time
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.knowledge import KnowledgeItem
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 分词模型（jieba） ----------
# 文本向量模型默认值（管理端 embedding_model 未配置时生效），调用 `${LLM_BASE_URL}/embeddings`
_EMBEDDING_MODEL = "qwen3.7-text-embedding"
_EMBEDDING_ENABLED_ENV = "DASHSCOPE_API_KEY"

_STOPWORDS = {
    "的", "了", "吗", "呢", "啊", "吧", "呀", "是", "我", "你", "他", "她", "它",
    "在", "有", "和", "与", "及", "或", "就", "都", "而", "也", "很", "一个",
    "怎么", "如何", "什么", "哪个", "请问", "一下", "可以", "需要", "没有", "这个",
}

try:
    import jieba

    _SEGMENTER = "jieba"
    # 减少 jieba 初始化日志噪音
    for handler in logging.getLogger("jieba").handlers[:]:
        logging.getLogger("jieba").removeHandler(handler)
    logging.getLogger("jieba").setLevel(logging.ERROR)
except ImportError:  # pragma: no cover
    jieba = None
    _SEGMENTER = "none"


def get_segmenter_name() -> str:
    """当前使用的分词模型名称"""
    if jieba is not None:
        try:
            return f"jieba {jieba.__version__}"
        except Exception:
            return "jieba"
    return "none（未安装 jieba，使用空白切分）"


def segment_query(text: str) -> list[str]:
    """对查询文本进行中文分词，返回去停用词后的有效词元"""
    text = (text or "").replace("？", "").replace("?", "").replace("！", "").replace("!", "").strip()
    if not text:
        return []
    if jieba is not None:
        tokens = [
            t.strip() for t in jieba.lcut(text)
            if len(t.strip()) > 1 and t.strip() not in _STOPWORDS
        ]
    else:
        tokens = [w for w in text.split() if len(w) > 1]
    if not tokens:
        tokens = [text[:10]]
    return tokens[:10]


def _setting_value(db, key: str) -> str | None:
    """从 system_settings 表读取配置值（空值视为未配置）"""
    if db is None:
        return None
    try:
        from app.models.setting import SystemSetting

        s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        return s.value if s and s.value not in (None, "") else None
    except Exception:  # noqa: BLE001
        return None


def get_embedding_config(db: Session | None = None) -> dict:
    """获取向量模型配置（模型名/地址/密钥/是否可用）。

    优先级：system_settings 表（管理员端可配置）> 环境变量配置。
    密钥存储为加密值时自动解密。
    """
    from app.core.config import settings
    from app.core.crypto import decrypt_value, is_encrypted

    model = (_setting_value(db, "embedding_model") or "").strip()
    base = (_setting_value(db, "embedding_base_url") or "").strip().rstrip("/")
    key = (_setting_value(db, "embedding_api_key") or "").strip()
    if is_encrypted(key):
        key = (decrypt_value(key) or "").strip()

    if not key:
        key = (settings.DASHSCOPE_API_KEY or settings.LLM_API_KEY or "").strip()
    if not base:
        base = (settings.LLM_BASE_URL or "").strip().rstrip("/")

    return {
        "model": model or _EMBEDDING_MODEL,
        "base_url": base,
        "api_key": key,
        "configured": bool(key and base),
    }


def get_embedding_model(db: Session | None = None) -> str | None:
    """当前可用的文本向量模型名；未配置密钥返回 None"""
    cfg = get_embedding_config(db)
    return cfg["model"] if cfg["configured"] else None


def embed_texts(texts: list[str], db: Session | None = None, err_out: list | None = None) -> list[list[float]] | None:
    """调用文本向量模型（兼容 OpenAI /embeddings 协议），失败返回 None；
    err_out 非空时，把失败原因写入其中，便于上层给出可操作的错误信息"""
    if not texts:
        return None

    cfg = get_embedding_config(db)
    if not cfg["configured"]:
        if err_out is not None:
            err_out.append("未配置向量模型密钥（请设置 DASHSCOPE_API_KEY 或在管理端配置）")
        return None
    try:
        import httpx

        resp = httpx.post(
            f"{cfg['base_url']}/embeddings",
            headers={"Authorization": f"Bearer {cfg['api_key']}"},
            json={"model": cfg["model"], "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        emb_list = data.get("data") or []
        emb_list.sort(key=lambda x: x.get("index", 0))
        vectors = [e.get("embedding") for e in emb_list]
        vectors = [v for v in vectors if v]
        return vectors if vectors else None
    except Exception as e:  # noqa: BLE001
        logger.warning("文本向量模型调用失败（%s）：%s，本次检索降级为关键词模式", cfg["model"], e)
        if err_out is not None:
            err_out.append(f"{cfg['model']} @ {cfg['base_url']}: {e}")
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _chunk_embedding(chunk: DocumentChunk) -> list[float] | None:
    raw = chunk.embedding_json
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return None
    return raw if isinstance(raw, list) else None


def count_indexed_chunks(db: Session) -> int:
    """已建立向量索引的分块数量"""
    return db.query(DocumentChunk).filter(DocumentChunk.embedding_json.isnot(None)).count()


def get_index_status(db: Session) -> dict:
    """知识库检索/索引状态总览（供管理端页面展示检索与向量分词模型）"""
    from app.models.knowledge import KnowledgeItem as _KI

    total_chunks = db.query(DocumentChunk).count()
    return {
        "segmenter": get_segmenter_name(),
        "embedding_model": get_embedding_model(db),
        "embedding_configured": get_embedding_model(db) is not None,
        "qa_count": db.query(_KI).count(),
        "document_count": db.query(Document).count(),
        "total_chunks": total_chunks,
        "indexed_chunks": count_indexed_chunks(db),
        "index_coverage": round(count_indexed_chunks(db) / total_chunks * 100, 1) if total_chunks else 0,
    }


def _escape_like(value: str) -> str:
    """转义 SQL LIKE 通配符，防止 LIKE 注入"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _keyword_search(db: Session, keywords: list[str], limit: int) -> tuple[list[dict], dict]:
    """关键词检索：问答对优先，文档分块兜底"""
    results: list[dict] = []

    conditions = []
    for kw in keywords[:5]:
        safe_kw = _escape_like(kw)
        conditions.append(KnowledgeItem.question.like(f"%{safe_kw}%", escape="\\"))
        conditions.append(KnowledgeItem.answer.like(f"%{safe_kw}%", escape="\\"))
        conditions.append(KnowledgeItem.tags.like(f"%{safe_kw}%", escape="\\"))

    if conditions:
        items = db.query(KnowledgeItem).filter(or_(*conditions)).limit(limit).all()
        for item in items:
            results.append({
                "type": "qa",
                "category": item.category,
                "question": item.question,
                "answer": item.answer,
                "score": None,
            })

    if len(results) < limit:
        chunk_conditions = []
        for kw in keywords[:3]:
            safe_kw = _escape_like(kw)
            chunk_conditions.append(DocumentChunk.content.like(f"%{safe_kw}%", escape="\\"))

        if chunk_conditions:
            chunks = db.query(DocumentChunk).filter(
                or_(*chunk_conditions)
            ).limit(limit - len(results)).all()
            for chunk in chunks:
                results.append({
                    "type": "document",
                    "content": chunk.content[:500],
                    "document_id": chunk.document_id,
                    "score": None,
                })

    return results, {"retrieval": "keyword"}


def _vector_search(db: Session, keywords: list[str], limit: int) -> tuple[list[dict], str]:
    """向量语义检索：对查询编码后与全库分块向量做余弦相似度排序"""
    model = get_embedding_model(db)
    if model is None:
        return [], "未配置向量模型密钥（DASHSCOPE_API_KEY / LLM_API_KEY）"

    q_vecs = embed_texts([" ".join(keywords)], db)
    if q_vecs is None:
        return [], "向量模型调用失败，本次检索降级为关键词模式"
    q_vec = q_vecs[0]

    chunks = db.query(DocumentChunk).filter(DocumentChunk.embedding_json.isnot(None)).all()
    if not chunks:
        return [], "知识库尚未建立向量索引，请在管理端「文档管理」中执行重建索引"

    scored = []
    for chunk in chunks:
        vec = _chunk_embedding(chunk)
        if not vec:
            continue
        score = _cosine(q_vec, vec)
        if score >= 0.3:
            scored.append((score, chunk))
    scored.sort(key=lambda x: -x[0])

    return [
        {
            "type": "document",
            "content": c.content[:500],
            "document_id": c.document_id,
            "score": round(s, 4),
        }
        for s, c in scored[:limit]
    ], ""


def search_knowledge(db: Session, query: str, limit: int = 5) -> tuple[list[dict], dict]:
    """混合检索：jieba 分词关键词检索 + 向量语义检索，返回 (结果列表, 检索元信息)"""
    t0 = time.time()
    keywords = segment_query(query)
    meta: dict = {
        "engine": "smart-campus-rag",
        "segmenter": get_segmenter_name(),
        "segment_tokens": keywords,
        "retrieval": "keyword",
        "embedding_model": None,
        "indexed_chunks": count_indexed_chunks(db),
        "note": "",
        "elapsed_ms": 0,
    }

    results, _ = _keyword_search(db, keywords, limit)

    # 关键词未填满时，用向量语义检索补足
    if len(results) < limit:
        vec_hits, note = _vector_search(db, keywords, limit - len(results))
        if vec_hits:
            meta["retrieval"] = "hybrid"
            meta["embedding_model"] = get_embedding_model(db)
            existing_ids = {r.get("document_id") for r in results if r["type"] == "document"}
            results.extend(h for h in vec_hits if h["document_id"] not in existing_ids)
        elif note and not meta["note"]:
            meta["note"] = note
            meta["embedding_model"] = get_embedding_model(db)

    # 检索方式判定：仅当实际使用了向量打分时标记 hybrid（已在上方标记）
    elapsed_ms = int((time.time() - t0) * 1000)
    meta["elapsed_ms"] = elapsed_ms
    return results[:limit], meta


def save_document(db: Session, filename: str, file_type: str, file_path: str, uploaded_by: int) -> Document:
    """保存文档元数据"""
    doc = Document(
        filename=filename,
        file_type=file_type,
        file_path=file_path,
        status="processing",
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def parse_document(file_path: str, file_type: str) -> list[str]:
    """解析文档，返回分块内容"""
    chunks = []

    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = _split_text(content)

    elif file_type == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                content = ""
                for page in pdf.pages:
                    content += (page.extract_text() or "") + "\n"
            chunks = _split_text(content)
        except ImportError:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                content = ""
                for page in reader.pages:
                    content += (page.extract_text() or "") + "\n"
                chunks = _split_text(content)
            except Exception:
                pass

    elif file_type == "docx":
        try:
            from docx import Document as DocxDoc
            doc = DocxDoc(file_path)
            content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            chunks = _split_text(content)
        except ImportError:
            pass

    return chunks


def _split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """将文本分块"""
    if not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap

    return chunks


def save_chunks(db: Session, document_id: int, chunks: list[str]):
    """保存文档分块，并尝试为分块建立向量索引"""
    for i, content in enumerate(chunks):
        chunk = DocumentChunk(
            document_id=document_id,
            content=content,
            chunk_index=i,
        )
        db.add(chunk)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.status = "completed"
        doc.chunk_count = len(chunks)

    db.commit()

    # 若配置了向量模型，顺带建立向量索引（失败不影响主流程）
    try:
        if get_embedding_model(db) is not None and chunks:
            build_embeddings_for_missing(db, limit=len(chunks))
    except Exception as e:  # noqa: BLE001
        logger.warning("文档分块自动向量化失败: %s", e)


def build_embeddings_for_missing(db: Session, batch_size: int = 16, limit: int | None = None) -> dict:
    """为缺少向量索引的文档分块建立向量索引，返回统计结果"""
    model = get_embedding_model(db)
    if model is None:
        return {
            "indexed": 0,
            "skipped": 0,
            "error": "未配置向量模型密钥（DASHSCOPE_API_KEY / LLM_API_KEY），无法建立向量索引",
        }

    query = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.embedding_json.is_(None))
        .order_by(DocumentChunk.id)
    )
    if limit:
        query = query.limit(limit)
    missing = query.all()

    if not missing:
        return {"indexed": 0, "skipped": 0, "error": ""}

    total = 0
    for i in range(0, len(missing), batch_size):
        batch = missing[i:i + batch_size]
        err_out: list = []
        vecs = embed_texts([c.content for c in batch], db, err_out=err_out)
        if vecs is None:
            skipped = len(missing) - total
            db.rollback()
            reason = err_out[0] if err_out else "未知错误"
            return {"indexed": total, "skipped": skipped, "error": f"向量模型调用失败：{reason}"}
        for chunk, vec in zip(batch, vecs):
            chunk.embedding_json = json.dumps(vec, ensure_ascii=False)
        db.commit()
        total += len(vecs)

    return {"indexed": total, "skipped": 0, "error": ""}


def get_all_knowledge_items(db: Session, category: str = None, search: str = None):
    """获取知识库条目查询对象（由调用方决定分页）"""
    query = db.query(KnowledgeItem)
    if category:
        query = query.filter(KnowledgeItem.category == category)
    if search:
        safe_search = _escape_like(search)
        like = f"%{safe_search}%"
        query = query.filter(
            or_(
                KnowledgeItem.question.like(like, escape="\\"),
                KnowledgeItem.answer.like(like, escape="\\"),
                KnowledgeItem.tags.like(like, escape="\\"),
            )
        )
    return query


def create_knowledge_item(db: Session, category: str, question: str, answer: str, tags: str = None) -> KnowledgeItem:
    """创建知识库条目"""
    item = KnowledgeItem(category=category, question=question, answer=answer, tags=tags)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_knowledge_item(db: Session, item_id: int, **kwargs) -> KnowledgeItem | None:
    """更新知识库条目"""
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_knowledge_item(db: Session, item_id: int) -> bool:
    """删除知识库条目"""
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def get_all_documents(db: Session) -> list[Document]:
    """获取所有文档"""
    return db.query(Document).order_by(Document.created_at.desc()).all()


def get_embedded_counts(db: Session, doc_ids: list[int]) -> dict[int, int]:
    """统计各文档已建立向量索引的分块数量"""
    if not doc_ids:
        return {}
    rows = (
        db.query(DocumentChunk.document_id, func.count())
        .filter(
            DocumentChunk.document_id.in_(doc_ids),
            DocumentChunk.embedding_json.isnot(None),
        )
        .group_by(DocumentChunk.document_id)
        .all()
    )
    return {doc_id: cnt for doc_id, cnt in rows}


def delete_document(db: Session, doc_id: int) -> bool:
    """删除文档及其分块"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return False

    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return True