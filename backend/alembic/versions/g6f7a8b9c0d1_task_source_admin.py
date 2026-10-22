"""teacher tasks: add ADMIN source type (admin dispatched tasks)

Revision ID: g6f7a8b9c0d1
Revises: f4d5e6f7a8b9
Create Date: 2026-10-22 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'f4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUM_OLD = ('AI_SUGGEST', 'FOLLOW_UP', 'APPROVAL', 'CARE_PLAN', 'ALERT', 'MANUAL')
_ENUM_NEW = _ENUM_OLD + ('ADMIN',)


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('teacher_tasks') as batch_op:
        batch_op.alter_column(
            'source_type',
            existing_type=sa.Enum(*_ENUM_OLD, name='tasksourcetype'),
            type_=sa.Enum(*_ENUM_NEW, name='tasksourcetype'),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # 先把已下发（ADMIN）的任务回退为手动任务，避免缩枚举时出现非法值
    op.execute("UPDATE teacher_tasks SET source_type='MANUAL' WHERE source_type='ADMIN'")
    with op.batch_alter_table('teacher_tasks') as batch_op:
        batch_op.alter_column(
            'source_type',
            existing_type=sa.Enum(*_ENUM_NEW, name='tasksourcetype'),
            type_=sa.Enum(*_ENUM_OLD, name='tasksourcetype'),
            existing_nullable=False,
        )