"""外部资讯抓取服务：AI 论文 / 开源项目榜 / 智能体榜 / 权威官方要闻
策略：RSS/Atom 或官方 API（arXiv、GitHub、Gitee）+ 权威官方站点首页 HTML 解析（时政要闻）。
每个来源独立 try/except 容错，单个失败不阻塞整体；按 URL 去重入库，并做条数裁剪。
"""
import logging
import ipaddress
import re
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape as _html_unescape
from urllib.parse import urlparse
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

# ==================== 资讯源地址安全校验（防 SSRF） ====================

_PRIVATE_HOST_EXACT = {"localhost"}
_PRIVATE_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".lan")


def _is_private_ip(ip) -> bool:
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


def _is_disallowed_host(host: str) -> bool:
    h = (host or "").strip().strip("[]").lower()
    if not h:
        return True
    if h in _PRIVATE_HOST_EXACT or h.endswith(_PRIVATE_HOST_SUFFIXES):
        return True
    try:
        return _is_private_ip(ipaddress.ip_address(h))
    except ValueError:
        return False  # 域名，交由下一步 DNS 校验


def validate_source_url(url: str) -> None:
    """校验资讯源地址：仅 http/https，且目标不得为本机/内网地址。

    防 SSRF：字面 IP 直接判定；域名在解析成功时判定解析结果，
    解析失败则放行（真正的抓取失败由抓取流程容错处理）。
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("仅支持 http/https 协议的资讯源地址")
    host = parsed.hostname
    if not host:
        raise ValueError("URL 无效，缺少域名")
    if _is_disallowed_host(host):
        raise ValueError("不允许配置本机/内网地址作为资讯源")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if _is_private_ip(ip):
            raise ValueError("不允许配置解析到内网地址的资讯源")


# ==================== 底层 HTTP ====================

def _get(url: str, params: dict | None = None, headers: dict | None = None, retries: int = 1) -> httpx.Response:
    """带一次重试的 GET：境外源常见 TLS 握手中断（SSL: UNEXPECTED_EOF）等瞬时故障。

    DNS 解析不了（如被墙域名）属确定性失败，重试只会白等，直接抛出交给上层记录。
    """
    h = {
        "User-Agent": UA,
        "Accept": "application/json,text/xml,application/xml,text/html,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }
    if headers:
        h.update(headers)
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = httpx.get(url, params=params, headers=h, timeout=TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
            return resp
        except (httpx.TransportError, ssl.SSLError) as e:
            last_exc = e
            if isinstance(getattr(e, "__cause__", None), socket.gaierror) or attempt >= retries:
                raise
            time.sleep(0.5)
    raise last_exc  # pragma: no cover - 循环内必然已 return 或 raise


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


# 列表页里的品类前缀（「动态2026 年 9 月 10 日DeepSeek V4.1 Flash：…」）
_TITLE_PREFIX_RE = re.compile(
    r"^\s*(?:动态|公告|新闻|资讯|头条|要闻|更新|活动|通知|速递|快讯|观点|技术博客)\s*"
)
# 标题开头的日期（「2026 年 9 月 10 日」「2026-09-10」「2026/9/10」）
_TITLE_DATE_PREFIX_RE = re.compile(
    r"^\s*20\d{2}\s*[年/.\-]\s*\d{1,2}\s*[月/.\-]\s*\d{1,2}\s*日?\s*"
)
_TITLE_TRAIL_PUNCT = " ·:：-—|/、,，。;；"


def _clean_title(raw: str) -> str:
    """清洗 HTML 列表页标题。

    DeepSeek 官网的列表项把「动态 + 日期 + 标题 + 副标题」全塞进一个 <a>，
    原始文本是「动态2026 年 9 月 10 日DeepSeek V4.1 Flash：更强、更快、更普惠
    DeepSeek V4.1 Flash 正式发布」，直接当帖子标题很脏。

    处理：剥品类前缀 → 剥日期 → 若开头一段在标题里第二次出现，说明是
    「主标题 + 副标题/重复段落」拼接，截到重复处。
    """
    title = " ".join((raw or "").split())
    for _ in range(3):
        before = title
        title = _TITLE_PREFIX_RE.sub("", title)
        title = _TITLE_DATE_PREFIX_RE.sub("", title)
        if title == before:
            break
    if len(title) < 8:  # 剥没了就还原，宁可脏也别空
        return " ".join((raw or "").split())

    # 重复段落截断：用开头 10 个字符做探针，在后半段找第二次出现
    probe_len = 10
    if len(title) >= probe_len * 2:
        probe = title[:probe_len]
        idx = title.find(probe, probe_len)
        if idx >= 15:
            trimmed = title[:idx].rstrip(_TITLE_TRAIL_PUNCT).strip()
            if len(trimmed) >= 8:
                title = trimmed
    return title


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


# 详情页里当成「摘要」用的 meta 字段（按优先级）
_ARTICLE_META_KEYS = (
    ("meta", {"name": "description"}),
    ("meta", {"property": "og:description"}),
    ("meta", {"name": "twitter:description"}),
)
# 正文段落里明显不是导语的片段
_ARTICLE_JUNK = (
    "版权所有", "ICP备", "责任编辑", "扫一扫", "客户端", "关注我们",
    "Copyright", "All Rights Reserved", "cookie",
)


# 视频页特征：这些页面没有文字稿，抓 meta description 只会白等一次超时
_VIDEO_HOSTS = {
    "tv.cctv.com", "v.cctv.com", "v.qq.com", "b23.tv", "www.bilibili.com",
    "www.youtube.com", "youtu.be", "vimeo.com", "www.douyin.com", "www.ixigua.com",
}
_VIDEO_PATH_HINTS = ("/video/", "/videos/", "/vod/", "/shipin/", "/live/", "/v/")


def is_video_url(url: str) -> bool:
    """判断链接是不是视频页。

    央视网时政源 139 条里有 60 条是 tv.cctv.com 的视频新闻：页面没有文字稿、
    也没有 meta description，抓摘要等于每轮白等 60 次超时，拿回来还是空正文。
    视频类直接不爬。
    """
    try:
        parsed = urlparse(url or "")
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host in _VIDEO_HOSTS or host.startswith(("tv.", "v.")):
        return True
    path = (parsed.path or "").lower()
    return any(hint in path for hint in _VIDEO_PATH_HINTS)


def _fetch_article_summary(url: str) -> str | None:
    """抓新闻详情页取一段导语。

    时政源（央视网/新华网/政府网）的列表页只有标题和链接，没有 description，
    转发帖正文就只剩「来源 + 链接」。详情页的头条 meta description 通常正是
    记者写的第一段导语，拿它当摘要比空着强得多。

    视频页直接返回 None（不请求），失败也一律返回 None：补摘要只是锦上添花，
    不能影响抓取主流程。
    """
    if is_video_url(url):
        return None
    try:
        resp = _get(url, retries=0)
    except Exception:  # noqa: BLE001 - 单篇失败不该影响整轮
        return None
    ctype = (resp.headers.get("content-type") or "").lower()
    if "html" not in ctype and "xml" not in ctype:
        return None
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:  # noqa: BLE001
        return None

    for tag, attrs in _ARTICLE_META_KEYS:
        el = soup.find(tag, attrs=attrs)
        if not el:
            continue
        text = _clean_summary(el.get("content") or "")
        if text and len(text) >= 20:
            return text[:400]

    # 兜底：找正文里第一段像导语的 <p>
    for p in soup.find_all("p"):
        text = _clean_summary(p.get_text(" ", strip=True))
        if not text or len(text) < 40:
            continue
        if any(j.lower() in text.lower() for j in _ARTICLE_JUNK):
            continue
        return text[:400]
    return None


def _summary_echoes_title(title: str, summary: str, slack: int = 8) -> bool:
    """摘要只是把标题又说了一遍（央视网短消息的 meta description 常这样）。

    例：标题「普速旅客列车车次变更自11月25日起实施」
        摘要「普速旅客列车车次变更自11月25日起实施。」
    这种摘要放进正文毫无信息量，还不如留空。
    """
    t = re.sub(r"[\W_]+", "", title or "").lower()
    s = re.sub(r"[\W_]+", "", summary or "").lower()
    if not t or not s:
        return False
    if s == t:
        return True
    return s.startswith(t) and len(s) - len(t) <= slack


def _fill_article_summaries(db: Session, items: list[dict], workers: int = 4) -> None:
    """给列表页条目补详情页摘要（原地写回 item["summary"]）。

    只为「库里还没有摘要」的链接抓详情页：已经在库里的条目下一轮不再重复请求，
    稳定后每轮只会多出几条新链接，成本可以忽略。
    """
    if not items:
        return
    links = [it["link"] for it in items if it.get("link")]
    if not links:
        return
    known: dict[str, str | None] = {
        link: summary
        for link, summary in db.query(ExternalFeedItem.link, ExternalFeedItem.summary)
        .filter(ExternalFeedItem.link.in_(links))
        .all()
    }
    for it in items:
        it["summary"] = known.get(it["link"])
    # 视频页不进线程池：它们没有文字稿，白跑一次还占并发
    pending = [
        it for it in items
        if not it.get("summary") and not is_video_url(it.get("link") or "")
    ]
    if not pending:
        return

    def _one(it: dict) -> str | None:
        return _fetch_article_summary(it["link"])

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_one, pending))
    except Exception:  # noqa: BLE001 - 线程池异常不该拖垮抓取
        logger.warning("详情页摘要抓取失败", exc_info=True)
        return
    for it, summary in zip(pending, results):
        # 只复述标题的摘要不入库，免得转发帖正文跟标题一模一样
        if summary and _summary_echoes_title(it.get("title") or "", summary):
            summary = None
        it["summary"] = summary


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


def _clean_summary(raw: str | None) -> str | None:
    """摘要去标签：部分源（Google AI Blog 等）的 description 是整段 HTML。

    原样入库会让资讯帖正文出现 `<img src="https://storage.googleapis.com/...">`
    这种标签，在社区里看着像乱码。入库前统一转纯文本。

    去标签之后还要解一次 HTML 实体：BeautifulSoup 的 get_text() 不会处理
    `&#8230;` / `&#8217;` 这类数字字符引用，MIT Tech Review 的 description
    就带着它们（帖子正文会出现「I immediately signed&#8230;」）。
    """
    if not raw:
        return None
    text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    # 双重转义（&amp;#8230;）很常见，解两轮；解不动就提前退出
    for _ in range(2):
        prev = text
        text = _html_unescape(text)
        if text == prev:
            break
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


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
            # 轻量更新标题/摘要/指标变化；同步来源归属，避免历史 feed_key 与资讯源漂移
            row.title = it["title"][:500]
            if it.get("summary"):
                cleaned = _clean_summary(it["summary"])
                if cleaned:
                    row.summary = cleaned[:2000]
            row.meta = it.get("meta") or {}
            row.source_name = it.get("source_name") or row.source_name
            row.feed_key = it["feed_key"]
            row.source_type = it["source_type"]
            continue
        db.add(ExternalFeedItem(
            source_type=it["source_type"],
            feed_key=it["feed_key"],
            title=it["title"][:500],
            summary=(_clean_summary(it.get("summary")) or "")[:2000] or None,
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
    # LMArena 走 storage.googleapis.com，受限网络整域不可达；OpenRouter 模型目录
    # 可作为同一账号（content_scope=rankings）的可用数据源，出「长上下文模型榜」。
    {"name": "OpenRouter 模型榜", "kind": "openrouter", "source_type": "rankings",
     "url": "https://openrouter.ai/api/v1/models", "per_page": 20},
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


# 抓取端曾经把 feed_key 写死成这些值（而非 feed_sources.feed_key）
_LEGACY_KIND_KEYS = {"arxiv": "arxiv", "lmarena": "lmarena"}


def backfill_source_feed_keys(db: Session) -> int:
    """把历史条目的 feed_key 对齐到所属资讯源（幂等，启动时跑一次）。

    arXiv / LMArena 抓取早期把 feed_key 写死成 "arxiv" / "lmarena"，与
    feed_sources.feed_key（按域名生成，如 export_arxiv_org_1）不一致；
    而资讯账号的连接线与每日汇总都按后者过滤，于是这批条目既不会被转发、
    也不会进汇总 —— 表现为「论文速递账号突然不再发帖」。抓取端已修，
    这里把库里残留的旧值一并改回。
    """
    fixed = 0
    for source in db.query(FeedSource).filter(FeedSource.kind.in_(list(_LEGACY_KIND_KEYS))).all():
        old = _LEGACY_KIND_KEYS[source.kind]
        if not source.feed_key or source.feed_key == old:
            continue
        fixed += (
            db.query(ExternalFeedItem)
            .filter(
                ExternalFeedItem.feed_key == old,
                ExternalFeedItem.source_type == source.source_type,
            )
            .update({ExternalFeedItem.feed_key: source.feed_key}, synchronize_session=False)
        )
    if fixed:
        db.commit()
        logger.info("历史资讯条目 feed_key 已对齐到资讯源：%d 条", fixed)
    return fixed


# ==================== 单源抓取（按 kind 分派） ====================

def _fetch_one(db: Session, source: FeedSource) -> list[dict]:
    key = _feed_key_for_url(db, source)
    per = source.per_page or 10
    kind = source.kind
    if kind == "arxiv":
        items = fetch_arxiv(per, getattr(source, "query", None) or None)
        # ⚠️ fetch_arxiv 里硬编码 feed_key="arxiv"。资讯账号的画布连接线是按
        # feed_sources.feed_key（按域名生成，如 export_arxiv_org_1）过滤的
        # （见 media_account_service._linked_feed_keys），不在这里覆盖成资讯源的 key，
        # 论文条目就永远不匹配连接线 —— 表现为「论文速递账号一条都收不到/不再发帖」。
        for it in items:
            it["feed_key"] = key
            it["source_type"] = source.source_type or it["source_type"]
            it["source_name"] = source.name
        return items
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
        # 日期解析与排序都用原始标题（日期常写在标题里），清洗放到最后一步
        items = sorted(items, key=lambda i: _parse_title_date(i["title"]) or datetime.min, reverse=True)
        items = items[:per]
        # 列表页没有 description，去详情页补一段导语当摘要
        _fill_article_summaries(db, items)
        return [{
            "source_type": source.source_type,
            "feed_key": key,
            "title": _clean_title(it["title"])[:120],
            "summary": it.get("summary"),
            "link": it["link"][:700],
            "author": None,
            "source_name": source.name,
            "meta": {"raw_date": _parse_title_date(it["title"]).strftime("%Y-%m-%d") if _parse_title_date(it["title"]) else None},
            "published_at": _parse_title_date(it["title"]),
        } for it in items]
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
    if kind == "openrouter":
        # LMArena 的 storage.googleapis.com 在受限网络里整域不可达，
        # 权威榜单账号一个帖子都发不出来。OpenRouter 的模型目录可达且字段完整
        # （上下文窗口 / 输入输出定价 / 上架时间），拿它出一份「长上下文模型榜」。
        resp = _get(source.url)
        rows = list((resp.json() or {}).get("data") or [])
        parsed = []
        for r in rows:
            name = str(r.get("name") or r.get("id") or "").strip()
            ctx = r.get("context_length")
            pricing = r.get("pricing") or {}
            try:
                ctx = int(ctx) if ctx else 0
            except (TypeError, ValueError):
                ctx = 0
            if not name or ctx <= 0:
                continue
            if "auto" in name.lower() and "router" in name.lower():
                continue  # OpenRouter 自己的路由条目，不是模型
            try:
                prompt_price = float(pricing.get("prompt"))
                completion_price = float(pricing.get("completion"))
            except (TypeError, ValueError):
                prompt_price = completion_price = None
            if prompt_price is not None and prompt_price < 0:
                continue  # -1 表示不单独计价（自动路由）
            if completion_price is not None and completion_price < 0:
                completion_price = None
            created = r.get("created")
            published = None
            if created:
                try:
                    published = datetime.fromtimestamp(int(created), tz=timezone.utc).replace(tzinfo=None)
                except (OverflowError, OSError, ValueError):
                    published = None
            desc = _clean_summary(r.get("description") or "") or ""
            parts = []
            if desc:
                parts.append(desc[:180])
            parts.append(f"上下文窗口 {ctx:,} tokens")
            if prompt_price is not None:
                parts.append(f"输入 ${prompt_price * 1_000_000:.2f}/百万 tokens")
            if completion_price is not None:
                parts.append(f"输出 ${completion_price * 1_000_000:.2f}/百万 tokens")
            parsed.append({
                "title": name[:120],
                "summary": " · ".join(parts)[:600],
                "link": f"https://openrouter.ai/{r.get('id') or ''}".rstrip("/"),
                "author": str(r.get("id") or "").split("/")[0] or None,
                "meta": {"context": ctx, "prompt_price": prompt_price,
                         "completion_price": completion_price,
                         "modality": (r.get("architecture") or {}).get("modality")},
                "published_at": published,
            })
        if not parsed:
            logger.warning("OpenRouter 模型目录为空或结构已变化")
            return []
        parsed.sort(key=lambda x: x["meta"]["context"], reverse=True)
        return [{
            "source_type": "rankings",
            "feed_key": key,
            "title": it["title"],
            "summary": it["summary"],
            "link": it["link"],
            "author": it["author"],
            "source_name": source.name,
            "meta": it["meta"],
            "published_at": it["published_at"],
        } for it in parsed[:per]]
    logger.warning("未知源类型: %s", kind)
    return []


def ingest_all(only: str | None = None) -> dict:
    """入口：从 feed_sources 读取启用的源，动态抓取并入库。返回统计。
    only 为 source_type 时仅抓该分类。

    画布连接即抓取范围：只抓取「已接入资讯站且启用」的账号所连接的资讯源；
    若系统尚无任何启用账号，则回落到抓取全部启用源，避免校园资讯空窗。
    """
    db = SessionLocal()
    stats = {"inserted": 0, "sources": {}, "errors": []}
    try:
        sync_builtin_sources(db)
        from app.models.media import MediaAccount
        from app.services.media_account_service import (
            ensure_station_graph, get_station_config, linked_source_ids,
            mount_new_builtin_sources,
        )

        ensure_station_graph(db)
        # 首次初始化之后新增的内置源（如 OpenRouter 模型榜）要补挂到账号，
        # 否则会被下面的 linked 过滤挡掉，账号永远拿不到内容
        mount_new_builtin_sources(db)
        station = get_station_config(db)
        if not station.is_enabled:
            logger.warning("资讯站已停用，跳过本轮抓取")
            return stats
        query = db.query(FeedSource).filter(FeedSource.enabled == True).order_by(FeedSource.sort_order, FeedSource.id)
        if only:
            query = query.filter(FeedSource.source_type == only)
        sources = query.all()
        has_active_account = db.query(MediaAccount.id).filter(
            MediaAccount.is_enabled.is_(True),
            MediaAccount.station_connected.is_(True),
        ).first() is not None
        if has_active_account:
            # 只保留画布上真实连到账号的资讯源
            linked = linked_source_ids(db)
            sources = [s for s in sources if s.id in linked]
        if not sources:
            logger.warning("画布上没有已连接的启用的资讯源，跳过抓取")
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