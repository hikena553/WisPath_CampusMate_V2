"""peer survey and anonymous responses

Revision ID: d3b4c5d6e7f8
Revises: c2a3b4c5d6e7
Create Date: 2026-10-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'c2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'peer_surveys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column(
            'target_type',
            sa.Enum('PEER', 'STUDENT', name='peersurveytargettype'),
            nullable=False,
        ),
        sa.Column('period', sa.String(length=64), nullable=True),
        sa.Column('questions_json', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'OPEN', 'CLOSED', name='peersurveystatus'),
            nullable=False,
        ),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_peer_surveys_status'), 'peer_surveys', ['status'], unique=False)
    op.create_index(op.f('ix_peer_surveys_created_by'), 'peer_surveys', ['created_by'], unique=False)

    op.create_table(
        'peer_survey_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=False),
        sa.Column('target_teacher_id', sa.Integer(), nullable=False),
        sa.Column('scores_json', sa.Text(), nullable=False),
        sa.Column('suggestion', sa.Text(), nullable=True),
        sa.Column('anonymous_token', sa.String(length=64), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'survey_id', 'target_teacher_id', 'anonymous_token',
            name='uq_peer_response_token',
        ),
    )
    op.create_index(
        op.f('ix_peer_survey_responses_survey_id'),
        'peer_survey_responses',
        ['survey_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_peer_survey_responses_target_teacher_id'),
        'peer_survey_responses',
        ['target_teacher_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_peer_survey_responses_anonymous_token'),
        'peer_survey_responses',
        ['anonymous_token'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_peer_survey_responses_anonymous_token'), table_name='peer_survey_responses')
    op.drop_index(op.f('ix_peer_survey_responses_target_teacher_id'), table_name='peer_survey_responses')
    op.drop_index(op.f('ix_peer_survey_responses_survey_id'), table_name='peer_survey_responses')
    op.drop_table('peer_survey_responses')

    op.drop_index(op.f('ix_peer_surveys_created_by'), table_name='peer_surveys')
    op.drop_index(op.f('ix_peer_surveys_status'), table_name='peer_surveys')
    op.drop_table('peer_surveys')