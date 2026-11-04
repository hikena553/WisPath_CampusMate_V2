# 管理员端功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建完整的管理员端，包含AI知识库管理、密码管理、教师管理、数据导入导出功能

**Architecture:** 前后端分离架构，后端新增admin API模块，前端新增admin布局和页面，参照教师端风格

**Tech Stack:** Vue 3 + Element Plus + TypeScript (前端) | FastAPI + SQLAlchemy + OpenPyXL (后端) | sentence-transformers + FAISS (向量检索)

---

## 文件结构总览

### 后端新增/修改文件
- Modify: `backend/app/models/user.py` — 新增 `password_changed` 字段
- Create: `backend/app/models/document.py` — Document 和 DocumentChunk 模型
- Create: `backend/app/api/admin.py` — 管理员路由
- Create: `backend/app/schemas/admin.py` — 管理员Pydantic模型
- Create: `backend/app/services/knowledge_service.py` — 知识库服务
- Create: `backend/app/services/import_export_service.py` — 导入导出服务
- Modify: `backend/app/main.py` — 注册admin路由
- Modify: `backend/app/api/auth.py` — 新增修改密码接口
- Modify: `backend/app/services/agent_service.py` — 增强知识库检索

### 前端新增/修改文件
- Create: `frontend/src/components/layout/AdminLayout.vue` — 管理员布局
- Create: `frontend/src/views/admin/HomePage.vue` — 首页
- Create: `frontend/src/views/admin/KnowledgePage.vue` — 知识库管理
- Create: `frontend/src/views/admin/TeachersPage.vue` — 教师管理
- Create: `frontend/src/views/admin/StudentsPage.vue` — 学生管理
- Create: `frontend/src/views/admin/DataPage.vue` — 数据导入导出
- Create: `frontend/src/api/admin.ts` — 管理员API
- Modify: `frontend/src/router/index.ts` — 新增admin路由
- Modify: `frontend/src/views/login/LoginPage.vue` — admin跳转
- Modify: `frontend/src/types/index.ts` — 新增类型
- Modify: `frontend/src/components/layout/TeacherLayout.vue` — 密码修改
- Modify: `frontend/src/components/layout/StudentLayout.vue` — 密码修改

---

## Task 1: 后端 — User 模型更新

**Files:**
- Modify: `backend/app/models/user.py:14-32`

- [ ] **Step 1: 添加 password_changed 字段**

```python
# backend/app/models/user.py
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(50))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))
    college: Mapped[str | None] = mapped_column(String(100))
    avatar: Mapped[str | None] = mapped_column(String(255))
    tutor_id: Mapped[int | None] = mapped_column(default=None)
    skills_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    gender: Mapped[str | None] = mapped_column(String(10))
    political_status: Mapped[str | None] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(50))
    hometown: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    department: Mapped[str | None] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer)
    password_changed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已修改过密码")
```

- [ ] **Step 2: 更新 UserInfo schema**

```python
# backend/app/schemas/user.py (在UserInfo类中添加字段)
password_changed: bool = False
```

- [ ] **Step 3: 验证模型**

运行: `cd mianyang-campus/backend && python -c "from app.models.user import User; print('OK')"`
Expected: OK

---

## Task 2: 后端 — Document 和 DocumentChunk 模型

**Files:**
- Create: `backend/app/models/document.py`

- [ ] **Step 1: 创建 Document 模型**

```python
# backend/app/models/document.py
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))  # pdf/docx/txt
    file_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing/completed/failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON序列化的向量
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 注册模型到 main.py**

在 `backend/app/main.py` 的 imports 中添加:
```python
from app.models.document import Document, DocumentChunk
```

- [ ] **Step 3: 验证模型**

运行: `cd mianyang-campus/backend && python -c "from app.models.document import Document, DocumentChunk; print('OK')"`
Expected: OK

---

## Task 3: 后端 — 知识库服务

**Files:**
- Create: `backend/app/services/knowledge_service.py`

- [ ] **Step 1: 创建知识库服务**

```python
# backend/app/services/knowledge_service.py
import json
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
    
    # 1. 搜索问答对
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
    
    # 2. 搜索文档分块（简单关键词匹配，向量检索在后续版本添加）
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
            # fallback: 尝试 PyPDF2
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
    
    # 更新文档状态
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
    
    # 删除分块
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
    
    # 删除文件
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    db.delete(doc)
    db.commit()
    return True
```

- [ ] **Step 2: 验证服务**

运行: `cd mianyang-campus/backend && python -c "from app.services.knowledge_service import search_knowledge; print('OK')"`
Expected: OK

---

## Task 4: 后端 — 导入导出服务

**Files:**
- Create: `backend/app/services/import_export_service.py`

- [ ] **Step 1: 创建导入导出服务**

```python
# backend/app/services/import_export_service.py
import io
from sqlalchemy.orm import Session
from openpyxl import Workbook, load_workbook

from app.models.user import User, UserRole
from app.core.security import hash_password


DEFAULT_PASSWORD = "123456"


def export_users(db: Session, role: UserRole) -> bytes:
    """导出用户数据为Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = "用户数据"
    
    if role == UserRole.STUDENT:
        headers = ["学号", "姓名", "学院", "性别", "年龄", "联系电话", "籍贯"]
        ws.append(headers)
        users = db.query(User).filter(User.role == UserRole.STUDENT).all()
        for u in users:
            ws.append([
                u.username,
                u.name,
                u.college or "",
                u.gender or "",
                u.age or "",
                u.phone or "",
                u.hometown or "",
            ])
    else:  # teacher
        headers = ["工号", "姓名", "学院", "性别", "年龄", "职称", "所属单位", "联系电话"]
        ws.append(headers)
        users = db.query(User).filter(User.role == UserRole.TEACHER).all()
        for u in users:
            ws.append([
                u.username,
                u.name,
                u.college or "",
                u.gender or "",
                u.age or "",
                u.title or "",
                u.department or "",
                u.phone or "",
            ])
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def import_users(db: Session, role: UserRole, file_content: bytes) -> dict:
    """导入用户数据，跳过重复记录"""
    wb = load_workbook(io.BytesIO(file_content))
    ws = wb.active
    
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        return {"total": 0, "created": 0, "skipped": 0, "errors": []}
    
    created = 0
    skipped = 0
    errors = []
    
    for i, row in enumerate(rows, start=2):
        try:
            if role == UserRole.STUDENT:
                if len(row) < 2:
                    errors.append(f"第{i}行: 数据不完整")
                    continue
                username = str(row[0]).strip()
                name = str(row[1]).strip()
                college = str(row[2]).strip() if len(row) > 2 and row[2] else None
                gender = str(row[3]).strip() if len(row) > 3 and row[3] else None
                age = int(row[4]) if len(row) > 4 and row[4] else None
                phone = str(row[5]).strip() if len(row) > 5 and row[5] else None
                hometown = str(row[6]).strip() if len(row) > 6 and row[6] else None
            else:  # teacher
                if len(row) < 2:
                    errors.append(f"第{i}行: 数据不完整")
                    continue
                username = str(row[0]).strip()
                name = str(row[1]).strip()
                college = str(row[2]).strip() if len(row) > 2 and row[2] else None
                gender = str(row[3]).strip() if len(row) > 3 and row[3] else None
                age = int(row[4]) if len(row) > 4 and row[4] else None
                title = str(row[5]).strip() if len(row) > 5 and row[5] else None
                department = str(row[6]).strip() if len(row) > 6 and row[6] else None
                phone = str(row[7]).strip() if len(row) > 7 and row[7] else None
            
            # 检查重复
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                skipped += 1
                continue
            
            # 创建用户
            user = User(
                username=username,
                password_hash=hash_password(DEFAULT_PASSWORD),
                name=name,
                role=role,
                college=college,
                gender=gender,
                age=age,
                phone=phone,
            )
            
            if role == UserRole.STUDENT:
                user.hometown = hometown
            else:
                user.title = title
                user.department = department
            
            db.add(user)
            created += 1
        
        except Exception as e:
            errors.append(f"第{i}行: {str(e)}")
    
    db.commit()
    
    return {
        "total": len(rows),
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }
```

- [ ] **Step 2: 安装依赖**

运行: `cd mianyang-campus/backend && pip install openpyxl`
Expected: 成功安装

- [ ] **Step 3: 验证服务**

运行: `cd mianyang-campus/backend && python -c "from app.services.import_export_service import export_users; print('OK')"`
Expected: OK

---

## Task 5: 后端 — 管理员 API 路由

**Files:**
- Create: `backend/app/schemas/admin.py`
- Create: `backend/app/api/admin.py`

- [ ] **Step 1: 创建 Pydantic schemas**

```python
# backend/app/schemas/admin.py
from pydantic import BaseModel


class KnowledgeItemCreate(BaseModel):
    category: str
    question: str
    answer: str
    tags: str | None = None


class KnowledgeItemUpdate(BaseModel):
    category: str | None = None
    question: str | None = None
    answer: str | None = None
    tags: str | None = None


class KnowledgeItemOut(BaseModel):
    id: int
    category: str
    question: str
    answer: str
    tags: str | None = None

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    chunk_count: int
    created_at: str | None = None

    class Config:
        from_attributes = True


class TeacherOut(BaseModel):
    id: int
    username: str
    name: str
    college: str | None = None
    avatar: str | None = None
    title: str | None = None
    department: str | None = None
    student_count: int = 0

    class Config:
        from_attributes = True


class StudentBriefOut(BaseModel):
    id: int
    username: str
    name: str
    college: str | None = None
    avatar: str | None = None
    score: float = 0
    crisis_level: str | None = None

    class Config:
        from_attributes = True


class ImportResult(BaseModel):
    total: int
    created: int
    skipped: int
    errors: list[str] = []
```

- [ ] **Step 2: 创建管理员路由**

```python
# backend/app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.admin import (
    KnowledgeItemCreate, KnowledgeItemUpdate, KnowledgeItemOut,
    DocumentOut, TeacherOut, StudentBriefOut, ImportResult,
)
from app.services import knowledge_service
from app.services.import_export_service import export_users, import_users
from app.services.scoring import calc_radar_score

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ========== 知识库管理 ==========

@router.get("/knowledge", response_model=list[KnowledgeItemOut])
def list_knowledge(
    category: str | None = None,
    search: str | None = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return knowledge_service.get_all_knowledge_items(db, category, search)


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
    # 验证文件类型
    allowed_types = {"pdf", "docx", "txt"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 PDF/DOCX/TXT 格式")
    
    # 保存文件
    import os
    from pathlib import Path
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 创建文档记录
    doc = knowledge_service.save_document(db, file.filename, ext, str(file_path), user.id)
    
    # 解析文档
    try:
        chunks = knowledge_service.parse_document(str(file_path), ext)
        if chunks:
            knowledge_service.save_chunks(db, doc.id, chunks)
        else:
            doc.status = "failed"
            db.commit()
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
    return [DocumentOut(
        id=d.id,
        filename=d.filename,
        file_type=d.file_type,
        status=d.status,
        chunk_count=d.chunk_count,
        created_at=d.created_at.isoformat() if d.created_at else None,
    ) for d in docs]


@router.delete("/knowledge/documents/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if not knowledge_service.delete_document(db, doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"message": "删除成功"}


# ========== 教师管理 ==========

@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(
    search: str | None = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role == UserRole.TEACHER)
    if search:
        like = f"%{search}%"
        query = query.filter(User.name.like(like) | User.username.like(like) | User.college.like(like))
    
    teachers = query.all()
    result = []
    for t in teachers:
        student_count = db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == t.id).count()
        result.append(TeacherOut(
            id=t.id,
            username=t.username,
            name=t.name,
            college=t.college,
            avatar=t.avatar,
            title=t.title,
            department=t.department,
            student_count=student_count,
        ))
    return result


@router.get("/teachers/{teacher_id}/students", response_model=list[StudentBriefOut])
def get_teacher_students(
    teacher_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == UserRole.TEACHER).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    
    students = db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == teacher_id).all()
    result = []
    for s in students:
        score = calc_radar_score(db, s.id, s)
        # 获取危机等级
        from app.models.crisis import AIDialogSummary
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == s.id
        ).order_by(AIDialogSummary.created_at.desc()).first()
        
        result.append(StudentBriefOut(
            id=s.id,
            username=s.username,
            name=s.name,
            college=s.college,
            avatar=s.avatar,
            score=score,
            crisis_level=latest_crisis.level.value if latest_crisis else None,
        ))
    return result


# ========== 学生管理 ==========

@router.get("/students", response_model=list[StudentBriefOut])
def list_students(
    search: str | None = None,
    college: str | None = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if search:
        like = f"%{search}%"
        query = query.filter(User.name.like(like) | User.username.like(like))
    if college:
        query = query.filter(User.college.like(f"%{college}%"))
    
    students = query.all()
    result = []
    for s in students:
        score = calc_radar_score(db, s.id, s)
        from app.models.crisis import AIDialogSummary
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == s.id
        ).order_by(AIDialogSummary.created_at.desc()).first()
        
        result.append(StudentBriefOut(
            id=s.id,
            username=s.username,
            name=s.name,
            college=s.college,
            avatar=s.avatar,
            score=score,
            crisis_level=latest_crisis.level.value if latest_crisis else None,
        ))
    return result


# ========== 密码管理 ==========

@router.post("/reset-password/{user_id}")
def reset_password(
    user_id: int,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    target.password_hash = hash_password("123456")
    target.password_changed = False
    db.commit()
    return {"message": f"已将 {target.name} 的密码重置为 123456"}


# ========== 数据导入导出 ==========

@router.get("/export")
def export_data(
    role: str = Query(..., description="student 或 teacher"),
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="role 必须是 student 或 teacher")
    
    user_role = UserRole.STUDENT if role == "student" else UserRole.TEACHER
    data = export_users(db, user_role)
    
    filename = "学生数据.xlsx" if role == "student" else "教师数据.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=ImportResult)
async def import_data(
    role: str = Query(..., description="student 或 teacher"),
    file: UploadFile = File(...),
    admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="role 必须是 student 或 teacher")
    
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件")
    
    content = await file.read()
    user_role = UserRole.STUDENT if role == "student" else UserRole.TEACHER
    result = import_users(db, user_role, content)
    return ImportResult(**result)
```

- [ ] **Step 3: 注册路由到 main.py**

在 `backend/app/main.py` 中添加:
```python
# imports 区域添加
from app.api.admin import router as admin_router

# include_router 区域添加
app.include_router(admin_router)
```

- [ ] **Step 4: 验证路由**

运行: `cd mianyang-campus/backend && python -c "from app.api.admin import router; print('OK')"`
Expected: OK

---

## Task 6: 后端 — 修改密码 API

**Files:**
- Modify: `backend/app/api/auth.py:1-37`

- [ ] **Step 1: 添加修改密码接口**

在 `backend/app/api/auth.py` 末尾添加:

```python
from pydantic import BaseModel
from app.core.security import hash_password, verify_password


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    
    user.password_hash = hash_password(data.new_password)
    user.password_changed = True
    db.commit()
    return {"message": "密码修改成功"}
```

- [ ] **Step 2: 更新 UserInfo 返回 password_changed**

确保 `backend/app/schemas/user.py` 中的 `UserInfo` 包含:
```python
password_changed: bool = False
```

- [ ] **Step 3: 验证**

运行: `cd mianyang-campus/backend && python -c "from app.api.auth import router; print('OK')"`
Expected: OK

---

## Task 7: 后端 — 增强智能体检索（知识库优先 + 联网搜索）

**Files:**
- Modify: `backend/app/services/agent_service.py:20-39`

- [ ] **Step 1: 修改 build_context 函数**

```python
# 替换原有的 build_context 函数
def build_context(message: str, user: User) -> str:
    db = SessionLocal()
    try:
        # 使用增强的知识库搜索
        from app.services.knowledge_service import search_knowledge
        results = search_knowledge(db, message, limit=5)
        
        if results:
            context = "相关校园知识：\n"
            for r in results:
                if r["type"] == "qa":
                    context += f"[{r['category']}] Q: {r['question']}\nA: {r['answer']}\n\n"
                elif r["type"] == "document":
                    context += f"[文档参考] {r['content']}\n\n"
            return context
        return ""
    finally:
        db.close()
```

- [ ] **Step 2: 添加联网搜索fallback（可选）**

在 `backend/app/services/agent_service.py` 的 `chat` 函数中，当知识库无结果时添加联网搜索逻辑：

```python
# 在 chat 函数中，context 为空时尝试联网搜索
if not context:
    web_result = await search_web(message)
    if web_result:
        system_content += "\n\n以下是从互联网搜索到的信息（仅供参考）：\n" + web_result
```

添加联网搜索函数（需要配置搜索API）:
```python
async def search_web(query: str) -> str:
    """联网搜索（需要配置搜索API密钥）"""
    # 此处预留联网搜索接口，可接入百度/Google搜索API
    # 目前返回空，后续可扩展
    return ""
```

- [ ] **Step 3: 验证修改**

运行: `cd mianyang-campus/backend && python -c "from app.services.agent_service import build_context; print('OK')"`
Expected: OK

---

## Task 8: 前端 — AdminLayout 布局

**Files:**
- Create: `frontend/src/components/layout/AdminLayout.vue`

- [ ] **Step 1: 创建 AdminLayout**

```vue
<!-- frontend/src/components/layout/AdminLayout.vue -->
<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-left" style="cursor:pointer" @click="goTo('/admin')">
        <img src="/images/校徽.png" class="topbar-badge" />
        <span class="logo">绵小城</span>
        <span class="logo-divider"></span>
        <span class="motto">博学、笃行、严谨、创新</span>
      </div>
      <div class="topbar-right">
        <el-tooltip :content="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'" placement="bottom">
          <el-button text circle @click="toggleSidebar">
            <el-icon :size="18"><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </header>
    <div class="body-area">
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <nav class="sidebar-nav">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
            <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
          </router-link>
        </nav>
        <div class="sidebar-footer">
          <el-dropdown trigger="click" placement="top-start">
            <div class="admin-info">
              <el-avatar :size="sidebarCollapsed ? 32 : 40" :src="auth.user?.avatar || ''">
                {{ auth.userName?.[0] }}
              </el-avatar>
              <div v-if="!sidebarCollapsed" class="admin-detail">
                <span class="admin-name">{{ auth.userName }}</span>
                <span class="admin-role">管理员</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-item divided @click="logout">
                <el-icon style="margin-right:6px"><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </template>
          </el-dropdown>
        </div>
      </aside>
      <main class="main-area">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  HomeFilled, Document, User, UserFilled, Upload,
  SwitchButton, Fold, Expand
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const sidebarCollapsed = ref(false)

const navItems = [
  { path: '/admin', label: '首页', icon: HomeFilled },
  { path: '/admin/knowledge', label: '知识库', icon: Document },
  { path: '/admin/teachers', label: '教师管理', icon: User },
  { path: '/admin/students', label: '学生管理', icon: UserFilled },
  { path: '/admin/data', label: '数据管理', icon: Upload },
]

function isActive(path: string) {
  return route.path === path
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function goTo(path: string) { router.push(path) }

function logout() {
  auth.logout()
  router.push('/')
}
</script>

<style>
body { overflow: hidden; margin: 0; }
</style>
<style scoped>
.app-shell { display: flex; flex-direction: column; height: 100vh; background: #fff; }

.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px; border-bottom: 1px solid #e8e8e8;
  background: #fff; flex-shrink: 0; z-index: 100;
}
.topbar-left { display: flex; align-items: center; gap: 8px; }
.topbar-badge { height: 32px; width: auto; border-radius: 4px; }
.logo { font-size: 20px; font-weight: 700; color: #409eff; letter-spacing: 1px; }
.logo-divider { width: 1px; height: 20px; background: #ddd; margin: 0 6px; }
.motto {
  font-size: 14px; font-weight: 600;
  background: linear-gradient(135deg, #c41d7f, #e8a020);
  background-clip: text; -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 4px;
}
.topbar-right { display: flex; align-items: center; gap: 4px; }

.body-area { display: flex; flex: 1; min-height: 0; }

.sidebar {
  width: 200px; flex-shrink: 0; display: flex; flex-direction: column;
  background: rgba(255,255,255,.85); backdrop-filter: blur(20px);
  border-right: 1px solid rgba(0,0,0,.06); box-shadow: 2px 0 12px rgba(0,0,0,.03);
  transition: width 0.2s ease;
  overflow: hidden;
}
.sidebar.collapsed { width: 64px; }

.sidebar-nav { flex: 1; padding: 12px 8px; display: flex; flex-direction: column; gap: 4px; }

.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-radius: 8px;
  text-decoration: none; color: #555; font-size: 14px; font-weight: 500;
  transition: all 0.15s ease; position: relative; white-space: nowrap;
}
.sidebar.collapsed .nav-item { justify-content: center; padding: 10px; }
.nav-item:hover { background: rgba(64,158,255,0.06); color: #409eff; }
.nav-item.active {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff; font-weight: 600;
}
.nav-item.active .el-icon { color: #fff; }
.nav-label { flex: 1; }

.sidebar-footer {
  padding: 16px 12px; border-top: 1px solid rgba(0,0,0,.06);
}
.admin-info {
  display: flex; align-items: center; gap: 14px;
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  transition: background 0.15s;
}
.sidebar.collapsed .admin-info { justify-content: center; padding: 10px 0; }
.admin-info:hover { background: rgba(64,158,255,0.06); }
.admin-detail { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.admin-name { font-size: 13px; font-weight: 600; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.admin-role { font-size: 11px; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.main-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
</style>
```

---

## Task 9: 前端 — 路由配置

**Files:**
- Modify: `frontend/src/router/index.ts:1-67`

- [ ] **Step 1: 添加 admin 路由**

```typescript
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUser } from '@/utils/token'

const publicPaths = ['/login']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'Login', component: () => import('@/views/login/LoginPage.vue') },

    {
      path: '/student',
      component: () => import('@/components/layout/StudentLayout.vue'),
      meta: { role: 'student' },
      children: [
        { path: '', component: () => import('@/views/student/HomePage.vue') },
        { path: 'agent', component: () => import('@/views/student/AgentPage.vue') },
        { path: 'campus', component: () => import('@/views/student/CampusPage.vue') },
        { path: 'growth', component: () => import('@/views/student/GrowthPage.vue') },
        { path: 'schedule', component: () => import('@/views/student/SchedulePage.vue') },
        { path: 'grade', redirect: '/student/schedule' },
        { path: 'service', component: () => import('@/views/student/ServicePage.vue') },
      ],
    },
    {
      path: '/teacher',
      component: () => import('@/components/layout/TeacherLayout.vue'),
      meta: { role: 'teacher' },
      children: [
        { path: '', component: () => import('@/views/teacher/HomePage.vue') },
        { path: 'agent', component: () => import('@/views/teacher/AgentPage.vue') },
        { path: 'students', component: () => import('@/views/teacher/StudentsPage.vue') },
        { path: 'approval', component: () => import('@/views/teacher/ApprovalPage.vue') },
        { path: 'messages', component: () => import('@/views/teacher/MessagesPage.vue') },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/components/layout/AdminLayout.vue'),
      meta: { role: 'admin' },
      children: [
        { path: '', component: () => import('@/views/admin/HomePage.vue') },
        { path: 'knowledge', component: () => import('@/views/admin/KnowledgePage.vue') },
        { path: 'teachers', component: () => import('@/views/admin/TeachersPage.vue') },
        { path: 'students', component: () => import('@/views/admin/StudentsPage.vue') },
        { path: 'data', component: () => import('@/views/admin/DataPage.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const token = getToken()
  const user = getUser()
  
  if (!token && !publicPaths.includes(to.path)) return '/login'
  
  if (token && to.path === '/login') {
    const roleMap: Record<string, string> = { teacher: '/teacher', admin: '/admin' }
    return roleMap[user?.role || ''] || '/student'
  }
  
  if (token && user && to.meta.role) {
    if (user.role === 'admin') return
    
    if (user.role === 'student' && to.meta.role === 'teacher') return '/student'
    if (user.role === 'student' && to.meta.role === 'admin') return '/student'
    
    if (user.role === 'teacher' && to.meta.role === 'student') return '/teacher'
    if (user.role === 'teacher' && to.meta.role === 'admin') return '/teacher'
  }
})

export default router
```

---

## Task 10: 前端 — 登录页修改

**Files:**
- Modify: `frontend/src/views/login/LoginPage.vue:80`

- [ ] **Step 1: 修改 admin 跳转**

```typescript
// 修改第80行
const roleMap: Record<string, string> = { student: '/student', teacher: '/teacher', admin: '/admin' }
```

---

## Task 11: 前端 — 管理员 API 模块

**Files:**
- Create: `frontend/src/api/admin.ts`

- [ ] **Step 1: 创建 admin API**

```typescript
// frontend/src/api/admin.ts
import request from '@/utils/request'

// 知识库
export interface KnowledgeItem {
  id: number
  category: string
  question: string
  answer: string
  tags: string | null
}

export interface DocumentInfo {
  id: number
  filename: string
  file_type: string
  status: string
  chunk_count: number
  created_at: string | null
}

export function getKnowledgeList(params?: { category?: string; search?: string }) {
  return request.get<KnowledgeItem[]>('/admin/knowledge', { params })
}

export function createKnowledgeItem(data: { category: string; question: string; answer: string; tags?: string }) {
  return request.post<KnowledgeItem>('/admin/knowledge', data)
}

export function updateKnowledgeItem(id: number, data: Partial<KnowledgeItem>) {
  return request.put<KnowledgeItem>(`/admin/knowledge/${id}`, data)
}

export function deleteKnowledgeItem(id: number) {
  return request.delete(`/admin/knowledge/${id}`)
}

export function uploadDocument(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ message: string; document_id: number; chunk_count: number }>('/admin/knowledge/upload', formData)
}

export function getDocumentList() {
  return request.get<DocumentInfo[]>('/admin/knowledge/documents')
}

export function deleteDocument(id: number) {
  return request.delete(`/admin/knowledge/documents/${id}`)
}

// 教师管理
export interface TeacherInfo {
  id: number
  username: string
  name: string
  college: string | null
  avatar: string | null
  title: string | null
  department: string | null
  student_count: number
}

export interface StudentBrief {
  id: number
  username: string
  name: string
  college: string | null
  avatar: string | null
  score: number
  crisis_level: string | null
}

export function getTeacherList(params?: { search?: string }) {
  return request.get<TeacherInfo[]>('/admin/teachers', { params })
}

export function getTeacherStudents(teacherId: number) {
  return request.get<StudentBrief[]>(`/admin/teachers/${teacherId}/students`)
}

// 学生管理
export function getStudentList(params?: { search?: string; college?: string }) {
  return request.get<StudentBrief[]>('/admin/students', { params })
}

// 密码管理
export function resetPassword(userId: number) {
  return request.post<{ message: string }>(`/admin/reset-password/${userId}`)
}

// 数据导入导出
export function exportData(role: 'student' | 'teacher') {
  return request.get('/admin/export', { params: { role }, responseType: 'blob' })
}

export interface ImportResult {
  total: number
  created: number
  skipped: number
  errors: string[]
}

export function importData(role: 'student' | 'teacher', file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<ImportResult>(`/admin/import?role=${role}`, formData)
}
```

---

## Task 12: 前端 — 管理员首页

**Files:**
- Create: `frontend/src/views/admin/HomePage.vue`

- [ ] **Step 1: 创建首页**

```vue
<!-- frontend/src/views/admin/HomePage.vue -->
<template>
  <div class="admin-home">
    <div class="welcome-section">
      <h1>管理员控制台</h1>
      <p>欢迎回来，{{ auth.userName }}</p>
    </div>
    
    <div class="stats-grid">
      <el-card v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-icon" :style="{ background: stat.color }">
          <el-icon :size="24"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
      </el-card>
    </div>
    
    <div class="quick-actions">
      <el-card>
        <template #header>
          <span>快捷操作</span>
        </template>
        <div class="action-grid">
          <el-button type="primary" @click="$router.push('/admin/knowledge')">
            <el-icon><Document /></el-icon>管理知识库
          </el-button>
          <el-button type="success" @click="$router.push('/admin/teachers')">
            <el-icon><User /></el-icon>查看教师
          </el-button>
          <el-button type="warning" @click="$router.push('/admin/data')">
            <el-icon><Upload /></el-icon>导入数据
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getTeacherList } from '@/api/admin'
import { Document, User, Upload, UserFilled } from '@element-plus/icons-vue'

const auth = useAuthStore()

const stats = ref([
  { label: '教师总数', value: 0, icon: User, color: '#409eff' },
  { label: '学生总数', value: 0, icon: UserFilled, color: '#67c23a' },
  { label: '知识库条目', value: 0, icon: Document, color: '#e6a23c' },
])

onMounted(async () => {
  try {
    const teachers = await getTeacherList()
    stats.value[0].value = teachers.length
  } catch {}
})
</script>

<style scoped>
.admin-home {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.welcome-section {
  margin-bottom: 24px;
}

.welcome-section h1 {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin: 0 0 8px;
}

.welcome-section p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 12px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
}

.quick-actions {
  margin-bottom: 24px;
}

.action-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
```

---

## Task 13: 前端 — 知识库管理页面

**Files:**
- Create: `frontend/src/views/admin/KnowledgePage.vue`

- [ ] **Step 1: 创建知识库管理页面**

```vue
<!-- frontend/src/views/admin/KnowledgePage.vue -->
<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h2>AI知识库管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon>添加问答对
        </el-button>
        <el-upload
          :show-file-list="false"
          :before-upload="handleUpload"
          accept=".pdf,.docx,.txt"
        >
          <el-button type="success">
            <el-icon><Upload /></el-icon>上传文档
          </el-button>
        </el-upload>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="问答对" name="qa">
        <div class="filter-bar">
          <el-select v-model="categoryFilter" placeholder="选择分类" clearable style="width: 150px">
            <el-option label="办事流程" value="办事流程" />
            <el-option label="校园导航" value="校园导航" />
            <el-option label="规章制度" value="规章制度" />
            <el-option label="校园生活" value="校园生活" />
            <el-option label="自定义" value="自定义" />
          </el-select>
          <el-input v-model="searchText" placeholder="搜索问题或答案" clearable style="width: 250px">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <el-table :data="filteredItems" style="width: 100%" border>
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="answer" label="答案" min-width="300" show-overflow-tooltip />
          <el-table-column prop="tags" label="标签" width="150" show-overflow-tooltip />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="editItem(row)">编辑</el-button>
              <el-popconfirm title="确定删除吗？" @confirm="deleteItem(row.id)">
                <template #reference>
                  <el-button type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="文档管理" name="docs">
        <el-table :data="documents" style="width: 100%" border>
          <el-table-column prop="filename" label="文件名" min-width="200" />
          <el-table-column prop="file_type" label="类型" width="100" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
                {{ row.status === 'completed' ? '已完成' : row.status === 'failed' ? '失败' : '处理中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="分块数" width="100" />
          <el-table-column prop="created_at" label="上传时间" width="180" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-popconfirm title="确定删除吗？" @confirm="deleteDoc(row.id)">
                <template #reference>
                  <el-button type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑问答对' : '添加问答对'" width="600px">
      <el-form :model="formData" label-width="80px">
        <el-form-item label="分类" required>
          <el-select v-model="formData.category" placeholder="选择分类">
            <el-option label="办事流程" value="办事流程" />
            <el-option label="校园导航" value="校园导航" />
            <el-option label="规章制度" value="规章制度" />
            <el-option label="校园生活" value="校园生活" />
            <el-option label="自定义" value="自定义" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题" required>
          <el-input v-model="formData.question" placeholder="输入问题" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="formData.answer" type="textarea" :rows="4" placeholder="输入答案" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="formData.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Upload, Search } from '@element-plus/icons-vue'
import {
  getKnowledgeList, createKnowledgeItem, updateKnowledgeItem, deleteKnowledgeItem,
  uploadDocument, getDocumentList, deleteDocument,
  type KnowledgeItem, type DocumentInfo,
} from '@/api/admin'

const activeTab = ref('qa')
const items = ref<KnowledgeItem[]>([])
const documents = ref<DocumentInfo[]>([])
const categoryFilter = ref('')
const searchText = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)

const formData = ref({
  category: '',
  question: '',
  answer: '',
  tags: '',
})

const filteredItems = computed(() => {
  return items.value.filter(item => {
    if (categoryFilter.value && item.category !== categoryFilter.value) return false
    if (searchText.value) {
      const search = searchText.value.toLowerCase()
      return item.question.toLowerCase().includes(search) || item.answer.toLowerCase().includes(search)
    }
    return true
  })
})

async function loadItems() {
  try {
    items.value = await getKnowledgeList()
  } catch {
    ElMessage.error('加载知识库失败')
  }
}

async function loadDocuments() {
  try {
    documents.value = await getDocumentList()
  } catch {
    ElMessage.error('加载文档列表失败')
  }
}

function showAddDialog() {
  editingId.value = null
  formData.value = { category: '', question: '', answer: '', tags: '' }
  dialogVisible.value = true
}

function editItem(item: KnowledgeItem) {
  editingId.value = item.id
  formData.value = {
    category: item.category,
    question: item.question,
    answer: item.answer,
    tags: item.tags || '',
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.category || !formData.value.question || !formData.value.answer) {
    ElMessage.warning('请填写必填项')
    return
  }
  
  submitting.value = true
  try {
    if (editingId.value) {
      await updateKnowledgeItem(editingId.value, formData.value)
      ElMessage.success('更新成功')
    } else {
      await createKnowledgeItem(formData.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadItems()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function deleteItem(id: number) {
  try {
    await deleteKnowledgeItem(id)
    ElMessage.success('删除成功')
    loadItems()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function handleUpload(file: File) {
  try {
    await uploadDocument(file)
    ElMessage.success('上传成功')
    loadDocuments()
  } catch {
    ElMessage.error('上传失败')
  }
  return false
}

async function deleteDoc(id: number) {
  try {
    await deleteDocument(id)
    ElMessage.success('删除成功')
    loadDocuments()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadItems()
  loadDocuments()
})
</script>

<style scoped>
.knowledge-page {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
```

---

## Task 14: 前端 — 教师管理页面

**Files:**
- Create: `frontend/src/views/admin/TeachersPage.vue`

- [ ] **Step 1: 创建教师管理页面**

```vue
<!-- frontend/src/views/admin/TeachersPage.vue -->
<template>
  <div class="teachers-page">
    <div class="page-header">
      <h2>教师管理</h2>
      <el-input v-model="searchText" placeholder="搜索教师" clearable style="width: 250px">
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <el-table :data="filteredTeachers" style="width: 100%" border @row-click="handleRowClick">
      <el-table-column prop="username" label="工号" width="120" />
      <el-table-column prop="name" label="姓名" width="120">
        <template #default="{ row }">
          <div class="teacher-name-cell">
            <el-avatar :size="32" :src="row.avatar || ''">{{ row.name?.[0] }}</el-avatar>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="college" label="学院" min-width="150" />
      <el-table-column prop="title" label="职称" width="120" />
      <el-table-column prop="department" label="所属单位" width="150" />
      <el-table-column prop="student_count" label="学生数量" width="100" align="center">
        <template #default="{ row }">
          <el-tag type="primary">{{ row.student_count }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click.stop="viewStudents(row)">查看学生</el-button>
          <el-popconfirm title="确定重置该教师密码为123456？" @confirm="handleResetPassword(row)">
            <template #reference>
              <el-button type="warning" link @click.stop>重置密码</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 学生详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="`${selectedTeacher?.name} - 学生列表`" size="600px">
      <div v-if="loadingStudents" class="loading-wrap">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      </div>
      <template v-else>
        <div v-if="teacherStudents.length === 0" class="empty-tip">暂无学生</div>
        <div v-else class="student-list">
          <div v-for="student in teacherStudents" :key="student.id" class="student-card">
            <el-avatar :size="40" :src="student.avatar || ''">{{ student.name?.[0] }}</el-avatar>
            <div class="student-info">
              <span class="student-name">{{ student.name }}</span>
              <span class="student-detail">{{ student.username }} · {{ student.college || '未分配' }}</span>
            </div>
            <div class="student-meta">
              <span class="student-score">综合评分: {{ student.score }}</span>
              <el-tag v-if="student.crisis_level" :type="student.crisis_level === 'severe' ? 'danger' : 'warning'" size="small">
                {{ student.crisis_level === 'severe' ? '严重' : student.crisis_level === 'moderate' ? '中等' : '轻微' }}
              </el-tag>
            </div>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Loading } from '@element-plus/icons-vue'
import { getTeacherList, getTeacherStudents, resetPassword, type TeacherInfo, type StudentBrief } from '@/api/admin'

const teachers = ref<TeacherInfo[]>([])
const searchText = ref('')
const drawerVisible = ref(false)
const selectedTeacher = ref<TeacherInfo | null>(null)
const teacherStudents = ref<StudentBrief[]>([])
const loadingStudents = ref(false)

const filteredTeachers = computed(() => {
  if (!searchText.value) return teachers.value
  const search = searchText.value.toLowerCase()
  return teachers.value.filter(t =>
    t.name.toLowerCase().includes(search) ||
    t.username.toLowerCase().includes(search) ||
    (t.college || '').toLowerCase().includes(search)
  )
})

async function loadTeachers() {
  try {
    teachers.value = await getTeacherList()
  } catch {
    ElMessage.error('加载教师列表失败')
  }
}

function handleRowClick(row: TeacherInfo) {
  viewStudents(row)
}

async function viewStudents(teacher: TeacherInfo) {
  selectedTeacher.value = teacher
  drawerVisible.value = true
  loadingStudents.value = true
  try {
    teacherStudents.value = await getTeacherStudents(teacher.id)
  } catch {
    ElMessage.error('加载学生列表失败')
  } finally {
    loadingStudents.value = false
  }
}

async function handleResetPassword(teacher: TeacherInfo) {
  try {
    const res = await resetPassword(teacher.id)
    ElMessage.success(res.message)
  } catch {
    ElMessage.error('重置密码失败')
  }
}

onMounted(loadTeachers)
</script>

<style scoped>
.teachers-page {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.teacher-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-wrap {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-tip {
  text-align: center;
  color: #999;
  padding: 40px;
}

.student-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.student-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #eee;
  border-radius: 8px;
  transition: background 0.2s;
}

.student-card:hover {
  background: #f5f7fa;
}

.student-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.student-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.student-detail {
  font-size: 12px;
  color: #999;
}

.student-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.student-score {
  font-size: 12px;
  color: #666;
}
</style>
```

---

## Task 15: 前端 — 学生管理页面

**Files:**
- Create: `frontend/src/views/admin/StudentsPage.vue`

- [ ] **Step 1: 创建学生管理页面**

```vue
<!-- frontend/src/views/admin/StudentsPage.vue -->
<template>
  <div class="students-page">
    <div class="page-header">
      <h2>学生管理</h2>
      <div class="header-filters">
        <el-input v-model="searchText" placeholder="搜索学生" clearable style="width: 200px">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-input v-model="collegeFilter" placeholder="学院筛选" clearable style="width: 200px" />
      </div>
    </div>

    <el-table :data="filteredStudents" style="width: 100%" border>
      <el-table-column prop="username" label="学号" width="120" />
      <el-table-column prop="name" label="姓名" width="120">
        <template #default="{ row }">
          <div class="student-name-cell">
            <el-avatar :size="32" :src="row.avatar || ''">{{ row.name?.[0] }}</el-avatar>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="college" label="学院" min-width="150" />
      <el-table-column prop="score" label="综合评分" width="100" align="center" />
      <el-table-column prop="crisis_level" label="危机等级" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.crisis_level" :type="row.crisis_level === 'severe' ? 'danger' : row.crisis_level === 'moderate' ? 'warning' : 'info'" size="small">
            {{ row.crisis_level === 'severe' ? '严重' : row.crisis_level === 'moderate' ? '中等' : '轻微' }}
          </el-tag>
          <span v-else class="text-muted">无</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确定重置该学生密码为123456？" @confirm="handleResetPassword(row)">
            <template #reference>
              <el-button type="warning" link>重置密码</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getStudentList, resetPassword, type StudentBrief } from '@/api/admin'

const students = ref<StudentBrief[]>([])
const searchText = ref('')
const collegeFilter = ref('')

const filteredStudents = computed(() => {
  return students.value.filter(s => {
    if (searchText.value) {
      const search = searchText.value.toLowerCase()
      if (!s.name.toLowerCase().includes(search) && !s.username.toLowerCase().includes(search)) return false
    }
    if (collegeFilter.value) {
      if (!(s.college || '').toLowerCase().includes(collegeFilter.value.toLowerCase())) return false
    }
    return true
  })
})

async function loadStudents() {
  try {
    students.value = await getStudentList()
  } catch {
    ElMessage.error('加载学生列表失败')
  }
}

async function handleResetPassword(student: StudentBrief) {
  try {
    const res = await resetPassword(student.id)
    ElMessage.success(res.message)
  } catch {
    ElMessage.error('重置密码失败')
  }
}

onMounted(loadStudents)
</script>

<style scoped>
.students-page {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.header-filters {
  display: flex;
  gap: 12px;
}

.student-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.text-muted {
  color: #999;
  font-size: 12px;
}
</style>
```

---

## Task 16: 前端 — 数据导入导出页面

**Files:**
- Create: `frontend/src/views/admin/DataPage.vue`

- [ ] **Step 1: 创建数据管理页面**

```vue
<!-- frontend/src/views/admin/DataPage.vue -->
<template>
  <div class="data-page">
    <div class="page-header">
      <h2>数据管理</h2>
    </div>

    <el-row :gutter="24">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>数据导出</span>
          </template>
          <p class="card-desc">导出用户数据为 Excel 文件</p>
          <div class="export-actions">
            <el-button type="primary" @click="handleExport('student')" :loading="exporting">
              <el-icon><Download /></el-icon>导出学生数据
            </el-button>
            <el-button type="success" @click="handleExport('teacher')" :loading="exporting">
              <el-icon><Download /></el-icon>导出教师数据
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span>数据导入</span>
          </template>
          <p class="card-desc">从 Excel 文件导入用户数据（重复学号/工号将跳过）</p>
          
          <el-radio-group v-model="importRole" style="margin-bottom: 16px">
            <el-radio value="student">导入学生</el-radio>
            <el-radio value="teacher">导入教师</el-radio>
          </el-radio-group>

          <el-upload
            :show-file-list="false"
            :before-upload="handleImport"
            accept=".xlsx,.xls"
          >
            <el-button type="warning" :loading="importing">
              <el-icon><Upload /></el-icon>选择文件导入
            </el-button>
          </el-upload>

          <div v-if="importResult" class="import-result">
            <el-alert
              :title="`导入完成：新增 ${importResult.created} 条，跳过 ${importResult.skipped} 条`"
              :type="importResult.errors.length > 0 ? 'warning' : 'success'"
              show-icon
              :closable="false"
            />
            <div v-if="importResult.errors.length > 0" class="error-list">
              <p>错误信息：</p>
              <ul>
                <li v-for="(err, i) in importResult.errors" :key="i">{{ err }}</li>
              </ul>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 24px">
      <template #header>
        <span>导入模板说明</span>
      </template>
      <div class="template-info">
        <h4>学生导入模板格式：</h4>
        <p>学号 | 姓名 | 学院 | 性别 | 年龄 | 联系电话 | 籍贯</p>
        <h4>教师导入模板格式：</h4>
        <p>工号 | 姓名 | 学院 | 性别 | 年龄 | 职称 | 所属单位 | 联系电话</p>
        <h4>注意事项：</h4>
        <ul>
          <li>第一行为表头，数据从第二行开始</li>
          <li>学号/工号重复的记录将自动跳过</li>
          <li>新用户的默认密码为 123456</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import { exportData, importData, type ImportResult } from '@/api/admin'

const exporting = ref(false)
const importing = ref(false)
const importRole = ref<'student' | 'teacher'>('student')
const importResult = ref<ImportResult | null>(null)

async function handleExport(role: 'student' | 'teacher') {
  exporting.value = true
  try {
    const data = await exportData(role)
    const blob = new Blob([data as any], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = role === 'student' ? '学生数据.xlsx' : '教师数据.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleImport(file: File) {
  importing.value = true
  importResult.value = null
  try {
    const result = await importData(importRole.value, file)
    importResult.value = result
    ElMessage.success('导入完成')
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
  return false
}
</script>

<style scoped>
.data-page {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.card-desc {
  color: #666;
  font-size: 14px;
  margin: 0 0 16px;
}

.export-actions {
  display: flex;
  gap: 12px;
}

.import-result {
  margin-top: 16px;
}

.error-list {
  margin-top: 8px;
  font-size: 13px;
  color: #e6a23c;
}

.error-list ul {
  margin: 4px 0 0 16px;
  padding: 0;
}

.template-info h4 {
  font-size: 14px;
  color: #333;
  margin: 12px 0 8px;
}

.template-info h4:first-child {
  margin-top: 0;
}

.template-info p {
  font-size: 13px;
  color: #666;
  margin: 0;
}

.template-info ul {
  font-size: 13px;
  color: #666;
  margin: 4px 0 0 16px;
  padding: 0;
}
</style>
```

---

## Task 17: 前端 — 教师端/学生端密码修改

**Files:**
- Modify: `frontend/src/components/layout/TeacherLayout.vue:64-127`
- Modify: `frontend/src/components/layout/StudentLayout.vue` (similar changes)

- [ ] **Step 1: 在 TeacherLayout 中添加密码修改按钮**

在个人资料对话框的 footer 区域添加修改密码按钮：

```vue
<!-- 在 <template #footer> 中添加 -->
<template #footer>
  <div style="display: flex; justify-content: space-between; width: 100%">
    <el-button 
      type="warning" 
      @click="showChangePassword = true"
      :disabled="auth.user?.password_changed"
    >
      {{ auth.user?.password_changed ? '密码已修改过' : '修改密码' }}
    </el-button>
    <div>
      <el-button @click="showProfile = false">取消</el-button>
      <el-button type="primary" @click="handleSaveProfile" :loading="saving">保存</el-button>
    </div>
  </div>
</template>
```

- [ ] **Step 2: 添加密码修改对话框**

在 TeacherLayout.vue 的 `</el-dialog>` 后面添加：

```vue
<el-dialog v-model="showChangePassword" title="修改密码" width="400px" :close-on-click-modal="false">
  <el-form :model="passwordForm" label-width="100px">
    <el-form-item label="旧密码" required>
      <el-input v-model="passwordForm.old_password" type="password" show-password />
    </el-form-item>
    <el-form-item label="新密码" required>
      <el-input v-model="passwordForm.new_password" type="password" show-password />
    </el-form-item>
    <el-form-item label="确认新密码" required>
      <el-input v-model="passwordForm.confirm_password" type="password" show-password />
    </el-form-item>
  </el-form>
  <template #footer>
    <el-button @click="showChangePassword = false">取消</el-button>
    <el-button type="primary" @click="handleChangePassword" :loading="changingPassword">确定</el-button>
  </template>
</el-dialog>
```

- [ ] **Step 3: 添加密码修改逻辑**

在 `<script setup>` 中添加：

```typescript
import { changePassword } from '@/api/user'

const showChangePassword = ref(false)
const changingPassword = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

async function handleChangePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    ElMessage.warning('请填写所有字段')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.error('新密码至少6位')
    return
  }
  
  changingPassword.value = true
  try {
    await changePassword(passwordForm.old_password, passwordForm.new_password)
    ElMessage.success('密码修改成功')
    showChangePassword.value = false
    // 更新本地用户状态
    if (auth.user) {
      auth.updateUser({ ...auth.user, password_changed: true })
    }
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '修改失败')
  } finally {
    changingPassword.value = false
  }
}
```

- [ ] **Step 4: 在 user.ts 中添加 changePassword API**

```typescript
// frontend/src/api/user.ts 末尾添加
export function changePassword(old_password: string, new_password: string) {
  return request.put('/auth/change-password', { old_password, new_password })
}
```

- [ ] **Step 5: 对 StudentLayout 做相同修改**

参考 TeacherLayout 的修改，在 StudentLayout 中添加相同的密码修改功能。

- [ ] **Step 6: 登录时检查密码修改状态**

在 `frontend/src/views/login/LoginPage.vue` 的 `handleLogin` 函数中添加：

```typescript
// 登录成功后检查密码是否修改过
if (res.user && !res.user.password_changed && res.user.role !== 'admin') {
  ElMessage.warning('请及时修改初始密码')
}
```

---

## Task 18: 前端 — 类型更新

**Files:**
- Modify: `frontend/src/types/index.ts:3-19`

- [ ] **Step 1: 更新 UserInfo 类型**

```typescript
// 在 UserInfo 接口中添加
export interface UserInfo {
  id: number
  username: string
  name: string
  role: UserRole
  college?: string
  avatar?: string
  skills_json?: { skills: { name: string; context: string }[]; interests: string[] }
  tutor_id?: number | null
  gender?: string | null
  age?: number | null
  political_status?: string | null
  title?: string | null
  hometown?: string | null
  phone?: string | null
  department?: string | null
  password_changed?: boolean
}
```

---

## Task 19: 验证与测试

- [ ] **Step 1: 启动后端**

运行: `cd mianyang-campus/backend && uvicorn app.main:app --reload`
Expected: 服务启动成功，无报错

- [ ] **Step 2: 启动前端**

运行: `cd mianyang-campus/frontend && npm run dev`
Expected: 服务启动成功，无报错

- [ ] **Step 3: 测试管理员登录**

1. 访问 http://localhost:5173/login
2. 使用 admin / admin123 登录
3. 预期：跳转到 /admin 管理员首页

- [ ] **Step 4: 测试知识库管理**

1. 点击"知识库"导航
2. 添加一个问答对
3. 上传一个TXT文档
4. 预期：列表显示新增条目，文档状态为"已完成"

- [ ] **Step 5: 测试教师管理**

1. 点击"教师管理"导航
2. 查看教师列表
3. 点击教师行，查看学生详情
4. 点击"重置密码"
5. 预期：学生抽屉显示，密码重置成功提示

- [ ] **Step 6: 测试数据导入导出**

1. 点击"数据管理"导航
2. 导出学生数据
3. 导入一个Excel文件
4. 预期：文件下载成功，导入结果显示

- [ ] **Step 7: 测试密码修改**

1. 用教师账号 t1001 登录
2. 打开个人资料
3. 点击"修改密码"
4. 预期：修改成功，再次打开显示"密码已修改过"

- [ ] **Step 8: 提交代码**

```bash
cd mianyang-campus
git add .
git commit -m "feat: 添加管理员端功能 - 知识库管理、密码管理、教师管理、数据导入导出"
```

---

## 验收清单

- [ ] 管理员登录后进入管理员端，布局与教师端风格一致
- [ ] 知识库支持增删改查问答对
- [ ] 知识库支持上传PDF/Word/TXT文档并自动解析
- [ ] 智能体优先检索本地知识库回答问题
- [ ] 管理员可重置教师/学生密码为123456
- [ ] 教师/学生可在个人资料修改密码（仅一次）
- [ ] 教师列表显示所带学生数量
- [ ] 点击教师可查看其学生详情
- [ ] 支持导出学生/教师数据为Excel
- [ ] 支持导入Excel数据，跳过重复记录
- [ ] 所有操作有适当的权限控制
