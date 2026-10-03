"""add pinned_at/archived_at/deleted_at to conversations

Revision ID: d7b1c4f0a925
Revises: 5191403c19a4
Create Date: 2026-10-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7b1c4f0a925'
down_revision: Union[str, Sequence[str], None] = '5191403c19a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("pinned_at", "archived_at", "deleted_at")


def upgrade() -> None:
    # 存在性探测：基线迁移之前的旧库由 create_all 建表，可能已含这三个字段
    # （alembic 接管前的历史库），直接 add_column 会抛 duplicate column name。
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("conversations")}
    for name in _COLUMNS:
        if name not in existing:
            op.add_column('conversations', sa.Column(name, sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('conversations', 'deleted_at')
    op.drop_column('conversations', 'archived_at')
    op.drop_column('conversations', 'pinned_at')