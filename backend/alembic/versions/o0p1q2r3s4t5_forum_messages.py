"""论坛互动消息表 forum_messages（赞 / 收藏 / 评论 / 新粉丝）

Revision ID: o0p1q2r3s4t5
Revises: n9o0p1q2r3s4
Create Date: 2026-10-29

论坛互动与聊天消息彻底分表：点赞、收藏、评论只进 forum_messages，
不再混进会话列表；取消赞/收藏时由业务层删除未读的那条，避免作者困惑。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'o0p1q2r3s4t5'
down_revision: Union[str, Sequence[str], None] = 'n9o0p1q2r3s4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("forum_messages"):
        return
    op.create_table(
        'forum_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.Enum('LIKE', 'FAVORITE', 'COMMENT', 'FOLLOW', name='forummessagekind'), nullable=True),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('post_title', sa.String(length=200), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_forum_messages_user_id', 'forum_messages', ['user_id'])
    op.create_index('ix_forum_messages_actor_id', 'forum_messages', ['actor_id'])
    op.create_index('ix_forum_messages_kind', 'forum_messages', ['kind'])
    op.create_index('ix_forum_messages_is_read', 'forum_messages', ['is_read'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("forum_messages"):
        op.drop_table('forum_messages')
