"""schedule change requests: 教师调课 / 增课申请

Revision ID: a5c6d7e8f9g0
Revises: z4b5c6d7e8f9
Create Date: 2026-11-07 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5c6d7e8f9g0'
down_revision: Union[str, Sequence[str], None] = 'z4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "schedule_change_requests"


def upgrade() -> None:
    """排课调整申请单。

    可重入：先 inspect 判断表是否已存在（部分环境手工建过表时不会中断升级）。
    """
    inspector = sa.inspect(op.get_bind())
    if TABLE in inspector.get_table_names():
        return

    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.Enum("SWAP", "ADD", name="schedulechangekind"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "CANCELLED", name="schedulechangestatus"),
            nullable=False,
        ),
        sa.Column("applicant_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("applicant_name", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
        sa.Column("origin_day_of_week", sa.Integer(), nullable=True),
        sa.Column("origin_start_period", sa.Integer(), nullable=True),
        sa.Column("origin_end_period", sa.Integer(), nullable=True),
        sa.Column("origin_location", sa.String(length=100), nullable=True),
        sa.Column("origin_teacher", sa.String(length=50), nullable=True),
        sa.Column("origin_week_start", sa.Integer(), nullable=True),
        sa.Column("origin_week_end", sa.Integer(), nullable=True),
        sa.Column("class_group_id", sa.Integer(), sa.ForeignKey("class_groups.id"), nullable=False),
        sa.Column("class_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("course_name", sa.String(length=100), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("teacher_name", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_period", sa.Integer(), nullable=False),
        sa.Column("end_period", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("week_end", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("semester", sa.String(length=20), nullable=False),
        sa.Column("credit", sa.Float(), nullable=True),
        # MySQL 不允许 TEXT 列带字面量默认值，改用 SQL 表达式默认值（同样可空）
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("approver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approver_name", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("applied_course_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_schedule_change_requests_kind", TABLE, ["kind"])
    op.create_index("ix_schedule_change_requests_status", TABLE, ["status"])
    op.create_index("ix_schedule_change_requests_applicant_id", TABLE, ["applicant_id"])
    op.create_index("ix_schedule_change_requests_course_id", TABLE, ["course_id"])
    op.create_index("ix_schedule_change_requests_class_group_id", TABLE, ["class_group_id"])
    op.create_index("ix_schedule_change_requests_teacher_id", TABLE, ["teacher_id"])
    op.create_index("ix_schedule_change_applicant_created", TABLE, ["applicant_id", "created_at"])
    op.create_index("ix_schedule_change_status_created", TABLE, ["status", "created_at"])
    op.create_index("ix_schedule_change_semester", TABLE, ["semester"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE not in inspector.get_table_names():
        return
    op.drop_table(TABLE)
