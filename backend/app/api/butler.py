"""小绵管家：面向教师端消息页 / 学生端消息中心的通用智能管家会话。

两条核心能力（前端以置顶会话形式呈现，设计语言对齐钉钉）：
1. 自动推送最新资讯 —— 复用外部资讯中心（``external_feed_items``）产出「资讯简报」；
2. 总结对话内容 —— 复用 LLM 服务的一次性补全能力，对前端传入的会话消息做摘要。

设计取舍：
- 简报文案优先本地确定性生成（LLM 未配置 / 网络异常也能出文案，不阻塞推送）；
- 对话与总结在 LLM 不可用时给出可读的降级回复，绝不向前端抛 500。
"""
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.feed import ExternalFeedItem
from app.models.user import User
from app.services import llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/butler", tags=["小绵管家"])

# 资讯来源分类 → 中文标签，用于简报文案
_TYPE_LABELS = {
    "papers": "论文速递",
    "agents": "智能体榜",
    "opensource": "开源热榜",
    "news": "行业要闻",
    "ai_news": "AI 行业",
    "rankings": "权威榜单",
    "cn_ai": "国产模型",
}

# 所有可选资讯类型（含 all）
_ALLOWED_TYPES = tuple(_TYPE_LABELS.keys()) + ("all",)

# 对话总结可接受的最大消息条数（防止超长上下文）
_MAX_HISTORY = 40
# 单条消息截断长度
_MAX_MSG_CHARS = 800


class ButlerChatIn(BaseModel):
    """管家对话入参。"""

    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] | None = None


class ButlerSummarizeIn(BaseModel):
    """对话总结入参：由前端传入待总结的消息序列。"""

    messages: list[dict] = Field(default_factory=list)


class ButlerFeedItem(BaseModel):
    id: int
    title: str
    summary: str
    link: str
    source_name: str
    source_type: str
    source_label: str
    published_at: str | None


class ButlerBriefingOut(BaseModel):
    generated_at: str
    greeting: str
    digest: str
    items: list[ButlerFeedItem]


class ButlerReplyOut(BaseModel):
    reply: str


def _greeting(user: User | None) -> str:
    """按当前时段 + 角色生成问候语。"""
    hour = datetime.now().hour
    if hour < 6:
        period = "凌晨好"
    elif hour < 12:
        period = "早上好"
    elif hour < 14:
        period = "中午好"
    elif hour < 18:
        period = "下午好"
    else:
        period = "晚上好"
    role_name = {"student": "同学", "teacher": "老师", "admin": "管理员"}
    who = role_name.get(user.role.value, "同学") if user else "同学"
    return f"{period}，{who}"


def _compose_digest(greeting: str, items: list[ButlerFeedItem]) -> str:
    """本地确定性生成简报正文（不依赖 LLM）。"""
    today = date.today().isoformat()
    if not items:
        return (
            f"{greeting}，今天是 {today}。资讯源暂未抓取到新内容，"
            "你可以稍后点「刷新资讯」再试，或直接问我校园里的问题。"
        )
    lines = [f"{greeting}，今天是 {today}，我为你精选了 {len(items)} 条最新资讯："]
    for idx, it in enumerate(items, start=1):
        brief = (it.summary or "").strip().replace("\n", " ")
        if len(brief) > 60:
            brief = brief[:60] + "…"
        suffix = f"（{it.source_label}）" if it.source_label else ""
        lines.append(f"{idx}. {it.title}{suffix}" + (f" —— {brief}" if brief else ""))
    lines.append("需要我展开哪一条，或帮你总结最近的对话，直接告诉我就行。")
    return "\n".join(lines)


@router.get("/briefing", response_model=ButlerBriefingOut)
def briefing(
    limit: int = Query(6, ge=1, le=20, description="推送条数"),
    source_type: str = Query("all", description="资讯分类，默认 all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成「最新资讯简报」：管家自动推送的消息内容。

    返回结构供前端渲染为一条管家主动消息（含逐条资讯卡片）。
    """
    stype = source_type if source_type in _ALLOWED_TYPES else "all"
    query = db.query(ExternalFeedItem)
    if stype != "all":
        query = query.filter(ExternalFeedItem.source_type == stype)
    rows = (
        query.order_by(ExternalFeedItem.published_at.desc(), ExternalFeedItem.id.desc())
        .limit(limit)
        .all()
    )

    items = [
        ButlerFeedItem(
            id=r.id,
            title=r.title or "",
            summary=r.summary or "",
            link=r.link or "",
            source_name=r.source_name or "",
            source_type=r.source_type or "",
            source_label=_TYPE_LABELS.get(r.source_type or "", "校园资讯"),
            published_at=r.published_at.isoformat() if r.published_at else None,
        )
        for r in rows
    ]

    greeting = _greeting(current_user)
    return ButlerBriefingOut(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        greeting=greeting,
        digest=_compose_digest(greeting, items),
        items=items,
    )


def _format_history(history: list[dict] | None) -> str:
    """把会话历史整理成提示词可读的文本。"""
    if not history:
        return ""
    lines: list[str] = []
    for msg in history[-_MAX_HISTORY:]:
        if not isinstance(msg, dict):
            continue
        role = "用户" if msg.get("role") == "user" else "管家"
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        if len(content) > _MAX_MSG_CHARS:
            content = content[:_MAX_MSG_CHARS] + "…"
        lines.append(f"{role}：{content}")
    return "\n".join(lines)


def _fallback_summary(messages: list[dict]) -> str:
    """LLM 不可用时的本地降级摘要：抽取式要点罗列。"""
    user_points: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = str(msg.get("content") or "").strip().replace("\n", " ")
        if not content:
            continue
        if len(content) > 40:
            content = content[:40] + "…"
        user_points.append(content)
    if not user_points:
        return "这段对话暂无可总结的内容，你可以先发几条消息，我再帮你总结。"
    tail = user_points[-6:]
    body = "\n".join(f"{i}. {p}" for i, p in enumerate(tail, start=1))
    return f"这段对话里你主要提到了这几点：\n{body}\n如需展开或补充，可以直接说。"


@router.post("/summarize", response_model=ButlerReplyOut)
async def summarize(
    body: ButlerSummarizeIn,
    current_user: User = Depends(get_current_user),
):
    """总结对话内容：把前端传入的会话消息压缩为要点摘要。"""
    messages = [m for m in (body.messages or []) if isinstance(m, dict)]
    if not messages:
        return ButlerReplyOut(reply="这段对话暂无可总结的内容，你可以先发几条消息，我再帮你总结。")

    transcript = _format_history(messages)
    if not transcript:
        return ButlerReplyOut(reply=_fallback_summary(messages))

    prompt = (
        "你是校园智能管家「小绵」，请阅读下面这段对话，输出简洁的中文总结。\n"
        "要求：\n"
        "1. 先用一句话概括对话主题；\n"
        "2. 再用不超过 5 条要点列出关键信息与待办事项；\n"
        "3. 纯文本，不使用 Markdown 标记（#、代码块等），不要编造对话中没有的信息。\n\n"
        f"【对话记录】\n{transcript}\n\n【总结】"
    )
    try:
        reply = await llm_service.complete(prompt, max_tokens=600)
        if reply:
            return ButlerReplyOut(reply=reply)
    except Exception:
        logger.exception("小绵管家总结对话失败，降级为本地摘要")
    return ButlerReplyOut(reply=_fallback_summary(messages))


@router.post("/chat", response_model=ButlerReplyOut)
async def chat(
    body: ButlerChatIn,
    current_user: User = Depends(get_current_user),
):
    """与管家对话：支持问答；识别「总结」类意图时转为对话总结。"""
    message = body.message.strip()
    if not message:
        return ButlerReplyOut(reply="我在的，有什么可以帮你？")

    # 明确要求总结当前对话 → 走总结通道
    if any(k in message for k in ("总结", "汇总", "概括一下", "小结")):
        return await summarize(ButlerSummarizeIn(messages=body.history or []), current_user)

    transcript = _format_history(body.history)
    context = f"\n\n【最近对话】\n{transcript}" if transcript else ""
    prompt = (
        "你是校园智能管家「小绵」，服务绵阳城市学院的师生。"
        "回答要亲切、简洁，纯文本输出，不使用 Markdown 标记，控制在 150 字以内。"
        "涉及个人隐私数据或不确定的信息时，如实说明并建议对方咨询老师或辅导员。"
        f"{context}\n\n【用户提问】\n{message}\n\n【回答】"
    )
    try:
        reply = await llm_service.complete(prompt, max_tokens=500)
        if reply:
            return ButlerReplyOut(reply=reply)
    except Exception:
        logger.exception("小绵管家对话失败")
    return ButlerReplyOut(
        reply="我暂时连不上智能服务，你可以稍后再试；也可以点「最新资讯」看看我为你准备的校园动态。"
    )