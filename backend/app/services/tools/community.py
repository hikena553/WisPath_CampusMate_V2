"""作品集/交流社区/资源中心工具 handlers。"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.campus import CampusImpressionItem
from app.models.certificate import Certificate
from app.models.community import CommunityPost
from app.models.favorite import ResourceFavorite
from app.models.growth import StudentProject
from app.models.knowledge import KnowledgeItem
from app.models.portfolio import StudentResume
from app.models.user import User
from app.utils.enum_helpers import safe_enum_str




def _query_portfolio(db: Session, args: dict, user: User) -> dict:
    projects = db.query(StudentProject).filter(StudentProject.student_id == user.id).order_by(
        StudentProject.start_date.desc()).all()
    certificates = db.query(Certificate).filter(Certificate.student_id == user.id).order_by(
        Certificate.created_at.desc()).all()
    resumes = db.query(StudentResume).filter(StudentResume.student_id == user.id).order_by(
        StudentResume.created_at.desc()).all()

    cert_status = {"pending": "待认证", "approved": "已认证", "rejected": "已驳回"}
    return {
        "message": f"作品集：项目 {len(projects)} 个，证书 {len(certificates)} 份，简历 {len(resumes)} 份",
        "projects": [{
            "id": p.id, "name": p.project_name, "start": str(p.start_date),
            "end": str(p.end_date) if p.end_date else "",
            "role": p.my_role or "", "tech_stack": p.tech_stack or "",
            "description": (p.description or "")[:200],
            "link": p.project_link or "",
        } for p in projects],
        "certificates": [{
            "id": c.id, "title": c.title,
            "competition_name": c.competition_name or "",
            "award_level": c.award_level.value if c.award_level else "",
            "date": str(c.date) if c.date else "",
            "status": cert_status.get(safe_enum_str(c.status, ""), safe_enum_str(c.status, "")),
        } for c in certificates],
        "resumes": [{"id": r.id, "filename": r.filename, "is_current": bool(r.is_current)} for r in resumes],
    }


def _query_community_posts(db: Session, args: dict, user: User) -> dict:
    q = (args.get("q") or "").strip()
    category = (args.get("category") or "").strip()
    sort = (args.get("sort") or "latest").strip()

    query = db.query(CommunityPost)
    if category:
        query = query.filter(CommunityPost.category == category)
    if q:
        from app.services.knowledge_service import _escape_like
        safe_q = _escape_like(q)
        like = f"%{safe_q}%"
        query = query.filter(or_(CommunityPost.title.like(like, escape="\\"), CommunityPost.content.like(like, escape="\\")))
    if sort == "hot":
        query = query.order_by(CommunityPost.like_count.desc(), CommunityPost.comment_count.desc())
    else:
        query = query.order_by(CommunityPost.created_at.desc())
    posts = query.limit(10).all()

    user_ids = {p.student_id for p in posts}
    name_map = {u.id: u.name for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    result = []
    for p in posts:
        result.append({
            "id": p.id, "title": p.title, "content": (p.content or "")[:150],
            "category": p.category,
            "author": name_map.get(p.student_id, "同学"),
            "likes": p.like_count, "comments": p.comment_count, "views": p.view_count,
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
        })
    return {"message": f"找到 {len(result)} 条帖子", "posts": result}


def _create_community_post(db: Session, args: dict, user: User) -> dict:
    title = (args.get("title") or "").strip()
    content = (args.get("content") or "").strip()
    category = (args.get("category") or "分享").strip()
    if category not in ("技术", "提问", "分享", "求助"):
        category = "分享"
    missing = []
    if not title:
        missing.append("title（标题）")
    if not content:
        missing.append("content（正文）")
    if missing:
        return {"success": False, "message": f"缺少必要参数：{', '.join(missing)}"}
    post = CommunityPost(
        student_id=user.id,
        category=category,
        title=title[:200],
        content=content[:5000],
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"success": True, "post_id": post.id, "message": f"✅ 帖子已发布到社区（#{post.id}）：{post.title}"}


def _query_resources(db: Session, args: dict, user: User) -> dict:
    q = (args.get("q") or "").strip()
    category = (args.get("category") or "all").strip()

    items = []
    # 1) 学习资源（知识库）
    if category in ("all", "learning"):
        kb_q = db.query(KnowledgeItem)
        if q:
            from app.services.knowledge_service import _escape_like
            safe_q = _escape_like(q)
            like = f"%{safe_q}%"
            kb_q = kb_q.filter(or_(KnowledgeItem.question.like(like, escape="\\"), KnowledgeItem.answer.like(like, escape="\\"), KnowledgeItem.tags.like(like, escape="\\")))
        for i in kb_q.limit(8).all():
            items.append({"item_type": "knowledge", "title": i.question, "category": i.category,
                          "summary": (i.answer or "")[:120], "source": "学习资源"})
    # 2) 校园信息
    if category in ("all", "campus"):
        ci_q = db.query(CampusImpressionItem)
        if q:
            from app.services.knowledge_service import _escape_like
            safe_q = _escape_like(q)
            like = f"%{safe_q}%"
            ci_q = ci_q.filter(CampusImpressionItem.title.like(like, escape="\\"))
        for i in ci_q.limit(8).all():
            items.append({"item_type": "campus", "title": i.title, "category": i.source,
                          "summary": i.date or "", "source": "校园信息", "link": i.url or ""})
    # 3) 行业资讯（知识库中 category 含招聘/就业等关键词的）
    if category in ("all", "industry"):
        from app.services.knowledge_service import _escape_like
        ind_q = db.query(KnowledgeItem).filter(
            KnowledgeItem.category.in_(["就业", "招聘", "行业", "考证", "职业发展"])
        )
        if q:
            safe_q = _escape_like(q)
            like = f"%{safe_q}%"
            ind_q = ind_q.filter(or_(KnowledgeItem.question.like(like, escape="\\"), KnowledgeItem.answer.like(like, escape="\\")))
        for i in ind_q.limit(8).all():
            items.append({"item_type": "industry", "title": i.question, "category": i.category,
                          "summary": (i.answer or "")[:120], "source": "行业资讯"})

    # 4) 我的收藏
    favorites = db.query(ResourceFavorite).filter(ResourceFavorite.user_id == user.id).order_by(
        ResourceFavorite.created_at.desc()).limit(10).all()

    return {
        "message": f"共找到 {len(items)} 条资源，收藏 {len(favorites)} 条",
        "resources": items,
        "favorites": [{"title": f.title, "category": f.category or "", "summary": (f.summary or "")[:80],
                       "item_type": f.item_type} for f in favorites],
    }
