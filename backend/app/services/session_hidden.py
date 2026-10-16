"""会话删除（用户级隐藏）：单聊与群聊共用的一套"隐藏水位"读写。

删除只作用于本人的会话列表，因此判定标准是消息 id 而非时间：
隐藏时记下该会话最后一条消息的 id，之后出现更大的 id 即视为新消息，
会话自动恢复展示。
"""
from sqlalchemy.orm import Session

from app.models.message import MessageSessionHidden


def hidden_watermarks(db: Session, user_id: int) -> dict[str, int]:
    """当前用户已删除会话的水位（session_key → 删除时刻最后一条消息 id）。"""
    rows = db.query(MessageSessionHidden).filter(MessageSessionHidden.user_id == user_id).all()
    return {r.session_key: r.hidden_upto_id for r in rows}


def is_hidden(watermarks: dict[str, int], session_key: str, latest_id: int) -> bool:
    """会话是否仍处于已删除状态：水位之后没有更新的消息才算仍未恢复。"""
    return watermarks.get(session_key, -1) >= latest_id


def hide_session(db: Session, user_id: int, session_key: str, latest_id: int) -> None:
    """写入 / 更新隐藏水位（重复删除同一会话时刷新水位）。"""
    row = db.query(MessageSessionHidden).filter(
        MessageSessionHidden.user_id == user_id,
        MessageSessionHidden.session_key == session_key,
    ).first()
    if row:
        row.hidden_upto_id = latest_id
    else:
        db.add(MessageSessionHidden(user_id=user_id, session_key=session_key, hidden_upto_id=latest_id))