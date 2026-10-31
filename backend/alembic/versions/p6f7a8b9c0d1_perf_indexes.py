"""性能索引补齐：高频查询列的复合索引（无损，不改数据）

Revision ID: p6f7a8b9c0d1
Revises: p5e6f7a8b9c0
Create Date: 2026-11-01

背景（见 docs/数据库规范.md 第 6 章「索引规范」）：
  基线体检发现 20 个高频查询列没有索引，查询计划退化为「单列索引 + filesort」。
  本次只补齐收益明确、且与真实访问路径对齐的 10 个复合索引，不做任何数据变更、
  不改表结构、不删表。

设计原则：
  1) 复合索引遵循「等值列在前、排序/范围列在后」——WHERE a=? AND b=? ORDER BY c
     对应 (a, b, c)，可以同时完成过滤与排序，消除 filesort。
  2) 不为布尔/枚举类低基数列单独建索引（is_read / status 单独建索引几乎无过滤能力），
     一律并入复合索引。
  3) 只为已验证的访问路径建索引；纯管理端低频查询不建，避免拖慢写入。

幂等性：每个索引创建前先查 inspector，已存在则跳过。这样在「手工加过索引」或
「从旧备份恢复」的库上重复执行也不会报 Duplicate key name。

回滚：downgrade 逐个 drop，索引与数据无关，可安全回滚。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'p6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'p5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (索引名, 表名, [列...], 说明)
_INDEXES: list[tuple[str, str, list[str], str]] = [
    # 通知列表：WHERE user_id=? [AND is_read=?] ORDER BY created_at DESC，以及未读数统计
    ("ix_notifications_user_read_created", "notifications", ["user_id", "is_read", "created_at"],
     "通知分页 + 未读数 + 时间倒序，一次走完索引"),
    # 按业务对象反查通知（同一请假/审批重复提醒去重、跳转关联详情）
    ("ix_notifications_type_related", "notifications", ["type", "related_id"],
     "按业务类型 + 业务主键反查通知"),
    # 辅导员/教师端审批列表：WHERE tutor_id=? AND status=? ORDER BY created_at DESC
    ("ix_leave_requests_tutor_status_created", "leave_requests", ["tutor_id", "status", "created_at"],
     "审批列表过滤 + 排序"),
    # 私聊会话：WHERE sender_id=? AND receiver_id=? ORDER BY created_at
    ("ix_messages_sender_receiver_created", "messages", ["sender_id", "receiver_id", "created_at"],
     "双人会话消息拉取与分页"),
    # 未读消息角标：WHERE receiver_id=? AND read=0
    ("ix_messages_receiver_read", "messages", ["receiver_id", "read"],
     "未读消息计数（低基数列并入复合索引）"),
    # 情绪记录按会话回溯：WHERE conversation_id=?
    ("ix_emotion_records_conversation", "emotion_records", ["conversation_id"],
     "会话关联的情绪轨迹查询"),
    # 成长档案：WHERE student_id=? AND type=? ORDER BY date
    ("ix_growth_records_student_type_date", "growth_records", ["student_id", "type", "date"],
     "按学生 + 类型筛选成长记录并按日期排序"),
    # 群聊消息：WHERE group_id=? ORDER BY created_at
    ("ix_group_messages_group_created", "group_messages", ["group_id", "created_at"],
     "群消息拉取与「最后一条消息」聚合"),
    # 资讯流：WHERE source_type=? ORDER BY published_at DESC
    ("ix_external_feed_items_type_published", "external_feed_items", ["source_type", "published_at", "id"],
     "资讯分类标签页排序（未过滤的全局流靠主键倒序，数据量小无需额外索引）"),
    # 会话列表：WHERE user_id=? ORDER BY updated_at DESC
    ("ix_conversations_user_updated", "conversations", ["user_id", "updated_at"],
     "AI 会话列表排序"),
]


def _existing_indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {ix["name"] for ix in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    is_mysql = bind.dialect.name == "mysql"
    for name, table, columns, _note in _INDEXES:
        if name in _existing_indexes(table):
            continue
        op.create_index(name, table, columns, unique=False)

    if is_mysql:
        # InnoDB 的统计信息在索引创建后不会立即刷新，ANALYZE 让优化器马上用上新索引
        for table in {t for _n, t, _c, _s in _INDEXES}:
            bind.execute(sa.text(f"ANALYZE TABLE `{table}`"))


def downgrade() -> None:
    for name, table, _columns, _note in reversed(_INDEXES):
        if name in _existing_indexes(table):
            op.drop_index(name, table_name=table)
