import logging
import re
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.campus import CampusScenery, CampusImpressionItem
from app.models.user import User
from app.services.article_reader import read_url, is_allowed_url, requires_js
from app.services.campus_embed import build_embed_html, build_embed_error_html
from app.services.impression_crawler import get_impression_cache, refresh_impression_data
from app.schemas.campus import CampusSceneryOut, AnnouncementOut, GalleryImageOut, CampusArticleOut

router = APIRouter(prefix="/api/campus", tags=["campus"])
logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, list]] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str):
    now = time.time()
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < CACHE_TTL:
            return data
    return None


def _set_cache(key: str, data: list):
    _cache[key] = (time.time(), data)


@router.get("/sceneries", response_model=list[CampusSceneryOut])
def list_sceneries(area: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CampusScenery)
    if area:
        query = query.filter(CampusScenery.area == area)
    return query.all()


@router.get("/gallery", response_model=list[GalleryImageOut])
async def list_gallery():
    cached = _get_cached("gallery")
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get("https://www.mycc.edu.cn/mcyx/xyfg.htm")
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for li in soup.select(".main-pic-list li"):
            a = li.find("a")
            img = li.find("img")
            if not a or not img:
                continue
            title = a.get("title", "").strip()
            src = img.get("src", "")
            if not src or not title:
                continue
            if not src.startswith("http"):
                src = "https://www.mycc.edu.cn" + src
            campus = "安州" if "安州" in title else "游仙" if "游仙" in title else "未知"
            items.append(GalleryImageOut(title=title, image_url=src, campus=campus))
        _set_cache("gallery", items)
        return items
    except Exception:
        return []


@router.get("/announcements", response_model=list[AnnouncementOut])
async def list_announcements():
    cached = _get_cached("announcements")
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get("https://jwc.mycc.edu.cn/jwgl/tzgg.htm")
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
        from app.utils.announcement_parser import parse_announcement_list
        parsed = parse_announcement_list(resp.text)
        items = [AnnouncementOut(title=p.title, date=p.date, url=p.url) for p in parsed]
        _set_cache("announcements", items[:10])
        return items[:10]
    except Exception:
        return []


@router.get("/impression")
def get_impression(db: Session = Depends(get_db)):
    """绵城印象聚合数据：缓存 → 数据库 → 实时爬取兜底"""
    cached = get_impression_cache()
    if cached is not None:
        return cached
    rows = db.query(CampusImpressionItem).order_by(CampusImpressionItem.id.desc()).limit(500).all()
    if rows:
        data = [
            {"source": r.source, "college_key": r.college_key, "title": r.title,
             "image_url": r.image_url, "url": r.url, "date": r.date, "fetched_at": r.fetched_at}
            for r in rows
        ]
        return data
    # 数据库为空 → 实时爬取兜底
    return refresh_impression_data()


@router.get("/reader", response_model=CampusArticleOut)
def read_campus_article(
    url: str = Query(..., min_length=8, max_length=700),
    current_user: User = Depends(get_current_user),
):
    """站内阅读：代理抓取校内页面并提取正文/链接清单，避免跳出应用。

    学校站点均设 X-Frame-Options: SAMEORIGIN，无法 iframe 内嵌，
    由后端代抓 + 白名单校验（仅 *.mycc.edu.cn）+ 正文净化后返回。

    响应附带 supports_original：该页面能否用「原页渲染」（反代 iframe）打开。
    对超星系 SPA（lib.mycc.edu.cn 等）为 False —— 其正文由脚本注入，
    而不透明源 iframe 会中断这些脚本，原页必然白屏。
    """
    if not is_allowed_url(url):
        raise HTTPException(400, "仅支持校内站点链接")
    try:
        data = read_url(url)
    except PermissionError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, f"页面抓取失败：{e}")
    except Exception:
        raise HTTPException(502, "页面解析失败")
    # 在接口层附加而非写进 read_url 的缓存：缓存值保持纯解析结果，
    # 该标记始终按「本次请求的地址」计算，不会因缓存命中而串站。
    return {**data, "supports_original": not requires_js(url)}


@router.get("/embed", response_class=HTMLResponse)
def embed_campus_page(
    request: Request,
    url: str = Query(..., min_length=8, max_length=700),
):
    """原页渲染：反代校内页面并注入桥接脚本，供应用内 iframe 原版展示。

    - 学校响应带 X-Frame-Options: SAMEORIGIN，iframe 不能直接嵌学校页面；
      这里以「我们自己的响应」返回（不带该头），浏览器即允许被应用内嵌。
    - 相对资源靠注入的 <base> 指回学校站，因此原版样式/图片完整保留。
    - 页面内脚本跑在代理源；前端 iframe 必须带 sandbox（不含 allow-same-origin），
      iframe 为不透明源，拿不到应用的 localStorage / Cookie。
    - 只代理白名单内的校内公开页面，无需登录态（iframe 跨源请求带不上 SameSite=Lax Cookie）。
    """
    if not is_allowed_url(url):
        raise HTTPException(400, "仅支持校内站点链接")
    embed_base = str(request.base_url) if request is not None else "/"
    try:
        html = build_embed_html(url, embed_base)
    except PermissionError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        # 给 iframe 一张可读的错误页（而不是一坨 JSON），父页面会据桥接消息切到自己的错误态
        return HTMLResponse(
            content=build_embed_error_html(url, f"页面抓取失败：{e}"),
            status_code=502,
            headers={"Cache-Control": "no-store"},
        )
    except Exception:
        logger.exception("embed 页面构建失败: %s", url)
        return HTMLResponse(
            content=build_embed_error_html(url, "页面解析失败，可切换纯净正文查看"),
            status_code=502,
            headers={"Cache-Control": "no-store"},
        )
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store",
            # 反代页跑的是学校站点的全部脚本（含内联），来源是我们自己的源。
            # sandbox（不含 allow-same-origin）已挡住「读应用数据」，但挡不住
            # 「脚本能发请求 / 能弹窗」。这里补一条 CSP 收口：
            #   - script-src 允许 inline/eval：学校页有 12+ 个内联脚本与 jQuery 系
            #     动态求值，收紧会直接白屏，只能保持宽松（这是原页渲染的固有代价）；
            #   - object-src / base-uri 'none'：挡插件与 <base> 劫持；
            #   - frame-ancestors 'self'：反代页只允许被本应用嵌（防被第三方盗嵌）；
            #   - img/style/font 放开 * 与 data:，因为资源经注入的 <base> 回学校站加载。
            "Content-Security-Policy": (
                "default-src 'self' * data: blob: 'unsafe-inline' 'unsafe-eval'; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
            ),
        },
    )
