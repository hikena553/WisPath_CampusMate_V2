"""修复 user_follows 的列漂移：followee_id（NOT NULL）+ following_id（可空）

Revision ID: q8c9d0e1f2a3
Revises: p7b8c9d0e1f2
Create Date: 2026-11-03

背景：这张表最早按 `followee_id` 建（老迁移），后来模型改成 `following_id`。
启动时的 schema 对账只做「缺列就补一列可空」，于是库里长成
`followee_id NOT NULL` + `following_id NULL` 的双列并存：

- 历史关注行只有 followee_id，ORM 按 following_id 查，通讯录永远空；
- 新关注走 ORM 只写 following_id，撞上 followee_id 的 NOT NULL，接口 500。

这里把表重建成模型实际需要的那一版：只留 following_id（NOT NULL），
历史数据从 followee_id 回填，索引与唯一约束一并重建。

SQLite 不支持「改列为 NOT NULL / 删列」，只能新建表 + 迁移数据 + 改名，
Alembic 的 batch 模式对这种「旧表还带着引用被删列的唯一约束」的处理不够稳，
所以这里直接写 SQL，整段可重入：列已经对了就直接返回。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'q8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'p7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TARGET_COLUMNS = {'id', 'follower_id', 'following_id', 'created_at'}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('user_follows'):
        return

    columns = {col['name'] for col in insp.get_columns('user_follows')}
    if columns == _TARGET_COLUMNS:
        # 已经是目标结构（新库直接按迁移建出来就是这个形状）
        return

    if 'followee_id' in columns and 'following_id' in columns:
        source = 'COALESCE(following_id, followee_id)'
    elif 'followee_id' in columns:
        source = 'followee_id'
    else:
        source = 'following_id'

    bind.exec_driver_sql('DROP TABLE IF EXISTS user_follows_rebuild')
    bind.exec_driver_sql(
        """
        CREATE TABLE user_follows_rebuild (
            id INTEGER NOT NULL,
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_follow_pair UNIQUE (follower_id, following_id),
            FOREIGN KEY(follower_id) REFERENCES users (id),
            FOREIGN KEY(following_id) REFERENCES users (id)
        )
        """
    )
    # INSERT OR IGNORE：历史上若有同一对重复关注，唯一约束只留最早一条
    bind.exec_driver_sql(
        f"""
        INSERT OR IGNORE INTO user_follows_rebuild (id, follower_id, following_id, created_at)
        SELECT id, follower_id, {source}, created_at
        FROM user_follows
        WHERE follower_id IS NOT NULL AND {source} IS NOT NULL
        ORDER BY id
        """
    )
    bind.exec_driver_sql('DROP TABLE user_follows')
    bind.exec_driver_sql('ALTER TABLE user_follows_rebuild RENAME TO user_follows')
    bind.exec_driver_sql(
        'CREATE INDEX IF NOT EXISTS ix_user_follows_follower_id ON user_follows (follower_id)'
    )
    bind.exec_driver_sql(
        'CREATE INDEX IF NOT EXISTS ix_user_follows_following_id ON user_follows (following_id)'
    )


def downgrade() -> None:
    # 数据方向不可逆（followee_id 只是 following_id 的旧别名），回滚只还原列结构
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('user_follows'):
        return
    columns = {col['name'] for col in insp.get_columns('user_follows')}
    if 'followee_id' in columns:
        return
    bind.exec_driver_sql('ALTER TABLE user_follows ADD COLUMN followee_id INTEGER')
    bind.exec_driver_sql('UPDATE user_follows SET followee_id = following_id WHERE followee_id IS NULL')
