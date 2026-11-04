"""合并迁移分支：社区帖子配图 与 快捷登录/资讯站链路

Revision ID: b9d0f2a4c6e8
Revises: v0e1f2a3b4c5, z4b5c6d7e8f9
Create Date: 2026-11-05

u9d0e1f2a3b4 合并之后又并行展开了两条分支：
- v0e1f2a3b4c5：community_posts.images 社区帖子配图；
- v0d1e2f3a4b5 → w1e2f3a4b5c6 → x2f3a4b5c6d7 → y3a4b5c6d7e8
  → z4b5c6d7e8f9：开源参考下线、资讯站三级结构、媒体账号拆分、QQ/SMS 快捷登录。

远程分支合并后版本图再次出现两个 head，启动时 `alembic upgrade head` 会抛
MultipleHeads。这里用一个空的合并迁移把两条分支收成单 head，不改任何表结构。
v0e1f2a3b4c5 的 upgrade 可重入（images 列已存在会自动跳过），即使本机库已手工
加过该列也能安全补跑并把版本号盖到合并点。
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'b9d0f2a4c6e8'
down_revision: Union[str, Sequence[str], None] = ('v0e1f2a3b4c5', 'z4b5c6d7e8f9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """两条分支各自完成 DDL，合并点无需额外操作。"""


def downgrade() -> None:
    """拆回两条分支，不涉及表结构。"""
