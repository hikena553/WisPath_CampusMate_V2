"""合并迁移分支：外部资讯 feed_key 归一化 与 study_sessions 补建

Revision ID: c1e3f4a5b6d7
Revises: c1a2b3c4d5e6, c1d2e3f4a5b6
Create Date: 2026-11-05 12:35:57.564670

c1a2b3c4d5e6（feed_key 数据订正）与 c1d2e3f4a5b6（study_sessions 补建）都基于
b9d0f2a4c6e8 各自成头，形成两个 head，启动期 `upgrade head` 会直接抛
Multiple head revisions 并退出。此迁移只做分支收束，不产生任何 DDL/DML：
两条分支的实际逻辑仍由各自迁移执行，可安全重复 apply。
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'c1e3f4a5b6d7'
down_revision: Union[str, Sequence[str], None] = ('c1a2b3c4d5e6', 'c1d2e3f4a5b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """仅收束分支，无结构/数据变更。"""
    pass


def downgrade() -> None:
    """拆分回两个头，同样无实际操作。"""
    pass
