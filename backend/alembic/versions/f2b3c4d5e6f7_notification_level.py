"""notifications: level for graded reminding (normal/important/urgent)

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-22 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('notifications') as batch_op:
        batch_op.add_column(
            sa.Column(
                'level',
                sa.Enum('NORMAL', 'IMPORTANT', 'URGENT', name='urgencylevel'),
                nullable=False,
                server_default=sa.text("'NORMAL'"),
            )
        )
        batch_op.create_index(op.f('ix_notifications_level'), ['level'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('notifications') as batch_op:
        batch_op.drop_index(op.f('ix_notifications_level'))
        batch_op.drop_column('level')