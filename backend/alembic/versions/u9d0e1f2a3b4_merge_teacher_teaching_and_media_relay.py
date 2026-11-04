"""合并迁移分支：教师端教学域 与 资讯账号发帖频率

Revision ID: u9d0e1f2a3b4
Revises: s1a2b3c4d5e6, t8c9d0e1f2a3
Create Date: 2026-11-04

两条分支都从 p7b8c9d0e1f2 展开：
- s1a2b3c4d5e6：q8 → r9 → s0 → s1，资讯账号 / 发帖频率链路，本机库已执行；
- t8c9d0e1f2a3：教师端教学域（courses.teacher_id + 三张教学表），库中未执行。

并行开发让版本图出现两个 head，启动时 `alembic upgrade head` 直接抛
MultipleHeads（与 j1e2f3a4b5c6 处理过的那次同源）。这里用一个空的合并迁移
把两条分支收成单 head，不改任何表结构；教学域的 DDL 仍由 t8c9d0e1f2a3
负责，合并后首次启动会自动把它补跑。
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'u9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = ('s1a2b3c4d5e6', 't8c9d0e1f2a3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """两条分支各自完成 DDL，合并点无需额外操作。"""


def downgrade() -> None:
    """拆回两条分支，不涉及表结构。"""
