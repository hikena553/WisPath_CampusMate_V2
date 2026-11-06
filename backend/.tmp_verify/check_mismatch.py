import sqlite3

c = sqlite3.connect("campus_mate.db")
c.row_factory = sqlite3.Row

print("=== pid=10 对应的资讯条目 ===")
for r in c.execute("select id,feed_item_id from media_posts where post_id=10"):
    print("feed_item_id =", r["feed_item_id"])
    it = c.execute("select * from external_feed_items where id=?", (r["feed_item_id"],)).fetchone()
    if it:
        d = dict(it)
        print("  title  :", d["title"])
        print("  summary:", d["summary"])
        print("  link   :", d["link"])
        print("  author :", d["author"])
        print("  meta   :", d["meta"])

print()
print("=== 该源的现存条目：title vs summary 抽样 ===")
q = """
select id, title, summary, link from external_feed_items
where source_type='agents' order by id desc limit 6
"""
for r in c.execute(q):
    print(f"\nid={r['id']}")
    print("  title  :", r["title"])
    print("  summary:", (r["summary"] or "")[:160])
    print("  link   :", r["link"])
