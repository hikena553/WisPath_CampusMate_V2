"""add group announcement and dismiss fields

Revision ID: a3c8f9e1b456
Revises: f2db7e9a2220
Create Date: 2026-08-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c8f9e1b456'
down_revision: Union[str, Sequence[str], None] = 'f2db7e9a2220'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('groups', sa.Column('announcement', sa.Text(), nullable=True))
    op.add_column('groups', sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    op.drop_column('groups', 'is_dismissed')
    op.drop_column('groups', 'announcement')
