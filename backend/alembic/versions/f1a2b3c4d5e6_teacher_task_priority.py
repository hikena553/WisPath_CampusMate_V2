"""teacher tasks: priority and remind_at

Revision ID: f1a2b3c4d5e6
Revises: c3d4e5f6a7b8
Create Date: 2026-10-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('teacher_tasks') as batch_op:
        batch_op.add_column(
            sa.Column(
                'priority',
                sa.Enum('HIGH', 'MID', 'LOW', name='taskpriority'),
                nullable=False,
                server_default=sa.text("'MID'"),
            )
        )
        batch_op.add_column(sa.Column('remind_at', sa.Date(), nullable=True))
        batch_op.create_index(op.f('ix_teacher_tasks_priority'), ['priority'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('teacher_tasks') as batch_op:
        batch_op.drop_index(op.f('ix_teacher_tasks_priority'))
        batch_op.drop_column('remind_at')
        batch_op.drop_column('priority')