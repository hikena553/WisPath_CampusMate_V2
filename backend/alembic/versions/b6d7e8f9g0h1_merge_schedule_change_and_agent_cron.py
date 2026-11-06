"""merge: 排课调整申请 与 下线 agent_cron_tasks 两条分支

Revision ID: b6d7e8f9g0h1
Revises: a5c6d7e8f9g0, c4d5e6f7a8b9
Create Date: 2026-11-07 01:30:00.000000

两条 head 的来源：
- ``a5c6d7e8f9g0``：新增 schedule_change_requests（本次排课调整功能）；
- ``c4d5e6f7a8b9``：下线 Agent 定时任务、删除 agent_cron_tasks 表（并行开发产生）。

本迁移只做合并，不改任何表结构；合并后 ``alembic upgrade head`` 才能找到唯一 head。
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'b6d7e8f9g0h1'
down_revision: Union[str, Sequence[str], None] = ('a5c6d7e8f9g0', 'c4d5e6f7a8b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """合并分支，无 DDL 变更。"""
    pass


def downgrade() -> None:
    """回退合并点，重新分裂为两条 head。"""
    pass
