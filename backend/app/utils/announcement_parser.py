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


def parse_announcement_list(html: str, base_url: str = "https://jwc.mycc.edu.cn") -> list[AnnouncementItem]:
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
        full_url = base_url + href.replace("../", "/")
        items.append(AnnouncementItem(title=title, date=date, url=full_url))
    return items
