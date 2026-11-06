"""副本端到端：新源挂载 → 抓取 → 转发，验证三项修复。"""
import asyncio
import os
import shutil
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))

COPY = HERE / "verify2.db"
shutil.copyfile(BACKEND / "campus_mate.db", COPY)
os.environ["DATABASE_URL"] = f"sqlite:///{COPY.as_posix()}"

from app.core.database import SessionLocal  # noqa: E402
from app.models.feed import FeedSource  # noqa: E402
from app.services.feed_ingest import (  # noqa: E402
    ingest_all, sync_builtin_sources,
)
from app.services.media_account_service import mount_new_builtin_sources  # noqa: E402

db = SessionLocal()
try:
    print("=== 1. sync 内置源 ===")
    print("  新增源:", sync_builtin_sources(db))
    orow = db.query(FeedSource).filter(FeedSource.kind == "openrouter").first()
    print("  openrouter 源:", orow.id if orow else None, orow.name if orow else "")

    print("\n=== 2. 增量挂载到账号 ===")
    added = mount_new_builtin_sources(db)
    print("  新增连接线:", added)
    conn = sqlite3.connect(COPY)
    for r in conn.execute(
        "select u.name, fs.name from media_source_links l "
        "join media_accounts ma on ma.id=l.account_id join users u on u.id=ma.user_id "
        "join feed_sources fs on fs.id=l.feed_source_id where fs.kind='openrouter'"
    ):
        print("   ", r)
    conn.close()
finally:
    db.close()

print("\n=== 3. 真实抓取一轮（只看 rankings 分类）===")
stats = ingest_all(only="rankings")
print("  ", stats)

conn = sqlite3.connect(COPY)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "select count(*) n from external_feed_items where source_type='rankings'"
).fetchone()
print("  库内 rankings 条目:", rows["n"])
for r in conn.execute(
    "select title, summary from external_feed_items where source_type='rankings' order by id desc limit 3"
):
    print(f"   - {r['title'][:52]}")
    print(f"     {(r['summary'] or '')[:130]}")
conn.close()

print("\n=== 4. 跑一轮发帖 ===")
from app.services.media_account_service import relay_new_items  # noqa: E402

db = SessionLocal()
try:
    before = db.execute(__import__("sqlalchemy").text("select coalesce(max(id),0) from media_posts")).scalar()
    res = relay_new_items(db)
    print("  relay:", res)
    rows = db.execute(
        __import__("sqlalchemy").text(
            "select u.name acc, p.title, p.content from media_posts mp "
            "join community_posts p on p.id=mp.post_id join users u on u.id=mp.account_user_id "
            "where mp.id > :m order by mp.id"
        ),
        {"m": before},
    ).fetchall()
    print(f"  新增 {len(rows)} 条：")
    for r in rows:
        print(f"   [{r.acc}] {r.title[:60]}")
        print(f"      {(r.content or '').replace(chr(10), ' / ')[:180]}")
finally:
    db.close()
