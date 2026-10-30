"""关注关系表 user_follows（好友 = 互相关注）

Revision ID: n9o0p1q2r3s4
Revises: o2b3c4d5e6f7
Create Date: 2026-10-29

原来「好友」用「是否聊过天」代替，导致同一个人在不同页面显示成不同关系。
改为显式关注关系后，消息页通讯录、个人主页、勋章 metrics.contacts 全部复用
social_service 的同一套口径。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'n9o0p1q2r3s4'
down_revision: Union[str, Sequence[str], None] = 'o2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("user_follows"):
        return
    op.create_table(
        'user_follows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('follower_id', sa.Integer(), nullable=False),
        sa.Column('following_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('follower_id', 'following_id', name='uq_follow_pair'),
    )
    op.create_index('ix_user_follows_follower_id', 'user_follows', ['follower_id'])
    op.create_index('ix_user_follows_following_id', 'user_follows', ['following_id'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("user_follows"):
        op.drop_table('user_follows')
