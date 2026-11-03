"""资讯账号加发帖频率：media_accounts.relay_interval_minutes

Revision ID: s1a2b3c4d5e6
Revises: s0e1f2a3b4c5
Create Date: 2026-11-04

发帖频率控制逐条转发的最小间隔（距该账号上一条 relay 帖）：30=跟随抓取每轮转发、
60/180/360/720/1440=更低频，0=关闭逐条转发仅发每日汇总。每日汇总帖固定每天一条，
不受此列影响。SQLite 支持直接 ADD COLUMN；带 server_default，存量行自动取 30
（与升级前行为一致）。可重入：列已存在则跳过。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 's1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 's0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("media_accounts"):
        return
    cols = {c["name"] for c in inspector.get_columns("media_accounts")}
    if "relay_interval_minutes" not in cols:
        op.add_column(
            "media_accounts",
            sa.Column(
                "relay_interval_minutes", sa.Integer(), nullable=False,
                server_default=sa.text("30"),
                comment="逐条转发频率（分钟），0=不转发仅每日汇总",
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("media_accounts"):
        return
    cols = {c["name"] for c in inspector.get_columns("media_accounts")}
    if "relay_interval_minutes" in cols:
        op.drop_column("media_accounts", "relay_interval_minutes")
