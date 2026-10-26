"""校园资讯收藏（明细表 + 汇总计数）

Revision ID: k2f3a4b5c6d7
Revises: j1e2f3a4b5c6
Create Date: 2026-10-27 10:00:00.000000

收藏与点赞同构：明细表以 (article_url, user_id) 唯一约束去重，计数冗余在
campus_article_socials 上，信息流 / 详情读路径保持 O(1)，不必逐篇 COUNT(*)。
两者语义不同（点赞 = 我看过且认可，收藏 = 我以后还要找回来），所以各自一张明细表。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'k2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'j1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    # 幂等：开发库可能已经手动建过表，直接跳过，避免 DuplicateTable 卡死整条 upgrade head
    if not inspector.has_table("campus_article_favorites"):
        op.create_table(
            'campus_article_favorites',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('article_url', sa.String(length=700), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            # 一人一篇只能收藏一次：唯一约束是并发下的最终防线
            sa.UniqueConstraint('article_url', 'user_id', name='uq_campus_article_favorite_user'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_campus_article_favorites_id'), 'campus_article_favorites', ['id'], unique=False)
        op.create_index(op.f('ix_campus_article_favorites_article_url'), 'campus_article_favorites', ['article_url'], unique=False)
        op.create_index(op.f('ix_campus_article_favorites_user_id'), 'campus_article_favorites', ['user_id'], unique=False)

    # 计数列同样幂等：老数据回填 0，服务端默认值兜住「没走过应用层」的插入
    columns = {c["name"] for c in inspector.get_columns("campus_article_socials")}
    if "favorite_count" not in columns:
        op.add_column(
            'campus_article_socials',
            sa.Column('favorite_count', sa.Integer(), nullable=False, server_default='0'),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("campus_article_socials")}
    if "favorite_count" in columns:
        op.drop_column('campus_article_socials', 'favorite_count')

    if inspector.has_table("campus_article_favorites"):
        op.drop_index(op.f('ix_campus_article_favorites_user_id'), table_name='campus_article_favorites')
        op.drop_index(op.f('ix_campus_article_favorites_article_url'), table_name='campus_article_favorites')
        op.drop_index(op.f('ix_campus_article_favorites_id'), table_name='campus_article_favorites')
        op.drop_table('campus_article_favorites')
