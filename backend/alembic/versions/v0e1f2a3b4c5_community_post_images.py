"""交流社区帖子支持配图：community_posts.images

Revision ID: v0e1f2a3b4c5
Revises: u9d0e1f2a3b4
Create Date: 2026-11-04

发帖编辑器改成全屏版式后带「文字配图」，图片 URL 以 JSON 数组存一列
（与 student_projects.images 同一套写法：Text 存 JSON 字符串、schema 出口转数组）。
可空、无默认值：存量帖子 images=NULL，出参统一回落成 []。SQLite / MySQL 都支持
直接 ADD COLUMN。可重入：列已存在则跳过。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'v0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'u9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("community_posts"):
        return
    cols = {c["name"] for c in inspector.get_columns("community_posts")}
    if "images" not in cols:
        op.add_column(
            "community_posts",
            sa.Column(
                "images", sa.Text(), nullable=True,
                comment="配图 URL JSON 数组，最多 9 张",
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("community_posts"):
        return
    cols = {c["name"] for c in inspector.get_columns("community_posts")}
    if "images" in cols:
        op.drop_column("community_posts", "images")
