"""消息会话删除（用户级隐藏）

message_session_hidden：把「删除会话」做成仅作用于本人的列表隐藏——
聊天记录保留、对方不受影响；hidden_upto_id 记录删除时刻最后一条消息 id，
出现更新的消息时会话自动恢复展示。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("message_session_hidden"):
        return
    op.create_table(
        'message_session_hidden',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_key', sa.String(length=64), nullable=False),
        sa.Column('hidden_upto_id', sa.Integer(), nullable=False),
        sa.Column('hidden_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_message_session_hidden_id'), 'message_session_hidden', ['id'], unique=False)
    op.create_index(op.f('ix_message_session_hidden_user_id'), 'message_session_hidden', ['user_id'], unique=False)
    op.create_index(op.f('ix_message_session_hidden_session_key'), 'message_session_hidden', ['session_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_message_session_hidden_session_key'), table_name='message_session_hidden')
    op.drop_index(op.f('ix_message_session_hidden_user_id'), table_name='message_session_hidden')
    op.drop_index(op.f('ix_message_session_hidden_id'), table_name='message_session_hidden')
    op.drop_table('message_session_hidden')