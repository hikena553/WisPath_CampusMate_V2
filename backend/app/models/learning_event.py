"""学情数据底座：LearningEvent（xAPI 精简版）。

只提供写入与查询，不做业务判断；写入失败不得影响主流程（由 Service 层旁路兜底）。
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 行为主体（学生 / 教师）
    actor_id: Mapped[int] = mapped_column(index=True)
    # 行为谓语，如 leave.apply / growth.create / care.record / task.done
    verb: Mapped[str] = mapped_column(String(50), index=True)
    # 作用对象类型与 id，如 leave / 12
    object_type: Mapped[str] = mapped_column(String(50), index=True, default="")
    object_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    # 结果 / 上下文（JSON 文本，结构由写入方决定）
    result_json: Mapped[str | None] = mapped_column(Text, default=None)
    context_json: Mapped[str | None] = mapped_column(Text, default=None)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )