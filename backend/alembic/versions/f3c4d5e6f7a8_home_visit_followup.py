"""home visits: follow-up status for care loop closure

Revision ID: f3c4d5e6f7a8
Revises: f2b3c4d5e6f7
Create Date: 2026-10-22 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'f2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('home_visit_records') as batch_op:
        batch_op.add_column(
            sa.Column(
                'follow_up_status',
                sa.Enum('PENDING', 'DONE', name='followupstatus'),
                nullable=False,
                server_default=sa.text("'PENDING'"),
            )
        )
        batch_op.add_column(sa.Column('follow_up_done_at', sa.DateTime(), nullable=True))
        batch_op.create_index(
            op.f('ix_home_visit_records_follow_up_status'), ['follow_up_status'], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('home_visit_records') as batch_op:
        batch_op.drop_index(op.f('ix_home_visit_records_follow_up_status'))
        batch_op.drop_column('follow_up_done_at')
        batch_op.drop_column('follow_up_status')