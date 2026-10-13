"""校内资讯站内阅读：代理抓取校内页面并提取正文 / 链接清单。

设计背景：
- 学校站点（jwc.mycc.edu.cn 等）统一设置 ``X-Frame-Options: SAMEORIGIN``，无法直接 iframe 内嵌；
- 因此由后端代抓，做域名白名单校验 + 正文净化，再把可读内容回传前端在应用内展示。

对外能力：
- ``is_allowed_url(url)``：白名单校验（仅 ``*.mycc.edu.cn`` 的 http/https 页面）；
- ``fetch_html(url)``：抓取并按页面字符集正确解码（兼容 gb2312/gbk 老站）；
- ``read_url(url)``：解析为 ``article``（正文）或 ``links``（列表页链接清单）两种形态。

错误约定（供 API 层映射 HTTP 状态码）：
- 非白名单 → ``PermissionError``（400）；
- 抓取/解析失败 → ``RuntimeError``（502）。
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

# 允许站内阅读的域名后缀（学校主域及其全部二级域名）
ALLOWED_HOST_SUFFIX = "mycc.edu.cn"

# 正文判定的最小文本长度：低于该值视为「列表页」而非「内容页」
MIN_ARTICLE_CHARS = 180

# 列表页最多返回的链接数，避免刷屏
MAX_LINKS = 80

# 抓取超时与伪装头（部分校园站对空 UA 直接 403）
_TIMEOUT = 12.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 正文容器候选选择器（覆盖常见高校 CMS：vsb/维普、织梦、自研等）
_CONTENT_SELECTORS = [
    "div.v_news_content",
    "div#vsb_content",
    "div#vsb_content_2",
    "div.wp_articlecontent",
    "div.v_news_content_box",
    "div.Article_Content",
    "div.article-content",
    "div.articleContent",
    "div.art_content",
    "div.news_content",
    "div.newscon",
    "div.show_content",
    "div.entry-content",
    "div.main-content",
    "div.content",
    "div#content",
    "div.cont",
    "div.txt",
    "article",
]

# 标题候选选择器
_TITLE_SELECTORS = [
    "meta[property='og:title']",
    "h1",
    "div.article-title",
    "div.news_title",
    "h2.title",
    "div.title",
    "title",
]

# 需要整体移除的噪音标签
_STRIP_TAGS = ("script", "style", "noscript", "iframe", "object", "embed", "form", "svg", "canvas")

_DATE_RE = re.compile(r"(\d{4})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})")


def _host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def is_allowed_url(url: str) -> bool:
    """仅放行校内站点（http/https，主机名为 mycc.edu.cn 或其子域）。"""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    return host == ALLOWED_HOST_SUFFIX or host.endswith("." + ALLOWED_HOST_SUFFIX)


def _decode(raw: bytes, content_type: str) -> str:
    """按 Content-Type 声明解码；缺失声明时依次尝试 utf-8 / gb18030（老站常用 gb2312）。"""
    charset = None
    m = re.search(r"charset=([\w-]+)", content_type or "", re.IGNORECASE)
    if m:
        charset = m.group(1)
    candidates = [charset] if charset else []
    candidates += ["utf-8", "gb18030", "latin-1"]
    for enc in candidates:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_html(url: str) -> tuple[str, str]:
    """抓取页面并解码，返回 ``(最终 URL, HTML 文本)``。"""
    if not is_allowed_url(url):
        raise PermissionError("仅支持校内站点链接")
    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT, headers=_HEADERS) as client:
            resp = client.get(url)
    except httpx.HTTPError as e:  # 网络/超时/TLS
        raise RuntimeError(f"无法访问该页面（{type(e).__name__}）") from e
    if resp.status_code >= 400:
        raise RuntimeError(f"页面返回 {resp.status_code}")
    html = _decode(resp.content, resp.headers.get("content-type", ""))
    return str(resp.url), html


def _text_of(node: Tag) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True) or "")


def _extract_title(soup: BeautifulSoup) -> str:
    for sel in _TITLE_SELECTORS:
        el = soup.select_one(sel)
        if not el:
            continue
        value = el.get("content") if el.name == "meta" else el.get_text(" ", strip=True)
        value = (value or "").strip()
        if value:
            # 去掉站点名后缀，如「xxx - 绵阳城市学院教务处」
            parts = re.split(r"\s*[-|_—]\s*", value)
            return parts[0].strip() if parts and parts[0].strip() else value
    return ""


def _extract_date(*texts: str) -> str | None:
    for t in texts:
        m = _DATE_RE.search(t or "")
        if m:
            y, mo, d = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None


def _pick_content(soup: BeautifulSoup) -> Tag | None:
    """在所有候选容器中挑选正文文本最长的一个。"""
    best: Tag | None = None
    best_len = 0
    for sel in _CONTENT_SELECTORS:
        for node in soup.select(sel):
            length = len(_text_of(node))
            if length > best_len:
                best, best_len = node, length
    if best is not None and best_len >= MIN_ARTICLE_CHARS:
        return best
    return None


def _sanitize(node: Tag, base_url: str) -> str:
    """净化正文：移除脚本/样式/表单与事件属性，相对地址改写为绝对地址。"""
    # 先整体移除噪音标签
    for tag in node.find_all(list(_STRIP_TAGS)):
        tag.decompose()

    for tag in node.find_all(True):
        # 去掉事件类属性与内联脚本
        for attr in list(tag.attrs.keys()):
            if attr.lower().startswith("on") or attr.lower() in ("style", "class", "id"):
                del tag.attrs[attr]
        if tag.name == "img":
            src = tag.get("src") or tag.get("data-src") or tag.get("data-original")
            if src:
                tag["src"] = urljoin(base_url, src)
            else:
                tag.decompose()
                continue
        if tag.name == "a":
            href = tag.get("href")
            if href:
                tag["href"] = urljoin(base_url, href)
            tag.attrs.pop("target", None)
        # 统一去掉表格的宽度限制，避免撑破移动端
        if tag.name in ("table", "td", "th"):
            tag.attrs.pop("width", None)

    return node.decode_contents()


def _collect_links(soup: BeautifulSoup, base_url: str, source_url: str) -> list[dict]:
    """列表页：抽取校内文章链接（标题 / 绝对地址 / 日期）。"""
    seen: set[str] = set()
    links: list[dict] = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        if not is_allowed_url(absolute):
            continue
        if absolute.rstrip("/") == source_url.rstrip("/"):
            continue
        text = _text_of(a)
        if len(text) < 4:  # 过滤「更多」「>>」等导航噪音
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append({
            "title": text[:120],
            "url": absolute,
            "date": _extract_date(text, a.get("title") or ""),
        })
        if len(links) >= MAX_LINKS:
            break
    return links


def read_url(url: str) -> dict:
    """解析校内页面：内容页返回正文，列表页返回链接清单。"""
    final_url, html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # 相对资源基准：优先页面自带 <base>，否则以最终 URL 所在目录为基准
    base_tag = soup.find("base", href=True)
    base_url = urljoin(final_url, base_tag["href"]) if base_tag else final_url

    title = _extract_title(soup) or urlparse(final_url).path.rsplit("/", 1)[-1] or "校内资讯"
    content = _pick_content(soup)

    if content is not None:
        body_text = _text_of(content)
        return {
            "kind": "article",
            "title": title,
            "date": _extract_date(title, body_text[:120]),
            "content_html": _sanitize(content, base_url),
            "links": [],
            "source_url": final_url,
        }

    return {
        "kind": "links",
        "title": title,
        "date": _extract_date(title),
        "content_html": None,
        "links": _collect_links(soup, base_url, final_url),
        "source_url": final_url,
    }