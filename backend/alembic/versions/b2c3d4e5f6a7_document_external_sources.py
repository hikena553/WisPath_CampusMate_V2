"""document external data sources (network url)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-20 10:00:00.000000

知识库数据源扩展：documents 表新增 source_type（file/url）与 source_url，
使知识库可直接纳入「项目需要引进的外部数据源」（网络数据位置/外部文件）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'documents',
        sa.Column('source_type', sa.String(length=20), nullable=False, server_default='file'),
    )
    op.add_column(
        'documents',
        sa.Column('source_url', sa.String(length=700), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'source_url')
    op.drop_column('documents', 'source_type')