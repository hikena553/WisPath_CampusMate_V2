"""统计：已发布的资讯转发帖里，正文只有「来源+链接」的有多少。"""
import sqlite3

conn = sqlite3.connect("campus_mate.db")
conn.row_factory = sqlite3.Row

q = """
select mp.id mid, p.id pid, u.name acc, p.title, p.content, f.id fid, f.link, f.summary, f.source_name
from media_posts mp
join community_posts p on p.id = mp.post_id
join users u on u.id = mp.account_user_id
left join external_feed_items f on f.id = mp.feed_item_id
where mp.kind = 'relay'
order by mp.id desc
"""
rows = conn.execute(q).fetchall()

empty = []
for r in rows:
    body = (r["content"] or "").strip()
    # 正文里除了「来源：…」「原文链接：…」没有别的实质内容
    lines = [ln for ln in body.split("\n") if ln.strip()]
    substantive = [ln for ln in lines if not ln.startswith(("来源：", "原文链接："))]
    if not substantive:
        empty.append(r)

print(f"转发帖总数 {len(rows)}，正文无实质内容 {len(empty)} 条\n")
for r in empty:
    print(f"  pid={r['pid']} [{r['acc']}] {r['title'][:44]}")
    print(f"     feed_item={r['fid']} summary={'有' if r['summary'] else '无'}")
conn.close()
