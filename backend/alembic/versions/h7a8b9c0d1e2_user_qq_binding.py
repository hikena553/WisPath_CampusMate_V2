"""user qq binding for quick login

Revision ID: h7a8b9c0d1e2
Revises: g6f7a8b9c0d1
Create Date: 2026-10-22 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'g6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """个人资料可绑定 QQ，登录页据此提供 QQ 一键登录。"""
    op.add_column('users', sa.Column('qq', sa.String(length=20), nullable=True, comment='绑定的 QQ 号，用于一键登录'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'qq')
