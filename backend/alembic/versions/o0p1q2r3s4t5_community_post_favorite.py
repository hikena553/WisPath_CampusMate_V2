"""帖子收藏（community_favorites + community_posts.favorite_count）

Revision ID: o0p1q2r3s4t5
Revises: n9o0p1q2r3s4
Create Date: 2026-10-29 17:20:00.000000

论坛互动补齐「收藏」这一动作：点赞是「我认可」，收藏是「我以后还要回来看」，
两者独立计数。收藏时给作者写一条 kind='favorite' 的 forum_messages，
让交流社区页的互动消息能分类展示 赞 / 收藏 / 评论 / 新粉丝。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'o0p1q2r3s4t5'
down_revision: Union[str, Sequence[str], None] = 'n9o0p1q2r3s4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    bind = op.get_bind()

    # 幂等：SQLite 不支持 ADD COLUMN IF NOT EXISTS，先查列
    cols = {c["name"] for c in inspector.get_columns("community_posts")}
    if "favorite_count" not in cols:
        op.add_column(
            "community_posts",
            sa.Column("favorite_count", sa.Integer(), nullable=False, server_default="0"),
        )
        # 存量行对齐：server_default 已给 0，这里再 UPDATE 一次兜住历史 NULL（若有）
        bind.execute(sa.text("UPDATE community_posts SET favorite_count = 0 WHERE favorite_count IS NULL"))

    if not inspector.has_table("community_favorites"):
        op.create_table(
            "community_favorites",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("post_id", "student_id", name="uq_post_favorite_student"),
        )
        op.create_index(op.f("ix_community_favorites_post_id"), "community_favorites", ["post_id"], unique=False)
        op.create_index(op.f("ix_community_favorites_student_id"), "community_favorites", ["student_id"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("community_favorites"):
        op.drop_table("community_favorites")
    cols = {c["name"] for c in inspector.get_columns("community_posts")}
    if "favorite_count" in cols:
        with op.batch_alter_table("community_posts") as batch:
            batch.drop_column("favorite_count")
