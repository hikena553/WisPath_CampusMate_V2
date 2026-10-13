"""open source reference library

Revision ID: f6a7b8c9d0e1
Revises: e1f2a3b4c5d6
Create Date: 2026-10-13 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'open_source_references',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('repo_url', sa.String(length=500), nullable=False),
        sa.Column('homepage', sa.String(length=500), nullable=True),
        sa.Column('license', sa.String(length=50), nullable=False),
        sa.Column('license_category', sa.String(length=20), nullable=False),
        sa.Column('stars', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('tech_tags', sa.String(length=300), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('reusable_scope', sa.Text(), nullable=True),
        sa.Column('attribution', sa.Text(), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_open_source_references_license_category'),
        'open_source_references',
        ['license_category'],
        unique=False,
    )
    op.create_index(
        op.f('ix_open_source_references_enabled'),
        'open_source_references',
        ['enabled'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_open_source_references_enabled'), table_name='open_source_references')
    op.drop_index(op.f('ix_open_source_references_license_category'), table_name='open_source_references')
    op.drop_table('open_source_references')
