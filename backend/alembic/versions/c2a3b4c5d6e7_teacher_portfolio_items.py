"""teacher portfolio items

Revision ID: c2a3b4c5d6e7
Revises: b1f2c3d4e5a6
Create Date: 2026-10-05 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'b1f2c3d4e5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'teacher_portfolio_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column(
            'item_type',
            sa.Enum('CASE', 'HONOR', 'TRAINING', 'RESEARCH', name='portfolioitemtype'),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('evidence_json', sa.Text(), nullable=True),
        sa.Column('reflection', sa.Text(), nullable=True),
        sa.Column('occurred_on', sa.Date(), nullable=True),
        sa.Column(
            'visibility',
            sa.Enum('PRIVATE', 'PUBLIC', name='portfoliovisibility'),
            nullable=False,
        ),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_teacher_portfolio_items_teacher_id'),
        'teacher_portfolio_items',
        ['teacher_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_teacher_portfolio_items_item_type'),
        'teacher_portfolio_items',
        ['item_type'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_teacher_portfolio_items_item_type'), table_name='teacher_portfolio_items')
    op.drop_index(op.f('ix_teacher_portfolio_items_teacher_id'), table_name='teacher_portfolio_items')
    op.drop_table('teacher_portfolio_items')