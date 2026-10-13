"""help requests: student ask-for-help -> tutor reply

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-10-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'help_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('anonymous', sa.Boolean(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'PROCESSING', 'RESOLVED', name='helprequeststatus'),
            nullable=False,
        ),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('reply', sa.Text(), nullable=True),
        sa.Column('replied_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_help_requests_student_id'), 'help_requests', ['student_id'], unique=False)
    op.create_index(op.f('ix_help_requests_category'), 'help_requests', ['category'], unique=False)
    op.create_index(op.f('ix_help_requests_status'), 'help_requests', ['status'], unique=False)
    op.create_index(op.f('ix_help_requests_teacher_id'), 'help_requests', ['teacher_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_help_requests_teacher_id'), table_name='help_requests')
    op.drop_index(op.f('ix_help_requests_status'), table_name='help_requests')
    op.drop_index(op.f('ix_help_requests_category'), table_name='help_requests')
    op.drop_index(op.f('ix_help_requests_student_id'), table_name='help_requests')
    op.drop_table('help_requests')