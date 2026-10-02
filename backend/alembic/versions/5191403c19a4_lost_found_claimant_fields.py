"""lost found claimant fields

Revision ID: 5191403c19a4
Revises: a5835ed04c5a
Create Date: 2026-10-02 20:42:20.095042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5191403c19a4'
down_revision: Union[str, Sequence[str], None] = 'a5835ed04c5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('lost_found_items') as batch_op:
        batch_op.add_column(sa.Column('claimant_name', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('claimant_contact', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('claim_note', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('claimed_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('claimed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('lost_found_items') as batch_op:
        batch_op.drop_column('claimed_at')
        batch_op.drop_column('claimed_by')
        batch_op.drop_column('claim_note')
        batch_op.drop_column('claimant_contact')
        batch_op.drop_column('claimant_name')
