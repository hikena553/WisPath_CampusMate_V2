"""匿名问卷互评服务：问卷管理 + 匿名提交 + 聚合结果。

匿名保证（设计硬约束）：
- 答卷表不存提交人；防重使用 HMAC 匿名令牌，令牌不落任何接口返回体；
- 结果接口只返回聚合分布；样本量 < MIN_SAMPLE 时不出均分与分布，杜绝小样本反推；
- 建议列表仅在样本足够时返回。
"""
import hashlib
import hmac
import json
import logging
import re
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.peer_survey import (
    PeerSurvey,
    PeerSurveyResponse,
    PeerSurveyStatus,
    PeerSurveyTargetType,
)

# 低于该样本量不出分布（防止小样本反推个人）
MIN_SAMPLE = 5

logger = logging.getLogger(__name__)


def _target_type(value: str | PeerSurveyTargetType | None) -> PeerSurveyTargetType:
    if isinstance(value, PeerSurveyTargetType):
        return value
    try:
        return PeerSurveyTargetType(value) if value else PeerSurveyTargetType.PEER
    except ValueError:
        return PeerSurveyTargetType.PEER


def _status(value: str | PeerSurveyStatus | None) -> PeerSurveyStatus:
    if isinstance(value, PeerSurveyStatus):
        return value
    try:
        return PeerSurveyStatus(value) if value else PeerSurveyStatus.DRAFT
    except ValueError:
        return PeerSurveyStatus.DRAFT


def _load_json(raw: str | None, fallback):
    if not raw:
        return fallback
    try:
        data = json.loads(raw)
        return data if isinstance(data, type(fallback)) else fallback
    except (ValueError, TypeError):
        return fallback


def compute_token(user_id: int, survey_id: int) -> str:
    """匿名令牌：HMAC 摘要，仅用于防重，不暴露身份。"""
    msg = f"peer-survey:{survey_id}:{user_id}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:48]


def _serialize_survey(
    survey: PeerSurvey, response_count: int = 0, my_submitted: bool = False
) -> dict:
    return {
        "id": survey.id,
        "title": survey.title,
        "target_type": survey.target_type.value if survey.target_type else "peer",
        "period": survey.period,
        "questions": _load_json(survey.questions_json, []),
        "status": survey.status.value if survey.status else "draft",
        "created_by": survey.created_by,
        "created_at": survey.created_at.isoformat() if survey.created_at else "",
        "response_count": response_count,
        "my_submitted": my_submitted,
    }


def create_survey(
    db: Session,
    *,
    created_by: int,
    title: str,
    target_type: str | PeerSurveyTargetType = PeerSurveyTargetType.PEER,
    period: str | None = None,
    questions: list[dict] | None = None,
    status: str | PeerSurveyStatus = PeerSurveyStatus.DRAFT,
) -> PeerSurvey:
    survey = PeerSurvey(
        title=title,
        target_type=_target_type(target_type),
        period=period,
        questions_json=json.dumps(questions or [], ensure_ascii=False),
        status=_status(status),
        created_by=created_by,
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


def get_survey(db: Session, survey_id: int) -> PeerSurvey | None:
    return db.query(PeerSurvey).filter(PeerSurvey.id == survey_id).first()


def list_surveys(db: Session, *, limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
    query = db.query(PeerSurvey)
    total = query.count()
    surveys = query.order_by(PeerSurvey.status.asc(), PeerSurvey.id.desc()).offset(offset).limit(limit).all()
    out: list[dict] = []
    for s in surveys:
        count = db.query(PeerSurveyResponse).filter(PeerSurveyResponse.survey_id == s.id).count()
        out.append(_serialize_survey(s, count))
    return out, total


def update_status(db: Session, survey: PeerSurvey, status: str) -> PeerSurvey:
    survey.status = _status(status)
    db.commit()
    db.refresh(survey)
    return survey


def submit_response(
    db: Session,
    *,
    survey: PeerSurvey,
    target_teacher_id: int,
    scores: dict[str, int],
    suggestion: str | None,
    token: str,
) -> PeerSurveyResponse:
    """匿名提交；同一问卷 + 同一被评人 + 同一令牌只允许一次（数据库唯一约束兜底）。"""
    response = PeerSurveyResponse(
        survey_id=survey.id,
        target_teacher_id=target_teacher_id,
        scores_json=json.dumps(scores or {}, ensure_ascii=False),
        suggestion=suggestion,
        anonymous_token=token,
    )
    db.add(response)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("你已提交过对该对象的评价")
    db.refresh(response)
    return response


def has_submitted(db: Session, survey_id: int, token: str) -> bool:
    return (
        db.query(PeerSurveyResponse)
        .filter(
            PeerSurveyResponse.survey_id == survey_id,
            PeerSurveyResponse.anonymous_token == token,
        )
        .first()
        is not None
    )


def aggregate(db: Session, survey: PeerSurvey, target_teacher_id: int | None = None) -> dict:
    """聚合结果：只出分布与均分，任何单条答卷不出接口。"""
    query = db.query(PeerSurveyResponse).filter(PeerSurveyResponse.survey_id == survey.id)
    if target_teacher_id is not None:
        query = query.filter(PeerSurveyResponse.target_teacher_id == target_teacher_id)
    responses = query.all()

    questions = _load_json(survey.questions_json, [])
    count = len(responses)
    enough = count >= MIN_SAMPLE

    stat_map: dict[str, dict] = {}
    for q in questions:
        key = q.get("key")
        if not key:
            continue
        stat_map[key] = {
            "key": key,
            "label": q.get("label") or key,
            "average": None,
            "distribution": {},
            "response_count": count,
        }

    if enough:
        sums: dict[str, float] = {k: 0.0 for k in stat_map}
        hits: dict[str, int] = {k: 0 for k in stat_map}
        for r in responses:
            scores = _load_json(r.scores_json, {})
            for key in stat_map:
                val = scores.get(key)
                if isinstance(val, (int, float)):
                    sums[key] += float(val)
                    hits[key] += 1
                    stat_map[key]["distribution"][str(int(val))] = (
                        stat_map[key]["distribution"].get(str(int(val)), 0) + 1
                    )
        for key, item in stat_map.items():
            item["average"] = round(sums[key] / hits[key], 2) if hits[key] else None

    averages = [i["average"] for i in stat_map.values() if i["average"] is not None]
    overall = round(sum(averages) / len(averages), 2) if averages else None

    suggestions: list[str] = []
    if enough:
        suggestions = [
            r.suggestion.strip()
            for r in responses
            if r.suggestion and r.suggestion.strip()
        ]

    return {
        "survey_id": survey.id,
        "title": survey.title,
        "target_teacher_id": target_teacher_id,
        "response_count": count,
        "min_sample": MIN_SAMPLE,
        "enough_sample": enough,
        "overall_average": overall,
        "questions": list(stat_map.values()),
        "suggestions": suggestions,
    }


def my_results(db: Session, teacher_id: int) -> list[dict]:
    """我的被评结果：按问卷聚合（只含被评对象是自己的答卷）。"""
    surveys = (
        db.query(PeerSurvey)
        .join(PeerSurveyResponse, PeerSurveyResponse.survey_id == PeerSurvey.id)
        .filter(PeerSurveyResponse.target_teacher_id == teacher_id)
        .distinct()
        .all()
    )
    out: list[dict] = []
    for s in surveys:
        data = aggregate(db, s, target_teacher_id=teacher_id)
        data["period"] = s.period
        data["target_type"] = s.target_type.value if s.target_type else "peer"
        out.append(data)
    return out


def serialize(survey: PeerSurvey, response_count: int = 0, my_submitted: bool = False) -> dict:
    return _serialize_survey(survey, response_count, my_submitted)


# ==================== AI 辅助发起问卷 ====================
_TARGET_LABEL = {
    PeerSurveyTargetType.PEER: "辅导员互评",
    PeerSurveyTargetType.STUDENT: "学生评辅导员",
}

# 大模型不可用时的本地兜底：按场景关键词推荐可聚合的评分维度
_DRAFT_RULES: list[tuple[tuple[str, ...], str, list[str]]] = [
    (
        ("教学", "课堂", "评教", "课程"),
        "课程教学反馈",
        ["讲解清晰", "课堂互动", "进度适中", "学习收获", "资料实用"],
    ),
    (
        ("活动", "比赛", "讲座", "培训"),
        "活动组织反馈",
        ["组织有序", "内容有用", "时间安排", "参与收获", "愿意推荐"],
    ),
    (
        ("家访", "家长", "家校", "沟通"),
        "家校沟通反馈",
        ["沟通及时", "信息清晰", "态度耐心", "协同有效"],
    ),
    (
        ("互评", "辅导员", "同事", "协作"),
        "辅导员互评",
        ["关心学生", "处事公正", "沟通及时", "工作负责"],
    ),
]

_DEFAULT_LABELS = {
    PeerSurveyTargetType.PEER: ["关心学生", "处事公正", "沟通及时", "工作负责"],
    PeerSurveyTargetType.STUDENT: ["讲解清晰", "答疑及时", "要求明确", "关注成长", "愿意推荐"],
}


def _fallback_draft(scene: str, target: PeerSurveyTargetType) -> dict:
    hit = next((r for r in _DRAFT_RULES if any(k in scene for k in r[0])), None)
    labels = hit[2] if hit else _DEFAULT_LABELS[target]
    base = hit[1] if hit else (scene or _TARGET_LABEL[target])
    title = f"{datetime.now().year}年{_TARGET_LABEL[target]} · {base}"[:200]
    questions = [
        {"key": f"q{i + 1}", "label": label, "max": 5}
        for i, label in enumerate(labels)
    ]
    return {"title": title, "questions": questions, "source": "rule"}


def _clean_questions(raw: object) -> list[dict]:
    """清洗模型输出：3–8 个维度、中文标签、ASCII 键名、1–5 分。"""
    if not isinstance(raw, list):
        return []
    labels: list[str] = []
    keys: list[str] = []
    for item in raw:
        if isinstance(item, str):
            label, key = item.strip(), ""
        elif isinstance(item, dict):
            label = str(item.get("label") or item.get("name") or "").strip()
            key = str(item.get("key") or "").strip()
        else:
            continue
        label = label[:14]
        if not label or label in labels:
            continue
        key = re.sub(r"[^a-z0-9_]", "", key.lower())[:24] or f"q{len(labels) + 1}"
        if key in keys:
            key = f"q{len(labels) + 1}"
        labels.append(label)
        keys.append(key)
        if len(labels) >= 8:
            break
    return [
        {"key": keys[i], "label": labels[i], "max": 5}
        for i in range(len(labels))
    ]


async def ai_draft(scene: str, target_type: str | PeerSurveyTargetType) -> dict:
    """AI 辅助发起：场景描述 → 问卷标题 + 评价维度；模型不可用时本地规则兜底。"""
    target = _target_type(target_type)
    scene = (scene or "").strip()[:200]
    fallback = _fallback_draft(scene, target)

    prompt = (
        "你是高校辅导员的问卷设计助手。请根据下面的使用场景，设计一份匿名评价问卷。\n"
        f"评价类型：{_TARGET_LABEL[target]}；使用场景：{scene or '常规匿名互评'}。\n"
        "要求：\n"
        "1. 标题不超过 40 字，说明周期或对象；\n"
        "2. 给出 4–6 个可量化、可聚合的评价维度，每个维度为 1–5 分；\n"
        "3. 维度名称不超过 8 个汉字，具体可观察，不要空泛套话；\n"
        "4. 只输出 JSON，不要解释。格式："
        '{"title":"标题","questions":[{"key":"english_key","label":"维度名称","max":5}]}'
    )
    try:
        from app.services.llm_service import _parse_json_loose, complete

        raw = await complete(prompt, temperature=0.35, max_tokens=700)
        data = _parse_json_loose(raw) or {}
        questions = _clean_questions(data.get("questions"))
        if len(questions) < 3:
            raise ValueError("模型未返回足够的评价维度")
        title = str(data.get("title") or "").strip()[:200] or fallback["title"]
        return {"title": title, "questions": questions, "source": "ai"}
    except Exception:
        # 未配置模型 / 网络异常 / 输出不合法，一律静默降级，保证按钮永远有结果
        logger.warning("问卷 AI 生成失败，使用本地规则兜底", exc_info=True)
        return fallback


def now() -> datetime:
    return datetime.now()