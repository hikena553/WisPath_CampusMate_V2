import sqlite3

c = sqlite3.connect("campus_mate.db")
c.row_factory = sqlite3.Row

q = """
select u.name acc, mp.kind, mp.created_at, p.id pid, p.title, p.content
from media_posts mp
join community_posts p on p.id = mp.post_id
join users u on u.id = mp.account_user_id
order by mp.id desc
"""
rows = c.execute(q).fetchall()

print("=== 各账号最近发帖（relay 最近 6 条 / digest 全部）===")
seen = {}
for r in rows:
    key = r["acc"]
    bucket = seen.setdefault(key, {"relay": 0})
    if r["kind"] == "relay":
        bucket["relay"] += 1
        if bucket["relay"] > 6:
            continue
        tag = f"relay#{bucket['relay']}"
    else:
        tag = "digest"
    print(f"\n[{r['acc']}] {tag} pid={r['pid']} {r['created_at'][:16]}")
    print(f"   标题: {r['title']}")
    body = (r["content"] or "").replace("\n", " ⏎ ")
    print(f"   正文: {body[:260]}")
