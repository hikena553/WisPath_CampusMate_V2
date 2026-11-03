"""资讯账号管理：media_accounts / media_posts 两张新表

Revision ID: s0e1f2a3b4c5
Revises: r9d0e1f2a3b4
Create Date: 2026-11-04

资讯账号 = users 表中 role='MEDIA' 的记录 + 本模块的配置/流水表：

- role 枚举新增 MEDIA 值。SQLite 下 users.role 本就是无 CHECK 的 VARCHAR(7)，
  'MEDIA'（5 字符）直接可用，无需改列；MySQL 生产库的 ENUM 列扩值由
  MySQL ALTER 处理，MySQL 分支用 MODIFY COLUMN 兜底（幂等：先查列定义）。
- media_accounts：账号配置（启停 / 内容方向），1:1 挂 users。
- media_posts：发帖流水，唯一约束做转发去重与日报幂等（可空列不参与约束）。

整段可重入：表已存在 / 列已含 MEDIA 时直接跳过。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 's0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'r9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _users_role_needs_media() -> bool:
    """users.role 列定义是否已包含 MEDIA（SQLite 是 VARCHAR 无约束，视作已就绪）。"""
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return False
    insp = sa.inspect(bind)
    if not insp.has_table("users"):
        return False
    col = next((c for c in insp.get_columns("users") if c["name"] == "role"), None)
    if col is None:
        return False
    enum_values = []
    if isinstance(col.get("type"), sa.Enum):
        enum_values = list(col["type"].enums or [])
    elif getattr(col.get("type"), "enums", None):
        enum_values = list(col["type"].enums)
    return bool(enum_values) and "MEDIA" not in enum_values


def upgrade() -> None:
    if _users_role_needs_media():
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('STUDENT','TEACHER','ADMIN','MEDIA') NOT NULL"
        )

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("media_accounts"):
        op.create_table(
            "media_accounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("content_scope", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_media_accounts_user"),
        )
        op.create_index("ix_media_accounts_is_enabled", "media_accounts", ["is_enabled"])

    if not inspector.has_table("media_posts"):
        op.create_table(
            "media_posts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_user_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("feed_item_id", sa.Integer(), nullable=True),
            sa.Column("kind", sa.String(length=20), nullable=False),
            sa.Column("digest_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("account_user_id", "feed_item_id", name="uq_media_posts_relay"),
            sa.UniqueConstraint("account_user_id", "digest_date", name="uq_media_posts_digest"),
        )
        op.create_index("ix_media_posts_account_user_id", "media_posts", ["account_user_id"])
        op.create_index("ix_media_posts_post_id", "media_posts", ["post_id"])
        op.create_index("ix_media_posts_feed_item_id", "media_posts", ["feed_item_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("media_posts"):
        op.drop_table("media_posts")
    if inspector.has_table("media_accounts"):
        op.drop_table("media_accounts")

    if bind_has_mysql(op) and users_role_has_media(op):
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role ENUM('STUDENT','TEACHER','ADMIN') NOT NULL"
        )


def bind_has_mysql(op) -> bool:
    return op.get_bind().dialect.name == "mysql"


def users_role_has_media(op) -> bool:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table("users"):
        return False
    col = next((c for c in insp.get_columns("users") if c["name"] == "role"), None)
    return bool(col and getattr(col.get("type"), "enums", None) and "MEDIA" in col["type"].enums)
