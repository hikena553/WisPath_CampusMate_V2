"""补建 study_sessions 表（库与迁移链漂移修复）

Revision ID: c1d2e3f4a5b6
Revises: b9d0f2a4c6e8
Create Date: 2026-11-05 12:25:00.000000

n1a2b3c4d5e6 已把版本号推到 head，但部分环境的真实库里没有 study_sessions
（备份恢复 / 手工 stamp 导致版本号虚高），启动期 schema 对账会持续报
「模型表 study_sessions 在库中不存在」，自习室相关接口全部 500。

alembic 不会重跑已标记执行过的迁移，因此这里用一份幂等迁移把表补回来：
has_table 为真时直接跳过，可安全重复执行，不影响结构正常的库。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b9d0f2a4c6e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """补建 study_sessions；已存在则跳过。"""
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("study_sessions"):
        return

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
    """回滚：删除本迁移补建的表。"""
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("study_sessions"):
        op.drop_table('study_sessions')
