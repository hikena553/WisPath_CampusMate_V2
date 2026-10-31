"""从真实数据库反向生成数据字典（docs/数据库数据字典.md）。

为什么用脚本而不是手写：手写字典三天就过期。规范要求「字典是 schema 的投影」，
每次迁移合入后重跑一次即可，永远和库一致。

用法：
    python scripts/db_dict.py              # 写入 docs/数据库数据字典.md
    python scripts/db_dict.py --stdout     # 打到终端，不落盘
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import pymysql  # noqa: E402

from app.core.config import settings  # noqa: E402

MODELS_DIR = BACKEND_DIR / "app" / "models"
OUT_PATH = PROJECT_DIR / "docs" / "数据库数据字典.md"


def table_to_domain() -> dict[str, str]:
    """表名 -> 业务域（用定义它的模型文件名表示，如 message.py -> 消息）。"""
    mapping: dict[str, str] = {}
    for py in sorted(MODELS_DIR.glob("*.py")):
        if py.name.startswith("__"):
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        for name in re.findall(r'__tablename__\s*=\s*["\']([^"\']+)["\']', text):
            mapping[name] = py.stem
    return mapping


def fetch() -> dict:
    parsed = urlparse(settings.DATABASE_URL)
    db = parsed.path.lstrip("/")
    conn = pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=db,
        charset="utf8mb4",
    )
    data: dict = {"db": db}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            data["version"] = cur.fetchone()[0]

            cur.execute(
                "SELECT table_name, engine, table_collation, table_rows, "
                "ROUND((data_length + index_length) / 1024 / 1024, 2), table_comment "
                "FROM information_schema.tables WHERE table_schema=%s ORDER BY table_name",
                (db,),
            )
            tables = cur.fetchall()

            cur.execute(
                "SELECT table_name, COUNT(*) FROM information_schema.columns "
                "WHERE table_schema=%s GROUP BY table_name",
                (db,),
            )
            col_count = dict(cur.fetchall())

            cur.execute(
                "SELECT table_name, index_name, GROUP_CONCAT(column_name ORDER BY seq_in_index) "
                "FROM information_schema.statistics WHERE table_schema=%s "
                "GROUP BY table_name, index_name",
                (db,),
            )
            indexes: dict[str, list[tuple[str, str]]] = defaultdict(list)
            for t, idx, cols in cur.fetchall():
                indexes[t].append((idx, cols))

            cur.execute(
                "SELECT table_name, column_name, referenced_table_name, referenced_column_name "
                "FROM information_schema.key_column_usage WHERE table_schema=%s "
                "AND referenced_table_name IS NOT NULL",
                (db,),
            )
            fks: dict[str, list[str]] = defaultdict(list)
            for t, col, rt, rc in cur.fetchall():
                fks[t].append(f"{col} -> {rt}.{rc}")

            cur.execute("SELECT version_num FROM alembic_version")
            row = cur.fetchone()
            data["revision"] = row[0] if row else "(无)"
    finally:
        conn.close()

    data["tables"] = tables
    data["col_count"] = col_count
    data["indexes"] = indexes
    data["fks"] = fks
    return data


def render(data: dict) -> str:
    domain_of = table_to_domain()
    tables = data["tables"]
    db = data["db"]

    total_mb = sum((t[4] or 0) for t in tables)
    orphan = [t for t in tables if t[0] not in domain_of]
    managed = [t for t in tables if t[0] in domain_of]

    engines = Counter(t[1] for t in tables)
    collations = Counter(t[2] for t in tables)

    out: list[str] = []
    a = out.append

    a("# 数据库数据字典")
    a("")
    a("> 本文件由 `backend/scripts/db_dict.py` 从真实数据库反向生成，**请勿手工编辑**。")
    a("> 每次 Alembic 迁移合入后重跑一次即可保持与库一致。")
    a("")
    a(f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    a(f"- 目标库：`{db}` @ MySQL {data['version']}")
    a(f"- Alembic 版本：`{data['revision']}`")
    a(f"- 表总数：**{len(tables)}**（代码托管 {len(managed)} + 历史归档 {len(orphan)}）")
    a(f"- 引擎分布：" + "、".join(f"{k} {v}" for k, v in engines.items()))
    a(f"- 排序规则：" + "、".join(f"{k} {v}" for k, v in collations.items()))
    a(f"- 数据 + 索引总大小：约 {total_mb:.2f} MB")
    a("")

    a("## 一、按业务域划分")
    a("")
    a("业务域取「定义该表的模型文件名」，便于代码与库对照。")
    a("")
    by_domain: dict[str, list[str]] = defaultdict(list)
    for t in managed:
        by_domain[domain_of[t[0]]].append(t[0])
    a("| 业务域（模型文件） | 表数 | 表名 |")
    a("|---|---:|---|")
    for dom in sorted(by_domain, key=lambda d: (-len(by_domain[d]), d)):
        names = "、".join(f"`{n}`" for n in sorted(by_domain[dom]))
        a(f"| `{dom}.py` | {len(by_domain[dom])} | {names} |")
    a("")

    a("## 二、表清单")
    a("")
    a("| 表名 | 业务域 | 行数(估) | 列数 | 索引 | 外键 | 大小(MB) |")
    a("|---|---|---:|---:|---:|---:|---:|")
    for name, _engine, _coll, rows, mb, _comment in tables:
        dom = domain_of.get(name, "**归档**")
        idx_n = len(data["indexes"].get(name, []))
        fk_n = len(data["fks"].get(name, []))
        a(f"| `{name}` | {dom} | {rows or 0} | {data['col_count'].get(name, 0)} | {idx_n} | {fk_n} | {mb or 0} |")
    a("")

    a("## 三、索引明细")
    a("")
    for name, *_ in tables:
        if name not in domain_of:
            continue
        idxs = data["indexes"].get(name, [])
        if not idxs:
            continue
        parts = []
        for idx, cols in sorted(idxs):
            mark = "PK " if idx == "PRIMARY" else ""
            parts.append(f"{mark}`{idx}`({cols})")
        a(f"- `{name}`：" + "；".join(parts))
    a("")

    a("## 四、外键明细")
    a("")
    for name, *_ in tables:
        if name not in domain_of:
            continue
        fl = data["fks"].get(name, [])
        if not fl:
            continue
        a(f"- `{name}`：" + "；".join(fl))
    a("")

    a("## 五、历史归档区（代码已不再引用）")
    a("")
    a("以下表在数据库中存在，但**没有任何模型定义引用**，属于历史版本遗留。")
    a("规范要求：保留只读、不得新增写入；确认无价值后走备份 + 下线流程，见规范第 10 章。")
    a("")
    a("| 表名 | 行数(估) | 说明 |")
    a("|---|---:|---|")
    for name, _engine, _coll, rows, _mb, _comment in orphan:
        if name == "alembic_version":
            a(f"| `{name}` | {rows or 0} | 迁移版本记录（框架表，非归档） |")
        else:
            a(f"| `{name}` | {rows or 0} | 历史遗留 |")
    a("")

    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="生成数据库数据字典")
    ap.add_argument("--stdout", action="store_true", help="只打印，不写文件")
    args = ap.parse_args()

    md = render(fetch())
    if args.stdout:
        print(md)
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(md, encoding="utf-8")
    print(f"已写入 {OUT_PATH}（{len(md.splitlines())} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
