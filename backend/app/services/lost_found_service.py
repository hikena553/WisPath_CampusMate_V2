"""失物招领检索服务。

为智能体工具（search_lost_found）和 REST 搜索接口提供统一的匹配能力。

采用两阶段策略：
1. 关键词打分召回——按 标题/描述/地点 分字段加权，并用中文二元组（bigram）
   兜住"水杯 / 保温杯"这类词形差异；
2. 打分全部落空时，回捞最新的待处理记录作为候选，交给 LLM 做语义判断，
   避免直接误判为"没有"而重复登记。
"""
import logging
import re

from sqlalchemy.orm import Session

from app.models.lost_found import LostFoundItem, ItemType, ItemStatus
from app.utils.enum_helpers import safe_enum_str

logger = logging.getLogger(__name__)

# 检索时剥离的修饰词（保留原词参与打分，只是额外生成更通用的核心词）
_MODIFIERS = (
    "我的", "我的一个", "一个", "这个", "那个", "自己", "本人",
    "黑色", "白色", "红色", "蓝色", "绿色", "灰色", "粉色", "棕色", "银色",
    "金色", "黄色", "紫色", "橙色", "深色", "浅色", "透明",
    "新的", "旧的", "小", "大",
)

# 打分阈值：低于此分视为未命中
_MATCH_THRESHOLD = 2.0

# 单次参与打分的记录上限，防止全表扫描
_SCAN_LIMIT = 500

_TOKEN_SPLIT = re.compile(r"[\s,，、;；/|+]+")


def _tokenize(keyword: str) -> tuple[list[str], set[str]]:
    """把关键词拆成检索词。

    返回 (全部检索词, 核心词集合)。核心词是剥离颜色/所属等修饰后的通用名，
    打分时权重更高，例如"我的黑色保温杯" -> 核心词"保温杯"。
    """
    raw_terms: list[str] = []
    for chunk in _TOKEN_SPLIT.split(keyword.strip()):
        chunk = chunk.strip()
        if chunk:
            raw_terms.append(chunk)

    core: set[str] = set()
    for term in raw_terms:
        stripped = term
        changed = True
        while changed and len(stripped) > 1:
            changed = False
            for mod in _MODIFIERS:
                if stripped.startswith(mod) and len(stripped) > len(mod):
                    stripped = stripped[len(mod):]
                    changed = True
                    break
        if len(stripped) >= 2:
            core.add(stripped)

    terms: list[str] = []
    seen = set()
    for t in list(core) + raw_terms:
        if t not in seen:
            seen.add(t)
            terms.append(t)
    return terms, core


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", "", text)
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def _score_item(item: LostFoundItem, terms: list[str], core: set[str]) -> float:
    title = item.title or ""
    description = item.description or ""
    location = item.location or ""
    score = 0.0

    for term in terms:
        weight = 1.5 if term in core else 1.0
        bonus = max(1.0, len(term) * 0.5)
        if term in title:
            score += 3.0 * weight * bonus
        elif term in description:
            score += 2.0 * weight * bonus
        elif term in location:
            score += 1.0 * weight

    # 二元组兜底：只在标题上比对，避免描述里的杂词造成误命中
    if core:
        title_grams = _bigrams(title)
        for term in core:
            shared = title_grams & _bigrams(term)
            if shared:
                score += 1.0 * len(shared)
    return score


def search_lost_found_items(
    db: Session,
    keyword: str,
    item_type: str = "all",
    limit: int = 5,
    candidate_limit: int = 8,
) -> dict:
    """检索失物招领记录。

    返回 {"matches": [(item, score)], "candidates": [item], "scanned": int}
    matches 为空时 candidates 提供最新待处理记录供语义判断。
    """
    limit = max(1, min(int(limit or 5), 20))
    candidate_limit = max(0, min(int(candidate_limit or 8), 20))

    query = db.query(LostFoundItem).filter(LostFoundItem.status == ItemStatus.OPEN)
    if item_type in ("lost", "found"):
        query = query.filter(LostFoundItem.type == ItemType(item_type))
    rows = query.order_by(LostFoundItem.created_at.desc()).limit(_SCAN_LIMIT).all()

    terms, core = _tokenize(keyword or "")
    scored: list[tuple[LostFoundItem, float]] = []
    if terms:
        for item in rows:
            s = _score_item(item, terms, core)
            if s >= _MATCH_THRESHOLD:
                scored.append((item, round(s, 2)))
    scored.sort(
        key=lambda x: (x[1], x[0].created_at.timestamp() if x[0].created_at else 0),
        reverse=True,
    )
    matches = scored[:limit]

    candidates: list[LostFoundItem] = []
    if not matches and candidate_limit:
        # 找丢失物品时，别人"捡到"的记录最相关，未限定类型时优先展示 found
        prefer_found = item_type == "all"
        ordered = sorted(
            rows,
            key=lambda it: (
                0 if (prefer_found and safe_enum_str(it.type, str(it.type)) == "found") else 1,
                -(it.created_at.timestamp() if it.created_at else 0),
            ),
        )
        candidates = ordered[:candidate_limit]

    return {"matches": matches, "candidates": candidates, "scanned": len(rows)}
