"""learning events (xAPI-lite)

Revision ID: a6b7c8d9e0f1
Revises: f5d6e7f8a9b0
Create Date: 2026-10-06 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, Sequence[str], None] = 'f5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'learning_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('verb', sa.String(length=50), nullable=False),
        sa.Column('object_type', sa.String(length=50), nullable=False),
        sa.Column('object_id', sa.Integer(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('context_json', sa.Text(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_learning_events_actor_id'), 'learning_events', ['actor_id'], unique=False)
    op.create_index(op.f('ix_learning_events_verb'), 'learning_events', ['verb'], unique=False)
    op.create_index(op.f('ix_learning_events_object_type'), 'learning_events', ['object_type'], unique=False)
    op.create_index(op.f('ix_learning_events_object_id'), 'learning_events', ['object_id'], unique=False)
    op.create_index(op.f('ix_learning_events_occurred_at'), 'learning_events', ['occurred_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_learning_events_occurred_at'), table_name='learning_events')
    op.drop_index(op.f('ix_learning_events_object_id'), table_name='learning_events')
    op.drop_index(op.f('ix_learning_events_object_type'), table_name='learning_events')
    op.drop_index(op.f('ix_learning_events_verb'), table_name='learning_events')
    op.drop_index(op.f('ix_learning_events_actor_id'), table_name='learning_events')
    op.drop_table('learning_events')