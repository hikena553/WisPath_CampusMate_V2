"""外部资讯抓取服务：AI 论文 / 开源项目榜 / 智能体榜 / 权威官方要闻
策略：RSS/Atom 或官方 API（arXiv、GitHub、Gitee）+ 权威官方站点首页 HTML 解析（时政要闻）。
每个来源独立 try/except 容错，单个失败不阻塞整体；按 URL 去重入库，并做条数裁剪。
"""
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.feed import ExternalFeedItem, FeedSource

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TIMEOUT = 15

# 每类每来源最多保留条数
PER_SOURCE_LIMIT = {"papers": 200, "opensource": 60, "agents": 60, "news": 120,
                    "ai_news": 60, "rankings": 60, "cn_ai": 60}

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
FEED_UPDATED_KEYS = ("updated_at", "pushed_at", "updated")

# ==================== 底层 HTTP ====================

def _get(url: str, params: dict | None = None, headers: dict | None = None) -> httpx.Response:
    h = {
        "User-Agent": UA,
        "Accept": "application/json,text/xml,application/xml,text/html,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }
    if headers:
        h.update(headers)
    resp = httpx.get(url, params=params, headers=h, timeout=TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    return resp


# ==================== arXiv 论文 ====================

def _parse_arxiv_datetime(s: str) -> datetime | None:
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def fetch_arxiv(max_results: int = 20, search_query: str | None = None) -> list[dict]:
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": search_query or "cat:cs.AI OR cat:cs.LG OR cat:cs.CL",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    resp = _get(url, params)
    root = ET.fromstring(resp.content)
    out = []
    for entry in root.findall(ATOM_NS + "entry"):
        title = " ".join((entry.findtext(ATOM_NS + "title") or "").split())
        if not title:
            continue
        aid = entry.findtext(ARXIV_NS + "id") or ""
        link = entry.findtext(ATOM_NS + "id") or f"https://arxiv.org/abs/{aid}"
        summary = " ".join((entry.findtext(ATOM_NS + "summary") or "").split())[:400]
        authors = [a.findtext(ATOM_NS + "name") for a in entry.findall(ATOM_NS + "author")]
        pub = _parse_arxiv_datetime(entry.findtext(ATOM_NS + "published"))
        out.append({
            "source_type": "papers",
            "feed_key": "arxiv",
            "title": title,
            "summary": summary,
            "link": link,
            "author": (authors[0] if authors else None),
            "source_name": "arXiv AI",
            "meta": {"arxivid": aid, "authors": authors[:3]},
            "published_at": pub,
        })
    return out


# ==================== GitHub / Gitee ====================

def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    token = settings.GITHUB_TOKEN
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _repo_to_item(item: dict, source_type: str, feed_key: str, source_name: str) -> dict:
    desc = (item.get("description") or "").strip()
    return {
        "source_type": source_type,
        "feed_key": feed_key,
        "title": item.get("full_name") or item.get("name") or item.get("full_path") or "",
        "summary": desc[:400] if desc else None,
        "link": item.get("html_url") or item.get("url") or "",
        "author": item.get("full_name") or item.get("namespace") or None,
        "source_name": source_name,
        "meta": {
            "stars": item.get("stargazers_count"),
            "forks": item.get("forks_count"),
            "language": item.get("language"),
            "open_issues": item.get("open_issues_count"),
            "owner": item.get("owner", {}).get("login") if isinstance(item.get("owner"), dict) else None,
        },
        "published_at": None,
    }


def fetch_github() -> list[dict]:
    base = "https://api.github.com/search/repositories"
    out: list[dict] = []
    plans = [
        # (query, source_type, feed_key, source_name)
        ("topic:ai-agent sort:stars", "agents", "github-agents", "GitHub 智能体榜"),
        ("AI topic:ai sort:stars", "opensource", "github-stars", "GitHub 最热"),
        ("AI topic:machine-learning sort:updated", "opensource", "github-active", "GitHub 最活跃"),
    ]
    for q, stype, fkey, sname in plans:
        try:
            resp = _get(base, {"q": q, "sort": "stars", "order": "desc", "per_page": 20}, headers=_gh_headers())
            data = resp.json()
            for it in data.get("items", [])[:20]:
                out.append(_repo_to_item(it, stype, fkey, sname))
        except Exception:
            logger.warning("GitHub 抓取失败(%s): %s", q, "详见日志", exc_info=True)
        # 慢速限流友好
    return out


def fetch_gitee() -> list[dict]:
    token = settings.GITEE_TOKEN
    # Gitee 官方搜索接口无 token 时匿名访问返回空，需配置 GITEE_TOKEN 才能抓取
    if not token:
        logger.info("未配置 GITEE_TOKEN，跳过 Gitee 榜单抓取")
        return []
    params = {"q": "AI agent", "sort": "stars_count", "order": "desc", "per_page": 20,
              "access_token": token}
    out = []
    try:
        resp = _get("https://gitee.com/api/v5/search/repositories", params)
        for it in resp.json()[:20]:
            out.append(_repo_to_item(it, "agents", "gitee-agents", "Gitee 智能体榜"))
    except Exception:
        logger.warning("Gitee 抓取失败", exc_info=True)
    return out


# ==================== 权威官方要闻（HTML 解析） ====================

# 弱相关导航片段，用于过滤非新闻链接
_BAD_LINK_PARTS = ("javascript", "login", "register", "search", "sitemap", "rss", "video", "photo",
                   "special/", ".css", ".js", "down/", "apps/", "about", "contact", "help")

_BAD_TITLE_PARTS = ("skip to", "menu", "sign in", "log in", "search", "download the app",
                    "联系我们", "登录", "注册")
_TITLE_DATE_RE = re.compile(r"(20\d{2})\s*[年/.-]\s*(\d{1,2})\s*[月/. -]?\s*(\d{1,2})")


def _abs_link(href: str, base_url: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith("//"):
        return "https:" + href
    if href.startswith(("http://", "https://")):
        return href
    if href.startswith("/"):
        from urllib.parse import urljoin
        return urljoin(base_url, href)
    return None


def _parse_news_page(html: str, base_url: str, limit: int = 18) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    out: list[dict] = []
    for a in soup.find_all("a", href=True):
        url = _abs_link(a["href"], base_url)
        if not url:
            continue
        title = " ".join(a.get_text().split())
        if len(title) < 8:
            continue
        if any(b in url.lower() for b in _BAD_LINK_PARTS):
            continue
        if any(b in title.lower() for b in _BAD_TITLE_PARTS):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({"title": title, "link": url})
        if len(out) >= limit:
            break
    return out


def fetch_news():
    """已迁移为 DB 驱动源（kind=html），此占位保留导入兼容"""


def _parse_title_date(title: str) -> datetime | None:
    """从标题中的日期文本（如 2026年9月10日 / 2026-07-16）解析出 naive datetime，用于排序"""
    m = _TITLE_DATE_RE.search(title or "")
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def fetch_cn_ai():
    """已迁移为 DB 驱动源（kind=html），此占位保留导入兼容"""


# ==================== AI 行业 RSS 订阅 ====================

ATOM2 = "{http://www.w3.org/2005/Atom}"


def _parse_rss_feed(xml_text: str) -> list[dict]:
    """通用解析 RSS 2.0 与 Atom 订阅，返回 [{title, link, summary, published_at}]"""
    root = ET.fromstring(xml_text)
    entries = [(("rss", it)) for it in root.findall(".//item")]
    if not entries:
        entries = [(("atom", e)) for e in root.findall(f"{ATOM2}entry")]

    out = []
    for kind, it in entries:
        if kind == "atom":
            title = _strip(it.findtext(f"{ATOM2}title"))
            link = it.findtext(f"{ATOM2}link")
            if link and (link.startswith("http") is False):
                for el in it.findall(f"{ATOM2}link"):
                    href = el.get("href")
                    if href and href.startswith("http"):
                        link = href
                        break
            summary = _strip(it.findtext(f"{ATOM2}summary")) or _strip(it.findtext(f"{ATOM2}content"))
            pub = _strip(it.findtext(f"{ATOM2}published")) or _strip(it.findtext(f"{ATOM2}updated"))
            pubdt = _parse_arxiv_datetime(pub)
        else:
            title = _strip(it.findtext("title"))
            link = _strip(it.findtext("link"))
            summary = _strip(it.findtext("description")) or _strip(it.findtext("encoded"))
            pub = _strip(it.findtext("pubDate")) or _strip(it.findtext("date"))
            pubdt = None
            if pub:
                try:
                    pubdt = parsedate_to_datetime(pub).replace(tzinfo=None)
                except Exception:
                    pubdt = _parse_arxiv_datetime(pub)
        if not title or not link:
            continue
        out.append({"title": title, "link": link, "summary": summary[:400] if summary else None,
                    "published_at": pubdt})
    return out


def _strip(s: str | None) -> str | None:
    return " ".join(s.split()) if s else None


def fetch_ai_news():
    """已迁移为 DB 驱动源（kind=rss），此占位保留导入兼容"""


# ==================== 权威排行榜（LMArena Chatbot Arena） ====================

LMArena_LEADERBOARD = "https://storage.googleapis.com/chatbot-arena-leaderboard/leaderboard.json"


def fetch_rankings(limit: int = 30) -> list[dict]:
    """动态抓取业界权威的 LMArena Chatbot Arena 模型能力竞技榜（按得分排序）"""
    try:
        data = _get(LMArena_LEADERBOARD).json()
    except Exception:
        logger.warning("LMArena 权威排行榜暂不可达（当前网络受限，联网环境自动生效）")
        return []
    rows = list(data.get("rankings") or data.get("leaderboard") or data.get("models") or [])
    parsed: list[dict] = []
    for r in rows:
        name = str(r.get("model") or r.get("name") or r.get("id") or "").strip()
        if not name:
            continue
        org = str(r.get("organization") or r.get("org") or r.get("vendor") or "").strip()
        score = r.get("styleControlElo_score") or r.get("elo_score") or r.get("score") or r.get("elo")
        votes = r.get("vote_count") or r.get("num_battles") or r.get("votes")
        try:
            score = float(score) if score is not None else None
        except Exception:
            score = None
        parsed.append({"name": name, "org": org, "score": score, "votes": votes})

    def _key(x) -> float:
        return x["score"] if x["score"] is not None else -1.0

    parsed.sort(key=_key, reverse=True)
    if not parsed:
        logger.warning("LMArena 排行榜数据为空或结构已变化")
        return []
    out = []
    for i, row in enumerate(parsed[:limit], 1):
        org_txt = f"{row['org']} · " if row["org"] else ""
        out.append({
            "source_type": "rankings",
            "feed_key": "lmarena",
            "title": f"{org_txt}{row['name']}",
            "summary": f"Chatbot Arena Elo: {row['score']}" if row["score"] is not None else None,
            "link": "https://lmarena.ai/leaderboard",
            "author": row["name"],
            "source_name": "LMArena · 权威榜",
            "meta": {"rank": i, "score": row["score"], "votes": row["votes"], "org": row["org"]},
            "published_at": None,
        })
    return out


# ==================== 入库 ====================

def _to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def upsert_feeds(db: Session, items: list[dict]) -> int:
    """按 link 去重入库（先预查 DB 中已存在的 URL + 批次内去重，避免同批同一 URL 触发唯一键冲突）；返回新增条数"""
    clean: list[dict] = []
    for it in items:
        link = (it.get("link") or "").strip()
        if link and (it.get("title") or "").strip():
            clean.append(it)

    links = [it["link"].strip() for it in clean]
    if not links:
        return 0
    existing = {
        row.link: row
        for row in db.query(ExternalFeedItem).filter(ExternalFeedItem.link.in_(links)).all()
    }

    inserted = 0
    seen: set[str] = set()
    for it in clean:
        link = it["link"].strip()
        if link in seen:
            continue  # 批次内重复，交给第一次出现的处理
        seen.add(link)
        row = existing.get(link)
        if row:
            # 轻量更新标题/摘要/指标变化
            row.title = it["title"][:500]
            if it.get("summary"):
                row.summary = it["summary"][:2000]
            row.meta = it.get("meta") or {}
            row.source_name = it.get("source_name") or row.source_name
            continue
        db.add(ExternalFeedItem(
            source_type=it["source_type"],
            feed_key=it["feed_key"],
            title=it["title"][:500],
            summary=(it.get("summary") or "")[:2000] or None,
            link=link[:700],
            author=(it.get("author") or "")[:200] or None,
            source_name=(it.get("source_name") or "")[:100] or None,
            meta=it.get("meta") or {},
            published_at=_to_naive(it.get("published_at")),
        ))
        inserted += 1
    try:
        db.commit()
    except Exception:
        db.rollback()
        db.commit()
    return inserted


def _trim(db: Session) -> None:
    """每类每来源仅保留最新 N 条，控制表体积"""
    for stype, limit in PER_SOURCE_LIMIT.items():
        keys = [k for (k,) in db.query(ExternalFeedItem.feed_key)
                .filter(ExternalFeedItem.source_type == stype).distinct().all()]
        for key in keys:
            ids = [i for (i,) in db.query(ExternalFeedItem.id)
                   .filter(ExternalFeedItem.source_type == stype,
                           ExternalFeedItem.feed_key == key)
                   .order_by(ExternalFeedItem.created_at.desc(), ExternalFeedItem.id.desc())
                   .limit(limit).all()]
            if not ids:
                continue
            keep = set(ids)
            stale = db.query(ExternalFeedItem).filter(
                ExternalFeedItem.source_type == stype,
                ExternalFeedItem.feed_key == key,
            ).filter(~ExternalFeedItem.id.in_(keep)).all()
            for s in stale:
                db.delete(s)
    db.commit()


def _feed_key_for_url(db: Session, source: FeedSource) -> str:
    """获取该源的稳定去重标识：优先自带 feed_key，否则按域名自动生成并回写"""
    if source.feed_key:
        return source.feed_key
    from urllib.parse import urlparse
    host = (urlparse(source.url).hostname or "source").replace(".", "_")
    key = f"{host}_{source.id}"
    source.feed_key = key
    db.commit()
    return key


# ==================== 内置预设源 ====================

_BUILTIN_SOURCES: list[dict] = [
    # 论文
    {"name": "arXiv AI 论文", "kind": "arxiv", "source_type": "papers",
     "url": "https://export.arxiv.org/api/query", "per_page": 20,
     "query": "cat:cs.AI OR cat:cs.LG OR cat:cs.CL", "sortBy": "submittedDate"},
    # AI 行业 RSS
    {"name": "OpenAI 官方", "kind": "rss", "source_type": "ai_news",
     "url": "https://openai.com/news/rss.xml", "per_page": 12},
    {"name": "Google AI Blog", "kind": "rss", "source_type": "ai_news",
     "url": "https://blog.google/technology/ai/rss/", "per_page": 12},
    {"name": "DeepMind 官方", "kind": "rss", "source_type": "ai_news",
     "url": "https://deepmind.google/blog/rss.xml", "per_page": 12},
    {"name": "MIT Technology Review", "kind": "rss", "source_type": "ai_news",
     "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "per_page": 12},
    # 国产模型 HTML
    {"name": "DeepSeek 官方", "kind": "html", "source_type": "cn_ai",
     "url": "https://www.deepseek.com/news", "base_url": "https://www.deepseek.com/", "per_page": 10},
    {"name": "豆包(火山引擎)", "kind": "html", "source_type": "cn_ai",
     "url": "https://www.volcengine.com/", "base_url": "https://www.volcengine.com/", "per_page": 10,
     "filter_kw": ["豆包", "Doubao", "大模型", "AI", "智能", "Agent"]},
    {"name": "通义(阿里)", "kind": "html", "source_type": "cn_ai",
     "url": "https://tongyi.aliyun.com/", "base_url": "https://tongyi.aliyun.com/", "per_page": 10,
     "filter_kw": ["Qwen", "Wan", "通义", "上架百炼", "发布", "模型"]},
    {"name": "Kimi(月之暗面)", "kind": "html", "source_type": "cn_ai",
     "url": "https://www.moonshot.cn/", "base_url": "https://www.moonshot.cn/", "per_page": 10, "date_only": True},
    {"name": "MiniMax", "kind": "html", "source_type": "cn_ai",
     "url": "https://www.minimaxi.com/", "base_url": "https://www.minimaxi.com/", "per_page": 10,
     "filter_kw": ["MiniMax", "模型", "M3", "M2", "Speech", "Music", "Code", "Design", "H3"]},
    # 开源 / 智能体榜
    {"name": "GitHub 智能体榜", "kind": "github", "source_type": "agents",
     "url": "https://api.github.com/search/repositories", "query": "topic:ai-agent sort:stars", "per_page": 20},
    {"name": "GitHub 最热", "kind": "github", "source_type": "opensource",
     "url": "https://api.github.com/search/repositories", "query": "AI topic:ai sort:stars", "per_page": 20},
    {"name": "GitHub 最活跃", "kind": "github", "source_type": "opensource",
     "url": "https://api.github.com/search/repositories", "query": "AI topic:machine-learning sort:updated", "per_page": 20},
    {"name": "Gitee 智能体榜", "kind": "gitee", "source_type": "agents",
     "url": "https://gitee.com/api/v5/search/repositories", "query": "AI agent", "per_page": 20},
    # 权威要闻
    {"name": "新华网 · 时政", "kind": "html", "source_type": "news",
     "url": "https://www.news.cn/politics/index.htm", "per_page": 18},
    {"name": "中国政府网 · 要闻", "kind": "html", "source_type": "news",
     "url": "https://www.gov.cn/yaowen/liebiao/", "per_page": 18},
    {"name": "央视网 · 要闻", "kind": "html", "source_type": "news",
     "url": "https://news.cctv.com/", "per_page": 18},
    # 权威排行
    {"name": "LMArena Chatbot Arena", "kind": "lmarena", "source_type": "rankings",
     "url": "https://storage.googleapis.com/chatbot-arena-leaderboard/leaderboard.json", "per_page": 30},
]


def sync_builtin_sources(db: Session) -> int:
    """把内置预设源同步进 feed_sources（按 kind+url 幂等），返回新增数"""
    created = 0
    for b in _BUILTIN_SOURCES:
        exists = (db.query(FeedSource)
                  .filter(FeedSource.kind == b["kind"], FeedSource.url == b["url"])
                  .first())
        if exists:
            continue
        db.add(FeedSource(
            name=b["name"], kind=b["kind"], source_type=b["source_type"],
            url=b["url"], query=b.get("query"), base_url=b.get("base_url"),
            filter_kw=b.get("filter_kw"),
            date_only=bool(b.get("date_only")), per_page=b.get("per_page", 10),
            is_builtin=True, enabled=True, sort_order=0,
        ))
        created += 1
    db.commit()
    return created


# ==================== 单源抓取（按 kind 分派） ====================

def _fetch_one(db: Session, source: FeedSource) -> list[dict]:
    key = _feed_key_for_url(db, source)
    per = source.per_page or 10
    kind = source.kind
    if kind == "arxiv":
        return fetch_arxiv(per, getattr(source, "query", None) or None)
    if kind == "rss":
        resp = _get(source.url)
        cur = []
        for it in _parse_rss_feed(resp.text):
            cur.append({
                "source_type": source.source_type,
                "feed_key": key,
                "title": it["title"],
                "summary": it["summary"],
                "link": it["link"],
                "author": None,
                "source_name": source.name,
                "meta": {},
                "published_at": it["published_at"],
            })
        cur.sort(key=lambda x: x["published_at"] or datetime.min, reverse=True)
        return cur[:per]
    if kind == "html":
        items = _parse_news_page(_get(source.url).text, source.base_url or source.url, limit=per * 3)
        fk = source.filter_kw or {}
        if isinstance(fk, list):
            items = [i for i in items if any(k.lower() in i["title"].lower() for k in fk)]
        if source.date_only:
            items = [i for i in items if _parse_title_date(i["title"])]
        items = sorted(items, key=lambda i: _parse_title_date(i["title"]) or datetime.min, reverse=True)
        return [{
            "source_type": source.source_type,
            "feed_key": key,
            "title": it["title"][:120],
            "summary": None,
            "link": it["link"][:700],
            "author": None,
            "source_name": source.name,
            "meta": {"raw_date": _parse_title_date(it["title"]).strftime("%Y-%m-%d") if _parse_title_date(it["title"]) else None},
            "published_at": _parse_title_date(it["title"]),
        } for it in items[:per]]
    if kind == "github":
        resp = _get(source.url, {"q": source.query, "sort": "stars", "order": "desc", "per_page": per}, headers=_gh_headers())
        return [_repo_to_item(it, source.source_type, key, source.name)
                for it in (resp.json().get("items") or [])[:per]]
    if kind == "gitee":
        token = settings.GITEE_TOKEN
        if not token:
            logger.info("未配置 GITEE_TOKEN，跳过 Gitee 源(%s)", source.name)
            return []
        params = {"q": source.query, "sort": "stars_count", "order": "desc",
                  "per_page": per, "access_token": token}
        resp = _get(source.url, params)
        return [_repo_to_item(it, source.source_type, key, source.name)
                for it in (resp.json() or [])[:per]]
    if kind == "lmarena":
        try:
            data = _get(source.url).json()
        except Exception:
            logger.warning("LMArena 权威排行榜暂不可达（当前网络受限）")
            return []
        rows = list(data.get("rankings") or data.get("leaderboard") or data.get("models") or [])
        parsed: list[dict] = []
        for r in rows:
            name = str(r.get("model") or r.get("name") or r.get("id") or "").strip()
            if not name:
                continue
            org = str(r.get("organization") or r.get("org") or r.get("vendor") or "").strip()
            score = r.get("styleControlElo_score") or r.get("elo_score") or r.get("score") or r.get("elo")
            votes = r.get("vote_count") or r.get("num_battles") or r.get("votes")
            try:
                score = float(score) if score is not None else None
            except Exception:
                score = None
            parsed.append({"name": name, "org": org, "score": score, "votes": votes})
        parsed.sort(key=lambda x: x["score"] if x["score"] is not None else -1.0, reverse=True)
        return [{
            "source_type": "rankings",
            "feed_key": key,
            "title": f"{p['org']} · {p['name']}" if p["org"] else p["name"],
            "summary": f"Chatbot Arena Elo: {p['score']}" if p["score"] is not None else None,
            "link": "https://lmarena.ai/leaderboard",
            "author": p["name"],
            "source_name": source.name,
            "meta": {"rank": i + 1, "score": p["score"], "votes": p["votes"], "org": p["org"]},
            "published_at": None,
        } for i, p in enumerate(parsed[:per])]
    logger.warning("未知源类型: %s", kind)
    return []


def _trim(db: Session) -> None:
    """每类每来源仅保留最新 N 条，控制表体积"""
    for stype, limit in PER_SOURCE_LIMIT.items():
        keys = [k for (k,) in db.query(ExternalFeedItem.feed_key)
                .filter(ExternalFeedItem.source_type == stype).distinct().all()]
        for key in keys:
            ids = [i for (i,) in db.query(ExternalFeedItem.id)
                   .filter(ExternalFeedItem.source_type == stype,
                           ExternalFeedItem.feed_key == key)
                   .order_by(ExternalFeedItem.created_at.desc(), ExternalFeedItem.id.desc())
                   .limit(limit).all()]
            if not ids:
                continue
            keep = set(ids)
            stale = db.query(ExternalFeedItem).filter(
                ExternalFeedItem.source_type == stype,
                ExternalFeedItem.feed_key == key,
            ).filter(~ExternalFeedItem.id.in_(keep)).all()
            for s in stale:
                db.delete(s)
    db.commit()


def ingest_all(only: str | None = None) -> dict:
    """入口：从 feed_sources 读取启用的源，动态抓取并入库。返回统计。
    only 为 source_type 时仅抓该分类。"""
    db = SessionLocal()
    stats = {"inserted": 0, "sources": {}, "errors": []}
    try:
        sync_builtin_sources(db)
        query = db.query(FeedSource).filter(FeedSource.enabled == True).order_by(FeedSource.sort_order, FeedSource.id)
        if only:
            query = query.filter(FeedSource.source_type == only)
        sources = query.all()
        if not sources:
            logger.warning("没有启用的资讯源")
        for src in sources:
            try:
                items = _fetch_one(db, src)
                if not items:
                    continue
                inserted = upsert_feeds(db, items)
                stats["inserted"] += inserted
                stats["sources"][src.name] = {"fetched": len(items), "inserted": inserted}
            except Exception as e:
                logger.warning("来源[%s]失败: %s", src.name, e)
                db.rollback()
                stats["errors"].append(src.name)
        _trim(db)
    finally:
        db.close()
    return stats