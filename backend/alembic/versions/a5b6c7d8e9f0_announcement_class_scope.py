"""teacher_announcements: 增加发布目标班级

Revision ID: a5b6c7d8e9f0
Revises: z4b5c6d7e8f9
Create Date: 2026-11-07 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = 'b6d7e8f9g0h1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """公告支持按班级定向发布。

    ``class_group_id`` 为 NULL 表示「名下全体学生」——这正是历史数据本来的语义，
    所以回填无需任何操作，旧公告的触达范围保持不变。

    可重入：按实际列/索引情况判断后再执行，避免 Duplicate column name
    中断升级（SQLite 的 DDL 非事务，中断会留下半截状态）。
    """
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("teacher_announcements")}
    if "class_group_id" not in columns:
        op.add_column(
            'teacher_announcements',
            sa.Column(
                'class_group_id', sa.Integer(), nullable=True,
                comment='发布目标班级；NULL 表示名下全体学生',
            ),
        )
    indexes = {idx["name"] for idx in inspector.get_indexes("teacher_announcements")}
    if "ix_teacher_announcements_class_group_id" not in indexes:
        op.create_index(
            'ix_teacher_announcements_class_group_id',
            'teacher_announcements', ['class_group_id'], unique=False,
        )


def downgrade() -> None:
    """回滚：删除索引与列（定向范围信息随之丢失，全体公告语义不变）。"""
    inspector = sa.inspect(op.get_bind())
    indexes = {idx["name"] for idx in inspector.get_indexes("teacher_announcements")}
    if "ix_teacher_announcements_class_group_id" in indexes:
        op.drop_index('ix_teacher_announcements_class_group_id', table_name='teacher_announcements')
    columns = {col["name"] for col in inspector.get_columns("teacher_announcements")}
    if "class_group_id" in columns:
        op.drop_column('teacher_announcements', 'class_group_id')
