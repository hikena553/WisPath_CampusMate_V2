"""端到端验证：论文速递「静默停更」是否已恢复。

做法：在数据库副本里塞两条「刚刚入库」的论文条目（feed_key 用真实资讯源的
export_arxiv_org_1），再跑一轮转发周期，看绵小城论文速递是否真的发出帖子。

顺带验证标题去重：两条标题相同、来源不同，只应发出 1 条。

用法：python verify_relay_fix.py
"""
import asyncio
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
MAIN_DB = BACKEND / "campus_mate.db"
COPY_DB = HERE / "verify.db"

sys.path.insert(0, str(BACKEND))
shutil.copyfile(MAIN_DB, COPY_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{COPY_DB.as_posix()}"

from app.core.database import SessionLocal  # noqa: E402
from app.models.feed import ExternalFeedItem  # noqa: E402
from app.services.media_account_service import relay_new_items  # noqa: E402

now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

conn = sqlite3.connect(COPY_DB)
max_post = conn.execute("select coalesce(max(id),0) from media_posts").fetchone()[0]
conn.close()

db = SessionLocal()
try:
    db.add_all([
        ExternalFeedItem(
            source_type="papers", feed_key="export_arxiv_org_1",
            title="[验证] Agentic Memory for Long-Horizon Campus Assistant",
            summary="We present a memory layer that keeps a campus assistant coherent "
                    "across multi-week interactions&#8230; and cuts&#160;latency.",
            link="https://arxiv.org/abs/2611.00001",
            author="Test Author", source_name="arXiv AI 论文", meta={},
            published_at=now_naive, created_at=now_naive,
        ),
        # 同标题、不同源：应被标题去重挡掉
        ExternalFeedItem(
            source_type="papers", feed_key="export_arxiv_org_1",
            title="[验证] Agentic Memory for Long-Horizon Campus Assistant",
            summary="转载版摘要，不应单独成帖。",
            link="https://arxiv.org/abs/2611.00002",
            author="Test Author", source_name="arXiv AI 论文", meta={},
            published_at=now_naive, created_at=now_naive,
        ),
    ])
    db.commit()
    print("已插入 2 条 paper 候选（同标题）")

    result = relay_new_items(db)
    print("relay 结果:", result)

    rows = db.execute(
        __import__("sqlalchemy").text(
            """
            select mp.id, u.name acc, p.title, p.content
            from media_posts mp
            join community_posts p on p.id = mp.post_id
            join users u on u.id = mp.account_user_id
            where mp.id > :m order by mp.id
            """
        ),
        {"m": max_post},
    ).fetchall()

    print(f"\n新增 {len(rows)} 条：")
    for r in rows:
        print(f"\n[{r.acc}] {r.title[:80]}")
        print("  正文:", (r.content or "").replace("\n", " / ")[:240])
finally:
    db.close()
