"""验证：详情页摘要提取 + OpenRouter 榜单源产出。"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.core.database import SessionLocal  # noqa: E402
from app.models.feed import FeedSource  # noqa: E402
from app.services.feed_ingest import (  # noqa: E402
    _fetch_article_summary, _fetch_one, _parse_news_page,
)

print("=== 1. 详情页摘要（央视网真实链接）===")
URLS = [
    "https://news.cctv.com/2026/11/06/ARTI0bnGcdLiQ5MBkErTzVYW261106.shtml",
    "https://news.cctv.com/2026/11/06/ARTIem49sSFGT6kpYEAnA2vc261106.shtml",
]
for u in URLS:
    s = _fetch_article_summary(u)
    print(f"  {u[-40:]} -> {s[:110] if s else '<None>'}")

db = SessionLocal()
try:
    print("\n=== 2. 央视网列表页抓取（标题 + 补摘要）===")
    src = db.query(FeedSource).filter(FeedSource.feed_key == "news_cctv_com_17").first()
    raw = _parse_news_page(
        __import__("httpx").get(src.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20,
                                follow_redirects=True).text,
        src.url, limit=6,
    )
    for it in raw[:4]:
        print("  原始:", it["title"][:60])

    print("\n=== 3. OpenRouter 榜单源 ===")
    orow = db.query(FeedSource).filter(FeedSource.kind == "openrouter").first()
    if not orow:
        print("  DB 里还没有 openrouter 源（重启后由 sync_builtin_sources 创建）")
    else:
        items = _fetch_one(db, orow)
        print(f"  抓到 {len(items)} 条，feed_key={items[0]['feed_key'] if items else '-'}")
        for it in items[:4]:
            print(f"   - {it['title'][:60]}")
            print(f"     摘要: {(it.get('summary') or '')[:120]}")
finally:
    db.close()
