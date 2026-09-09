from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from urllib.parse import urlparse
from pathlib import Path

from app.core.config import settings


def _ensure_database():
    """确保数据库存在，支持 SQLite 和 MySQL。"""
    if settings.DATABASE_URL.startswith("sqlite"):
        # SQLite: 确保数据库目录存在
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    else:
        # MySQL: 连接时不指定数据库，自动创建目标数据库（如不存在）
        parsed = urlparse(settings.DATABASE_URL)
        db_name = parsed.path.lstrip("/")
        base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
        tmp_engine = create_engine(base_url)
        with tmp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        tmp_engine.dispose()


_ensure_database()

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
