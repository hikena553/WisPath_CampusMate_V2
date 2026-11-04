"""资讯站三级图谱：媒体站配置、账号接入状态、账号-资讯源连接线

Revision ID: w1e2f3a4b5c6
Revises: v0d1e2f3a4b5
Create Date: 2026-11-05

管理端资讯画布改为「绵小城 AI 资讯站 → 资讯账号 → 资讯源连接」三级结构：

- media_station_config：资讯站单例配置（抓取间隔 / 每日汇总时刻 / 发帖模式 / 总开关）；
- media_accounts.station_connected：账号是否接入资讯站（断线不删内容，可重连）；
- media_source_links：账号到资讯源的连接线（连接名 + 启停），断开即停发该源内容。

整段可重入：表已存在 / 列已存在时直接跳过。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'w1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'v0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("media_station_config"):
        op.create_table(
            "media_station_config",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=60), nullable=False, server_default="绵小城 AI 资讯站"),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("ingest_interval_minutes", sa.Integer(), nullable=False, server_default=sa.text("30")),
            sa.Column("digest_hour", sa.Integer(), nullable=False, server_default=sa.text("8")),
            sa.Column("publish_mode", sa.String(length=20), nullable=False, server_default="auto"),
            sa.Column("description", sa.String(length=200), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if inspector.has_table("media_accounts"):
        cols = {c["name"] for c in inspector.get_columns("media_accounts")}
        if "station_connected" not in cols:
            op.add_column(
                "media_accounts",
                sa.Column(
                    "station_connected", sa.Boolean(), nullable=False,
                    server_default=sa.text("1"),
                    comment="是否接入绵小城AI资讯站",
                ),
            )
            op.create_index(
                "ix_media_accounts_station_connected", "media_accounts", ["station_connected"]
            )

    if not inspector.has_table("media_source_links"):
        op.create_table(
            "media_source_links",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("feed_source_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=60), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["account_id"], ["media_accounts.id"]),
            sa.ForeignKeyConstraint(["feed_source_id"], ["feed_sources.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("account_id", "feed_source_id", name="uq_media_source_links"),
        )
        op.create_index("ix_media_source_links_account_id", "media_source_links", ["account_id"])
        op.create_index("ix_media_source_links_feed_source_id", "media_source_links", ["feed_source_id"])
        op.create_index("ix_media_source_links_enabled", "media_source_links", ["enabled"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("media_source_links"):
        op.drop_table("media_source_links")
    if inspector.has_table("media_accounts"):
        cols = {c["name"] for c in inspector.get_columns("media_accounts")}
        if "station_connected" in cols:
            op.drop_column("media_accounts", "station_connected")
    if inspector.has_table("media_station_config"):
        op.drop_table("media_station_config")
