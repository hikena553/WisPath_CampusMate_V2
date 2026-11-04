"""交流社区模块（帖子 / 互动 / 数字赋能增强）

- 帖子：发帖（标题/内容/分类：技术/提问/分享/求助）、分类筛选、关键词搜索、分页
- 互动：评论发布/列表、点赞、浏览计数、作者展示
- 数字赋能：热帖推荐（按学生画像/学习方向关键词匹配）、社区内容作为 RAG 知识来源
"""
from datetime import datetime, timedelta, timezone
import json
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.social import Follow
from app.models.campus import CampusImpressionItem
from app.models.community import CommunityPost, CommunityComment, CommunityLike
from app.models.plan import GrowthGoal
from app.schemas.community import (
    CommunityPostCreate, CommunityPostUpdate, CommunityPostOut,
    CommunityCommentCreate, CommunityCommentOut, LikeOut,
)

router = APIRouter(prefix="/api/community", tags=["交流社区"])

CATEGORIES = ["技术", "提问", "分享", "求助", "资讯"]

# 一条帖子最多带 9 张图（前端九宫格上限，超出的截断而不是报错）
MAX_POST_IMAGES = 9


def _images_to_db(images: list[str] | None) -> str | None:
    """URL 数组 → 入库 JSON 字符串；空数组存 None，避免库里出现 '[]' 与 NULL 两种空值。"""
    if not images:
        return None
    cleaned = [str(u).strip() for u in images if str(u).strip()][:MAX_POST_IMAGES]
    return json.dumps(cleaned, ensure_ascii=False) if cleaned else None


def _post_out(db: Session, p: CommunityPost, current_user: User, with_content: bool = True) -> CommunityPostOut:
    author = db.query(User).filter(User.id == p.student_id).first()
    liked = db.query(CommunityLike).filter(
        CommunityLike.post_id == p.id,
        CommunityLike.student_id == current_user.id,
    ).first() is not None
    # 作者关注状态：帖子卡片/详情上的「关注」按钮按它回显
    author_is_following = db.query(Follow.id).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == p.student_id,
    ).first() is not None
    return CommunityPostOut(
        id=p.id,
        student_id=p.student_id,
        category=p.category,
        title=p.title,
        content=p.content if with_content else p.content[:120] + ("…" if len(p.content) > 120 else ""),
        view_count=p.view_count,
        like_count=p.like_count,
        comment_count=p.comment_count,
        created_at=p.created_at,
        author_name=author.name if author else "匿名同学",
        author_avatar=author.avatar if author else None,
        author_is_following=author_is_following,
        liked=liked,
        images=p.images,
    )


# ==================== 帖子 ====================

@router.get("/posts", response_model=list[CommunityPostOut])
def list_posts(
    category: str | None = Query(None),
    q: str | None = Query(None, max_length=50),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    sort: str = Query("new", description="new/hot"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(CommunityPost)
    if category and category != "全部":
        query = query.filter(CommunityPost.category == category)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (CommunityPost.title.like(like)) | (CommunityPost.content.like(like))
        )
    if sort == "hot":
        query = query.order_by(CommunityPost.like_count.desc(), CommunityPost.created_at.desc())
    else:
        query = query.order_by(CommunityPost.created_at.desc())
    posts = query.offset((page - 1) * page_size).limit(page_size).all()
    return [_post_out(db, p, current_user, with_content=False) for p in posts]


@router.get("/following", response_model=list[CommunityPostOut])
def list_following_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关注流：我关注的人发的帖子，按发布时间倒序（校园资讯「关注」页签）。

    与 /posts 的差别只有作者集合 —— 这里只收我关注的人。三条口径：
    ① 不收自己：自己的帖子在个人中心「我发布的」，混进来会让人以为关注流串了号；
    ② 不做推荐加权：关注流是「我主动选的这些人说了什么」，按时间倒序最可预期，
       加权排序会让晚发的内容插到早发的前面，用户会怀疑漏看了；
    ③ 关注关系为空时直接走 JOIN 得空结果，不额外查一次关注表。
    """
    posts = (
        db.query(CommunityPost)
        .join(Follow, Follow.following_id == CommunityPost.student_id)
        .filter(
            Follow.follower_id == current_user.id,
            CommunityPost.student_id != current_user.id,
        )
        .order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # with_content=False：列表只要摘要（120 字），正文留给详情页按需取
    return [_post_out(db, p, current_user, with_content=False) for p in posts]


@router.post("/posts", response_model=CommunityPostOut)
def create_post(req: CommunityPostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if req.category not in CATEGORIES:
        raise HTTPException(400, "分类不合法")
    if not req.title.strip() or len(req.title) > 100:
        raise HTTPException(400, "标题不能为空且不超过100字")
    if not req.content.strip():
        raise HTTPException(400, "内容不能为空")
    post = CommunityPost(
        student_id=current_user.id,
        category=req.category,
        title=req.title.strip(),
        content=req.content.strip(),
        images=_images_to_db(req.images),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_out(db, post, current_user)


@router.get("/posts/mine", response_model=list[CommunityPostOut])
def list_my_posts(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我发布的帖子：按发布时间倒序（个人中心「我发布的」使用）。"""
    posts = (
        db.query(CommunityPost)
        .filter(CommunityPost.student_id == current_user.id)
        .order_by(CommunityPost.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_post_out(db, p, current_user) for p in posts]


@router.get("/posts/{post_id}", response_model=CommunityPostOut)
def get_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return _post_out(db, post, current_user)


@router.put("/posts/{post_id}", response_model=CommunityPostOut)
def update_post(
    post_id: int, req: CommunityPostUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(
        CommunityPost.id == post_id, CommunityPost.student_id == current_user.id
    ).first()
    if not post:
        raise HTTPException(404, "帖子不存在或无权修改")
    data = req.model_dump(exclude_unset=True)
    if req.category is not None and req.category not in CATEGORIES:
        raise HTTPException(400, "分类不合法")
    # images 是数组，不能走下面那个「字符串就 strip」的通用分支
    if "images" in data and data["images"] is not None:
        post.images = _images_to_db(data.pop("images"))
    for k, v in data.items():
        if v is not None:
            setattr(post, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    db.refresh(post)
    return _post_out(db, post, current_user)


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")
    if post.student_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(403, "无权删除他人帖子")
    db.query(CommunityComment).filter(CommunityComment.post_id == post_id).delete()
    db.query(CommunityLike).filter(CommunityLike.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    return {"message": "deleted"}


# ==================== 点赞 / 浏览 ====================

@router.post("/posts/{post_id}/like", response_model=LikeOut)
def toggle_like(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")
    existing = db.query(CommunityLike).filter(
        CommunityLike.post_id == post_id,
        CommunityLike.student_id == current_user.id,
    ).first()
    if existing:
        db.delete(existing)
        post.like_count = max(0, post.like_count - 1)
        liked = False
    else:
        db.add(CommunityLike(post_id=post_id, student_id=current_user.id))
        post.like_count += 1
        liked = True
    db.commit()
    return LikeOut(liked=liked, count=post.like_count)


# ==================== 评论 ====================

@router.get("/posts/{post_id}/comments", response_model=list[CommunityCommentOut])
def list_comments(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")
    comments = db.query(CommunityComment).filter(
        CommunityComment.post_id == post_id
    ).order_by(CommunityComment.created_at.asc()).all()
    authors = {u.id: u for u in db.query(User).filter(User.id.in_({c.student_id for c in comments})).all()} if comments else {}
    result = []
    for c in comments:
        author = authors.get(c.student_id)
        out = CommunityCommentOut.model_validate(c)
        out.author_name = author.name if author else "匿名同学"
        out.author_avatar = author.avatar if author else None
        result.append(out)
    return result


@router.post("/posts/{post_id}/comments", response_model=CommunityCommentOut)
def create_comment(post_id: int, req: CommunityCommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")
    if not req.content.strip():
        raise HTTPException(400, "评论不能为空")
    comment = CommunityComment(post_id=post_id, student_id=current_user.id, content=req.content.strip()[:500])
    post.comment_count += 1
    db.add(comment)
    db.commit()
    db.refresh(comment)
    out = CommunityCommentOut.model_validate(comment)
    out.author_name = current_user.name
    out.author_avatar = current_user.avatar
    return out


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comment = db.query(CommunityComment).filter(CommunityComment.id == comment_id).first()
    if not comment:
        raise HTTPException(404, "评论不存在")
    post = db.query(CommunityPost).filter(CommunityPost.id == comment.post_id).first()
    if comment.student_id != current_user.id and not (post and post.student_id == current_user.id):
        raise HTTPException(403, "无权删除")
    if post:
        post.comment_count = max(0, post.comment_count - 1)
    db.delete(comment)
    db.commit()
    return {"message": "deleted"}


# ==================== 数字赋能：推荐候选（热度 × 兴趣 × 新鲜度） ====================

# 新鲜度半衰期：帖子更替快，3 天折半。资讯不参与打分（它们按发布时间排），
# 帖子要靠「够新」才能争到推荐流里的位置。
RECOMMEND_HALF_LIFE_DAYS = 3.0

# 打分权重：新鲜度 45 / 热度 30 / 兴趣 20 / 质量 5。
# 仿信息流产品的可解释规则分：每一项都能单独讲清楚为什么这条被推上来。
W_FRESH, W_HEAT, W_INTEREST, W_QUALITY = 0.45, 0.30, 0.20, 0.05


def _utc_now() -> datetime:
    """库里 created_at 存的是 naive UTC（SQLite 无时区），统一按 naive UTC 比较。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _post_age_days(p: CommunityPost, now: datetime) -> float:
    if not p.created_at:
        return 999.0
    dt = p.created_at
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def _norm_title(t: str | None) -> str:
    """标题归一化：去掉空白与常见标点，用于「同一条新闻」的去重判断。"""
    if not t:
        return ""
    drop = " \t\r\n·—－-|｜「」『』【】《》()（）[]，,。.、：:；;！!？?“”\"'"
    return "".join(ch for ch in str(t).lower() if ch not in drop)


def _keyword_variants(k: str) -> set[str]:
    """画像关键词的匹配变体。

    中文长词整串匹配基本等于没匹配：画像写「编程开发」，学生正文里只会出现「开发」。
    所以把 4 字以上的纯中文词再切成 2 字片段一起参与匹配（噪声由「任一命中即加一次分」兜住）。
    """
    k = str(k).strip().lower()
    if not k:
        return set()
    out = {k}
    if len(k) >= 4 and all("\u4e00" <= ch <= "\u9fff" for ch in k):
        out.update(k[i:i + 2] for i in range(len(k) - 1))
    return out


def _interest_profile(db: Session, user: User) -> tuple[set[str], set[int], set[str]]:
    """画像信号：兴趣关键词 / 关注的作者 / 近 7 天赞过的分区。

    任一项取数失败都返回空集合而不是 500 —— 推荐位是增强功能，不该把首页打死。
    """
    keywords: set[str] = set()
    try:
        skills_data = user.skills_json or {}
        for s in skills_data.get("skills", []) or []:
            name = s.get("name") if isinstance(s, dict) else s
            if name:
                keywords |= _keyword_variants(name)
        for i in skills_data.get("interests", []) or []:
            if i:
                keywords |= _keyword_variants(i)
        for g in db.query(GrowthGoal).filter(GrowthGoal.student_id == user.id).all():
            for v in (g.title, g.goal_type):
                if v:
                    keywords |= _keyword_variants(v)
    except Exception:
        pass
    keywords.discard("")

    followed: set[int] = set()
    try:
        followed = {
            r[0] for r in db.query(Follow.following_id).filter(Follow.follower_id == user.id).all()
        }
    except Exception:
        pass

    liked_categories: set[str] = set()
    try:
        since = _utc_now() - timedelta(days=7)
        rows = (
            db.query(CommunityPost.category)
            .join(CommunityLike, CommunityLike.post_id == CommunityPost.id)
            .filter(
                CommunityLike.student_id == user.id,
                CommunityLike.created_at >= since,
            )
            .all()
        )
        liked_categories = {r[0] for r in rows if r[0]}
    except Exception:
        pass

    return keywords, followed, liked_categories


def _score_post(
    p: CommunityPost,
    now: datetime,
    keywords: set[str],
    followed: set[int],
    liked_categories: set[str],
    is_media: bool = False,
) -> float:
    """0~100 的推荐分。四项分别可解释，方便以后接入点击率做加权修正。"""
    age = _post_age_days(p, now)
    fresh = 100.0 * (0.5 ** (age / RECOMMEND_HALF_LIFE_DAYS))

    # 热度做对数压缩：一条爆款不该长期霸占位置，新帖也不至于永远是 0 分
    base = p.like_count * 3 + p.comment_count * 5 + p.view_count * 0.2
    heat = min(100.0, 22.0 * math.log1p(max(0.0, base)))

    interest = 0.0
    if p.student_id in followed:
        interest += 45          # 关注的作者：最直接的兴趣信号
    if p.category in liked_categories:
        interest += 30          # 近期赞过同类内容
    if keywords:
        text = f"{p.title} {p.content}".lower()
        if any(k in text for k in keywords):
            interest += 25      # 画像关键词命中（技能 / 兴趣 / 成长目标）
    interest = min(100.0, interest)

    quality = 0.0
    if p.images:
        quality += 3
    if len(p.content or "") >= 80:
        quality += 2

    # 冷启动：发布不满一天、还没什么互动的帖子给一笔保底曝光（新内容也该被看到）
    if age < 1.0 and base < 3:
        fresh = max(fresh, 62.0)

    # 同学原创优先于资讯站的搬运内容：社区属性更强，也避免推荐位被同一个账号占满
    student_bonus = 0.0 if is_media else 10.0

    return (
        W_FRESH * fresh + W_HEAT * heat + W_INTEREST * interest + W_QUALITY * quality
        + student_bonus
    )


def _mostly_chinese(t: str | None) -> bool:
    """标题是否以中文为主（汉字占字母数的 50% 以上）。

    资讯站账号会搬运大量英文论文 / 外媒标题，它们属于「AI 资源」那条线；
    混在中文校园资讯流里，一屏之内中英夹杂会显得很割裂。
    """
    if not t:
        return False
    letters = [ch for ch in t if ch.isalpha()]
    if not letters:
        return False
    cn = sum(1 for ch in letters if "\u4e00" <= ch <= "\u9fff")
    return cn / len(letters) >= 0.5


def _diversify(
    ranked: list[CommunityPost],
    limit: int,
    media_ids: set[int] | None = None,
    media_cap: int = 0,
) -> list[CommunityPost]:
    """同类打散：相邻两条不同分区、不同作者；资讯站帖子最多占 media_cap 条。

    池子不够时逐级放宽（先放宽分区，再放宽作者），保证有内容可插而不是空手返回。
    """
    media_ids = media_ids or set()
    pool = list(ranked)
    out: list[CommunityPost] = []
    last_cat: str | None = None
    last_author: int | None = None
    media_used = 0

    def _too_many_media(p: CommunityPost) -> bool:
        # 资讯站占比是硬上限：到顶就只返回已选出的这些，宁可少插几条也不让它霸屏
        return p.student_id in media_ids and media_used >= media_cap

    while pool and len(out) < limit:
        idx = None
        # 严格模式先避开「同分区 + 同作者」，不行再只避开同作者
        for strict in (True, False):
            for i, p in enumerate(pool):
                if _too_many_media(p) or p.student_id == last_author:
                    continue
                if strict and p.category == last_cat:
                    continue
                idx = i
                break
            if idx is not None:
                break
        if idx is None:
            # 同作者限制也放宽，但只要还没到资讯站上限就补一条
            for i, p in enumerate(pool):
                if not _too_many_media(p):
                    idx = i
                    break
        if idx is None:
            break
        p = pool.pop(idx)
        out.append(p)
        last_cat, last_author = p.category, p.student_id
        if p.student_id in media_ids:
            media_used += 1
    return out


@router.get("/recommend", response_model=list[CommunityPostOut])
def recommend_posts(
    limit: int = Query(12, ge=1, le=30),
    days: int = Query(30, ge=1, le=365, description="只看最近 N 天发布的帖子"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """校园资讯「推荐」页的帖子候选（前端按密度插进资讯流）。

    与 /posts 的区别：
      - 只取近 N 天 / 非本人的帖子；
      - 与资讯流同名的帖子剔除（同一条新闻不在推荐流里出现两次）；
      - 按「新鲜度 × 热度 × 兴趣画像」打分，同类打散，并限制资讯站账号的占比。
    """
    now = _utc_now()
    since = now - timedelta(days=days)
    rows = (
        db.query(CommunityPost, User.role)
        .join(User, User.id == CommunityPost.student_id)
        .filter(
            CommunityPost.created_at >= since,
            CommunityPost.student_id != current_user.id,
        )
        .order_by(CommunityPost.created_at.desc())
        .limit(200)
        .all()
    )
    if not rows:
        return []

    posts = [p for p, _ in rows]
    media_ids = {p.student_id for p, role in rows if role == UserRole.MEDIA}

    # 资讯标题集合：帖子与其中任意一条同名，说明是同一条新闻，推荐流里只留资讯那条
    news_titles: set[str] = set()
    try:
        for (t,) in db.query(CampusImpressionItem.title).all():
            n = _norm_title(t)
            if n:
                news_titles.add(n)
    except Exception:
        pass

    keywords, followed, liked_categories = _interest_profile(db, current_user)
    scored = [
        (p, _score_post(p, now, keywords, followed, liked_categories, p.student_id in media_ids))
        for p in posts
        if _norm_title(p.title) not in news_titles
        # 资讯站的英文搬运不进推荐位（留给「AI 资源」）：一屏里中英夹杂，读起来像两个产品
        and (p.student_id not in media_ids or _mostly_chinese(p.title))
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    # 推荐位里资讯站内容最多占一半：社区的主体应该是同学，不是一个自动发帖账号
    ranked = _diversify(
        [p for p, _ in scored],
        limit,
        media_ids=media_ids,
        media_cap=max(1, limit // 2),
    )
    return [_post_out(db, p, current_user, with_content=False) for p in ranked]


# ==================== 数字赋能：热帖推荐（按画像/学习方向） ====================

@router.get("/hot", response_model=list[CommunityPostOut])
def hot_posts(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按学生画像关键词匹配的热帖（与 /recommend 共用同一套打分，口径保持一致）"""
    now = _utc_now()
    posts = (
        db.query(CommunityPost)
        .order_by(CommunityPost.created_at.desc())
        .limit(200)
        .all()
    )
    keywords, followed, liked_categories = _interest_profile(db, current_user)
    ranked = sorted(
        posts,
        key=lambda p: _score_post(p, now, keywords, followed, liked_categories),
        reverse=True,
    )[:limit]
    return [_post_out(db, p, current_user, with_content=False) for p in ranked]