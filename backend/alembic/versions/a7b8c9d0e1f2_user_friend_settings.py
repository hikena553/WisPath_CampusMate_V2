"""frontend friend settings: remark / care / mute / block / feed privacy / intimacy

Revision ID: a7b8c9d0e1f2
Revises: c1e3f4a5b6d7
Create Date: 2026-11-05 13:10:00.000000

个人主页「设置」页的每一项原来只落在浏览器 localStorage，换设备就丢、对方也看不到。
这里把 备注 / 特别关心 / 免打扰 / 黑名单 / 动态权限 / 亲密关系 收进一张表：

- 唯一键 (user_id, peer_id)：一人对一人只有一条，重复写走 upsert；
- hide_peer_posts / hide_my_posts 是「动态权限」的两个方向，各自一条记录上各存一份；
- care 建索引：消息列表要按「特别关心」名单给会话挂标，按 user_id 反查很频繁。

整段可重入：表已存在直接跳过（SQLite 的 DDL 非事务，中断会留下半截状态）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'c1e3f4a5b6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("user_friend_settings"):
        return
    op.create_table(
        "user_friend_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("remark", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("care", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("mute", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("hide_peer_posts", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("hide_my_posts", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("intimacy", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "peer_id", name="uq_friend_setting_pair"),
    )
    op.create_index("ix_user_friend_settings_user_id", "user_friend_settings", ["user_id"])
    op.create_index("ix_user_friend_settings_peer_id", "user_friend_settings", ["peer_id"])
    op.create_index("ix_user_friend_settings_care", "user_friend_settings", ["care"])
    op.create_index(
        "ix_user_friend_settings_hide_peer_posts", "user_friend_settings", ["hide_peer_posts"]
    )
    op.create_index(
        "ix_user_friend_settings_hide_my_posts", "user_friend_settings", ["hide_my_posts"]
    )


def downgrade() -> None:
    op.drop_table("user_friend_settings")
