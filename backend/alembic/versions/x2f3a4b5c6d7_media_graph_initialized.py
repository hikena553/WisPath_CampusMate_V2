"""资讯站画布首次初始化标记

Revision ID: x2f3a4b5c6d7
Revises: w1e2f3a4b5c6
Create Date: 2026-11-05

校园资讯的抓取源已在 feed_sources 中维护。画布改为「连接即抓取范围」后，
需要一次性把现有抓取源挂到已有资讯账号下（迁移不直接写数据，由服务层在
首次加载图谱时完成），并用 graph_initialized 保证只初始化一次，
避免管理员主动清空连接后又被自动补回。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'x2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'w1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("media_station_config"):
        return
    cols = {c["name"] for c in inspector.get_columns("media_station_config")}
    if "graph_initialized" not in cols:
        op.add_column(
            "media_station_config",
            sa.Column(
                "graph_initialized", sa.Boolean(), nullable=False,
                server_default=sa.text("0"),
                comment="画布是否已完成首次初始化",
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("media_station_config"):
        return
    cols = {c["name"] for c in inspector.get_columns("media_station_config")}
    if "graph_initialized" in cols:
        op.drop_column("media_station_config", "graph_initialized")
