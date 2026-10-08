"""care center: events, home visits, praise

Revision ID: e4c5d6e7f8a9
Revises: d3b4c5d6e7f8
Create Date: 2026-10-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'd3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'care_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column(
            'event_type',
            sa.Enum('BIRTHDAY', 'DIFFICULTY', 'ACADEMIC', 'OTHER', name='careeventtype'),
            nullable=False,
        ),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('auto_generated', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_care_events_teacher_id'), 'care_events', ['teacher_id'], unique=False)
    op.create_index(op.f('ix_care_events_student_id'), 'care_events', ['student_id'], unique=False)
    op.create_index(op.f('ix_care_events_event_type'), 'care_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_care_events_event_date'), 'care_events', ['event_date'], unique=False)

    op.create_table(
        'home_visit_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('visit_date', sa.Date(), nullable=False),
        sa.Column(
            'method',
            sa.Enum('HOME', 'PHONE', 'VIDEO', 'SCHOOL', 'OTHER', name='homevisitmethod'),
            nullable=False,
        ),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('follow_up', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_home_visit_records_student_id'), 'home_visit_records', ['student_id'], unique=False
    )
    op.create_index(
        op.f('ix_home_visit_records_teacher_id'), 'home_visit_records', ['teacher_id'], unique=False
    )
    op.create_index(
        op.f('ix_home_visit_records_visit_date'), 'home_visit_records', ['visit_date'], unique=False
    )

    op.create_table(
        'praise_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column(
            'praise_type',
            sa.Enum('PRAISE', 'BADGE', name='praisetype'),
            nullable=False,
        ),
        sa.Column('badge_name', sa.String(length=50), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('occurred_on', sa.Date(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_praise_records_student_id'), 'praise_records', ['student_id'], unique=False)
    op.create_index(op.f('ix_praise_records_teacher_id'), 'praise_records', ['teacher_id'], unique=False)
    op.create_index(op.f('ix_praise_records_occurred_on'), 'praise_records', ['occurred_on'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_praise_records_occurred_on'), table_name='praise_records')
    op.drop_index(op.f('ix_praise_records_teacher_id'), table_name='praise_records')
    op.drop_index(op.f('ix_praise_records_student_id'), table_name='praise_records')
    op.drop_table('praise_records')

    op.drop_index(op.f('ix_home_visit_records_visit_date'), table_name='home_visit_records')
    op.drop_index(op.f('ix_home_visit_records_teacher_id'), table_name='home_visit_records')
    op.drop_index(op.f('ix_home_visit_records_student_id'), table_name='home_visit_records')
    op.drop_table('home_visit_records')

    op.drop_index(op.f('ix_care_events_event_date'), table_name='care_events')
    op.drop_index(op.f('ix_care_events_event_type'), table_name='care_events')
    op.drop_index(op.f('ix_care_events_student_id'), table_name='care_events')
    op.drop_index(op.f('ix_care_events_teacher_id'), table_name='care_events')
    op.drop_table('care_events')