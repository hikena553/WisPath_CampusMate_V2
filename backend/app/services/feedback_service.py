"""反馈模块业务逻辑：列表/详情/提交/回复，屏蔽 ORM 细节，供 API 层调用。"""
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import jieba
except ModuleNotFoundError:  # pragma: no cover
    # 环境未安装 jieba 时，回退加载项目 vendor_packages 目录内置的同版本副本
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor_packages"))
    import jieba
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.feedback import Feedback, FeedbackType, FeedbackStatus
from app.models.user import User, UserRole
from app.schemas.feedback import FeedbackCreate, FeedbackOut, FeedbackReply, FeedbackWordOut

_DT_FMT = "%Y-%m-%d %H:%M:%S"

# 词云停用词：常见虚词/口语词，过滤后保留高信息量关键词
_STOPWORDS = {
    "的", "了", "和", "是", "在", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "有", "就", "不", "都", "也", "很", "吗", "啊", "呢", "吧", "个", "这", "那",
    "等", "与", "及", "或", "从", "去", "为", "之", "对", "到", "中", "上", "下",
    "一个", "没有", "可以", "希望", "觉得", "感觉", "问题", "反馈", "建议",
}


def _fmt(dt: Optional[datetime]) -> str:
    return dt.strftime(_DT_FMT) if dt else ""


def _to_out(f: Feedback, user_name: Optional[str], replier_name: Optional[str]) -> FeedbackOut:
    return FeedbackOut(
        id=f.id,
        user_id=f.user_id,
        user_name=user_name,
        type=f.type.value if f.type else "other",
        title=f.title,
        content=f.content,
        contact=f.contact,
        status=f.status.value if f.status else "pending",
        reply=f.reply,
        replied_by=f.replied_by,
        replier_name=replier_name,
        replied_at=_fmt(f.replied_at),
        created_at=_fmt(f.created_at),
    )


def _resolve_names(db: Session, f: Feedback) -> tuple[Optional[str], Optional[str]]:
    user = db.query(User).filter(User.id == f.user_id).first()
    replier = db.query(User).filter(User.id == f.replied_by).first() if f.replied_by else None
    return (user.name if user else None, replier.name if replier else None)


def create_feedback(db: Session, current_user: User, data: FeedbackCreate) -> FeedbackOut:
    feedback = Feedback(
        user_id=current_user.id,
        type=FeedbackType(data.type) if data.type in [t.value for t in FeedbackType] else FeedbackType.OTHER,
        title=data.title,
        content=data.content,
        contact=data.contact,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return _to_out(feedback, current_user.name, None)


def list_feedbacks(
    db: Session,
    current_user: User,
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> list[FeedbackOut]:
    query = db.query(Feedback)

    # 非管理员只能看自己的反馈
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Feedback.user_id == current_user.id)

    if status:
        query = query.filter(Feedback.status == status)
    if type:
        query = query.filter(Feedback.type == type)

    feedbacks = (
        query.order_by(desc(Feedback.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for f in feedbacks:
        user_name, replier_name = _resolve_names(db, f)
        result.append(_to_out(f, user_name, replier_name))
    return result


def get_feedback_detail(db: Session, current_user: User, feedback_id: int) -> FeedbackOut:
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    # 非管理员只能看自己的反馈
    if current_user.role != UserRole.ADMIN and feedback.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问")

    user_name, replier_name = _resolve_names(db, feedback)
    return _to_out(feedback, user_name, replier_name)


def reply_feedback(db: Session, current_user: User, feedback_id: int, data: FeedbackReply) -> FeedbackOut:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可回复")

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    feedback.reply = data.reply
    feedback.status = (
        FeedbackStatus(data.status)
        if data.status in [s.value for s in FeedbackStatus]
        else FeedbackStatus.RESOLVED
    )
    feedback.replied_by = current_user.id
    feedback.replied_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(feedback)

    user_name = db.query(User).filter(User.id == feedback.user_id).first().name
    return _to_out(feedback, user_name, current_user.name)


def get_feedback_word_cloud(db: Session, current_user: User, top_n: int = 60) -> list[FeedbackWordOut]:
    """基于全部反馈的标题+内容，用 jieba 分词统计关键词频次，返回词云数据。

    管理员统计全部反馈；普通用户仅统计自己的反馈。
    """
    query = db.query(Feedback)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Feedback.user_id == current_user.id)

    feedbacks = query.all()
    pieces = []
    for f in feedbacks:
        if f.title:
            pieces.append(f.title)
        if f.content:
            pieces.append(f.content)

    full_text = "\n".join(pieces)
    if not full_text.strip():
        return []

    counter: Counter = Counter()
    for word in jieba.lcut(full_text):
        w = word.strip()
        if not w or len(w) < 2:
            continue
        if w in _STOPWORDS:
            continue
        # 仅保留中文/英文/数字混合的真实词条，丢弃纯标点、空白等
        if not re.search(r"[\u4e00-\u9fa5a-zA-Z0-9]", w):
            continue
        if re.fullmatch(r"[\d\W_]+", w):
            continue
        counter[w] += 1

    return [
        FeedbackWordOut(word=w, count=c)
        for w, c in counter.most_common(top_n)
    ]