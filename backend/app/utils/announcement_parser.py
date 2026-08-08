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


def parse_college_news(html: str, college_key: str, base_url: str) -> list[AnnouncementItem]:
    """学院首页新闻列表：取 href 含 /info/ 的 a 标签"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "info/" not in href:
            continue
        text = a.get_text(strip=True)
        if len(text) < 6 or text in ("查看更多", "更多", "进入官网", "查看详情"):
            continue
        date_match = re.search(r"(\d{4}[-.]\d{2}[-.]\d{2})", text)
        date = date_match.group(1) if date_match else None
        title = text.replace(date, "").strip() if date else text
        url = _absolute(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        items.append(AnnouncementItem(title=title, date=date, url=url, college_key=college_key))
    return items
