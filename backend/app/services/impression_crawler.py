"""绵城印象爬虫服务：抓取 → 入库 → 更新缓存"""
import logging
import re
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.campus import CampusImpressionItem
from app.utils.announcement_parser import (
    AnnouncementItem,
    parse_system_entries,
    parse_news_list,
    parse_detail_first_image,
    parse_college_news,
)

logger = logging.getLogger(__name__)

JWC_BASE = "https://jwc.mycc.edu.cn"

JWC_PAGES = {
    "jwc_jxdt": ("/jwgl/jxdt.htm", "info/1012/"),
    "jwc_tzgg": ("/jwgl/tzgg.htm", "info/1011/"),
    "jwc_gjxx": ("/gjxx.htm", None),
    "jwc_jxjs": ("/jxjs.htm", "info/"),
}

COLLEGES = {
    "马克思主义学院": "https://mksxy.mycc.edu.cn/",
    "人工智能学院": "https://xdjsxy.mycc.edu.cn/",
    "智能制造与工程学院": "https://xdcsjsxy.mycc.edu.cn/",
    "健康与教育学院": "https://xdfw.mycc.edu.cn/",
    "商学院": "https://jgxy.mycc.edu.cn/",
    "创意设计学院": "https://cysjxy.mycc.edu.cn/",
    "终身教育学院": "https://jxjy.mycc.edu.cn/",
}

_impression_cache: list[dict] | None = None
_impression_cache_ts = 0.0
IMPRESSION_TTL = 300


def _set_impression_cache(data: list[dict]) -> None:
    global _impression_cache, _impression_cache_ts
    _impression_cache = data
    _impression_cache_ts = time.time()


def get_impression_cache() -> list[dict] | None:
    if _impression_cache is not None and time.time() - _impression_cache_ts < IMPRESSION_TTL:
        return _impression_cache
    return None


def _get(url: str, timeout: float = 10) -> str:
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.encoding = resp.encoding or "utf-8"
    return resp.text


def fetch_jwc_entries() -> list[AnnouncementItem]:
    html = _get(JWC_BASE + "/")
    items = parse_system_entries(html, base_url=JWC_BASE)
    for it in items:
        it.source = "jwc_entries"
    return items


def fetch_jwc_jxdt() -> list[AnnouncementItem]:
    """教学动态：列表 + 详情页取首图，无图丢弃"""
    path, marker = JWC_PAGES["jwc_jxdt"]
    html = _get(JWC_BASE + path)
    items = parse_news_list(html, base_url=JWC_BASE, url_marker=marker)
    result = []
    for it in items[:10]:
        try:
            detail = _get(it.url)
        except Exception:
            continue
        img = parse_detail_first_image(detail, base_url=JWC_BASE)
        if not img:
            continue
        it.image_url = img
        it.source = "jwc_jxdt"
        result.append(it)
    return result


def fetch_jwc_simple(source: str) -> list[AnnouncementItem]:
    """通知公告/高教信息/教学建设"""
    path, marker = JWC_PAGES[source]
    html = _get(JWC_BASE + path)
    items = parse_news_list(html, base_url=JWC_BASE, url_marker=marker)
    for it in items:
        it.source = source
    return items[:10]


def fetch_college_news() -> list[AnnouncementItem]:
    items = []
    for name, url in COLLEGES.items():
        try:
            html = _get(url)
        except Exception as e:
            logger.warning("college %s fetch failed: %s", name, e)
            continue
        parsed = parse_college_news(html, college_key=name, base_url=url)
        for it in parsed[:2]:
            it.source = "college_news"
        items.extend(parsed[:2])
    return items


def _library_news_via_playwright() -> list[AnnouncementItem]:
    """用 Playwright 渲染图书馆 SPA，提取新闻公告标题+日期"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed")
        return []
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://lib.mycc.edu.cn/", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        text = page.inner_text("body")
        browser.close()
    idx = text.find("新闻公告")
    if idx == -1:
        return []
    chunk = text[idx: idx + 1200]
    lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
    titles: list[tuple[str, str]] = []
    for i, line in enumerate(lines):
        date_match = re.match(r"\d{4}-\d{2}-\d{2}", line)
        if date_match and i > 0:
            titles.append((lines[i - 1], line))
    for title, date in titles[:10]:
        items.append(AnnouncementItem(title=title, date=date, url="https://lib.mycc.edu.cn/", source="library"))
    return items


def fetch_library_news() -> list[AnnouncementItem]:
    items = _library_news_via_playwright()
    for it in items:
        if not it.source:
            it.source = "library"
    return items


def crawl_all() -> list[AnnouncementItem]:
    """全量爬取：入口 + 教学动态 + 通知/高教/建设 + 学院 + 图书馆"""
    results: list[AnnouncementItem] = []
    results += fetch_jwc_entries()
    results += fetch_jwc_jxdt()
    for source in ("jwc_tzgg", "jwc_gjxx", "jwc_jxjs"):
        results += fetch_jwc_simple(source)
    results += fetch_college_news()
    results += fetch_library_news()
    return results


def _save_to_db(items: list[AnnouncementItem]) -> None:
    db: Session = SessionLocal()
    try:
        db.query(CampusImpressionItem).delete()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for it in items:
            db.add(CampusImpressionItem(
                source=it.source,
                college_key=it.college_key,
                title=it.title,
                image_url=it.image_url,
                url=it.url or "",
                date=it.date,
                fetched_at=now,
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("save impression failed: %s", e)
    finally:
        db.close()


def refresh_impression_data() -> list[dict]:
    """定时任务入口：先入库再更新缓存"""
    try:
        items = crawl_all()
        _save_to_db(items)
        data = [vars(i) for i in items]
        _set_impression_cache(data)
        return data
    except Exception:
        logger.exception("refresh impression failed")
        return get_impression_cache() or []
