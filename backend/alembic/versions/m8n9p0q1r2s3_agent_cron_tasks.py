"""Agent 定时任务表

Revision ID: m8n9p0q1r2s3
Revises: k2f3a4b5c6d7
Create Date: 2026-10-29 00:00:00.000000

每个任务绑定一个专属会话：执行输出全部追加在同一会话，学生可回溯历史运行，
会话列表也不会被定时输出刷屏（specs/2026-10-29-agent-cron-task-design.md §1）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'm8n9p0q1r2s3'
down_revision: Union[str, Sequence[str], None] = 'k2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    # 幂等：开发库可能已手动建过表，避免 DuplicateTable 卡死整条 upgrade head
    if not inspector.has_table("agent_cron_tasks"):
        op.create_table(
            'agent_cron_tasks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('prompt', sa.Text(), nullable=False),
            sa.Column('schedule_kind', sa.Enum('DAILY', 'WEEKLY', 'INTERVAL', name='cronschedulekind'), nullable=False),
            sa.Column('hour', sa.Integer(), nullable=True),
            sa.Column('minute', sa.Integer(), nullable=True),
            sa.Column('weekday', sa.Integer(), nullable=True),
            sa.Column('interval_hours', sa.Integer(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('conversation_id', sa.Integer(), nullable=False),
            sa.Column('created_via', sa.Enum('CHAT', 'MANUAL', name='crontasksource'), nullable=False, server_default='CHAT'),
            sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_agent_cron_tasks_id'), 'agent_cron_tasks', ['id'], unique=False)
        op.create_index(op.f('ix_agent_cron_tasks_user_id'), 'agent_cron_tasks', ['user_id'], unique=False)
        op.create_index(op.f('ix_agent_cron_tasks_enabled'), 'agent_cron_tasks', ['enabled'], unique=False)
        op.create_index(op.f('ix_agent_cron_tasks_next_run_at'), 'agent_cron_tasks', ['next_run_at'], unique=False)


def downgrade() -> None:
    op.drop_table('agent_cron_tasks')
