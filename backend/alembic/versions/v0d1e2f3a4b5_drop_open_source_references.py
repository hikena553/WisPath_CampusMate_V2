"""drop open source references table

Revision ID: v0d1e2f3a4b5
Revises: u9d0e1f2a3b4
Create Date: 2026-11-04 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'v0d1e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'u9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('open_source_references')


def downgrade() -> None:
    """Downgrade schema."""
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
