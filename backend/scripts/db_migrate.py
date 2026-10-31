#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SQLite -> MySQL 行数据搬运工具（WisPath CampusMate）

背景
----
本地开发跑 SQLite（backend/campus_mate.db），生产跑 MySQL 8。两者的表结构由
同一套 Alembic 迁移生成，所以「schema」不用搬 —— 云端执行 `alembic upgrade head`
就建好了。本脚本只搬「行数据」，并处理三类方言差异：

1. JSON 列
   SQLite 里是 TEXT（'{"a": 1}'），MySQL 是原生 JSON 类型。若把字符串原样塞进去，
   SQLAlchemy 会再 json.dumps 一次，落库变成 "{\\"a\\": 1}"（双重编码），
   业务层读出来就是字符串而不是对象。所以写库前必须先 json.loads。
2. 日期列
   SQLite 里可能存在空串 ''，MySQL 严格模式（STRICT_TRANS_TABLES）遇到会直接
   报 Incorrect datetime value。统一转成 NULL。
3. 外键顺序
   跨表插入顺序无法预先确定，全程 FOREIGN_KEY_CHECKS=0，结束再恢复。

用法
----
在 backend/ 目录下执行：

    # 1) 导出本地 SQLite 为可移植的 JSON（列名 + 行数据，含表结构版本指纹）
    python scripts/db_migrate.py export --out dump.json

    # 2) 干跑：只统计会写多少行，不落库（仍然会连目标库读列类型）
    python scripts/db_migrate.py import --dump dump.json --target "mysql+pymysql://..." --dry-run

    # 3) 正式导入（默认先清空目标表，保证 id 与源库一致）
    python scripts/db_migrate.py import --dump dump.json --target "mysql+pymysql://..."

    # 4) 核对每张表源/目标行数
    python scripts/db_migrate.py verify --dump dump.json --target "mysql+pymysql://..."

--source / --target 省略时，分别回落到 backend/.env 与同名环境变量里的 DATABASE_URL。
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import (
    JSON,
    JSON as SAJSON,
    Date as SADate,
    DateTime as SADateTime,
    MetaData,
    Table,
    Time as SATime,
    create_engine,
    inspect,
)
from sqlalchemy.engine import Engine

# 这些表属于数据库自身的元数据，不能跨库搬运：
#   alembic_version —— 目标库必须保留自己的版本号（决定后续迁移起点）
#   sqlite_*        —— SQLite 内部统计/自增序列表，MySQL 没有对应物
SKIP_TABLES = {
    "alembic_version",
    "sqlite_sequence",
    "sqlite_stat1",
    "sqlite_stat4",
}

BATCH_SIZE = 500

# 历史遗留的列名映射（本地 SQLite 早期手工建表留下的旧列名 -> 当前模型/迁移的列名）。
# user_follows：旧库是 followee_id，模型与迁移（n9o0p1q2r3s4）统一为 following_id；
# 该迁移脚本里有 has_table 短路，所以已存在的旧表不会被纠正，只能在这里对齐。
COLUMN_ALIASES: dict[str, dict[str, str]] = {
    "user_follows": {"followee_id": "following_id"},
}


# ─────────────────────────── 基础工具 ───────────────────────────


def _backend_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _url_from_dotenv() -> str:
    """从 backend/.env 读取 DATABASE_URL，避免为了跑脚本而 import 整个应用配置。"""
    env_path = _backend_dir() / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "DATABASE_URL":
            return value.strip().strip('"').strip("'")
    return ""


def _json_default(obj):
    """导出时兜底序列化：SQLite 原生返回的多是 str/int/float/None，其余按需转换。"""
    if isinstance(obj, _dt.datetime):
        return obj.isoformat(sep=" ")
    if isinstance(obj, (_dt.date, _dt.time)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (bytes, bytearray)):
        return {"__blob_b64__": base64.b64encode(obj).decode("ascii")}
    raise TypeError(f"无法序列化的类型: {type(obj).__name__}")


def _quote(engine: Engine, name: str) -> str:
    """按目标方言给标识符加引号（MySQL 反引号 / SQLite 双引号）。"""
    return engine.dialect.identifier_preparer.quote(name)


def _chunks(seq: list, size: int = BATCH_SIZE):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _set_fk_checks(conn, engine: Engine, enabled: bool) -> None:
    """按方言开关外键检查（MySQL 走会话变量，SQLite 走 PRAGMA）。"""
    dialect = engine.dialect.name
    if dialect in ("mysql", "mariadb"):
        conn.exec_driver_sql(f"SET FOREIGN_KEY_CHECKS={1 if enabled else 0}")
    elif dialect == "sqlite":
        conn.exec_driver_sql(f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}")


def _alembic_revision(engine: Engine, table_names: set[str]) -> str | None:
    if "alembic_version" not in table_names:
        return None
    try:
        with engine.connect() as conn:
            row = conn.exec_driver_sql("SELECT version_num FROM alembic_version").first()
        return row[0] if row else None
    except Exception:  # noqa: BLE001 - 版本号读不到不影响搬运本身
        return None


# ─────────────────────────── 类型适配 ───────────────────────────


def _is_json_type(coltype) -> bool:
    """MySQL 反射出的 JSON 是 sqlalchemy.dialects.mysql.JSON，仍是 SAJSON 子类。"""
    return isinstance(coltype, SAJSON) or coltype.__class__.__name__ == "JSON"


def _is_temporal_type(coltype) -> bool:
    return isinstance(coltype, (SADateTime, SADate, SATime))


def _coerce(value, coltype, ctx: str):
    """把 SQLite 读到的原始值，转成目标列类型能接受的形式。

    ctx 仅用于告警定位，形如 "users.birthday[12]"。
    """
    if value is None:
        return None

    # JSON：字符串 -> 对象，避免双重编码；空串/非法 JSON 一律降级为 NULL
    if _is_json_type(coltype):
        if isinstance(value, (dict, list, int, float, bool)):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                print(f"  [warn] {ctx}: JSON 解析失败，已置 NULL -> {text[:60]!r}")
                return None
        return None

    # 日期时间：空串是 SQLite 时代的「假 NULL」；能解析的显式转成 Python 对象，
    # 这样 MySQL（隐式转换）和 SQLite（只认 datetime 对象）两边都能写。
    if _is_temporal_type(coltype):
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                if isinstance(coltype, SADateTime):
                    return _dt.datetime.fromisoformat(text)
                if isinstance(coltype, SADate):
                    return _dt.date.fromisoformat(text[:10])
                if isinstance(coltype, SATime):
                    return _dt.time.fromisoformat(text)
            except ValueError:
                print(f"  [warn] {ctx}: 日期无法解析，已置 NULL -> {text[:40]!r}")
                return None
        return value

    return value


# ─────────────────────────── export ───────────────────────────


def cmd_export(args) -> int:
    source_url = args.source or _url_from_dotenv()
    if not source_url:
        print("[error] 未指定 --source，且 backend/.env 里没有 DATABASE_URL")
        return 2

    engine = create_engine(source_url)
    insp = inspect(engine)
    names = sorted(n for n in insp.get_table_names() if n not in SKIP_TABLES)

    print(f"[export] 源库: {engine.url.render_as_string(hide_password=True)}")
    print(f"[export] 表数量: {len(names)}")

    tables: dict[str, dict] = {}
    total = 0
    with engine.connect() as conn:
        for name in names:
            quoted = _quote(engine, name)
            columns = [c["name"] for c in insp.get_columns(name)]
            rows = [list(r) for r in conn.exec_driver_sql(f"SELECT * FROM {quoted}")]
            total += len(rows)
            tables[name] = {"columns": columns, "rows": rows}
            if rows:
                print(f"  {name:<40} {len(rows):>6} 行")

    doc = {
        "_meta": {
            "tool": "db_migrate.py",
            "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "source_url": engine.url.render_as_string(hide_password=True),
            "alembic_revision": _alembic_revision(engine, set(insp.get_table_names())),
            "table_count": len(names),
            "row_count": total,
        },
        "tables": tables,
    }

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(doc, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(f"[export] 完成: {out_path.resolve()}")
    print(f"[export] 共 {len(names)} 张表 / {total} 行，文件 {out_path.stat().st_size / 1024:.1f} KB")
    return 0


def _load_dump(path: str) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if "tables" not in doc:
        raise SystemExit("[error] dump 文件格式不正确：缺少 tables 字段")
    return doc


# ─────────────────────────── import ───────────────────────────


def cmd_import(args) -> int:
    doc = _load_dump(args.dump)
    target_url = args.target or os.environ.get("DATABASE_URL", "")
    if not target_url:
        print("[error] 未指定 --target，且环境变量 DATABASE_URL 为空")
        return 2

    engine = create_engine(target_url, pool_pre_ping=True)
    insp = inspect(engine)
    existing = set(insp.get_table_names())

    print(f"[import] 目标库: {engine.url.render_as_string(hide_password=True)}")
    src_rev = doc.get("_meta", {}).get("alembic_revision")
    tgt_rev = _alembic_revision(engine, existing)
    if src_rev and tgt_rev and src_rev != tgt_rev:
        print(
            f"[warn] 版本不一致：源库 {src_rev} / 目标库 {tgt_rev}\n"
            f"       请先在目标库执行 `alembic upgrade head`，否则可能出现列缺失或类型不匹配。"
        )
    if tgt_rev is None:
        print("[warn] 目标库没有 alembic_version 表 —— 表结构可能尚未初始化，"
              "请先运行 `alembic upgrade head`。")

    if args.dry_run:
        print("[import] DRY-RUN 模式：只统计，不写入")

    planned = 0
    written: list[tuple[str, int]] = []
    skipped_tables: list[tuple[str, int]] = []
    missing_cols: list[str] = []
    blocked_tables: list[tuple[str, list[str]]] = []

    conn = engine.connect()
    try:
        if not args.dry_run:
            _set_fk_checks(conn, engine, False)

        for name, payload in doc["tables"].items():
            src_cols: list[str] = payload["columns"]
            rows: list[list] = payload["rows"]

            if name not in existing:
                skipped_tables.append((name, len(rows)))
                continue
            if not rows:
                continue

            table = Table(name, MetaData(), autoload_with=engine)
            # JSON 列默认 none_as_null=False：Python None 会被 dumps 成文本 'null'，
            # 落库存的是「JSON null」而不是 SQL NULL，导致 `WHERE col IS NULL` 查不到。
            # 换成 none_as_null=True 的等价类型，让 None 老老实实写成 NULL。
            for col in table.columns:
                if _is_json_type(col.type):
                    col.type = JSON(none_as_null=True)
            tgt_cols = {c.name for c in table.columns}
            aliases = COLUMN_ALIASES.get(name, {})
            # 源列 -> 目标列（含改名映射）
            mapping = {c: aliases.get(c, c) for c in src_cols}
            absent = [c for c in src_cols if mapping[c] not in tgt_cols]
            if absent:
                missing_cols.append(f"{name}: {', '.join(absent)}")

            # 预检：目标表里 NOT NULL 且无默认值、但源库根本提供不了的列。
            # 不提前拦住的话，会在批量插入时抛 IntegrityError 且无法定位到表。
            mapped_targets = set(mapping.values())
            required = [
                c.name
                for c in table.columns
                if not c.nullable
                and c.default is None
                and c.server_default is None
                and not c.primary_key
                and c.name not in mapped_targets
            ]
            if required:
                blocked_tables.append((name, required))
                print(f"  [skip] {name}: 目标表要求 NOT NULL 列 {required}，源库无对应数据")
                continue

            records = []
            for idx, row in enumerate(rows):
                rec = {}
                for col, value in zip(src_cols, row):
                    dest = mapping[col]
                    if dest not in tgt_cols:
                        continue
                    rec[dest] = _coerce(value, table.columns[dest].type, f"{name}.{dest}[{idx}]")
                records.append(rec)

            planned += len(records)
            if args.dry_run:
                print(f"  [plan] {name:<40} {len(records):>6} 行")
                continue

            quoted = _quote(engine, name)
            if args.truncate:
                conn.exec_driver_sql(f"DELETE FROM {quoted}")
            for chunk in _chunks(records):
                conn.execute(table.insert(), chunk)
            written.append((name, len(records)))

        if not args.dry_run:
            if not args.commit:
                print("[import] --no-commit 模式：已执行但将回滚，用于演练")
                conn.rollback()
            else:
                conn.commit()
            _set_fk_checks(conn, engine, True)
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if skipped_tables:
        print("[warn] 目标库无对应表，这些表的数据不会导入（通常是已废弃的表）:")
        for name, n in skipped_tables:
            print(f"        - {name} ({n} 行)")
    if blocked_tables:
        print("[warn] 以下表因目标表 NOT NULL 列缺数据被跳过，需要人工决定填充值:")
        for name, cols in blocked_tables:
            print(f"        - {name}: {', '.join(cols)}")
    if missing_cols:
        print("[warn] 以下源列在目标表不存在（通常是目标库版本落后），已忽略:")
        for m in missing_cols:
            print(f"        - {m}")

    if args.dry_run:
        print(f"[import] DRY-RUN 完成：计划写入 {planned} 行")
    else:
        verb = "映射" if args.truncate else "追加"
        print(f"[import] 完成：{verb} {len(written)} 张表 / {planned} 行")
        top = sorted(written, key=lambda x: -x[1])[:10]
        for name, n in top:
            print(f"        {name:<40} {n:>6}")

    return 0 if not blocked_tables else 1


# ─────────────────────────── verify ───────────────────────────


def cmd_verify(args) -> int:
    doc = _load_dump(args.dump)
    target_url = args.target or os.environ.get("DATABASE_URL", "")
    if not target_url:
        print("[error] 未指定 --target，且环境变量 DATABASE_URL 为空")
        return 2

    engine = create_engine(target_url, pool_pre_ping=True)
    insp = inspect(engine)
    existing = set(insp.get_table_names())

    mismatch = 0
    checked = 0
    missing_tables = 0
    print(f"[verify] 目标库: {engine.url.render_as_string(hide_password=True)}")
    with engine.connect() as conn:
        for name, payload in doc["tables"].items():
            expect = len(payload["rows"])
            if not expect:
                continue
            if name not in existing:
                # 目标库没有这张表（通常是已废弃的表），不算行数不一致
                print(f"  [SKIP] {name:<40} 目标库无此表（源 {expect} 行）")
                missing_tables += 1
                continue
            got = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {_quote(engine, name)}").scalar_one()
            checked += 1
            if got != expect:
                print(f"  [DIFF] {name:<40} 源 {expect:>6} / 目标 {got:>6}")
                mismatch += 1

    summary = f"[verify] 核对 {checked} 张非空表"
    if missing_tables:
        summary += f"，{missing_tables} 张目标库无对应表（已跳过）"
    summary += "，行数全部一致 ✅" if not mismatch else f"，{mismatch} 张行数不一致 ❌"
    print(summary)
    return 0 if not mismatch else 1


# ─────────────────────────── CLI ───────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SQLite -> MySQL 行数据搬运工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_exp = sub.add_parser("export", help="从源库导出 JSON")
    p_exp.add_argument("--source", default="", help="源库连接串，默认取 backend/.env 的 DATABASE_URL")
    p_exp.add_argument("--out", default="dump.json", help="输出文件，默认 dump.json")
    p_exp.set_defaults(func=cmd_export)

    p_imp = sub.add_parser("import", help="把 JSON 写入目标库")
    p_imp.add_argument("--dump", default="dump.json", help="导出文件路径")
    p_imp.add_argument("--target", default="", help="目标库连接串，默认取环境变量 DATABASE_URL")
    p_imp.add_argument("--dry-run", action="store_true", help="只统计不写入")
    p_imp.add_argument("--no-truncate", dest="truncate", action="store_false",
                       help="不清空目标表，改为追加（默认清空，保证 id 与源库一致）")
    p_imp.add_argument("--no-commit", dest="commit", action="store_false",
                       help="执行后回滚，用于在真实库上演练")
    p_imp.set_defaults(func=cmd_import, truncate=True, commit=True)

    p_ver = sub.add_parser("verify", help="核对源/目标行数")
    p_ver.add_argument("--dump", default="dump.json", help="导出文件路径")
    p_ver.add_argument("--target", default="", help="目标库连接串，默认取环境变量 DATABASE_URL")
    p_ver.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
