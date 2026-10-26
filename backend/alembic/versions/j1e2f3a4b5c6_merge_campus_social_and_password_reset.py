"""合并迁移分支：校园资讯互动 与 密码自助找回

Revision ID: j1e2f3a4b5c6
Revises: c7d8e9f0a1b2, i8b9c0d1e2f3
Create Date: 2026-10-26 15:00:00.000000

两条分支都从 b2c3d4e5f6a7 展开：
- c7d8e9f0a1b2：校园资讯互动（点赞/评论/转发/浏览）；
- i8b9c0d1e2f3：随远端合入的账号体系链路，末端是密码自助找回。

并行开发导致版本图出现两个 head，启动时 `alembic upgrade head` 会直接抛
MultipleHeads。这里用一个空的合并迁移把两条分支收成单 head；它不改任何表结构，
只是让后续迁移有唯一的继承关系。
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'j1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = ('c7d8e9f0a1b2', 'i8b9c0d1e2f3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """两条分支均已各自完成建表，合并点无需额外操作。"""


def downgrade() -> None:
    """回退合并点只需拆回两条分支，不涉及表结构。"""
