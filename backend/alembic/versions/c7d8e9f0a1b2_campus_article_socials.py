"""校园资讯互动（点赞/评论/转发/浏览）

Revision ID: c7d8e9f0a1b2
Revises: b2c3d4e5f6a7
Create Date: 2026-10-22 16:50:00.000000

资讯来自爬虫，没有内部主键，url 就是文章的唯一身份，因此互动表以 article_url
作逻辑外键而非外键到资讯表（重抓、改标题都不会打断互动数据）。
campus_article_socials 冗余四类计数，信息流读路径 O(1)，不必逐篇 COUNT(*)。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    # 幂等：生产库上有人手动建过表 / 旧版本已建过（如开发库先跑过 create_all）时直接跳过，
    # 避免迁移因 DuplicateTable 中途失败、把整条 upgrade head 卡死。
    if inspector.has_table("campus_article_socials"):
        return

    op.create_table(
        'campus_article_socials',
        sa.Column('id', sa.Integer(), nullable=False),
        # 700：带中文/追踪参数的链接容易超长；MySQL utf8mb4 下 700*4=2800 < 3072 字节索引上限，
        # unique 索引在 InnoDB 上依然可建。
        sa.Column('url', sa.String(length=700), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('repost_count', sa.Integer(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campus_article_socials_id'), 'campus_article_socials', ['id'], unique=False)
    op.create_index(op.f('ix_campus_article_socials_url'), 'campus_article_socials', ['url'], unique=True)

    op.create_table(
        'campus_article_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_url', sa.String(length=700), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campus_article_comments_id'), 'campus_article_comments', ['id'], unique=False)
    op.create_index(op.f('ix_campus_article_comments_article_url'), 'campus_article_comments', ['article_url'], unique=False)
    op.create_index(op.f('ix_campus_article_comments_user_id'), 'campus_article_comments', ['user_id'], unique=False)

    op.create_table(
        'campus_article_likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_url', sa.String(length=700), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        # 一人一篇只能点一次赞：唯一约束是并发下的最终防线（先查后插会竞态）
        sa.UniqueConstraint('article_url', 'user_id', name='uq_campus_article_like_user'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campus_article_likes_id'), 'campus_article_likes', ['id'], unique=False)
    op.create_index(op.f('ix_campus_article_likes_article_url'), 'campus_article_likes', ['article_url'], unique=False)
    op.create_index(op.f('ix_campus_article_likes_user_id'), 'campus_article_likes', ['user_id'], unique=False)

    op.create_table(
        'campus_article_reposts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_url', sa.String(length=700), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        # 预留多去向（timeline/私聊/班级群），当前只用 timeline
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        # 刻意不加唯一约束：转发不去重，同一用户可多次转发，每次一行都计入 repost_count
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campus_article_reposts_id'), 'campus_article_reposts', ['id'], unique=False)
    op.create_index(op.f('ix_campus_article_reposts_article_url'), 'campus_article_reposts', ['article_url'], unique=False)
    op.create_index(op.f('ix_campus_article_reposts_user_id'), 'campus_article_reposts', ['user_id'], unique=False)


def downgrade() -> None:
    # 先删子表（明细），最后删计数表；索引随表删除，顺序与 upgrade 相反的索引显式 drop 更稳妥
    op.drop_index(op.f('ix_campus_article_reposts_user_id'), table_name='campus_article_reposts')
    op.drop_index(op.f('ix_campus_article_reposts_article_url'), table_name='campus_article_reposts')
    op.drop_index(op.f('ix_campus_article_reposts_id'), table_name='campus_article_reposts')
    op.drop_table('campus_article_reposts')

    op.drop_index(op.f('ix_campus_article_likes_user_id'), table_name='campus_article_likes')
    op.drop_index(op.f('ix_campus_article_likes_article_url'), table_name='campus_article_likes')
    op.drop_index(op.f('ix_campus_article_likes_id'), table_name='campus_article_likes')
    op.drop_table('campus_article_likes')

    op.drop_index(op.f('ix_campus_article_comments_user_id'), table_name='campus_article_comments')
    op.drop_index(op.f('ix_campus_article_comments_article_url'), table_name='campus_article_comments')
    op.drop_index(op.f('ix_campus_article_comments_id'), table_name='campus_article_comments')
    op.drop_table('campus_article_comments')

    op.drop_index(op.f('ix_campus_article_socials_url'), table_name='campus_article_socials')
    op.drop_index(op.f('ix_campus_article_socials_id'), table_name='campus_article_socials')
    op.drop_table('campus_article_socials')
