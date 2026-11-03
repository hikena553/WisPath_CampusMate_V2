"""修复 forum_messages 的列漂移：post_title / content 等列被建成了 NOT NULL

Revision ID: r9d0e1f2a3b4
Revises: q8c9d0e1f2a3
Create Date: 2026-11-03

`o0p1q2r3s4t5_forum_messages` 建表时这些列都是可空的（关注类消息没有帖子标题，
存 None 是正常语义），但这套库当年是 create_all 建的，列被写成 NOT NULL，
此后的迁移因为「表已存在」直接跳过，漂移一直留着。表现：

    关注某人 → 写一条 kind=follow 的互动消息（post_title=None）
             → NOT NULL constraint failed: forum_messages.post_title → 接口 500

SQLite 改不了列的 NOT NULL，只能重建表。整段可重入：列已经可空就直接返回。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'r9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'q8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('forum_messages'):
        return

    columns = {col['name']: col for col in insp.get_columns('forum_messages')}
    relaxable = ('kind', 'post_title', 'content', 'is_read', 'created_at')
    if all(columns.get(name, {}).get('nullable', True) for name in relaxable):
        return

    bind.exec_driver_sql('DROP TABLE IF EXISTS forum_messages_rebuild')
    bind.exec_driver_sql(
        """
        CREATE TABLE forum_messages_rebuild (
            id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            kind VARCHAR(20),
            post_id INTEGER,
            post_title VARCHAR(200),
            content TEXT,
            is_read BOOLEAN DEFAULT 0,
            created_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id),
            FOREIGN KEY(actor_id) REFERENCES users (id)
        )
        """
    )
    bind.exec_driver_sql(
        """
        INSERT INTO forum_messages_rebuild
            (id, user_id, actor_id, kind, post_id, post_title, content, is_read, created_at)
        SELECT id, user_id, actor_id, LOWER(kind), post_id, post_title, content,
               COALESCE(is_read, 0), created_at
        FROM forum_messages
        """
    )
    bind.exec_driver_sql('DROP TABLE forum_messages')
    bind.exec_driver_sql('ALTER TABLE forum_messages_rebuild RENAME TO forum_messages')
    for name, column in (
        ('ix_forum_messages_user_id', 'user_id'),
        ('ix_forum_messages_actor_id', 'actor_id'),
        ('ix_forum_messages_kind', 'kind'),
        ('ix_forum_messages_is_read', 'is_read'),
    ):
        bind.exec_driver_sql(f'CREATE INDEX IF NOT EXISTS {name} ON forum_messages ({column})')


def downgrade() -> None:
    # 放宽约束没有信息损失，回滚不重新收紧（否则历史 follow 消息会让回滚失败）
    pass
