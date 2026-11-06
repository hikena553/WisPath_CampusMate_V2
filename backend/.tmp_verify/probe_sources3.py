"""探测国内可达的权威榜单源 + 新华网详情页摘要。"""
import sqlite3
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

RANK_SITES = [
    ("SuperCLUE", "https://www.superclueai.com/"),
    ("FlagEval 智源", "https://flageval.baai.ac.cn/"),
    ("OpenCompass 榜单", "https://rank.opencompass.org.cn/"),
    ("中文大模型评测", "https://cevalbenchmark.com/"),
    ("OpenRouter 模型", "https://openrouter.ai/api/v1/models"),
]

for name, url in RANK_SITES:
    try:
        r = httpx.get(url, headers=UA, timeout=15, follow_redirects=True)
        print(f"[{name}] {r.status_code} len={len(r.content)}")
    except Exception as exc:  # noqa: BLE001
        print(f"[{name}] 失败 {type(exc).__name__}: {exc}")

print("\n=== 新华网/政府网真实详情页 ===")
conn = sqlite3.connect(BACKEND / "campus_mate.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "select title, link, feed_key from external_feed_items where source_type='news' "
    "and feed_key in ('www_news_cn_15','www_gov_cn_16') order by id desc limit 4"
).fetchall()
conn.close()

for r in rows:
    try:
        resp = httpx.get(r["link"], headers=UA, timeout=15, follow_redirects=True)
        resp.encoding = resp.encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        desc = None
        for sel in ('meta[name="description"]', 'meta[property="og:description"]'):
            el = soup.select_one(sel)
            if el and el.get("content"):
                desc = " ".join(el["content"].split())
                break
        print(f"\n{r['feed_key']} | {r['title'][:50]}")
        print(f"   {r['link'][:90]}  -> {resp.status_code}")
        print(f"   desc: {(desc or '<无>')[:150]}")
    except Exception as exc:  # noqa: BLE001
        print(f"\n{r['title'][:40]} 失败 {type(exc).__name__}: {exc}")
