"""绵城印象爬虫服务：抓取 → 入库 → 更新缓存"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

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

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

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
# 同一时刻只允许一个后台刷新在跑（爬虫是同步阻塞网络请求，重复触发只会白烧带宽）
_refresh_lock = threading.Lock()
_refresh_running = False


def _set_impression_cache(data: list[dict]) -> None:
    global _impression_cache, _impression_cache_ts
    _impression_cache = data
    _impression_cache_ts = time.time()


def _refresh_in_background() -> None:
    """后台线程里跑一次全量刷新（stale-while-revalidate 的 revalidate 阶段）。

    为什么要另起线程：crawl_all() 是同步阻塞网络请求（要串行访问十余个校站，
    教学动态/通知公告/教学建设/学院动态还会并发抓各条详情页提取首图），
    放进请求线程会让 /api/campus/impression
    卡住数秒——前端表现为「进页面空白很久」。这里改为后台刷新，请求立刻返回旧数据。
    """
    global _refresh_running
    with _refresh_lock:
        if _refresh_running:
            return
        _refresh_running = True
    try:
        refresh_impression_data()
    finally:
        with _refresh_lock:
            _refresh_running = False


def get_impression_cache() -> list[dict] | None:
    """读取内存缓存：存在即返回，不因 TTL 过期而返回 None。

    stale-while-revalidate：过期只代表「该刷新了」，不代表「没数据可用」。
    若因过期返回 None，接口会退化成同步全量爬取（卡数秒甚至几十秒），
    前端每次都要重新等待——这正是校园资讯页反复闪加载的根因之一。
    这里改为：过期时启动后台刷新，本次仍返回旧数据，前端始终秒开。
    """
    if _impression_cache is None:
        return None
    if time.time() - _impression_cache_ts >= IMPRESSION_TTL:
        threading.Thread(target=_refresh_in_background, daemon=True).start()
    return _impression_cache


def _get(url: str, timeout: float = 10) -> str:
    resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers={"User-Agent": UA})
    return resp.content.decode("utf-8", errors="replace")


def _detail_base(url: str) -> str:
    """详情页首图的补链基准：教务处与全部学院站同一套 CMS，正文图都是 /__local/ 站内相对路径。"""
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _attach_first_images(items: list[AnnouncementItem], drop_without_image: bool = False) -> list[AnnouncementItem]:
    """并发进入各条详情页提取正文首图（parse_detail_first_image 只认 /__local/，天然跳过站点图标菜单图）。

    为什么并发：全量刷新本身是串行的，通知公告/教学建设/学院动态再加 30+ 次详情页请求
    会让刷新时长翻倍；线程池把每批详情页压到一两个网络往返的量级。
    drop_without_image=True 沿用教学动态「无图丢弃」的老规则，其余来源无图照常保留。
    """
    def _fetch(it: AnnouncementItem) -> tuple[AnnouncementItem, str | None]:
        try:
            return it, _get(it.url)
        except Exception:
            return it, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        fetched = list(pool.map(_fetch, items))
    result = []
    for it, html in fetched:
        img = parse_detail_first_image(html, base_url=_detail_base(it.url)) if html else None
        if img:
            it.image_url = img
        elif drop_without_image:
            continue
        result.append(it)
    return result


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
    items = parse_news_list(html, base_url=JWC_BASE, url_marker=marker)[:10]
    for it in items:
        it.source = "jwc_jxdt"
    return _attach_first_images(items, drop_without_image=True)


def fetch_jwc_simple(source: str) -> list[AnnouncementItem]:
    """通知公告/高教信息/教学建设"""
    path, marker = JWC_PAGES[source]
    html = _get(JWC_BASE + path)
    items = parse_news_list(html, base_url=JWC_BASE, url_marker=marker)
    for it in items:
        it.source = source
    items = items[:10]
    if source == "jwc_gjxx":
        # 高教信息条目全是外链（教育部/省考试院等政府站点），不去外站抓图：
        # 每轮刷新都访问十几个第三方站点既慢又不可靠，且外站图片有防盗链风险
        return items
    return _attach_first_images(items)


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
    return _attach_first_images(items)


def crawl_all() -> list[AnnouncementItem]:
    """全量爬取：入口 + 教学动态 + 通知/高教/建设 + 学院"""
    results: list[AnnouncementItem] = []
    results += fetch_jwc_entries()
    results += fetch_jwc_jxdt()
    for source in ("jwc_tzgg", "jwc_gjxx", "jwc_jxjs"):
        results += fetch_jwc_simple(source)
    results += fetch_college_news()
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
