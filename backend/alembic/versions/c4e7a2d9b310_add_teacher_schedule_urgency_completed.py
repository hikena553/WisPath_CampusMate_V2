"""add urgency/completed/completed_at to teacher_schedules

Revision ID: c4e7a2d9b310
Revises: b5d8f2e3c789
Create Date: 2026-09-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e7a2d9b310'
down_revision: Union[str, Sequence[str], None] = 'ef8ceac9af06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # urgency 与 teacher_announcements.urgency 保持一致：ENUM 存枚举成员名
    op.add_column('teacher_schedules', sa.Column('urgency', sa.Enum('NORMAL', 'IMPORTANT', 'URGENT'), nullable=False, server_default='NORMAL'))
    op.add_column('teacher_schedules', sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('teacher_schedules', sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('teacher_schedules', 'completed_at')
    op.drop_column('teacher_schedules', 'completed')
    op.drop_column('teacher_schedules', 'urgency')