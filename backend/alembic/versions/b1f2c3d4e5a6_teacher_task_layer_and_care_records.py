"""teacher task layer and care records

Revision ID: b1f2c3d4e5a6
Revises: d7b1c4f0a925
Create Date: 2026-10-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f2c3d4e5a6'
down_revision: Union[str, Sequence[str], None] = 'd7b1c4f0a925'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'teacher_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column(
            'source_type',
            sa.Enum(
                'AI_SUGGEST', 'FOLLOW_UP', 'APPROVAL', 'CARE_PLAN', 'ALERT', 'MANUAL',
                name='tasksourcetype',
            ),
            nullable=False,
        ),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'CONTACTED', 'CARED', 'DONE', 'EXPIRED', name='taskstatus'),
            nullable=False,
        ),
        sa.Column('due_at', sa.Date(), nullable=True),
        sa.Column('done_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_type', 'source_id', 'teacher_id', name='uq_teacher_task_source'),
    )
    op.create_index(op.f('ix_teacher_tasks_teacher_id'), 'teacher_tasks', ['teacher_id'], unique=False)
    op.create_index(op.f('ix_teacher_tasks_student_id'), 'teacher_tasks', ['student_id'], unique=False)
    op.create_index(op.f('ix_teacher_tasks_status'), 'teacher_tasks', ['status'], unique=False)

    op.create_table(
        'care_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column(
            'record_type',
            sa.Enum('CARE', 'TALK', 'COMMENT', name='carerecordtype'),
            nullable=False,
        ),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_care_records_student_id'), 'care_records', ['student_id'], unique=False)
    op.create_index(op.f('ix_care_records_teacher_id'), 'care_records', ['teacher_id'], unique=False)

    with op.batch_alter_table('leave_requests') as batch_op:
        batch_op.add_column(sa.Column('return_confirmed', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('return_confirmed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('leave_requests') as batch_op:
        batch_op.drop_column('return_confirmed_at')
        batch_op.drop_column('return_confirmed')

    op.drop_index(op.f('ix_care_records_teacher_id'), table_name='care_records')
    op.drop_index(op.f('ix_care_records_student_id'), table_name='care_records')
    op.drop_table('care_records')

    op.drop_index(op.f('ix_teacher_tasks_status'), table_name='teacher_tasks')
    op.drop_index(op.f('ix_teacher_tasks_student_id'), table_name='teacher_tasks')
    op.drop_index(op.f('ix_teacher_tasks_teacher_id'), table_name='teacher_tasks')
    op.drop_table('teacher_tasks')
