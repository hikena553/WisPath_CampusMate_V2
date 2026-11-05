"""合并迁移分支：媒体转播间隔 与 教师教学域

Revision ID: u9d0e1f2a3b4
Revises: s1a2b3c4d5e6, t8c9d0e1f2a3
Create Date: 2026-11-04 14:50:00.000000

两条分支都从 p7b8c9d0e1f2 展开：
- s1a2b3c4d5e6：媒体账号转播间隔；
- t8c9d0e1f2a3：教师教学域相关表与字段。

并行开发导致版本图出现两个 head，启动时 `alembic upgrade head` 会直接抛
MultipleHeads。这里用一个空的合并迁移把两条分支收成单 head；它不改任何表结构，
只是让后续迁移有唯一的继承关系。
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'u9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = ('s1a2b3c4d5e6', 't8c9d0e1f2a3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """两条分支均已各自完成建表，合并点无需额外操作。"""


def downgrade() -> None:
    """回退合并点只需拆回两条分支，不涉及表结构。"""
