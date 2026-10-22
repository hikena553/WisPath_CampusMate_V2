"""care center: home visit follow-up sync fields

Revision ID: f4d5e6f7a8b9
Revises: f3c4d5e6f7a8
Create Date: 2026-10-22 11:00:00.000000

说明：家访回访字段（follow_up_status / follow_up_done_at）已由
f3c4d5e6f7a8_home_visit_followup 引入。本迁移对列做存在性校验后
再补齐，保证在既有库上幂等可执行、且 fresh 升级链可安全通过。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'f3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = 'home_visit_records'


def _existing_columns() -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col['name'] for col in insp.get_columns(_TABLE)}


def upgrade() -> None:
    """Upgrade schema."""
    existing = _existing_columns()
    need_status = 'follow_up_status' not in existing
    need_done_at = 'follow_up_done_at' not in existing
    if not need_status and not need_done_at:
        return

    with op.batch_alter_table(_TABLE) as batch_op:
        if need_status:
            batch_op.add_column(
                sa.Column(
                    'follow_up_status',
                    sa.Enum('PENDING', 'DONE', name='followupstatus'),
                    nullable=False,
                    server_default=sa.text("'PENDING'"),
                )
            )
            batch_op.create_index(
                op.f('ix_home_visit_records_follow_up_status'),
                ['follow_up_status'],
                unique=False,
            )
        if need_done_at:
            batch_op.add_column(sa.Column('follow_up_done_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    existing = _existing_columns()
    with op.batch_alter_table(_TABLE) as batch_op:
        if 'follow_up_status' in existing:
            batch_op.drop_index(op.f('ix_home_visit_records_follow_up_status'))
            batch_op.drop_column('follow_up_status')
        if 'follow_up_done_at' in existing:
            batch_op.drop_column('follow_up_done_at')