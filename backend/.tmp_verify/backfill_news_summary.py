"""回填历史转发帖的正文：为 summary 为空的资讯条目抓详情页导语，重写帖子正文。

用法：
    python backfill_news_summary.py           # 只报告
    python backfill_news_summary.py --apply   # 写库
"""
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.feed_ingest import (  # noqa: E402
    _fetch_article_summary, _summary_echoes_title,
)

DB = BACKEND / "campus_mate.db"
APPLY = "--apply" in sys.argv

conn = sqlite3.connect(DB, timeout=15)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    select mp.id mid, p.id pid, p.title, p.content, f.id fid, f.link, f.summary
    from media_posts mp
    join community_posts p on p.id = mp.post_id
    left join external_feed_items f on f.id = mp.feed_item_id
    where mp.kind = 'relay'
    order by mp.id desc
    """
).fetchall()

targets = []
for r in rows:
    lines = [ln for ln in (r["content"] or "").split("\n") if ln.strip()]
    if [ln for ln in lines if not ln.startswith(("来源：", "原文链接："))]:
        continue  # 已有实质内容
    if not r["link"]:
        continue
    targets.append(r)

print(f"待补正文的帖子 {len(targets)} 条，开始抓详情页导语...\n")


def grab(r):
    return r, _fetch_article_summary(r["link"])


with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(grab, targets))

updated = 0
plan = []
for r, summary in results:
    if summary and _summary_echoes_title(r["title"] or "", summary):
        summary = None  # 只是复述标题
    status = "拿到" if summary else "跳过"
    print(f"  pid={r['pid']} [{status}] {r['title'][:40]}")
    if summary:
        print(f"      {summary[:100]}")
    if not summary:
        continue
    source_lines = [ln for ln in (r["content"] or "").split("\n") if ln.startswith(("来源：", "原文链接："))]
    new_content = "\n\n".join([summary] + source_lines)
    plan.append((r["fid"], r["pid"], summary, new_content))
    updated += 1

print(f"\n可补 {updated} 条")
if not APPLY:
    print("（未写库；加 --apply 执行）")
    sys.exit(0)

with conn:
    for fid, pid, summary, content in plan:
        conn.execute("update external_feed_items set summary=? where id=? and (summary is null or summary='')",
                     (summary, fid))
        conn.execute("update community_posts set content=? where id=?", (content, pid))
print(f"已写库：帖子 {updated} 条，资讯条目摘要同步更新")
