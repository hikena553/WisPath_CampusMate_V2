from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    """知识库外部数据源：上传的外部文件 + 需要引进的网络数据位置（URL）。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    # 数据源类型：file=上传文件 / url=网络数据源；file_type 保留原文件格式（pdf/docx/txt/url）
    file_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str] = mapped_column(String(500))
    # 网络数据源地址（source_type=url 时填写，file 类型为空）
    source_url: Mapped[str | None] = mapped_column(String(700), default=None)
    source_type: Mapped[str] = mapped_column(String(20), default="file")  # file / url
    status: Mapped[str] = mapped_column(String(20), default="processing")  # 状态：processing/completed/failed
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
