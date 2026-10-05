"""add rule_code to teacher_tasks (alert pipeline idempotency)

Revision ID: b8c9d0e1f2a3
Revises: a6b7c8d9e0f1
Create Date: 2026-10-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('teacher_tasks') as batch_op:
        batch_op.add_column(sa.Column('rule_code', sa.String(length=50), nullable=True))
        batch_op.create_index(
            op.f('ix_teacher_tasks_rule_code'), ['rule_code'], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('teacher_tasks') as batch_op:
        batch_op.drop_index(op.f('ix_teacher_tasks_rule_code'))
        batch_op.drop_column('rule_code')