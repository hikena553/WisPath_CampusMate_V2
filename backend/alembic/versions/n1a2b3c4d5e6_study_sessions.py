"""自习室专注记录表

Revision ID: n1a2b3c4d5e6
Revises: m8n9p0q1r2s3
Create Date: 2026-10-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'n1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'm8n9p0q1r2s3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    # 幂等：开发库可能已手动建过表，避免 DuplicateTable 卡死整条 upgrade head
    if not inspector.has_table("study_sessions"):
        op.create_table(
            'study_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('mode', sa.String(length=20), nullable=False, server_default='focus'),
            sa.Column('task_title', sa.String(length=200), nullable=True),
            sa.Column('planned_minutes', sa.Integer(), nullable=False, server_default='25'),
            sa.Column('actual_minutes', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('study_date', sa.Date(), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_study_sessions_id'), 'study_sessions', ['id'], unique=False)
        op.create_index(op.f('ix_study_sessions_student_id'), 'study_sessions', ['student_id'], unique=False)
        op.create_index(op.f('ix_study_sessions_study_date'), 'study_sessions', ['study_date'], unique=False)


def downgrade() -> None:
    op.drop_table('study_sessions')
