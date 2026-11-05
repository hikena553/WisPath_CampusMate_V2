"""统一外部资讯条目的 feed_key，使其与资讯源当前 feed_key 一致

早期版本用硬编码的简短 feed_key（arxiv / xinhua / github-stars 等）入库，
后续资讯源改为数据库驱动后 feed_key 变为「域名+源ID」形式，导致同一批资讯
在按资讯源/资讯账号统计时对不上。这里按 source_name 回填为新 feed_key。

Revision ID: c1a2b3c4d5e6
Revises: b9d0f2a4c6e8
"""

from alembic import op
import sqlalchemy as sa

revision = "c1a2b3c4d5e6"
down_revision = "b9d0f2a4c6e8"
branch_labels = None
depends_on = None


def _find_source(name: str, sources: list[tuple[str, str, str]]) -> tuple[str, str] | None:
    """按来源名匹配资讯源；兼容「arXiv AI」→「arXiv」这类前后缀差异。"""
    target = (name or "").strip().lower()
    if not target:
        return None
    for src_name, feed_key, source_type in sources:
        if (src_name or "").strip().lower() == target:
            return feed_key, source_type
    for src_name, feed_key, source_type in sources:
        s = (src_name or "").strip().lower()
        if len(s) >= 4 and (target.startswith(s) or s.startswith(target)):
            return feed_key, source_type
    return None


def upgrade() -> None:
    conn = op.get_bind()
    sources = [
        (row[0], row[1], row[2])
        for row in conn.execute(
            sa.text(
                "SELECT name, feed_key, source_type FROM feed_sources "
                "WHERE feed_key IS NOT NULL AND feed_key <> ''"
            )
        )
    ]
    if not sources:
        return
    legacy = conn.execute(
        sa.text(
            "SELECT DISTINCT feed_key, source_name FROM external_feed_items "
            "WHERE feed_key IS NOT NULL AND source_name IS NOT NULL"
        )
    ).fetchall()
    for feed_key, source_name in legacy:
        matched = _find_source(source_name, sources)
        if not matched:
            continue
        new_key, new_type = matched
        if new_key == feed_key:
            continue
        conn.execute(
            sa.text(
                "UPDATE external_feed_items SET feed_key = :new_key, source_type = :new_type "
                "WHERE feed_key = :old_key AND source_name = :source_name"
            ),
            {
                "new_key": new_key,
                "new_type": new_type,
                "old_key": feed_key,
                "source_name": source_name,
            },
        )


def downgrade() -> None:
    # 纯数据订正，不做回滚
    pass
