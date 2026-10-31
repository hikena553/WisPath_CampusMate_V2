"""数据库接入自检 / 初始化：保证不同开发者的库与仓库迁移脚本完全一致。

为什么需要它
------------
模型（app/models）与迁移（alembic/versions）是仓库里的事实源，但每个开发者
本地那份库是各跑各的：有人从旧 dump 恢复、有人忘了 upgrade、有人手工 ALTER 过。
结果就是「同样的代码，别人那里能跑，我这里 500」。本脚本把「一致性」变成一条
可执行的命令，任何人 clone 之后跑一次就知道自己的库是否合格。

    python scripts/db_bootstrap.py --check    # 只自检，有漂移 exit 1（可进 CI / pre-push）
    python scripts/db_bootstrap.py --init     # 建库 + 迁移到 head（新成员首次接入）
    python scripts/db_bootstrap.py --init --accounts   # 顺带建最小权限账号
    python scripts/db_bootstrap.py --dict     # 迁移后重建数据字典

检查项（对应 docs/数据库规范.md）：
    1. 连接与版本              MySQL >= 8.0
    2. 库级字符集              utf8mb4 / utf8mb4_0900_ai_ci（§2.1）
    3. 迁移版本                alembic_version == 仓库 head（§9.2）
    4. 缺表                    模型声明但库里没有 —— 致命
    5. 缺列                    模型声明但表里没有 —— 致命（启动期 schema_guard 会补，
                               但补出来的列是 NULL 的，属于「静默漂移」，必须报出来）
    6. 缺索引                  模型声明 index=True/Index() 但库里没建 —— 性能静默劣化（§6.4）
    7. 无主键 / 非 InnoDB 表   违反 §4.1
    8. 历史遗留表              库里有、模型没有 —— 只提示不报错（§19 归档区）

退出码：0 = 一致 / 1 = 有致命漂移 / 2 = 环境错误（连不上库）
"""
from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pymysql  # noqa: E402
from sqlalchemy import create_engine, inspect  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

REQUIRED_COLLATION = "utf8mb4_0900_ai_ci"


def load_all_models() -> None:
    """把 app/models 下所有模块都 import 一遍，确保 Base.metadata 完整。

    只 import app.models 包是不够的：`__init__` 未必逐个导出，漏掉的模型不会
    进 metadata，自检就会把「其实缺的表」判成「一致」。这里用 pkgutil 兜底。
    """
    import app.models as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name.startswith("_"):
            continue
        importlib.import_module(f"{pkg.__name__}.{mod.name}")


def conn_params() -> dict:
    parsed = urlparse(settings.DATABASE_URL)
    if parsed.scheme.startswith("sqlite"):
        raise SystemExit("当前 DATABASE_URL 是 SQLite；本脚本只校验 MySQL（项目正式库形态）。")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "db": parsed.path.lstrip("/"),
    }


def connect(database: str | None = None, **kw):
    return pymysql.connect(charset="utf8mb4", autocommit=True, database=database, **kw)


def repo_head() -> str | None:
    """读取仓库里迁移脚本的最新 head（不连库）。"""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


def db_state(p: dict) -> dict:
    try:
        conn = connect(database=p["db"], host=p["host"], port=p["port"],
                       user=p["user"], password=p["password"])
    except pymysql.err.OperationalError as exc:
        if exc.args and exc.args[0] == 1049:  # Unknown database
            return {"missing_db": True, "version": "?", "db": p["db"]}
        raise
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
            cur.execute(
                "SELECT default_character_set_name, default_collation_name "
                "FROM information_schema.schemata WHERE schema_name=%s",
                (p["db"],),
            )
            row = cur.fetchone()
            if row is None:
                return {"missing_db": True, "version": version}
            charset, collation = row
            cur.execute(
                "SELECT table_name, engine FROM information_schema.tables "
                "WHERE table_schema=%s AND table_type='BASE TABLE'",
                (p["db"],),
            )
            tables = {t: (e or "") for t, e in cur.fetchall()}
            rev = None
            if "alembic_version" in tables:
                cur.execute("SELECT version_num FROM alembic_version")
                got = cur.fetchone()
                rev = got[0] if got else None
    finally:
        conn.close()

    engine = create_engine(settings.DATABASE_URL)
    try:
        insp = inspect(engine)
        columns: dict[str, set[str]] = {}
        indexes: dict[str, set[str]] = {}
        pks: dict[str, bool] = {}
        for t in tables:
            columns[t] = {c["name"] for c in insp.get_columns(t)}
            indexes[t] = {i["name"] for i in insp.get_indexes(t)} | {"PRIMARY"} if insp.get_pk_constraint(t).get("constrained_columns") else {i["name"] for i in insp.get_indexes(t)}
            pks[t] = bool(insp.get_pk_constraint(t).get("constrained_columns"))
    finally:
        engine.dispose()

    return {
        "missing_db": False,
        "version": version,
        "charset": charset,
        "collation": collation,
        "tables": tables,
        "columns": columns,
        "indexes": indexes,
        "pks": pks,
        "revision": rev,
    }


def check(state: dict, head: str | None) -> list[tuple[str, str]]:
    """返回 [(级别, 描述)]，级别 ok / warn / fail。"""
    load_all_models()
    md = Base.metadata
    out: list[tuple[str, str]] = []

    ver = state["version"]
    major = int(ver.split(".")[0]) if ver and ver[0].isdigit() else 0
    out.append(("ok" if major >= 8 else "warn", f"MySQL {ver}" + ("" if major >= 8 else "（规范要求 8.0+）")))

    if state["missing_db"]:
        out.append(("fail", f"库 `{state.get('db')}` 不存在，先执行 --init"))
        return out

    coll = state["collation"]
    out.append(("ok" if coll == REQUIRED_COLLATION else "fail",
                f"库排序规则 {coll}" + ("" if coll == REQUIRED_COLLATION else f"（应为 {REQUIRED_COLLATION}）")))

    rev = state["revision"]
    if rev == head:
        out.append(("ok", f"迁移版本 {rev} == 仓库 head"))
    else:
        out.append(("fail", f"迁移版本 {rev or '空'} != 仓库 head {head}，执行 `alembic upgrade head`"))

    missing_tables = sorted(set(md.tables) - set(state["tables"]))
    if missing_tables:
        out.append(("fail", f"缺表 {len(missing_tables)} 张：{', '.join(missing_tables[:8])}"
                            + (" …" if len(missing_tables) > 8 else "")))
    else:
        out.append(("ok", f"模型 {len(md.tables)} 张表全部存在"))

    missing_cols: list[str] = []
    for tname, table in md.tables.items():
        if tname not in state["tables"]:
            continue
        have = state["columns"].get(tname, set())
        for col in table.columns:
            if col.name not in have:
                missing_cols.append(f"{tname}.{col.name}")
    if missing_cols:
        out.append(("fail", f"缺列 {len(missing_cols)} 个：{', '.join(missing_cols[:8])}"
                            + (" …" if len(missing_cols) > 8 else "")))
    else:
        out.append(("ok", "模型字段全部存在"))

    missing_idx: list[str] = []
    for tname, table in md.tables.items():
        if tname not in state["tables"]:
            continue
        have = state["indexes"].get(tname, set())
        for idx in table.indexes:
            if idx.name not in have:
                missing_idx.append(f"{tname}.{idx.name}")
    if missing_idx:
        out.append(("fail", f"缺索引 {len(missing_idx)} 个：{', '.join(missing_idx[:8])}"
                            + (" …" if len(missing_idx) > 8 else "")))
    else:
        out.append(("ok", "模型声明的索引全部存在"))

    no_pk = sorted(t for t in state["tables"] if not state["pks"].get(t))
    out.append(("ok" if not no_pk else "warn",
                "所有表均有主键" if not no_pk else f"无主键表 {len(no_pk)} 张：{', '.join(no_pk[:8])}"))

    non_innodb = sorted(t for t, e in state["tables"].items() if e and e.lower() != "innodb")
    out.append(("ok" if not non_innodb else "warn",
                "全部 InnoDB" if not non_innodb else f"非 InnoDB 表：{', '.join(non_innodb[:8])}"))

    legacy = sorted(set(state["tables"]) - set(md.tables) - {"alembic_version"})
    out.append(("warn" if legacy else "ok",
                f"历史遗留表 {len(legacy)} 张（不计入失败，见 docs/遗留表下线评估.md）"
                if legacy else "无历史遗留表"))
    return out


def do_init(p: dict, with_accounts: bool) -> int:
    import subprocess

    admin = connect(host=p["host"], port=p["port"], user=p["user"], password=p["password"])
    try:
        with admin.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{p['db']}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE {REQUIRED_COLLATION}"
            )
    finally:
        admin.close()
    print(f"[init] 库 `{p['db']}` 就绪（utf8mb4 / {REQUIRED_COLLATION}）")

    print("[init] 执行 alembic upgrade head（用 MIGRATION_DATABASE_URL 的账号）")
    rc = subprocess.call([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=str(BACKEND_DIR))
    if rc != 0:
        print("[init] 迁移失败：若是 1142/1044，说明该账号没有 DDL 权限，换 campus_ddl 或管理员账号")
        return rc

    if with_accounts:
        print("[init] 创建最小权限账号（密码只显示一次）")
        subprocess.call([sys.executable, str(BACKEND_DIR / "scripts" / "db_accounts.py")], cwd=str(BACKEND_DIR))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="数据库接入自检 / 初始化，保证多人协作时库结构一致")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="只自检，有漂移返回 1")
    g.add_argument("--init", action="store_true", help="建库 + 迁移到 head")
    g.add_argument("--dict", action="store_true", help="重新生成 docs/数据库数据字典.md")
    ap.add_argument("--accounts", action="store_true", help="配合 --init：顺带创建最小权限账号")
    args = ap.parse_args()

    if args.dict:
        import subprocess

        return subprocess.call([sys.executable, str(BACKEND_DIR / "scripts" / "db_dict.py")], cwd=str(BACKEND_DIR))

    p = conn_params()
    if args.init:
        return do_init(p, args.accounts)

    try:
        state = db_state(p)
    except pymysql.err.OperationalError as exc:
        code = exc.args[0] if exc.args else "?"
        print(f"[fail] 连不上 {p['user']}@{p['host']}:{p['port']}/{p['db']}（errno={code}）")
        print("       1049 库不存在 -> --init   1045 密码错 -> 检查 backend/.env")
        return 2

    state["db"] = p["db"]
    head = repo_head()
    rows = check(state, head)

    print("=" * 68)
    print(f"  数据库一致性自检  {p['user']}@{p['host']}:{p['port']}/{p['db']}")
    print("=" * 68)
    mark = {"ok": "[ OK ]", "warn": "[WARN]", "fail": "[FAIL]"}
    for level, msg in rows:
        print(f"  {mark[level]} {msg}")
    print("=" * 68)

    failed = [m for lv, m in rows if lv == "fail"]
    if failed:
        print(f"  结论：{len(failed)} 项不一致 —— 这份库不能直接用于联调/提测。")
        print("  修复：python scripts/db_bootstrap.py --init   （或在库里跑 alembic upgrade head）")
        return 1
    print("  结论：与仓库迁移脚本一致，可以正常开发。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
