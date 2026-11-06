"""心理预警双轨降噪：triage 分流字段 + 情绪台账备注

- ai_dialog_summaries 增加 triage_status / triage_source / judge_reason
- emotion_records 增加 note（对话来源的情绪台账短句）

可重入：全部为 additive 列，已存在时跳过。
"""
from alembic import op
import sqlalchemy as sa

revision = "f8a9b0c1d2e3"
down_revision = "c7e8f9a0b1c2"
branch_labels = None
depends_on = None


def _add_column_safe(table: str, column: sa.Column) -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns(table)}
    if column.name not in cols:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_safe(
        "ai_dialog_summaries",
        sa.Column("triage_status", sa.String(20), nullable=False, server_default="alert"),
    )
    _add_column_safe("ai_dialog_summaries", sa.Column("triage_source", sa.String(20), nullable=True))
    _add_column_safe("ai_dialog_summaries", sa.Column("judge_reason", sa.Text(), nullable=True))
    _add_column_safe("emotion_records", sa.Column("note", sa.String(200), nullable=True))


def downgrade() -> None:
    pass
