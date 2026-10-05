"""guardian contacts, contact logs and share links

Revision ID: f5d6e7f8a9b0
Revises: e4c5d6e7f8a9
Create Date: 2026-10-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'e4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'guardians',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('relation', sa.String(length=20), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('remark', sa.String(length=200), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_guardians_student_id'), 'guardians', ['student_id'], unique=False)

    op.create_table(
        'guardian_contact_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('guardian_id', sa.Integer(), nullable=True),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column(
            'scene',
            sa.Enum('LEAVE', 'CRISIS', 'ACADEMIC', 'CARE', 'OTHER', name='guardianscene'),
            nullable=False,
        ),
        sa.Column(
            'channel',
            sa.Enum('SMS', 'REPORT', 'LINK', 'NOTE', name='guardianchannel'),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'SENT', 'PENDING', 'FAILED', name='guardiancontactstatus'),
            nullable=False,
        ),
        sa.Column('content_summary', sa.Text(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_guardian_contact_logs_student_id'), 'guardian_contact_logs', ['student_id'], unique=False
    )
    op.create_index(
        op.f('ix_guardian_contact_logs_guardian_id'), 'guardian_contact_logs', ['guardian_id'], unique=False
    )
    op.create_index(
        op.f('ix_guardian_contact_logs_teacher_id'), 'guardian_contact_logs', ['teacher_id'], unique=False
    )
    op.create_index(
        op.f('ix_guardian_contact_logs_scene'), 'guardian_contact_logs', ['scene'], unique=False
    )

    op.create_table(
        'guardian_share_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False),
        sa.Column('last_viewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_guardian_share_links_log_id'), 'guardian_share_links', ['log_id'], unique=False)
    op.create_index(op.f('ix_guardian_share_links_token'), 'guardian_share_links', ['token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_guardian_share_links_token'), table_name='guardian_share_links')
    op.drop_index(op.f('ix_guardian_share_links_log_id'), table_name='guardian_share_links')
    op.drop_table('guardian_share_links')

    op.drop_index(op.f('ix_guardian_contact_logs_scene'), table_name='guardian_contact_logs')
    op.drop_index(op.f('ix_guardian_contact_logs_teacher_id'), table_name='guardian_contact_logs')
    op.drop_index(op.f('ix_guardian_contact_logs_guardian_id'), table_name='guardian_contact_logs')
    op.drop_index(op.f('ix_guardian_contact_logs_student_id'), table_name='guardian_contact_logs')
    op.drop_table('guardian_contact_logs')

    op.drop_index(op.f('ix_guardians_student_id'), table_name='guardians')
    op.drop_table('guardians')