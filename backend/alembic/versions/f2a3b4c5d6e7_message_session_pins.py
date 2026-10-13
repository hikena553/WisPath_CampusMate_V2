"""消息会话置顶持久化

message_session_pins：把「会话置顶」从浏览器 localStorage 迁到服务端，
使教师端/学生端、跨设备都能同步同一份置顶顺序。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("message_session_pins"):
        return
    op.create_table(
        'message_session_pins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_key', sa.String(length=64), nullable=False),
        sa.Column('pinned_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_message_session_pins_id'), 'message_session_pins', ['id'], unique=False)
    op.create_index(op.f('ix_message_session_pins_user_id'), 'message_session_pins', ['user_id'], unique=False)
    op.create_index(op.f('ix_message_session_pins_session_key'), 'message_session_pins', ['session_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_message_session_pins_session_key'), table_name='message_session_pins')
    op.drop_index(op.f('ix_message_session_pins_user_id'), table_name='message_session_pins')
    op.drop_index(op.f('ix_message_session_pins_id'), table_name='message_session_pins')
    op.drop_table('message_session_pins')