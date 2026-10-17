"""教务处通知公告解析（共享工具函数）

支持同步和异步两种调用方式，解析逻辑统一维护。
"""

import re
from dataclasses import dataclass


@dataclass
class AnnouncementItem:
    title: str
    date: str | None = None
    url: str | None = None
    image_url: str | None = None
    college_key: str | None = None
    source: str | None = None


def _absolute(base_url: str, href: str) -> str:
    href = href.replace("../", "/")
    if href.startswith("http"):
        return href
    return base_url.rstrip("/") + "/" + href.lstrip("/")


def parse_announcement_list(html: str, base_url: str = "https://jwc.mycc.edu.cn") -> list[AnnouncementItem]:
    """通知公告列表（兼容现有调用）"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.find_all("li"):
        a = li.find("a")
        if not a:
            continue
        href = a.get("href", "")
        if "info/1011/" not in href:
            continue
        text = a.get_text(strip=True)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})$", text)
        date = date_match.group(1) if date_match else None
        title = text[:-10] if date else text
        items.append(AnnouncementItem(title=title, date=date, url=_absolute(base_url, href)))
    return items


def parse_system_entries(html: str, base_url: str = "https://jwc.mycc.edu.cn") -> list[AnnouncementItem]:
    """教务处首页 .function-icons 系统入口"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select(".function-icons a.icon-item"):
        p = a.find("p")
        href = a.get("href", "")
        if not p or not href:
            continue
        items.append(AnnouncementItem(title=p.get_text(strip=True), url=_absolute(base_url, href)))
    return items


def parse_news_list(html: str, base_url: str = "https://jwc.mycc.edu.cn", url_marker: str | None = "info/") -> list[AnnouncementItem]:
    """通用新闻列表：教学动态/通知公告/高教信息/教学建设。

    url_marker 为 None 时不过滤 href（外链列表，如高教信息）。
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if url_marker and url_marker not in href:
            continue
        if not href.startswith("http") and "info/" not in href and url_marker:
            continue
        text = a.get_text(strip=True)
        if len(text) < 6 or text in ("查看更多", "更多", "查看详情"):
            continue
        date = None
        # 优先：开头 DDYYYY-MM（教学动态分离日期，如 "312026-07师生..."）
        m = re.match(r"(\d{2})(\d{4})[-.](\d{2})", text)
        if m:
            date = f"{m.group(2)}-{m.group(3)}-{m.group(1)}"
            text = text[m.end():].strip()
        else:
            # 开头 MM-DDYYYY（通知公告分离年份，如 "08-012026关于..."）
            m = re.match(r"(\d{2})-(\d{2})(\d{4})", text)
            if m:
                date = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
                text = text[m.end():].strip()
            else:
                # 末尾 YYYY-MM-DD（高教信息等外部链接）
                m = re.search(r"(\d{4}[-.]\d{2}[-.]\d{2})$", text)
                if m:
                    date = m.group(1)
                    text = text[:m.start()].strip()
                else:
                    # 内联 YYYY-MM-DD（教学建设等）
                    m = re.search(r"(\d{4}[-.]\d{2}[-.]\d{2})", text)
                    if m:
                        date = m.group(1)
                        text = text.replace(m.group(0), "").strip()
        items.append(AnnouncementItem(title=text, date=date, url=_absolute(base_url, href)))
    return items


def parse_detail_first_image(html: str, base_url: str = "https://jwc.mycc.edu.cn") -> str | None:
    """从新闻详情页正文提取第一张 __local 图片"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "__local" in src:
            return _absolute(base_url, src)
    return None


# 标题最大长度：学院站列表用 CSS 截断到 ~20 字并带 "..."，短标题保持原样；
# 超过该长度说明混入了正文摘要，需要按结构或标点切出标题。
_TITLE_MAX_LEN = 40

# 列表里的占位/导航链接（不当成新闻）
_PLACEHOLDER_TEXTS = ("查看更多", "更多", "进入官网", "查看详情", "了解详情")

# 承载日期的容器：不同学院的 class 命名各不相同（见各学院首页实测结构）
_DATE_CLASS_KEYWORDS = ("date", "datatime", "time", "nian", "ribbon", "riqi")

_FULL_DATE_RE = re.compile(r"(\d{4})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})\s*日?")
_MD_RE = re.compile(r"^\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})\s*日?\s*$")
_YEAR_RE = re.compile(r"^\s*(\d{4})\s*年?\s*$")
# 形如 "10-14 2026" / "10-14\u00a02026"：月日在前、年份在后（智能制造与工程学院）
_MD_YEAR_RE = re.compile(r"(\d{1,2})\s*[-./月]\s*(\d{1,2})\s*日?\s*[,，]?\s*(\d{4})")
# 形如 "2026-10"（商学院 <span class="year">2026-10</span>：年-月，日另在 <span class="date">）
_YM_RE = re.compile(r"^\s*(\d{4})\s*[-./年]\s*(\d{1,2})\s*月?\s*$")
_DAY_RE = re.compile(r"^\s*(\d{1,2})\s*日?\s*$")

# 标题尾部站点截断残渣：结尾的 "..." / "…"（含其后可能的空白）。
# 注意只吃省略号类字符，不能吃普通句号——否则 "…的通知。" 会被削掉句号。
_TRAILING_ELLIPSIS_RE = re.compile(r"[\s.．·]*[.．·]{2,}[\s.．·…]*$|[\s…]+$")
# 「正文起句」标记：只在退化路径（结构拿不到标题）下用于打断被拼进来的摘要。
# 必须带逗号/标点，避免 "关于根据上级要求…的通知" 这类正常标题被误伤。
_SUMMARY_MARKERS = (
    "近日，", "近日,", "为进一步", "据悉，", "据悉,", "会议指出，", "会议认为，",
    "活动伊始，", "首先，", "随后，", "近日",
)


def _norm_date(year: str | int, month: str | int, day: str | int) -> str | None:
    """组装 YYYY-MM-DD；月份/日期越界时放弃（避免 2025-2026 之类学年版被当日期）。"""
    y, m, d = int(year), int(month), int(day)
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return None
    if not (2000 <= y <= 2100):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def _extract_full_date(text: str) -> str | None:
    """从文本里找完整年月日（支持 2026-04-01 / 2026.04.01 / 2026年4月1日）。"""
    if not text:
        return None
    m = _FULL_DATE_RE.search(text)
    if not m:
        return None
    # 学年版 "2025-2026学年" 这类不含日的串不会被 _FULL_DATE_RE 匹配（需三段），安全
    return _norm_date(m.group(1), m.group(2), m.group(3))


def _is_date_node(node) -> bool:
    """判断节点是否专门用于承载日期（class 含 date/time 等关键词）。"""
    classes = node.get("class") or []
    if isinstance(classes, str):
        classes = [classes]
    return any(any(k in str(c).lower() for k in _DATE_CLASS_KEYWORDS) for c in classes)


def _strip_title_noise(text: str) -> str:
    """去掉标题里的残留省略号与空白。"""
    return _TRAILING_ELLIPSIS_RE.sub("", (text or "").replace("\u3000", " ")).strip()


def _title_from_structure(a) -> str | None:
    """按 DOM 结构取标题：a 内的语义标题标签优先，其次排除日期节点后的文本。

    各学院首页实测结构差异很大：
    - 马克思主义学院: a > h3(标题) + p(摘要正文)  ← 123 字污染源
    - 健康与教育学院: a > div(标题)
    - 人工智能学院:   a 直接文本(标题) + span.date(日期)
    - 创意设计学院:   a > span(标题) + span.label_datatime(日期)
    """
    # 1) a 的 title 属性通常是没有被 CSS 截断的完整标题，最可靠
    attr_title = _strip_title_noise(a.get("title") or "")
    if attr_title:
        return attr_title

    # 2) 语义标题标签
    for tag in ("h1", "h2", "h3", "h4", "strong", "b", "em"):
        node = a.find(tag)
        if node:
            text = _strip_title_noise(node.get_text(" ", strip=True))
            if text:
                return text

    # 3) a 内的 p / div / span：排除日期节点后取第一个像标题的
    for node in a.find_all(["p", "div", "span"]):
        if _is_date_node(node):
            continue
        if _extract_full_date(node.get_text(" ", strip=True)) and len(node.get_text(strip=True)) <= 12:
            continue  # 纯日期节点（如 <span>2026.04.01</span>）
        text = _strip_title_noise(node.get_text(" ", strip=True))
        if text and not _looks_like_summary(text):
            return text

    # 4) 退化：a 的直接文本（排除日期），取日期节点之前的文本
    parts = []
    for child in a.children:
        if getattr(child, "name", None):
            if _is_date_node(child) or child.name == "p":
                continue
            parts.append(child.get_text(" ", strip=True))
        else:
            parts.append(str(child))
    text = _strip_title_noise(" ".join(p for p in parts if p).strip())
    if text:
        return text
    return None


def _looks_like_summary(text: str) -> bool:
    """判断一段文字是否更像正文摘要而非标题。"""
    if len(text) > _TITLE_MAX_LEN:
        return True
    stripped = text.lstrip()
    return any(stripped.startswith(marker) for marker in _SUMMARY_MARKERS)


def _clean_title(raw: str, allow_marker_cut: bool = False) -> str:
    """标题清洗：剥离尾部截断残渣，超长时按标点断句或硬截断。

    allow_marker_cut 仅在「结构拿不到标题、整段 a 文本被当标题」的退化路径下为 True：
    此时才用「正文起句标记」切断被拼进来的摘要。结构路径（h3 等）下绝不按词切断，
    否则 "关于根据上级文件要求…的通知" 这类正常标题会被削成 "关于"。
    正常的短标题（≤40 字）原样保留，不误伤。
    """
    text = _strip_title_noise(raw)
    if not text:
        return ""

    # 退化路径：被拼进来的摘要正文起点（如 "标题...近日，由四川省教育厅指导…"）
    if allow_marker_cut:
        cut = len(text)
        for marker in _SUMMARY_MARKERS:
            idx = text.find(marker)
            # 标记必须出现在前 40 字之后的正文区，且前面已有一个完整标题
            if idx >= 8 and idx < cut:
                cut = idx
        if cut < len(text):
            text = _strip_title_noise(text[:cut])
            if not text:
                text = _strip_title_noise(raw)
    if not text:
        return ""

    if len(text) <= _TITLE_MAX_LEN:
        return text

    # 超长：优先在句末标点处断句
    match = re.search(r"[。！？；!?;]", text)
    if match and match.start() >= 6:
        return _strip_title_noise(text[: match.start()])

    # 退而求其次：硬截断并加省略号（列表本身也是这么截断的）
    # 省略号要计入长度上限，否则会得到 _TITLE_MAX_LEN + 1 个字
    return text[: _TITLE_MAX_LEN - 1].rstrip() + "…"


def _extract_date(a, li) -> str | None:
    """按 a 内 → a 的兄弟节点 → 父级 <li> 的顺序提取日期，统一成 YYYY-MM-DD。

    各学院实测：
    - 人工智能学院: <a>...<span class="date">2026.04.01</span></a>（点号）
    - 创意设计学院: <a><span>标题</span><span class="label_datatime">2026-10-15</span></a>
    - 健康与教育学院: <a>标题</a><p class="section2-Body-Date">2026-09-24</p>（兄弟节点）
    - 商学院: <li><span class="label_datatime">10-13</span><a>标题</a></li>（仅月日，无年份）
    - 智能制造与工程学院: <div class="dat fl"><h1>10-14</h1><div class="nian">2026</div></div>
    仅能取到「月-日」而无年份时返回 None：不臆造年份，交前端降级。
    """
    # 1) a 自身及其后代里的完整日期
    for node in [a, *a.find_all(True)]:
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        if _is_date_node(node) or node is a:
            date = _extract_full_date(text)
            if date:
                return date
    date = _extract_full_date(a.get_text(" ", strip=True))
    if date:
        return date

    scope = li if li is not None else a.parent
    if scope is None:
        return None

    # 2) 月日 + 年份分处两个节点（智能制造与工程学院：h1 "10-14" + div.nian "2026"）
    #    先在 a 之后的兄弟节点里找完整日期，再退到 li 整体文本
    for node in scope.find_all(True):
        if node is a or a in node.parents:
            continue
        text = node.get_text(" ", strip=True)
        date = _extract_full_date(text)
        if date:
            return date

    combined = scope.get_text(" ", strip=True)
    date = _extract_full_date(combined)
    if date:
        return date

    # 3) 形如 "10-14 2026"：月日在前、年份在后
    m = _MD_YEAR_RE.search(combined)
    if m:
        return _norm_date(m.group(3), m.group(1), m.group(2))

    # 4) 年-月 与 日 分处两个节点（商学院：<span class="date">14</span> + <span class="year">2026-10</span>）
    ym_part = day_part = None
    for node in scope.find_all(["span", "div", "p", "em", "i"]):
        if node is a or a in node.parents:
            continue
        raw = node.get_text(" ", strip=True)
        if not raw or len(raw) > 24:
            continue
        ym = _YM_RE.match(raw)
        if ym:
            if ym_part is None:
                ym_part = (ym.group(1), ym.group(2))
            continue
        dm = _DAY_RE.match(raw)
        if dm and day_part is None:
            day_part = dm.group(1)
    if ym_part and day_part:
        return _norm_date(ym_part[0], ym_part[1], day_part)

    # 5) 月-日 与 年份 分处两个节点（智能制造与工程学院：
    #    <div class="dat fl"><h1>10-14</h1><div class="nian">2026</div></div>）
    md_part = year_part = None
    for node in scope.find_all(["h1", "h2", "h3", "span", "div", "p"]):
        if node is a or a in node.parents:
            continue
        text = node.get_text(" ", strip=True)
        if not text or len(text) > 12:
            continue
        if md_part is None:
            md = _MD_RE.match(text)
            if md:
                md_part = (md.group(1), md.group(2))
                continue
        if md_part is not None and year_part is None:
            ym = _YEAR_RE.match(text)
            if ym:
                year_part = ym.group(1)
                break
    if md_part and year_part:
        return _norm_date(year_part, md_part[0], md_part[1])

    return None


def parse_college_news(html: str, college_key: str, base_url: str) -> list[AnnouncementItem]:
    """学院首页新闻列表：取 href 含 /info/ 的 a 标签。

    与旧实现的差别（修复学院新闻质量）：
    - 标题不再直接吃 a.get_text()：学院首页常把「标题 + 摘要正文」包在同一个 a 里
      （马克思主义学院 123 字污染），改为 a[title] 属性 / h3 等语义标签 / 排除日期节点，
      再按摘要起句标记与句末标点兜底截断，最长 40 字。
    - 日期从 a 内、a 的兄弟节点、父级 <li> 依次提取，支持 2026.04.01 与 2026-10-15，
      以及「10-14 + 2026」分处两节点与「10-13 2026」月日在前两种排布，统一成 YYYY-MM-DD。
    - 只有月-日而无年份时 date 为 None（不臆造年份，前端降级处理）。
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items: list[AnnouncementItem] = []
    by_url: dict[str, AnnouncementItem] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "info/" not in href:
            continue

        # 占位/导航链接先按原始文本排除（避免清洗后短文本误入）
        raw_text = a.get_text(strip=True)
        if not raw_text or raw_text in _PLACEHOLDER_TEXTS:
            continue
        if any(raw_text.startswith(p) for p in _PLACEHOLDER_TEXTS):
            continue

        url = _absolute(base_url, href)
        date = _extract_date(a, a.find_parent("li"))

        # 同一 URL 在页面上常被渲染多次：一次是「轮播展示」（标题无日期），
        # 一次是「列表项」（标题 + 日期）。健康与教育学院即如此——首见为无日期的
        # 展示位，日期在后面的 <li> 里。因此重复 URL 不能简单丢弃，而要补齐日期。
        existing = by_url.get(url)
        if existing is not None:
            if date and not existing.date:
                existing.date = date
            continue

        # 标题：优先结构（a[title] / h3 / 排除日期节点），退化到整段文本清洗。
        # 只有退化路径才允许按「正文起句标记」切断，避免误伤正常长标题。
        title = _title_from_structure(a)
        if title:
            title = _clean_title(title)
        else:
            title = _clean_title(_strip_title_noise(raw_text), allow_marker_cut=True)
        if not title:
            continue

        # 清洗后仍需满足最短长度（沿用旧行为：len < 6 视为非新闻链接）
        if len(title) < 6:
            continue

        item = AnnouncementItem(
            title=title, date=date, url=url, college_key=college_key
        )
        by_url[url] = item
        items.append(item)
    return items
