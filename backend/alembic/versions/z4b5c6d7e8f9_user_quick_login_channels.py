"""user quick login channels: QQ OAuth openid / nickname

Revision ID: z4b5c6d7e8f9
Revises: y3a4b5c6d7e8
Create Date: 2026-11-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'z4b5c6d7e8f9'
down_revision: Union[str, Sequence[str], None] = 'y3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """QQ 互联 OAuth 登录：保存 openid 与授权昵称，供 QQ 授权登录反查账号。

    可重入：部分环境曾手工 ALTER 补过列，这里按实际结构判断后再执行，
    避免 Duplicate column name 中断升级（SQLite 的 DDL 非事务，中断会留下半截状态）。
    """
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "qq_openid" not in columns:
        op.add_column(
            'users',
            sa.Column('qq_openid', sa.String(length=64), nullable=True, comment='QQ 互联 openid，用于 OAuth 登录'),
        )
    if "qq_nickname" not in columns:
        op.add_column(
            'users',
            sa.Column('qq_nickname', sa.String(length=64), nullable=True, comment='QQ 互联授权后获取的昵称'),
        )
    indexes = {idx["name"] for idx in inspector.get_indexes("users")}
    if "ix_users_qq_openid" not in indexes:
        op.create_index('ix_users_qq_openid', 'users', ['qq_openid'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_users_qq_openid', table_name='users')
    op.drop_column('users', 'qq_nickname')
    op.drop_column('users', 'qq_openid')
