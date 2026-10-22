"""password reset requests

Revision ID: i8b9c0d1e2f3
Revises: h7a8b9c0d1e2
Create Date: 2026-10-22 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i8b9c0d1e2f3'
down_revision: Union[str, Sequence[str], None] = 'h7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """忘记密码：学生/教师提交身份核验申请，管理员审核后重置密码。"""
    op.create_table(
        'password_reset_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('contact', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RESET', 'REJECTED', name='passwordresetstatus'), nullable=True),
        sa.Column('admin_note', sa.String(length=200), nullable=True),
        sa.Column('handled_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('handled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['handled_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_password_reset_requests_user_id', 'password_reset_requests', ['user_id'])
    op.create_index('ix_password_reset_requests_username', 'password_reset_requests', ['username'])
    op.create_index('ix_password_reset_requests_status', 'password_reset_requests', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_password_reset_requests_status', table_name='password_reset_requests')
    op.drop_index('ix_password_reset_requests_username', table_name='password_reset_requests')
    op.drop_index('ix_password_reset_requests_user_id', table_name='password_reset_requests')
    op.drop_table('password_reset_requests')
