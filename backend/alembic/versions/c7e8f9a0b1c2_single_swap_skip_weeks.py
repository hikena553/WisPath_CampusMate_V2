"""single-week swap: courses.skip_weeks / source_change_id, requests.origin_week_no

单次调课落地字段：
- courses.skip_weeks      —— 被调走的教学周（原课保留，只是那几周不上）
- courses.source_change_id—— 由哪张调课申请补出来的单次补课（溯源/撤销）
- schedule_change_requests.origin_week_no —— 挪走的是第几教学周

Revision ID: c7e8f9a0b1c2
Revises: a5b6c7d8e9f0
Create Date: 2026-11-07 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'a5b6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table: str) -> set[str]:
    return {c["name"] for c in inspector.get_columns(table)} if table in inspector.get_table_names() else set()


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    course_cols = _columns(inspector, "courses")
    if course_cols and "skip_weeks" not in course_cols:
        op.add_column(
            "courses",
            sa.Column("skip_weeks", sa.String(length=100), nullable=True,
                      comment="跳过的教学周，逗号分隔，如 5,7"),
        )
    if course_cols and "source_change_id" not in course_cols:
        op.add_column("courses", sa.Column("source_change_id", sa.Integer(), nullable=True))
        op.create_index("ix_courses_source_change_id", "courses", ["source_change_id"])

    req_cols = _columns(inspector, "schedule_change_requests")
    if req_cols and "origin_week_no" not in req_cols:
        op.add_column(
            "schedule_change_requests",
            sa.Column("origin_week_no", sa.Integer(), nullable=True,
                      comment="被调整的是第几教学周（单次调课）"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    req_cols = _columns(inspector, "schedule_change_requests")
    if "origin_week_no" in req_cols:
        op.drop_column("schedule_change_requests", "origin_week_no")
    course_cols = _columns(inspector, "courses")
    if "source_change_id" in course_cols:
        op.drop_index("ix_courses_source_change_id", table_name="courses")
        op.drop_column("courses", "source_change_id")
    if "skip_weeks" in course_cols:
        op.drop_column("courses", "skip_weeks")
