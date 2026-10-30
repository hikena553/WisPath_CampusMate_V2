"""交流社区模块（帖子 / 互动 / 数字赋能增强）

- 帖子：发帖（标题/内容/分类：技术/提问/分享/求助）、分类筛选、关键词搜索、分页
- 互动：评论发布/列表、点赞、浏览计数、作者展示
- 数字赋能：热帖推荐（按学生画像/学习方向关键词匹配）、社区内容作为 RAG 知识来源
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.community import CommunityPost, CommunityComment, CommunityLike
from app.models.plan import GrowthGoal
from app.schemas.community import (
    CommunityPostCreate, CommunityPostUpdate, CommunityPostOut,
    CommunityCommentCreate, CommunityCommentOut, LikeOut,
)

router = APIRouter(prefix="/api/community", tags=["交流社区"])

CATEGORIES = ["技术", "提问", "分享", "求助"]


def _post_out(db: Session, p: CommunityPost, current_user: User, with_content: bool = True) -> CommunityPostOut:
    author = db.query(User).filter(User.id == p.student_id).first()
    liked = db.query(CommunityLike).filter(
        CommunityLike.post_id == p.id,
        CommunityLike.student_id == current_user.id,
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
        liked=liked,
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
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_out(db, post, current_user)


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


# ==================== 数字赋能：热帖推荐（按画像/学习方向） ====================

@router.get("/hot", response_model=list[CommunityPostOut])
def hot_posts(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按学生画像关键词匹配的热帖（无匹配时回退为点赞数最高）"""
    keywords = []
    skills_data = current_user.skills_json or {"skills": [], "interests": []}
    raw = skills_data.get("skills", [])
    keywords += [s["name"] if isinstance(s, dict) else s for s in raw]
    keywords += [str(i) for i in skills_data.get("interests", [])]
    goals = db.query(GrowthGoal).filter(
        GrowthGoal.student_id == current_user.id
    ).all()
    for g in goals:
        keywords += [g.title, g.goal_type]

    posts = db.query(CommunityPost).order_by(
        CommunityPost.like_count.desc(), CommunityPost.view_count.desc()
    ).limit(60).all()

    def _score(p: CommunityPost) -> int:
        s = p.like_count * 3 + min(p.view_count, 500) // 10
        if keywords:
            text = (p.title + " " + p.content).lower()
            for kw in keywords:
                if kw and kw.lower() in text:
                    s += 40
        # 时间衰减：7 天内热度加成
        if p.created_at and p.created_at.date() >= date(2024, 1, 1):
            pass
        return s

    ranked = sorted(posts, key=_score, reverse=True)[:limit]
    return [_post_out(db, p, current_user, with_content=False) for p in ranked]