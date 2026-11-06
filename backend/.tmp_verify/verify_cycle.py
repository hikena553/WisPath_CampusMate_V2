"""在数据库副本上跑一轮真实发帖周期，验证「论文速递停更」是否已恢复。

不碰线上 campus_mate.db —— 先把主库复制成 .tmp_verify/verify.db 再跑。
用法：python verify_cycle.py
"""
import asyncio
import os
import shutil
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
MAIN_DB = BACKEND / "campus_mate.db"
COPY_DB = HERE / "verify.db"

if not MAIN_DB.exists():
    sys.exit(f"主库不存在：{MAIN_DB}")

sys.path.insert(0, str(BACKEND))

shutil.copyfile(MAIN_DB, COPY_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{COPY_DB.as_posix()}"
os.environ.pop("TESTING", None)

before = sqlite3.connect(COPY_DB)
before.row_factory = sqlite3.Row
max_id = before.execute("select coalesce(max(id),0) from media_posts").fetchone()[0]
before.close()
print(f"跑之前 media_posts 最大 id = {max_id}")

from app.services.media_account_service import run_media_publish_cycle  # noqa: E402

result = asyncio.run(run_media_publish_cycle())
print("周期结果:", result)

conn = sqlite3.connect(COPY_DB)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """
    select mp.id, mp.kind, mp.created_at, u.name acc, p.title, p.content
    from media_posts mp
    join community_posts p on p.id = mp.post_id
    join users u on u.id = mp.account_user_id
    where mp.id > ?
    order by mp.id
    """,
    (max_id,),
).fetchall()

print(f"\n新增 {len(rows)} 条：")
for r in rows:
    body = (r["content"] or "").replace("\n", " / ")
    print(f"\n[{r['acc']}] {r['kind']} {r['created_at'][:19]}")
    print(f"  标题: {r['title'][:90]}")
    print(f"  正文: {body[:200]}")
