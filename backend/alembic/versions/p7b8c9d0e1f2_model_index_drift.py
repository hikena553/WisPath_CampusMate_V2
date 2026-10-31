"""补齐模型已声明但库中缺失的索引（users.role / users.tutor_id / plan_tasks.stage_id）

背景
----
`alembic check` 的输出里除了已知的归档表漂移（见 docs/数据库规范.md §9.2.1），还夹着
三条 `add_index`：

    add_index ix_users_role            (role)
    add_index ix_users_tutor_id        (tutor_id)
    add_index ix_plan_tasks_stage_id   (stage_id)

这三条与归档表无关：模型里写了 `index=True`，但迁移链从来没有真正建过。后果不是
报错，而是**查询静默走全表扫描**，数据量小的时候完全看不出来，等 users 涨到几万行
才发现「教师查看我的学生」变慢，那时已经很难定位到是一次漏建的迁移。

根因
----
先加字段（模型带 index=True）→ 后续某个迁移只 ALTER 加了列、没建索引 → `autogenerate`
被禁用的项目里，这种不一致没有任何机制会自动纠正。所以这类漂移只能靠 `alembic check`
的 add_* 部分定期捞（remove_* 部分一律忽略，那是归档表）。

为什么现在补是安全的
--------------------
- users 459 行、plan_tasks 47 行，建索引秒级完成，无需 ONLINE DDL；
- 三个索引都对应真实访问路径：登录/权限按 role 过滤、教师端按 tutor_id 查学生、
  计划详情按 stage_id 取任务；
- 全部幂等（先查 inspector），重复执行不报错。

不在本次范围
------------
`alembic check` 还报了三处 add_fk（users.tutor_id、plan_tasks.stage_id、
lost_found_items.claimed_by）。外键会改变写入行为（孤儿数据直接插入失败），
必须单独评审 + 单独验证数据干净，不与索引混在一个迁移里。

Revision ID: p7b8c9d0e1f2
Revises: p6f7a8b9c0d1
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "p7b8c9d0e1f2"
down_revision = "p6f7a8b9c0d1"
branch_labels = None
depends_on = None


# (表, 索引名, 列) —— 与模型声明一一对应，改动时两处同步
INDEXES: list[tuple[str, str, str]] = [
    ("users", "ix_users_role", "role"),
    ("users", "ix_users_tutor_id", "tutor_id"),
    ("plan_tasks", "ix_plan_tasks_stage_id", "stage_id"),
]


def _has_index(inspector, table: str, name: str) -> bool:
    return any(ix["name"] == name for ix in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    for table, name, column in INDEXES:
        if table not in tables:
            # 表都不存在说明是精简部署，跳过而不是报错（迁移应能在部分环境下跑通）
            continue
        if _has_index(inspector, table, name):
            continue
        op.create_index(name, table, [column])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    for table, name, _column in reversed(INDEXES):
        if table not in tables:
            continue
        if not _has_index(inspector, table, name):
            continue
        op.drop_index(name, table_name=table)
