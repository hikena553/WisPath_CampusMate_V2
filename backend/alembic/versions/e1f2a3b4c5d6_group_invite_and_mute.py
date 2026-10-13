"""群邀请码 + 消息免打扰

- groups.invite_code：群二维码邀请（扫码入群），首次打开二维码页时惰性生成
- group_members.is_muted：群消息免打扰（不计未读、不接收实时推送）
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    group_cols = {c["name"] for c in inspector.get_columns("groups")}
    if "invite_code" not in group_cols:
        op.add_column('groups', sa.Column('invite_code', sa.String(length=32), nullable=True))
        op.create_index('ix_groups_invite_code', 'groups', ['invite_code'], unique=True)

    member_cols = {c["name"] for c in inspector.get_columns("group_members")}
    if "is_muted" not in member_cols:
        op.add_column(
            'group_members',
            sa.Column('is_muted', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        )


def downgrade() -> None:
    op.drop_column('group_members', 'is_muted')
    op.drop_index('ix_groups_invite_code', table_name='groups')
    op.drop_column('groups', 'invite_code')