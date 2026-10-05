"""workflow definitions and instances

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'workflow_defs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('biz_type', sa.String(length=50), nullable=False),
        sa.Column('nodes_json', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflow_defs_code'), 'workflow_defs', ['code'], unique=True)
    op.create_index(op.f('ix_workflow_defs_biz_type'), 'workflow_defs', ['biz_type'], unique=False)

    op.create_table(
        'workflow_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('def_id', sa.Integer(), nullable=False),
        sa.Column('biz_type', sa.String(length=50), nullable=False),
        sa.Column('biz_id', sa.Integer(), nullable=True),
        sa.Column('initiator_id', sa.Integer(), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('RUNNING', 'APPROVED', 'REJECTED', 'CANCELLED', name='workflowstatus'),
            nullable=False,
        ),
        sa.Column('history_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflow_instances_def_id'), 'workflow_instances', ['def_id'], unique=False)
    op.create_index(op.f('ix_workflow_instances_biz_type'), 'workflow_instances', ['biz_type'], unique=False)
    op.create_index(op.f('ix_workflow_instances_biz_id'), 'workflow_instances', ['biz_id'], unique=False)
    op.create_index(
        op.f('ix_workflow_instances_initiator_id'), 'workflow_instances', ['initiator_id'], unique=False
    )
    op.create_index(op.f('ix_workflow_instances_status'), 'workflow_instances', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_workflow_instances_status'), table_name='workflow_instances')
    op.drop_index(op.f('ix_workflow_instances_initiator_id'), table_name='workflow_instances')
    op.drop_index(op.f('ix_workflow_instances_biz_id'), table_name='workflow_instances')
    op.drop_index(op.f('ix_workflow_instances_biz_type'), table_name='workflow_instances')
    op.drop_index(op.f('ix_workflow_instances_def_id'), table_name='workflow_instances')
    op.drop_table('workflow_instances')

    op.drop_index(op.f('ix_workflow_defs_biz_type'), table_name='workflow_defs')
    op.drop_index(op.f('ix_workflow_defs_code'), table_name='workflow_defs')
    op.drop_table('workflow_defs')