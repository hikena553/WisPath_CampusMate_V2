"""帖子收藏：community_favorites 表 + community_posts.favorite_count

Revision ID: p5e6f7a8b9c0
Revises: o0p1q2r3s4t5
Create Date: 2026-10-29

收藏与点赞刻意分开：点赞是「我认可」，收藏是「我以后还要回来看」。
模型层早已有 CommunityFavorite 与 favorite_count，但历史库缺这两项，
导致 /api/community/posts、/api/community/hot 直接 500（favorite_count 列不存在）。
这里补齐列与表，并在热点排序里作为独立计数字段使用。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'p5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'o0p1q2r3s4t5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if inspector.has_table("community_posts"):
        cols = {c["name"] for c in inspector.get_columns("community_posts")}
        if "favorite_count" not in cols:
            op.add_column(
                "community_posts",
                sa.Column("favorite_count", sa.Integer(), nullable=False, server_default="0"),
            )

    if not inspector.has_table("community_favorites"):
        op.create_table(
            "community_favorites",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("post_id", "student_id", name="uq_post_favorite_student"),
        )
        op.create_index("ix_community_favorites_post_id", "community_favorites", ["post_id"])
        op.create_index("ix_community_favorites_student_id", "community_favorites", ["student_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("community_favorites"):
        op.drop_table("community_favorites")
    if inspector.has_table("community_posts"):
        cols = {c["name"] for c in inspector.get_columns("community_posts")}
        if "favorite_count" in cols:
            op.drop_column("community_posts", "favorite_count")
