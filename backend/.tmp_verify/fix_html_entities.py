"""一次性修补：把资讯摘要 / 资讯帖正文里残留的 HTML 实体解码。

背景：feed_ingest._clean_summary 早期只去标签没解实体，MIT Tech Review 等源的
description 带着 `&#8230;`（省略号）、`&#8217;`（右单引号），入库后直接进了帖子正文。

用法：
    python fix_html_entities.py          # 只报告，不写库
    python fix_html_entities.py --apply  # 实际写库
"""
import re
import sqlite3
import sys
from html import unescape

DB = "campus_mate.db"
APPLY = "--apply" in sys.argv

ENT_RE = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")


def decode(text: str) -> str:
    for _ in range(2):
        prev = text
        text = unescape(text)
        if text == prev:
            break
    return text


def main() -> None:
    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row

    print("== external_feed_items.summary ==")
    rows = conn.execute(
        "select id, summary from external_feed_items where summary like '%&%'"
    ).fetchall()
    feed_hits = []
    for r in rows:
        s = r["summary"] or ""
        if not ENT_RE.search(s):
            continue
        new = decode(s)
        if new != s:
            feed_hits.append((r["id"], s, new))
    print(f"命中 {len(feed_hits)} 条")
    for i, old, new in feed_hits[:5]:
        print(f"  id={i}\n    旧: …{old[-70:]}\n    新: …{new[-70:]}")

    print()
    print("== community_posts.content（category=资讯）==")
    rows = conn.execute(
        "select id, content from community_posts where category='资讯' and content like '%&%'"
    ).fetchall()
    post_hits = []
    for r in rows:
        s = r["content"] or ""
        if not ENT_RE.search(s):
            continue
        new = decode(s)
        if new != s:
            post_hits.append((r["id"], s, new))
    print(f"命中 {len(post_hits)} 条")
    for i, old, new in post_hits:
        print(f"  pid={i}  {len(old)} -> {len(new)} 字符")

    if not APPLY:
        print("\n（未写库；加 --apply 执行）")
        return

    with conn:
        for i, _, new in feed_hits:
            conn.execute("update external_feed_items set summary=? where id=?", (new, i))
        for i, _, new in post_hits:
            conn.execute("update community_posts set content=? where id=?", (new, i))
    print(f"\n已写库：feed_items {len(feed_hits)} 条，posts {len(post_hits)} 条")


if __name__ == "__main__":
    main()
