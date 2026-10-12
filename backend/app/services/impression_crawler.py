"""绵城印象爬虫服务：抓取 → 入库 → 更新缓存"""
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
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

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 图书馆站（超星托管的 SPA）：域名可在 .env 用 LIBRARY_SITE_URL 覆盖
LIBRARY_URL = settings.LIBRARY_SITE_URL or "https://lib.mycc.edu.cn/"
LIBRARY_RENDER_TIMEOUT_MS = 20000      # 页面导航上限
LIBRARY_CONTENT_WAIT_MS = 12000        # 等待“新闻公告”内容出现上限
LIBRARY_PREFLIGHT_TIMEOUT = 8          # 渲染前可达性探测（DNS/连接）超时
LIBRARY_FAIL_COOLDOWN = 6 * 3600       # 不可达后的短路时长：不再每轮都烧 30s + 刷告警
# 系统 DNS 解析失败时的兜底 DoH（校内域名常有解析视图差异：公网能解析、校内回不来）
LIBRARY_DOH_ENDPOINTS = ("https://223.5.5.5/resolve", "https://doh.pub/dns-query")

_library_unreachable_until = 0.0

JWC_PAGES = {
    "jwc_jxdt": ("/jwgl/jxdt.htm", "info/1012/"),
    "jwc_tzgg": ("/jwgl/tzgg.htm", "info/1011/"),
    "jwc_gjxx": ("/gjxx.htm", None),
    "jwc_jxjs": ("/jxjs.htm", "info/"),
}

# “教务系统入口”网格中不展示的项（按标题 / 链接双重匹配）
HIDDEN_ENTRY_TITLES = ("课表查询", "教学校历", "作息时间")
HIDDEN_ENTRY_URLS = ("/jwgl/kbcx.htm", "/jwgl/jxxl.htm", "/jwgl/zxsj.htm")

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
    resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers={"User-Agent": UA})
    return resp.content.decode("utf-8", errors="replace")


def _is_hidden_entry(item: AnnouncementItem) -> bool:
    """入口卡片里不再展示的系统入口。

    课表查询 / 教学校历 / 作息时间 都是教务处静态工具页，与应用内已有页面重复，
    不适合放在“教务系统入口”网格里；标题与链接双重匹配，避免学校改文案后又被抓回来。
    """
    title = item.title or ""
    url = (item.url or "").rstrip("/")
    return any(k in title for k in HIDDEN_ENTRY_TITLES) or url.endswith(HIDDEN_ENTRY_URLS)


def fetch_jwc_entries() -> list[AnnouncementItem]:
    html = _get(JWC_BASE + "/")
    items = [it for it in parse_system_entries(html, base_url=JWC_BASE) if not _is_hidden_entry(it)]
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


def _doh_resolve(host: str) -> str | None:
    """系统 DNS 解析失败时的兜底：用公共 DoH 查 A 记录。

    校内域名常见「解析视图不同」：公网 DNS 能正常解析（如图书馆站 CNAME 到超星），
    校内/本地 DNS 却可能不回或超时。拿到公网 IP 后交给 Chromium 的
    --host-resolver-rules 映射，浏览器仍以原域名发起请求，SNI/Host/证书校验不变。
    """
    if not host:
        return None
    for endpoint in LIBRARY_DOH_ENDPOINTS:
        try:
            resp = httpx.get(
                endpoint,
                params={"name": host, "type": "A"},
                headers={"Accept": "application/dns-json", "User-Agent": UA},
                timeout=6,
            )
            for answer in resp.json().get("Answer", []):
                data = str(answer.get("data") or "").strip()
                if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", data):
                    return data
        except Exception:
            continue
    return None


def _library_launch_args() -> list[str] | None:
    """渲染前先探测图书馆站可达性。

    返回 Chromium 额外启动参数（空列表表示直连正常）；返回 None 表示本轮应跳过：
    站点不可达时立刻放弃，避免再让 Playwright 白等超时。
    """
    host = urlparse(LIBRARY_URL).hostname or ""
    try:
        httpx.get(
            LIBRARY_URL,
            timeout=LIBRARY_PREFLIGHT_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": UA},
        )
        return []
    except httpx.TransportError as e:
        ip = _doh_resolve(host)
        if ip:
            logger.info("图书馆站 %s 本地 DNS 解析失败，改用 DoH 兜底 IP %s 渲染", host, ip)
            return [f"--host-resolver-rules=MAP {host} {ip}"]
        logger.info("图书馆站 %s 不可达，跳过渲染: %s", LIBRARY_URL, e)
        return None


def _library_news_via_playwright() -> list[AnnouncementItem]:
    """用 Playwright 渲染图书馆 SPA，提取新闻公告标题+日期

    优先复用系统已装的 Edge/Chrome（channel 方式，无需下载内置 Chromium），
    失败再回退官方内置 Chromium；整个渲染路径容错，单模块失败不影响其他来源。
    """
    global _library_unreachable_until
    if time.time() < _library_unreachable_until:
        logger.debug("图书馆站冷却中（上次不可达），跳过渲染")
        return []

    launch_args = _library_launch_args()
    if launch_args is None:
        _library_unreachable_until = time.time() + LIBRARY_FAIL_COOLDOWN
        logger.warning(
            "图书馆公告暂停抓取 %.0f 小时：%s 当前网络不可达（可在 .env 用 LIBRARY_SITE_URL 覆盖）",
            LIBRARY_FAIL_COOLDOWN / 3600,
            LIBRARY_URL,
        )
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed")
        return []

    def _launch_browser(playwright):
        try:
            return playwright.chromium.launch(headless=True, channel="msedge", args=launch_args)
        except Exception:
            # 部分 Windows 无 Edge / 非 Windows 环境，回退官方内置 Chromium
            return playwright.chromium.launch(headless=True, args=launch_args)

    items = []
    text = ""
    try:
        with sync_playwright() as p:
            try:
                browser = _launch_browser(p)
            except Exception as e:
                logger.warning("library browser launch failed: %s", e)
                return []
            try:
                page = browser.new_page()
                # SPA 常带长连接/轮询，networkidle 永远等不到；改为 DOM 就绪 + 等目标内容
                page.goto(LIBRARY_URL, wait_until="domcontentloaded", timeout=LIBRARY_RENDER_TIMEOUT_MS)
                try:
                    page.wait_for_selector("text=新闻公告", timeout=LIBRARY_CONTENT_WAIT_MS)
                except Exception:
                    pass  # 文案/结构变化时不阻塞，下面按整页文本兜底解析
                page.wait_for_timeout(1000)
                text = page.inner_text("body")
            finally:
                browser.close()
    except Exception as e:
        logger.warning("library playwright render failed: %s", e)
        return []
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
        items.append(AnnouncementItem(title=title, date=date, url=LIBRARY_URL, source="library"))
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
    """将爬取结果写入数据库（全表替换）。

    注意：使用 delete-all + insert 模式，在 delete 之后、commit 之前若进程异常退出，
    会导致数据丢失。当前设计由 refresh_impression_data 作为单一写入者保证安全性。
    """
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
    """定时任务入口：先入库再更新缓存。

    注意：本函数包含同步阻塞网络请求，应在后台线程中调用（如 asyncio.to_thread），
    不要在 FastAPI 异步事件循环中直接调用。
    """
    try:
        items = crawl_all()
        _save_to_db(items)
        data = [vars(i) for i in items]
        _set_impression_cache(data)
        return data
    except Exception:
        logger.exception("refresh impression failed")
        return get_impression_cache() or []
