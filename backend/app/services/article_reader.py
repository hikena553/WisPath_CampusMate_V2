"""校内资讯站内阅读：代理抓取校内页面并提取正文 / 链接清单。

设计背景：
- 学校站点（jwc.mycc.edu.cn 等）统一设置 ``X-Frame-Options: SAMEORIGIN``，无法直接 iframe 内嵌；
- 因此由后端代抓，做域名白名单校验 + 正文净化，再把可读内容回传前端在应用内展示。

对外能力：
- ``is_allowed_url(url)``：白名单校验（仅 ``*.mycc.edu.cn`` 的 http/https 页面）；
- ``requires_js(url)``：判定该地址是否属于「正文由脚本注入」的 SPA 站点
  （超星系 lib.mycc.edu.cn 等），这类页面无法原页渲染，必然白屏；
- ``fetch_html(url)``：抓取并按页面字符集正确解码（兼容 gb2312/gbk 老站）；
- ``extract_article(html, url)``：**纯函数**，只解析给定 HTML，不发网络请求，
  便于单元测试直接喂字符串；
- ``read_url(url)``：``fetch_html`` + ``extract_article`` 的组合包装，
  返回 ``article``（正文）或 ``links``（列表页链接清单）两种形态。

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

# _CONTENT_SELECTORS 中前 N 项是「专用正文容器」（各高校 CMS 的固定 class/id），
# 命中即视为内容页；其余为通用兜底选择器，需配合长度门槛使用。
_STRONG_SELECTOR_COUNT = 13

# 文章头部（标题/日期）区块候选选择器。
# 高校 CMS 常把「标题 + 发布日期」放在正文容器**之外**的同级 div 里
# （如 ``div.art-tit`` 与 ``div.v_news_content`` 平级），
# 因此日期不能只从正文里找。
_HEADER_SELECTORS = [
    "div.art-tit",
    "div.cont-tit",
    "div.article-title",
    "div.news_title",
    "div.news-title",
    "div.info",
    "div.article-info",
    "div.pub-info",
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

# 「正文由脚本注入」的站点主机：这类页面原页渲染必然白屏，只能走纯净正文。
# 命中规则为主机精确匹配或其子域（见 requires_js），因此不会误伤
# ``notlib.mycc.edu.cn`` 这类形近域名。
_JS_ONLY_HOSTS = (
    "lib.mycc.edu.cn",        # 超星系图书馆
    "passport2.chaoxing.com",  # 超星统一身份认证
)

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


def requires_js(url: str) -> bool:
    """该地址是否只能靠 JS 渲染（原页渲染必然白屏）。

    用于前端决定是否提供「原页渲染」切换：SPA 站点的正文由脚本注入，
    而反代 iframe 是不透明源沙箱、会中断这些脚本，所以只能走「纯净正文」。

    非法/空地址不抛异常，按「不需要 JS」返回（白名单由 ``is_allowed_url`` 另行拦截）。
    """
    host = _host_of(url)
    if not host:
        return False
    return any(host == js_host or host.endswith("." + js_host) for js_host in _JS_ONLY_HOSTS)


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


def _header_text(soup: BeautifulSoup) -> str:
    """正文容器之外的文章头部文本（标题块里的日期就藏在这里）。"""
    parts: list[str] = []
    for sel in _HEADER_SELECTORS:
        for node in soup.select(sel):
            text = _text_of(node)
            # 头部块通常很短；过长说明选择器命中了整页容器，不可信
            if text and len(text) < 300:
                parts.append(text)
    return " ".join(parts)


def _pick_content(soup: BeautifulSoup) -> Tag | None:
    """在所有候选容器中挑选正文文本最长的一个。

    长度门槛（``MIN_ARTICLE_CHARS``）只用于**兜底**：短页面里靠前的
    ``div.content`` / ``div.txt`` 之类的通用选择器命中率低、误判代价高，
    故要求足够长才认。而白名单里靠前的 CMS 正文选择器
    （``div.v_news_content`` / ``div#vsb_content`` 等）本身已是强信号，
    命中即认定为内容页 —— 否则正文偏短的页面会被误判成列表页。
    """
    best: Tag | None = None
    best_len = 0
    for idx, sel in enumerate(_CONTENT_SELECTORS):
        # 靠前的专用正文选择器命中即可信，无需再比长度
        if idx < _STRONG_SELECTOR_COUNT:
            node = soup.select_one(sel)
            if node is not None:
                return node
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


def _nearby_text(a: Tag) -> str:
    """链接自身文本之外的日期来源。

    高校 CMS 列表页常把日期放在 ``<a>`` 的兄弟节点里
    （``<li><a>标题</a><span>2026-10-01</span></li>``），日期并不在链接内部；
    因此额外取父节点文本。父节点只多包一层无关导航文字，日期正则仍能精确命中。
    """
    parent = a.parent
    if isinstance(parent, Tag):
        return _text_of(parent)
    return ""


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
            "date": _extract_date(text, a.get("title") or "", _nearby_text(a)),
        })
        if len(links) >= MAX_LINKS:
            break
    return links


def extract_article(html: str, url: str) -> dict:
    """纯解析：从 HTML 文本中提取正文或链接清单，不发网络请求。

    内容页（正文长度 ≥ ``MIN_ARTICLE_CHARS``）返回 ``kind="article"``，
    否则视为列表页返回 ``kind="links"``。``url`` 用于把相对地址绝对化。
    """
    soup = BeautifulSoup(html, "html.parser")

    # 相对资源基准：优先页面自带 <base>，否则以最终 URL 所在目录为基准
    base_tag = soup.find("base", href=True)
    base_url = urljoin(url, base_tag["href"]) if base_tag else url

    title = _extract_title(soup) or urlparse(url).path.rsplit("/", 1)[-1] or "校内资讯"
    content = _pick_content(soup)

    if content is not None:
        body_text = _text_of(content)
        return {
            "kind": "article",
            "title": title,
            # 日期优先取正文开头，其次取正文外的标题块（CMS 常见布局）
            "date": _extract_date(title, body_text[:120], _header_text(soup)),
            "content_html": _sanitize(content, base_url),
            "links": [],
            "source_url": url,
        }

    return {
        "kind": "links",
        "title": title,
        "date": _extract_date(title),
        "content_html": None,
        "links": _collect_links(soup, base_url, url),
        "source_url": url,
    }


def read_url(url: str) -> dict:
    """解析校内页面：抓取后交由 ``extract_article`` 解析。

    内容页返回正文，列表页返回链接清单；``source_url`` 为跟随重定向后的最终地址。
    """
    final_url, html = fetch_html(url)
    return extract_article(html, final_url)
