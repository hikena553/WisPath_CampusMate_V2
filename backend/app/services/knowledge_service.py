import os
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.knowledge import KnowledgeItem
from app.models.document import Document, DocumentChunk


UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def search_knowledge(db: Session, query: str, limit: int = 5) -> list[dict]:
    """搜索知识库（问答对 + 文档分块）"""
    results = []

    keywords = [w for w in query.replace("？", "").replace("?", "").split() if len(w) > 1]
    if not keywords:
        keywords = [query[:10]]

    conditions = []
    for kw in keywords[:5]:
        conditions.append(KnowledgeItem.question.like(f"%{kw}%"))
        conditions.append(KnowledgeItem.answer.like(f"%{kw}%"))
        conditions.append(KnowledgeItem.tags.like(f"%{kw}%"))

    if conditions:
        items = db.query(KnowledgeItem).filter(or_(*conditions)).limit(limit).all()
        for item in items:
            results.append({
                "type": "qa",
                "category": item.category,
                "question": item.question,
                "answer": item.answer,
            })

    if len(results) < limit:
        chunk_conditions = []
        for kw in keywords[:3]:
            chunk_conditions.append(DocumentChunk.content.like(f"%{kw}%"))

        if chunk_conditions:
            chunks = db.query(DocumentChunk).filter(
                or_(*chunk_conditions)
            ).limit(limit - len(results)).all()
            for chunk in chunks:
                results.append({
                    "type": "document",
                    "content": chunk.content[:500],
                    "document_id": chunk.document_id,
                })

    return results


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
    """保存文档分块"""
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


def get_all_knowledge_items(db: Session, category: str = None, search: str = None) -> list[KnowledgeItem]:
    """获取所有知识库条目"""
    query = db.query(KnowledgeItem)
    if category:
        query = query.filter(KnowledgeItem.category == category)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(KnowledgeItem.question.like(like), KnowledgeItem.answer.like(like), KnowledgeItem.tags.like(like))
        )
    return query.all()


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
