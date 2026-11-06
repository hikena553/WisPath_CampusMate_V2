import sqlite3

c = sqlite3.connect("campus_mate.db")
c.row_factory = sqlite3.Row

print("=== 账号 ← 连接线 → 资讯源 ===")
q = """
select ma.id aid, u.name acc, ma.content_scope, l.name link_name, l.enabled,
       fs.name fsname, fs.feed_key, fs.source_type
from media_accounts ma
join users u on u.id = ma.user_id
left join media_source_links l on l.account_id = ma.id
left join feed_sources fs on fs.id = l.feed_source_id
order by ma.id, fs.id
"""
for r in c.execute(q):
    print(
        f"{r['aid']} {r['acc']:<12} scope={str(r['content_scope']):<14} "
        f"link={'有' if r['link_name'] else '无'} en={r['enabled']} "
        f"{str(r['fsname']):<22} {str(r['feed_key']):<32} {r['source_type']}"
    )

print()
print("=== 各 source_type 的资讯条目数 ===")
for r in c.execute("select source_type, count(*) total, max(created_at) last from external_feed_items group by source_type"):
    print(f"{r['source_type']:<10} {r['total']:>5}  最近入库 {r['last']}")

print()
print("=== 未转发的资讯条目数（按类型）===")
q2 = """
select f.source_type, count(*) total,
       sum(case when mp.id is null then 1 else 0 end) unrelayed
from external_feed_items f
left join media_posts mp on mp.feed_item_id = f.id
group by f.source_type
"""
for r in c.execute(q2):
    print(f"{r['source_type']:<10} 总 {r['total']:>5}  未转发 {r['unrelayed']:>5}")
