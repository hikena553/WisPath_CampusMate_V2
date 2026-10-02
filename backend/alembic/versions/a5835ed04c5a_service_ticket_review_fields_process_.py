"""service ticket review fields & process status

Revision ID: a5835ed04c5a
Revises: 0d9844ecf863
Create Date: 2026-10-02 20:42:18.080651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5835ed04c5a'
down_revision: Union[str, Sequence[str], None] = '0d9844ecf863'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch 模式：SQLite 重建表（原生不支持 ALTER COLUMN），MySQL 透传原生 DDL
    with op.batch_alter_table('service_tickets') as batch_op:
        batch_op.add_column(sa.Column('review_comment', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('approver_name', sa.String(length=50), nullable=True))
        # 状态机引入中间态 PROCESSING：MySQL 下重建 ENUM，SQLite 下重建 CHECK 约束
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='ticketstatus'),
            type_=sa.Enum('PENDING', 'PROCESSING', 'APPROVED', 'REJECTED', name='ticketstatus'),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('service_tickets') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('PENDING', 'PROCESSING', 'APPROVED', 'REJECTED', name='ticketstatus'),
            type_=sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='ticketstatus'),
            existing_nullable=False,
        )
        batch_op.drop_column('approver_name')
        batch_op.drop_column('review_comment')
