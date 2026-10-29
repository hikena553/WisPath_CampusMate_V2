"""社交关系表（关注 / 论坛互动消息）

Revision ID: n9o0p1q2r3s4
Revises: m8n9p0q1r2s3
Create Date: 2026-10-29 15:00:00.000000

- user_follows：单向关注边，互关即好友（好友不单独建表，靠双向查询推导）
- forum_messages：论坛互动消息，与聊天消息物理隔离
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'n9o0p1q2r3s4'
down_revision: Union[str, Sequence[str], None] = 'm8n9p0q1r2s3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    # 幂等：开发库可能已手动建过表，避免 DuplicateTable 卡死整条 upgrade head
    if not inspector.has_table("user_follows"):
        op.create_table(
            'user_follows',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('follower_id', sa.Integer(), nullable=False),
            sa.Column('followee_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['follower_id'], ['users.id']),
            sa.ForeignKeyConstraint(['followee_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('follower_id', 'followee_id', name='uq_user_follow_pair'),
        )
        op.create_index(op.f('ix_user_follows_follower_id'), 'user_follows', ['follower_id'], unique=False)
        op.create_index(op.f('ix_user_follows_followee_id'), 'user_follows', ['followee_id'], unique=False)

    if not inspector.has_table("forum_messages"):
        op.create_table(
            'forum_messages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('actor_id', sa.Integer(), nullable=False),
            sa.Column('kind', sa.String(length=20), nullable=False),
            sa.Column('post_id', sa.Integer(), nullable=True),
            sa.Column('post_title', sa.String(length=200), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('is_read', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['actor_id'], ['users.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_forum_messages_user_id'), 'forum_messages', ['user_id'], unique=False)
        op.create_index(op.f('ix_forum_messages_actor_id'), 'forum_messages', ['actor_id'], unique=False)
        op.create_index(op.f('ix_forum_messages_kind'), 'forum_messages', ['kind'], unique=False)
        op.create_index(op.f('ix_forum_messages_post_id'), 'forum_messages', ['post_id'], unique=False)
        op.create_index(op.f('ix_forum_messages_is_read'), 'forum_messages', ['is_read'], unique=False)
        op.create_index(op.f('ix_forum_messages_created_at'), 'forum_messages', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('forum_messages')
    op.drop_table('user_follows')
