"""审批流程引擎：流程定义（WorkflowDef）+ 流程实例（WorkflowInstance）。

设计（规划）：
- 节点定义 JSON 化，新增审批类型无需改代码；
- 引擎只提供 start / approve / reject / cancel 四个原语；
- 迁移期新旧并存：既有 leave / service / material 仍走原逻辑，逐个切换到本引擎。
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkflowStatus(str, enum.Enum):
    RUNNING = "running"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class WorkflowDef(Base):
    __tablename__ = "workflow_defs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    biz_type: Mapped[str] = mapped_column(String(50), index=True, default="")
    # 节点定义 JSON：[{"key": "tutor", "name": "辅导员审批", "approver_role": "teacher"}]
    nodes_json: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    def_id: Mapped[int] = mapped_column(index=True)
    biz_type: Mapped[str] = mapped_column(String(50), index=True, default="")
    biz_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    initiator_id: Mapped[int] = mapped_column(index=True)
    # 当前待办节点下标（指向 def.nodes 数组）
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[WorkflowStatus] = mapped_column(
        SAEnum(WorkflowStatus), default=WorkflowStatus.RUNNING, index=True
    )
    # 审批历史 JSON：[{"node": "tutor", "node_name": "...", "actor_id": 1, "action": "approve", "comment": "...", "at": "..."}]
    history_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )