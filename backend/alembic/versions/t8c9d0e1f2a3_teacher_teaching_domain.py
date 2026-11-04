"""教师端教学域：courses.teacher_id + attendances / homeworks / homework_submissions

背景
----
教师端 v3 把产品定位明确为「育人 + 辅导员工作台 + 个人工作台」，其中原先完全
缺位的「教学」域需要三块数据支撑：课堂考勤、作业布置与提交、课程归属。

本次迁移做两件事：

1. ``courses`` 增加 ``teacher_id``（可空 + 索引），并**按姓名回填一次**。
   历史数据里授课教师只有 ``teacher`` 这一个姓名字符串，没有它就回答不了
   「这位老师教哪些课」——教师端所有按课过滤的查询都绕不开这一列。
2. 新建 ``attendances`` / ``homeworks`` / ``homework_submissions`` 三张表。

为什么 teacher_id 可空、且不删 teacher
--------------------------------------
- 回填靠 ``users.name`` 匹配，必然有命不中的（同名、教师账号未建、离职教师）。
  设成 NOT NULL 会让迁移在真实库上直接失败，也会卡住「先建课、后指派」的录入流程。
- ``teacher`` 字符串是教务导入的原始事实，删了就无法再核对回填结果。
  过渡期读取走 ``teacher_id == me OR (teacher_id IS NULL AND teacher == 我的姓名)``，
  回填覆盖率达标后再由后续迁移下线兜底条件。

幂等
----
所有 ``ADD COLUMN`` / ``CREATE TABLE`` 都先查 inspector，重复执行不报错——
本项目的部署环境存在「手工 stamp head」的历史，迁移必须能安全重跑。

Revision ID: t8c9d0e1f2a3
Revises: p7b8c9d0e1f2
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "t8c9d0e1f2a3"
down_revision = "p7b8c9d0e1f2"
branch_labels = None
depends_on = None


def _has_column(inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def _has_table(inspector, table: str) -> bool:
    return table in set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── 1. courses.teacher_id ──────────────────────────────────────────
    if _has_table(inspector, "courses") and not _has_column(inspector, "courses", "teacher_id"):
        op.add_column(
            "courses",
            sa.Column("teacher_id", sa.Integer(), nullable=True, comment="授课教师用户 id"),
        )
        op.create_index("ix_courses_teacher_id", "courses", ["teacher_id"])
        op.create_index("ix_courses_teacher_semester", "courses", ["teacher_id", "semester"])

        # 回填：姓名 → 教师账号。只认「姓名唯一命中且 role=teacher」的记录，
        # 同名歧义一律留空并计入待人工核对，宁可空着也不猜。
        bind.execute(
            sa.text(
                """
                UPDATE courses c
                JOIN (
                    SELECT name, MIN(id) AS teacher_id
                    FROM users
                    WHERE role = 'teacher' AND name IS NOT NULL AND name <> ''
                    GROUP BY name
                    HAVING COUNT(*) = 1
                ) t ON t.name = c.teacher
                SET c.teacher_id = t.teacher_id
                WHERE c.teacher_id IS NULL AND c.teacher IS NOT NULL AND c.teacher <> ''
                """
            )
        )

    # ── 2. attendances ────────────────────────────────────────────────
    if not _has_table(inspector, "attendances"):
        op.create_table(
            "attendances",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("class_group_id", sa.Integer(), nullable=True),
            sa.Column("teacher_id", sa.Integer(), nullable=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("attend_date", sa.Date(), nullable=False),
            sa.Column("period_start", sa.Integer(), nullable=False),
            sa.Column("period_end", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "status",
                sa.Enum(
                    "PRESENT", "LATE", "ABSENT", "LEAVE", "EXCUSED",
                    name="attendancestatus",
                ),
                nullable=False,
                server_default="PRESENT",
            ),
            sa.Column("leave_request_id", sa.Integer(), nullable=True),
            sa.Column("remark", sa.String(200), nullable=True),
            sa.Column("task_created", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("recorded_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "course_id", "attend_date", "period_start", "student_id",
                name="uq_attendance_seat",
            ),
        )
        op.create_index("ix_attendances_course_id", "attendances", ["course_id"])
        op.create_index("ix_attendances_class_group_id", "attendances", ["class_group_id"])
        op.create_index("ix_attendances_teacher_id", "attendances", ["teacher_id"])
        op.create_index("ix_attendances_student_id", "attendances", ["student_id"])
        op.create_index("ix_attendances_attend_date", "attendances", ["attend_date"])
        op.create_index("ix_attendances_status", "attendances", ["status"])
        op.create_index("ix_attendances_course_date", "attendances", ["course_id", "attend_date"])
        op.create_index("ix_attendances_student_date", "attendances", ["student_id", "attend_date"])

    # ── 3. homeworks ──────────────────────────────────────────────────
    if not _has_table(inspector, "homeworks"):
        op.create_table(
            "homeworks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("class_group_id", sa.Integer(), nullable=True),
            sa.Column("teacher_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("attachment_url", sa.String(500), nullable=True),
            sa.Column("due_at", sa.DateTime(), nullable=True),
            sa.Column("total_score", sa.Float(), nullable=False, server_default="100"),
            sa.Column(
                "status",
                sa.Enum("DRAFT", "PUBLISHED", "CLOSED", name="homeworkstatus"),
                nullable=False,
                server_default="PUBLISHED",
            ),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_homeworks_course_id", "homeworks", ["course_id"])
        op.create_index("ix_homeworks_class_group_id", "homeworks", ["class_group_id"])
        op.create_index("ix_homeworks_teacher_id", "homeworks", ["teacher_id"])
        op.create_index("ix_homeworks_status", "homeworks", ["status"])
        op.create_index("ix_homeworks_course_due", "homeworks", ["course_id", "due_at"])

    # ── 4. homework_submissions ───────────────────────────────────────
    if not _has_table(inspector, "homework_submissions"):
        op.create_table(
            "homework_submissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("homework_id", sa.Integer(), sa.ForeignKey("homeworks.id"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "PENDING", "SUBMITTED", "GRADED", "RETURNED", "LATE",
                    name="submissionstatus",
                ),
                nullable=False,
                server_default="PENDING",
            ),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("attachment_url", sa.String(500), nullable=True),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("graded_at", sa.DateTime(), nullable=True),
            sa.Column("graded_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("homework_id", "student_id", name="uq_homework_submission"),
        )
        op.create_index("ix_homework_submissions_homework_id", "homework_submissions", ["homework_id"])
        op.create_index("ix_homework_submissions_student_id", "homework_submissions", ["student_id"])
        op.create_index("ix_homework_submissions_status", "homework_submissions", ["status"])
        op.create_index("ix_hw_submissions_student", "homework_submissions", ["student_id", "submitted_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in ("homework_submissions", "homeworks", "attendances"):
        if _has_table(inspector, table):
            op.drop_table(table)

    if _has_table(inspector, "courses") and _has_column(inspector, "courses", "teacher_id"):
        for name in ("ix_courses_teacher_semester", "ix_courses_teacher_id"):
            try:
                op.drop_index(name, table_name="courses")
            except Exception:  # noqa: BLE001 - 索引不存在时降级不阻断
                pass
        op.drop_column("courses", "teacher_id")
