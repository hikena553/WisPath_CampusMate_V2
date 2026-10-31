"""Schema 对账守卫：进程启动时补齐「真实库比模型少的列」。

为什么需要它
------------
schema 的唯一事实源是 Alembic 迁移链，正常路径下 `alembic upgrade head` 就能把库
带到目标状态。但现实里有三种让库「版本号已是 head、真实结构却缺列」的情况：

1. **从旧备份恢复**：备份是 head 之前的快照，但 `alembic_version` 表来自更晚的备份；
2. **手工 `alembic stamp head`**：有人为了「先跑起来」直接把版本号顶到最新；
3. **迁移脚本在某个环境漏跑**（多环境手工发布时的典型事故）。

这三种情况下应用不会报「迁移失败」，而是在第一次访问对应接口时抛
`Unknown column 'xxx' in 'field list'`，整片接口 500，且重启也不会变好——
因为 `upgrade head` 认为无事可做。本模块就是打破这个死循环的最后一道闸门。

设计取舍
--------
- **只补列，不建表、不删列、不改类型**：建表属于迁移职责，擅自建表会与迁移链冲突；
  改类型有数据丢失风险。补列是三者里唯一「加了就一定更接近正确」的操作。
- **一律以「可空」方式加列**：给已有行补 NOT NULL 且无默认值会直接失败；
  补成可空后由业务写入填补，并在日志里明确告警。
- **失败不阻断启动**：这是兜底，不是主路径。任何异常只记 ERROR，让应用继续起，
  避免「本来只有一张表缺列，结果整个服务起不来」。
"""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.schema import DefaultClause

from app.core.database import Base, get_migration_engine

logger = logging.getLogger(__name__)


def _render_default(column, dialect) -> str | None:
    """把模型里声明的 server_default 渲染成可拼进 DDL 的 SQL 片段。"""
    default = column.server_default
    if default is None:
        return None

    arg = default.arg if isinstance(default, DefaultClause) else default
    if arg is None:
        return None

    if isinstance(arg, str):
        # 纯数字/布尔字面量直接拼；其余按字符串加引号
        stripped = arg.strip()
        if stripped.upper() in {"NULL", "CURRENT_TIMESTAMP"} or stripped.replace(".", "", 1).isdigit():
            return stripped
        return "'" + stripped.replace("\\", "\\\\").replace("'", "''") + "'"

    try:  # func.now() 之类的 SQL 表达式
        return str(arg.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
    except Exception:  # noqa: BLE001 - 渲染失败就不带默认值,见函数注释的取舍
        return None


def _add_column_sql(table_name: str, column, dialect) -> str:
    """生成 ADD COLUMN 语句。可空优先，见模块注释「设计取舍」。"""
    type_sql = column.type.compile(dialect=dialect)
    default_sql = _render_default(column, dialect)
    ddl = f"ALTER TABLE `{table_name}` ADD COLUMN `{column.name}` {type_sql}"
    if default_sql:
        ddl += f" DEFAULT {default_sql}"
    return ddl


def repair_missing_columns() -> list[str]:
    """对比模型与真实库，补齐缺失列。返回被修复的 `table.column` 列表。"""
    repaired: list[str] = []

    # 读写检查 + DDL 修复都走迁移账号：运行时账号按规范没有 ALTER 权限，
    # 用它执行 ADD COLUMN 只会拿到 1142，然后每张表刷一条 ERROR 日志。
    ddl_engine = get_migration_engine()
    dialect = ddl_engine.dialect

    try:
        inspector = inspect(ddl_engine)
        table_names = set(inspector.get_table_names())
    except Exception as exc:  # noqa: BLE001 - 连不上库时交给上层迁移逻辑报错
        logger.error("schema 对账：无法读取库结构，跳过（%s）", exc)
        return repaired

    for table in Base.metadata.sorted_tables:
        if table.name not in table_names:
            # 表缺失意味着迁移没跑或跑了一半，这里不擅自建表（会与迁移链冲突）
            logger.error(
                "schema 对账：模型表 `%s` 在库中不存在，请执行 alembic upgrade head",
                table.name,
            )
            continue

        try:
            existing = {c["name"] for c in inspector.get_columns(table.name)}
        except Exception as exc:  # noqa: BLE001
            logger.warning("schema 对账：读取 `%s` 列信息失败，跳过（%s）", table.name, exc)
            continue

        missing = [c for c in table.columns if c.name not in existing]
        if not missing:
            continue

        for column in missing:
            ddl = _add_column_sql(table.name, column, dialect)
            try:
                with ddl_engine.begin() as conn:
                    conn.execute(text(ddl))
            except Exception as exc:  # noqa: BLE001 - 单列失败不影响其他列
                logger.error(
                    "schema 对账：补齐 `%s.%s` 失败（%s）；请手工核对：%s",
                    table.name, column.name, exc, ddl,
                )
                continue

            repaired.append(f"{table.name}.{column.name}")
            logger.warning(
                "schema 对账：已补齐缺失列 `%s.%s`（按可空方式添加，已有行该列为 NULL）。"
                "这说明该环境的迁移链与真实库不一致，请尽快核对并补一份正式迁移。",
                table.name, column.name,
            )

    if repaired:
        logger.error(
            "schema 对账：本次共修补 %d 个列，说明库曾偏离迁移链：%s",
            len(repaired), ", ".join(repaired),
        )
    return repaired
