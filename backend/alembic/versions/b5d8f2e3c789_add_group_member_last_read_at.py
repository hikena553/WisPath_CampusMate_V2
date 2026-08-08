"""add last_read_at to group_members

Revision ID: b5d8f2e3c789
Revises: a3c8f9e1b456
Create Date: 2026-08-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d8f2e3c789'
down_revision: Union[str, Sequence[str], None] = 'a3c8f9e1b456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('group_members', sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('group_members', 'last_read_at')
