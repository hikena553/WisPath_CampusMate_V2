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
from app.models.campus_social import (
    CampusArticleComment,
    CampusArticleFavorite,
    CampusArticleLike,
    CampusArticleRepost,
    CampusArticleSocial,
)
from app.models.user import User
from app.services.article_reader import read_url, is_allowed_url, requires_js
from app.services.campus_embed import build_embed_html, build_embed_error_html
from app.services.impression_crawler import get_impression_cache, refresh_impression_data
from app.schemas.campus import (
    AnnouncementOut,
    CampusArticleCommentCreate,
    CampusArticleCommentOut,
    CampusArticleDetailOut,
    CampusArticleFavoriteIn,
    CampusArticleFavoriteOut,
    CampusArticleInteractOut,
    CampusArticleLikeIn,
    CampusArticleLikeOut,
    CampusArticleOut,
    CampusArticleRepostIn,
    CampusArticleRepostOut,
    CampusSceneryOut,
    GalleryImageOut,
    OkOut,
)

router = APIRouter(prefix="/api/campus", tags=["campus"])
logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, list]] = {}
CACHE_TTL = 300  # 5 minutes
# 校园公告一次返回条数：前端卡片固定高度内滚动展示，十余条足够覆盖近期公告
ANNOUNCEMENT_LIMIT = 20


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
    """校园公告（教务处通知公告）：抓取整页列表，按时间降序取前若干条。

    前端「校园公告」卡片在固定高度内滚动展示，因此这里多返回一些（十余条），
    由前端展示靠前的几条、其余滚动查看。
    """
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
        # 时间降序（无日期的排末尾）：页面顺序变化或缺日期时不丢最新公告
        parsed.sort(key=lambda p: p.date or "", reverse=True)
        items = [AnnouncementOut(title=p.title, date=p.date, url=p.url) for p in parsed[:ANNOUNCEMENT_LIMIT]]
        _set_cache("announcements", items)
        return items
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

# ==================== 资讯互动：浏览 / 点赞 / 评论 / 转发 ====================
#
# 设计要点（改这块之前先读）：
# 1) 资讯来自校站爬虫，**没有内部 id**，所以统一用「原文链接」当文章唯一键。
#    链接在 campus_article_socials.url 上有唯一约束，计数也集中在这一行上，
#    评论/点赞/转发三张明细表只存 url + user_id，不做外键 —— 资讯本身并不在本库里。
# 2) 计数是「明细表 + 汇总行」双写：汇总行供列表接口一次性取数（逐条 count 会让资讯流变慢），
#    明细表保证「谁点过 / 谁评论过」可追溯。点赞的切换以 (article_url, user_id) 唯一约束为准，
#    并发重复点赞最多撞唯一约束回滚，不会把计数加两次。
# 3) 互动必须登录：资讯流本身（/impression）是公开数据，但点赞/评论要落到具体用户。
# 4) 这里刻意不校验 is_allowed_url：详情可能由阅读器「链接清单」下钻而来，
#    地址仍来自校内白名单；评论/点赞只落一个字符串 url、不发起外网请求，无需重复白名单。

_MAX_URL = 700
_MAX_COMMENT = 500


def _social_row(db: Session, url: str, *, create: bool = False) -> "CampusArticleSocial | None":
    """取/建某篇文章的汇总行。create=False 时没有就返回 None（只读接口不写库）。"""
    row = db.query(CampusArticleSocial).filter(CampusArticleSocial.url == url).first()
    if row is None and create:
        row = CampusArticleSocial(url=url)
        db.add(row)
        db.flush()
    return row


def _update_social_meta(
    db: Session,
    url: str,
    *,
    title: str | None = None,
    source: str | None = None,
    image_url: str | None = None,
) -> CampusArticleSocial:
    """记录/刷新文章元信息（标题/来源/封面）。

    资讯来自爬虫，标题与封面可能被校站改掉；每次打开详情都用最新值覆盖一遍，
    保证他人看到的是当下的标题。空值不覆盖已有值，避免「列表接口没传 image_url」把封面抹掉。
    """
    row = _social_row(db, url, create=True)
    if title:
        row.title = title.strip()[:200]
    if source:
        row.source = source.strip()[:30]
    if image_url:
        row.image_url = image_url[:500]
    return row


def _interact_out(
    db: Session,
    url: str,
    current_user: User,
    *,
    article: dict | None = None,
) -> CampusArticleInteractOut:
    """组装单篇资讯的互动状态。article 非空时用它的标题兜底（汇总行可能还没落标题）。"""
    row = _social_row(db, url)
    liked = (
        db.query(CampusArticleLike.id)
        .filter(CampusArticleLike.article_url == url, CampusArticleLike.user_id == current_user.id)
        .first()
        is not None
    )
    favorited = (
        db.query(CampusArticleFavorite.id)
        .filter(CampusArticleFavorite.article_url == url, CampusArticleFavorite.user_id == current_user.id)
        .first()
        is not None
    )
    return CampusArticleInteractOut(
        url=url,
        title=(article or {}).get("title") or (row.title if row else ""),
        source=row.source if row else "",
        image_url=row.image_url if row else None,
        like_count=row.like_count if row else 0,
        favorite_count=row.favorite_count if row else 0,
        comment_count=row.comment_count if row else 0,
        repost_count=row.repost_count if row else 0,
        view_count=row.view_count if row else 0,
        liked=liked,
        favorited=favorited,
        updated_at=row.updated_at if row else None,
    )


@router.get("/interactions", response_model=dict[str, CampusArticleInteractOut])
def get_interactions(
    urls: list[str] = Query(default_factory=list),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """资讯流批量取互动状态，返回 {url: 互动状态}。

    一次请求补齐整屏资讯的赞/评/转计数，避免 N 条资讯发 N 次请求。
    查不到记录的文章不返回 —— 前端按 0 渲染，保持接口「只报事实」的语义。
    """
    clean = [u for u in urls if u and len(u) <= _MAX_URL][:120]
    if not clean:
        return {}
    rows = db.query(CampusArticleSocial).filter(CampusArticleSocial.url.in_(clean)).all()
    by_url = {r.url: r for r in rows}
    liked_urls = {
        u
        for (u,) in db.query(CampusArticleLike.article_url)
        .filter(
            CampusArticleLike.article_url.in_(clean),
            CampusArticleLike.user_id == current_user.id,
        )
        .all()
    }
    favorited_urls = {
        u
        for (u,) in db.query(CampusArticleFavorite.article_url)
        .filter(
            CampusArticleFavorite.article_url.in_(clean),
            CampusArticleFavorite.user_id == current_user.id,
        )
        .all()
    }
    out: dict[str, CampusArticleInteractOut] = {}
    for url in clean:
        row = by_url.get(url)
        if row is None:
            continue
        out[url] = CampusArticleInteractOut(
            url=url,
            title=row.title,
            source=row.source,
            image_url=row.image_url,
            like_count=row.like_count,
            favorite_count=row.favorite_count,
            comment_count=row.comment_count,
            repost_count=row.repost_count,
            view_count=row.view_count,
            liked=url in liked_urls,
            favorited=url in favorited_urls,
            updated_at=row.updated_at,
        )
    return out


@router.get("/articles/detail", response_model=CampusArticleDetailOut)
def get_article_detail(
    url: str = Query(..., min_length=8, max_length=_MAX_URL),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """资讯详情子页数据：正文（或列表页链接清单）+ 互动状态。

    浏览数在这里 +1：详情子页才是「真的读了这篇」，信息流划过不算阅读。
    正文抓取失败（校站超时/改版）不让整个详情页 502 —— 互动区与评论区仍然可用，
    前端据 article.kind == "error" 展示「正文暂不可用」并保留操作入口。
    """
    if not is_allowed_url(url):
        raise HTTPException(400, "仅支持校内站点链接")

    row = _update_social_meta(db, url)
    row.view_count = (row.view_count or 0) + 1
    db.commit()
    db.refresh(row)

    try:
        data = read_url(url)
        data = {**data, "supports_original": not requires_js(url)}
        # 用抓到的真实标题校正汇总行（列表里给出的标题可能带公共前缀或已过期）
        if data.get("title"):
            _update_social_meta(db, url, title=data["title"])
            db.commit()
    except Exception as exc:  # 抓取失败不拖垮详情页
        logger.warning("campus article detail fetch failed: %s (%s)", url, exc)
        data = {
            "kind": "error",
            "title": row.title or "",
            "date": None,
            "content_html": None,
            "links": [],
            "attachments": [],
            "source_url": url,
            "supports_original": False,
        }

    return CampusArticleDetailOut(
        article=data,
        social=_interact_out(db, url, current_user, article=data),
    )


@router.get("/articles/comments", response_model=list[CampusArticleCommentOut])
def list_article_comments(
    url: str = Query(..., min_length=8, max_length=_MAX_URL),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """文章评论：按时间正序（楼层感），带作者昵称/头像与「是否本人」。"""
    rows = (
        db.query(CampusArticleComment)
        .filter(CampusArticleComment.article_url == url)
        .order_by(CampusArticleComment.created_at.asc(), CampusArticleComment.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    authors = (
        {u.id: u for u in db.query(User).filter(User.id.in_({r.user_id for r in rows})).all()}
        if rows
        else {}
    )
    out: list[CampusArticleCommentOut] = []
    for r in rows:
        a = authors.get(r.user_id)
        out.append(
            CampusArticleCommentOut(
                id=r.id,
                article_url=r.article_url,
                user_id=r.user_id,
                content=r.content,
                created_at=r.created_at,
                author_name=a.name if a else "匿名同学",
                author_avatar=a.avatar if a else None,
                mine=r.user_id == current_user.id,
            )
        )
    return out


@router.post("/articles/comments", response_model=CampusArticleCommentOut)
def create_article_comment(
    req: CampusArticleCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发表评论：写明细 + 汇总行 comment_count +1。内容只做空白校验，不做敏感词拦截。"""
    content = req.content.strip()
    if not content:
        raise HTTPException(400, "评论内容不能为空")

    row = _update_social_meta(db, req.url)
    comment = CampusArticleComment(
        article_url=req.url, user_id=current_user.id, content=content[:_MAX_COMMENT]
    )
    db.add(comment)
    row.comment_count = (row.comment_count or 0) + 1
    db.commit()
    db.refresh(comment)
    return CampusArticleCommentOut(
        id=comment.id,
        article_url=comment.article_url,
        user_id=comment.user_id,
        content=comment.content,
        created_at=comment.created_at,
        author_name=current_user.name,
        author_avatar=current_user.avatar,
        mine=True,
    )


@router.delete("/articles/comments/{comment_id}", response_model=OkOut)
def delete_article_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除评论：本人可删自己；管理员可删任意（社区治理）。

    汇总行计数同步 -1 且不低于 0 —— 计数是冗余字段，宁可少数也不出现负数。
    """
    comment = db.query(CampusArticleComment).filter(CampusArticleComment.id == comment_id).first()
    if comment is None:
        raise HTTPException(404, "评论不存在")
    is_admin = getattr(current_user.role, "value", current_user.role) == "admin"
    if comment.user_id != current_user.id and not is_admin:
        raise HTTPException(403, "只能删除自己的评论")
    row = _social_row(db, comment.article_url)
    db.delete(comment)
    if row is not None:
        row.comment_count = max(0, (row.comment_count or 0) - 1)
    db.commit()
    return OkOut()


@router.post("/articles/like", response_model=CampusArticleLikeOut)
def toggle_article_like(
    req: CampusArticleLikeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """点赞 / 取消点赞（同一接口切换），返回最新状态与总数。

    幂等靠 (article_url, user_id) 唯一约束：并发双击时第二个请求会撞唯一约束，
    这里捕获后按「已点过赞」回传真实状态，前端不会看到计数错乱。
    """
    from sqlalchemy.exc import IntegrityError

    row = _update_social_meta(db, req.url)
    existing = (
        db.query(CampusArticleLike)
        .filter(
            CampusArticleLike.article_url == req.url,
            CampusArticleLike.user_id == current_user.id,
        )
        .first()
    )
    if existing is not None:
        db.delete(existing)
        row.like_count = max(0, (row.like_count or 0) - 1)
        db.commit()
        return CampusArticleLikeOut(liked=False, count=row.like_count)

    db.add(CampusArticleLike(article_url=req.url, user_id=current_user.id))
    row.like_count = (row.like_count or 0) + 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fresh = _social_row(db, req.url)
        return CampusArticleLikeOut(liked=True, count=fresh.like_count if fresh else 0)
    return CampusArticleLikeOut(liked=True, count=row.like_count)


@router.post("/articles/favorite", response_model=CampusArticleFavoriteOut)
def toggle_article_favorite(
    req: CampusArticleFavoriteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """收藏 / 取消收藏（同一接口切换），返回最新状态与总数。

    与点赞完全同构：唯一约束 (article_url, user_id) 兜住并发双击，
    撞约束时按「已收藏」回传真实计数，避免前端看到计数错乱。
    """
    from sqlalchemy.exc import IntegrityError

    row = _update_social_meta(db, req.url)
    existing = (
        db.query(CampusArticleFavorite)
        .filter(
            CampusArticleFavorite.article_url == req.url,
            CampusArticleFavorite.user_id == current_user.id,
        )
        .first()
    )
    if existing is not None:
        db.delete(existing)
        row.favorite_count = max(0, (row.favorite_count or 0) - 1)
        db.commit()
        return CampusArticleFavoriteOut(favorited=False, count=row.favorite_count)

    db.add(CampusArticleFavorite(article_url=req.url, user_id=current_user.id))
    row.favorite_count = (row.favorite_count or 0) + 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fresh = _social_row(db, req.url)
        return CampusArticleFavoriteOut(favorited=True, count=fresh.favorite_count if fresh else 0)
    return CampusArticleFavoriteOut(favorited=True, count=row.favorite_count)


@router.post("/articles/repost", response_model=CampusArticleRepostOut)
def repost_article(
    req: CampusArticleRepostIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """转发资讯：每次转发记一行（不去重），汇总行 repost_count +1。

    与点赞不同，转发是显式的分享动作，用户可能带不同附言多次转发，因此不做唯一约束；
    附言仅作留档，暂不进入统一动态流（本项目尚无跨模块时间线）。
    """
    row = _update_social_meta(db, req.url)
    db.add(
        CampusArticleRepost(
            article_url=req.url,
            user_id=current_user.id,
            content=(req.content or "").strip()[:120],
        )
    )
    row.repost_count = (row.repost_count or 0) + 1
    db.commit()
    return CampusArticleRepostOut(ok=True, count=row.repost_count)
