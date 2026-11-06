"""给「视频报道且没有文字稿」的历史转发帖补一句正文说明。

只处理正文除「来源/原文链接」外没有任何内容的视频帖 —— 这些帖子的正文
是空壳（视频页没有 meta description，抓也抓不到）。
用法：python patch_video_posts.py [--apply]
"""
import sqlite3
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.feed_ingest import is_video_url  # noqa: E402

DB = BACKEND / "campus_mate.db"
APPLY = "--apply" in sys.argv
NOTE = "本条为视频报道，暂无文字摘要。"

conn = sqlite3.connect(DB, timeout=15)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    select p.id pid, p.title, p.content, f.link
    from media_posts mp
    join community_posts p on p.id = mp.post_id
    left join external_feed_items f on f.id = mp.feed_item_id
    where mp.kind = 'relay'
    """
).fetchall()

targets = []
for r in rows:
    body = r["content"] or ""
    lines = [ln for ln in body.split("\n") if ln.strip()]
    if [ln for ln in lines if not ln.startswith(("来源：", "原文链接："))]:
        continue
    if NOTE in body:
        continue
    if not is_video_url(r["link"] or ""):
        continue
    targets.append(r)

print(f"待补说明的视频帖 {len(targets)} 条")
for r in targets:
    print(f"  pid={r['pid']} {r['title'][:40]}")

if not APPLY:
    print("（未写库；加 --apply 执行）")
    sys.exit(0)

with conn:
    for r in targets:
        lines = [ln for ln in (r["content"] or "").split("\n") if ln.strip()]
        source_lines = [ln for ln in lines if ln.startswith(("来源：", "原文链接："))]
        conn.execute(
            "update community_posts set content=? where id=?",
            ("\n\n".join([NOTE] + source_lines), r["pid"]),
        )
print(f"已更新 {len(targets)} 条")
