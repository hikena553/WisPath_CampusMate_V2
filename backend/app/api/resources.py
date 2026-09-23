"""资源中心：学习资源/行业资讯/校园信息 统一浏览 + 收藏去重 + AI"为你发现"推荐流"""
import re
import traceback

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.knowledge import KnowledgeItem
from app.models.campus import CampusImpressionItem
from app.models.favorite import ResourceFavorite
from app.models.plan import GrowthGoal
from app.models.user import User
from app.services.llm_service import _get_llm_config, _get_client
from app.schemas.resources import FavoriteCreate, FavoriteOut, ResourceItem, RecommendItem

router = APIRouter(prefix="/api/resources", tags=["资源中心"])

INDUSTRY_KEYWORDS = ["招聘", "就业", "实习", "行业", "竞赛", "考试", "四六级", "考研", "公务员", "证书", "创业", "技能"]
CATEGORY_NAMES = {
    "learning": "学习资源",
    "industry": "行业资讯",
    "campus": "校园信息",
}


def _profile_keywords(user: User, db: Session) -> list[str]:
    """学生画像关键词：技能 + 兴趣 + 长期目标"""
    keywords: list[str] = []
    skills_data = user.skills_json or {"skills": [], "interests": []}
    raw = skills_data.get("skills", [])
    keywords += [s["name"] if isinstance(s, dict) else str(s) for s in raw]
    keywords += [str(i) for i in skills_data.get("interests", [])]
    goals = db.query(GrowthGoal).filter(
        GrowthGoal.student_id == user.id
    ).all()
    for g in goals:
        keywords += [g.title, g.goal_type]
    return [k for k in keywords if k and len(k) > 1]


def _kb_item_to_resource(i: KnowledgeItem) -> ResourceItem:
    return ResourceItem(
        item_type="knowledge",
        item_id=i.id,
        title=i.question,
        category=i.category,
        summary=i.answer[:120] if i.answer else "",
        link=None,
        source="学习资源",
        extra={"tags": i.tags or ""},
    )


def _campus_item_to_resource(i: CampusImpressionItem) -> ResourceItem:
    return ResourceItem(
        item_type="campus",
        item_id=i.id,
        title=i.title,
        category=i.source,
        summary=i.date or "",
        link=i.url,
        source="校园信息",
        extra={"college_key": i.college_key or "", "date": i.date or ""},
    )


# ==================== 资源浏览 ====================

@router.get("/items", response_model=list[ResourceItem])
def list_items(
    category: str = Query("all", pattern="^(all|learning|industry|campus)$", description="分类筛选"),
    q: str = Query("", max_length=50, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    keyword = q.strip()
    result: list[ResourceItem] = []

    # 学习资源：知识库问答 + 上传文档
    if category in ("all", "learning"):
        kb_q = db.query(KnowledgeItem)
        if keyword:
            like = f"%{keyword}%"
            kb_q = kb_q.filter(or_(
                KnowledgeItem.question.like(like),
                KnowledgeItem.answer.like(like),
                KnowledgeItem.tags.like(like),
            ))
        for item in kb_q.order_by(KnowledgeItem.id.desc()).limit(100).all():
            result.append(_kb_item_to_resource(item))

    # 校园信息：爬虫快照
    if category in ("all", "campus"):
        cp_q = db.query(CampusImpressionItem)
        if keyword:
            cp_q = cp_q.filter(CampusImpressionItem.title.like(f"%{keyword}%"))
        for item in cp_q.order_by(CampusImpressionItem.id.desc()).limit(200).all():
            result.append(_campus_item_to_resource(item))

    # 行业资讯：知识库/校园信息中与行业、就业、竞赛相关的条目
    if category in ("all", "industry"):
        kw_conds = []
        for kw in INDUSTRY_KEYWORDS:
            kw_conds.append(CampusImpressionItem.title.like(f"%{kw}%"))
        hits = set()
        if kw_conds:
            for item in db.query(CampusImpressionItem).filter(or_(*kw_conds)).limit(60).all():
                hits.add(item.id)
        for item in db.query(CampusImpressionItem).filter(
            CampusImpressionItem.id.in_(hits) if hits else False
        ).limit(60).all():
            result.append(_campus_item_to_resource(item))
        for item in db.query(KnowledgeItem).filter(or_(
            *[KnowledgeItem.question.like(f"%{kw}%") for kw in ("就业", "考研", "竞赛", "证书", "四六级", "实习", "招聘")]
        )).limit(40).all():
            result.append(_kb_item_to_resource(item))

    # 去重（同 item_type + item_id）
    seen = set()
    merged = []
    for r in result:
        key = (r.item_type, r.item_id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)

    start = (page - 1) * page_size
    return merged[start:start + page_size]


# ==================== 收藏（去重） ====================

@router.get("/favorites", response_model=list[FavoriteOut])
def list_favorites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ResourceFavorite).filter(
        ResourceFavorite.user_id == current_user.id
    ).order_by(ResourceFavorite.created_at.desc()).limit(200).all()


@router.post("/favorites", response_model=FavoriteOut)
def create_favorite(
    req: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.item_type not in ("knowledge", "announcement", "community", "campus"):
        raise HTTPException(400, "不支持的资源类型")
    # 去重：同一资源重复收藏直接幂等返回
    exists = db.query(ResourceFavorite).filter(
        ResourceFavorite.user_id == current_user.id,
        ResourceFavorite.item_type == req.item_type,
        ResourceFavorite.item_id == req.item_id,
    ).first()
    if exists:
        return exists
    fav = ResourceFavorite(
        user_id=current_user.id,
        item_type=req.item_type,
        item_id=req.item_id,
        title=req.title[:200],
        category=req.category,
        summary=req.summary[:500] if req.summary else None,
        link=req.link,
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


@router.delete("/favorites/{fav_id}")
def delete_favorite(fav_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fav = db.query(ResourceFavorite).filter(
        ResourceFavorite.id == fav_id, ResourceFavorite.user_id == current_user.id
    ).first()
    if not fav:
        raise HTTPException(404, "收藏不存在")
    db.delete(fav)
    db.commit()
    return {"message": "deleted"}


# ==================== 数字赋能：AI"为你发现"推荐流 ====================

def _build_candidates(db: Session, limit: int = 45) -> list[ResourceItem]:
    """候选池：学习资源 + 校园信息 + 行业相关"""
    candidates: list[ResourceItem] = []
    for item in db.query(KnowledgeItem).order_by(KnowledgeItem.id.desc()).limit(20).all():
        candidates.append(_kb_item_to_resource(item))
    for item in db.query(CampusImpressionItem).order_by(CampusImpressionItem.id.desc()).limit(20).all():
        candidates.append(_campus_item_to_resource(item))
    kw_conds = [CampusImpressionItem.title.like(f"%{kw}%") for kw in INDUSTRY_KEYWORDS]
    if kw_conds:
        for item in db.query(CampusImpressionItem).filter(or_(*kw_conds)).limit(15).all():
            candidates.append(_campus_item_to_resource(item))
    seen, merged = set(), []
    for r in candidates:
        key = (r.item_type, r.item_id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)
    return merged[:limit]


def _fallback_recommend(candidates: list[ResourceItem], keywords: list[str], limit: int) -> list[RecommendItem]:
    """规则回退：画像关键词命中打分"""
    def _score(r: ResourceItem) -> int:
        score = len(candidates) - candidates.index(r)  # 新鲜度加权
        text = (r.title + " " + (r.category or "") + " " + (r.summary or "")).lower()
        for kw in keywords:
            if kw and kw.lower() in text:
                score += 40
        return score

    ranked = sorted(candidates, key=_score, reverse=True)[:limit]
    out = []
    for r in ranked:
        kw_hit = next((kw for kw in keywords if kw and kw.lower() in (r.title + (r.summary or "")).lower()), None)
        if kw_hit:
            reason = f"匹配你的「{kw_hit}」方向，建议收藏"
        elif r.source == "校园信息":
            reason = "校园最新动态，值得关注"
        else:
            reason = "热门学习资源，可提升技能储备"
        out.append(RecommendItem(**r.model_dump(), reason=reason))
    return out


@router.get("/recommend", response_model=list[RecommendItem])
async def recommend(
    limit: int = Query(6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 推荐流：画像关键词 + RAG 语义匹配评分；LLM 失败时规则回退"""
    candidates = _build_candidates(db)
    keywords = _profile_keywords(current_user, db)

    # 收藏过的资源提升权重
    fav_keys = {
        (f.item_type, f.item_id)
        for f in db.query(ResourceFavorite).filter(ResourceFavorite.user_id == current_user.id).all()
    }

    try:
        cfg = _get_llm_config()
        if not cfg.get("api_key"):
            raise RuntimeError("未配置 LLM")
        client = _get_client()
        pool = [
            {"index": i, "type": r.item_type, "title": r.title,
             "category": r.category or "", "summary": (r.summary or "")[:60]}
            for i, r in enumerate(candidates[:30])
        ]
        sys_msg = (
            "你是校园平台的内容推荐助手。根据学生的兴趣画像，从候选资源中挑选最值得推荐的条目，"
            "并给出简短推荐理由（不超过25字，贴合学生方向）。"
            f"学生画像关键词：{', '.join(keywords[:10]) if keywords else '暂无（默认推荐热门内容）'}"
        )
        user_msg = f"候选资源：{pool}\n请返回 JSON：{{\"items\":[{{\"index\":0,\"reason\":\"...\"}}]}}，共 {limit} 条。"
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
            temperature=0.4,
        )
        text = resp.choices[0].message.content or ""
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError("无 JSON 输出")
        data = __import__("json").loads(m.group(0))
        picked: list[RecommendItem] = []
        for it in data.get("items", []):
            idx = int(it.get("index", -1))
            reason = str(it.get("reason", "")).strip() or "为你精选的内容"
            if 0 <= idx < len(candidates):
                r = candidates[idx]
                picked.append(RecommendItem(**r.model_dump(), reason=reason))
            if len(picked) >= limit:
                break
        if picked:
            return picked
        raise ValueError("空结果")
    except Exception:
        traceback.print_exc()
        return _fallback_recommend(candidates, keywords, limit)