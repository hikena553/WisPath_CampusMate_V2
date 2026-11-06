"""探测可用性：LMArena 替代榜单源 + 时政详情页摘要可提取性。"""
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

CANDIDATES = [
    ("LMArena 页面", "https://lmarena.ai/leaderboard"),
    ("HF 模型趋势", "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=5"),
    ("HF 模型下载榜", "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=5"),
    ("OpenRouter 模型", "https://openrouter.ai/api/v1/models"),
    ("HF 空间", "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=3"),
]

for name, url in CANDIDATES:
    try:
        r = httpx.get(url, headers=UA, timeout=12, follow_redirects=True)
        print(f"[{name}] {r.status_code} len={len(r.content)}")
        if r.status_code == 200:
            print("   前 160 字符:", r.text[:160].replace("\n", " "))
    except Exception as exc:  # noqa: BLE001
        print(f"[{name}] 失败 {type(exc).__name__}: {exc}")

print("\n=== 时政详情页摘要 ===")
ARTICLES = [
    "https://news.cctv.com/2026/11/06/ARTI0bnGcdLiQ5MBkErTzVYW261106.shtml",
    "https://www.news.cn/politics/20261106/index.htm",
]
for url in ARTICLES:
    try:
        r = httpx.get(url, headers=UA, timeout=12, follow_redirects=True)
        r.encoding = r.encoding or "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        desc = None
        for sel in ('meta[name="description"]', 'meta[property="og:description"]'):
            el = soup.select_one(sel)
            if el and el.get("content"):
                desc = el["content"].strip()
                break
        print(f"\n{url}  {r.status_code} len={len(r.text)}")
        print("   meta description:", (desc or "<无>")[:160])
        ps = [" ".join(p.get_text().split()) for p in soup.find_all("p")]
        ps = [p for p in ps if len(p) >= 30]
        print("   段落数:", len(ps))
        for p in ps[:2]:
            print("   p:", p[:140])
    except Exception as exc:  # noqa: BLE001
        print(f"{url} 失败 {type(exc).__name__}: {exc}")
