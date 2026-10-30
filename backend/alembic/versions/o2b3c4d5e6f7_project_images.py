"""项目作品图片（作品集多图）

Revision ID: o2b3c4d5e6f7
Revises: n1a2b3c4d5e6
Create Date: 2026-10-29

作品集需要「一个项目几张图」——封面 + 过程截图。存 JSON 数组字符串，
不单独建表：图片只在项目详情里整体读写，没有按图查询/统计的需求。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'o2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'n1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    cols = {c["name"] for c in inspector.get_columns("student_projects")}
    # 幂等：本地库可能已被手工 ALTER 过
    if "images" not in cols:
        op.add_column("student_projects", sa.Column("images", sa.Text(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    cols = {c["name"] for c in inspector.get_columns("student_projects")}
    if "images" in cols:
        op.drop_column("student_projects", "images")
