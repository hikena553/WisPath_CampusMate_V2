"""启动期 schema 漂移自愈（防御性兜底）

背景：schema 的唯一事实源仍是 alembic/versions。但历史库存在「alembic_version
已经是 head，真实表却少列」的情况（库从备份恢复、手工 stamp、迁移脚本被跳过等），
表现为运行期 `sqlite3.OperationalError: no such column: xxx` → 接口整片 500，
而 alembic 再跑多少遍都不会修，因为版本号认为已经升到位了。

本模块在迁移之后做一次「模型 vs 真实表结构」对账，把**能安全补的列**直接补上：
  - 只处理「模型里有、表里没有」的列（纯新增，不改不删，无数据风险）；
  - 只补 nullable 或有 server_default 的列，NOT NULL 无默认值的列补不上会明确报错，
    要求走正式迁移（避免静默 ALTER 失败后继续 500）；
  - 缺整张表 / 缺列 都会 WARNING/ERROR 打出来，把「隐性 500」变成「启动期可见」。

DDL 由 SQLAlchemy 按当前 dialect 编译，SQLite 与 MySQL 都能用。
"""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn

from app.core.database import Base, engine

logger = logging.getLogger(__name__)


def _safe_addable(column) -> bool:
    """能否安全 ALTER ADD COLUMN：有主键/NOT NULL 无默认值的列不可直接加。"""
    if column.primary_key:
        return False
    return bool(column.nullable or column.server_default is not None)


def repair_missing_columns() -> list[tuple[str, str]]:
    """补齐缺失列，返回实际补上的 [(table, column)]。"""
    # 模型必须全部注册进来，否则 metadata 里没有对应表
    import app.models  # noqa: F401

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    added: list[tuple[str, str]] = []
    unpreparable: list[tuple[str, str]] = []
    missing_tables: list[str] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            missing_tables.append(table.name)
            continue

        actual = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in actual:
                continue
            if not _safe_addable(column):
                unpreparable.append((table.name, column.name))
                continue

            ddl = str(CreateColumn(column).compile(dialect=engine.dialect))
            quoted = engine.dialect.identifier_preparer.quote(table.name)
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {quoted} ADD COLUMN {ddl}"))
            except Exception as exc:  # noqa: BLE001 - 自愈失败绝不能拖垮启动
                unpreparable.append((table.name, column.name))
                logger.error("schema 自愈失败 %s.%s: %s", table.name, column.name, exc)
                continue
            added.append((table.name, column.name))
            logger.warning("schema 漂移已自动修复：%s 新增列 %s", table.name, column.name)

    if missing_tables:
        logger.error(
            "schema 缺少表（应用将报 500，请补 alembic 迁移）: %s", ", ".join(missing_tables)
        )
    if unpreparable:
        logger.error(
            "schema 缺列但无法自动补（NOT NULL 无默认值或 ALTER 失败，请写正式迁移）: %s",
            ", ".join(f"{t}.{c}" for t, c in unpreparable),
        )
    return added
