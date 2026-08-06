from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from urllib.parse import urlparse

from app.core.config import settings


def _ensure_database():
    """连接 MySQL 时不指定数据库，自动创建目标数据库（如不存在）。"""
    parsed = urlparse(settings.DATABASE_URL)
    # 去掉路径中的数据库名，只连接 MySQL 服务器
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
