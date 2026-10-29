from urllib.parse import urlparse
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")


def _ensure_database():
    """确保数据库存在，支持 SQLite 和 MySQL。"""
    if _IS_SQLITE:
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

# SQLite 并发加固（稳定性 p4_2）：
#   本项目同一进程内有「HTTP 请求 + 5 个后台周期任务线程 + 定时任务执行」
#   同时读写同一个 .db 文件。pysqlite 默认 busy timeout 只有 5 秒，一旦写入
#   撞车就抛 "database is locked"，轻则接口 500，重则启动阶段的迁移/种子数据
#   抛异常直接把进程带走（表现为"启动几秒后窗口自己关了"）。
#   - timeout=30：把驱动层等待放宽到 30 秒；
#   - WAL：读写不再互斥，读不被写阻塞，写入并发大幅提升；
#   - synchronous=NORMAL：WAL 下的推荐值，掉电最多丢最后一个事务，换取写入快数倍。
_connect_args = {"timeout": 30, "check_same_thread": False} if _IS_SQLITE else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)


if _IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _sqlite_on_connect(dbapi_conn, _record):  # pragma: no cover - 驱动级钩子
        """每个新连接建立时统一设置 PRAGMA（WAL 是持久属性，重复设置无副作用）。"""
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        finally:
            cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
