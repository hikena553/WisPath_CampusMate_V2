"""遗留表下线评估：找出「库里有、代码里没有模型」的表，并给出可复核的引用证据。

背景
----
项目经历过至少两轮命名重构（sys_user -> users、knowledge_document ->
documents/knowledge_base、post_comment -> community_comments ...）。旧表被留在
库里，模型已删。这些表本身不报错，但会带来三个实际问题：

1. 看库的人会误以为它们还在用，新人照着旧表名写代码；
2. `alembic revision --autogenerate` 会把它们全部识别为「该删的表」，生成一堆
   DROP TABLE（真实踩过，见 docs/数据库规范.md §9.2.1）；
3. 备份、迁移、审计的认知负担永久存在。

本脚本只做**只读评估**，不删表、不改表。它回答一个问题：
「这张表从代码里还能不能被访问到？」——能，就必须先改代码；不能，才谈下线。

判定口径
--------
- **强证据（runtime）**：表名出现在真正的 SQL 上下文里 —— `FROM x` / `JOIN x` /
  `INTO x` / `UPDATE x` / `TABLE x`，或 `__tablename__ = "x"`，或 Alembic 的
  `op.xxx("x"` / `has_table("x")` 调用。这等价于「真的会被执行」。
- **迁移证据（migration）**：命中位置在 `alembic/versions/` 下。它不是运行时引用，
  但意味着**在新环境跑全量迁移时该表会被重建**，所以删表必须连同迁移脚本一起处理。
- **弱证据**：表名作为裸词出现（注释、日志文案、字典键、动作类型字符串）。
  `"notification"` 这种动作类型字符串极易误报，仅作人工复核线索，**不作为禁用依据**。

判定规则：
- 有 runtime 强证据 → 禁止下线（删了就是 500）
- 只有 migration 证据或仍有行数 → 需先备份
- 零证据且零行数 → 可下线

用法
----
    python scripts/db_legacy_audit.py                 # 打印报告
    python scripts/db_legacy_audit.py --write         # 同时写入 docs/遗留表下线评估.md
    python scripts/db_legacy_audit.py --include-docs  # 文档目录也纳入强证据扫描

注意：默认**不把 docs/ 与 *.md 计入强证据**——规范文档里天然会提到旧表名（本脚本
自己就会），把那算作「在引用」会让所有表都判成「不可下线」。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import pymysql  # noqa: E402

from app.core.config import settings  # noqa: E402

MODELS_DIR = BACKEND_DIR / "app" / "models"

# 扫描范围：只看"会被执行"的代码，加上迁移脚本（迁移里的 drop_table 是重要证据）
SCAN_ROOTS = [
    BACKEND_DIR / "app",
    BACKEND_DIR / "scripts",
    BACKEND_DIR / "alembic" / "versions",
    BACKEND_DIR / "tests",
]
OPTIONAL_DOC_ROOTS = [BACKEND_DIR / "docs", PROJECT_DIR / "docs", PROJECT_DIR / "frontend" / "src"]

SKIP_DIR_NAMES = {
    "node_modules", "__pycache__", "vendor_packages", ".venv", "venv",
    "dist", "build", "backup", ".git", ".mypy_cache", ".pytest_cache",
}

CODE_SUFFIXES = {".py", ".sql", ".ts", ".tsx", ".js", ".jsx", ".vue"}


def _connect():
    parsed = urlparse(settings.DATABASE_URL)
    if parsed.scheme.startswith("sqlite"):
        raise SystemExit("当前 DATABASE_URL 是 SQLite，本脚本只评估 MySQL。")
    return pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=parsed.path.lstrip("/") or None,
        charset="utf8mb4",
    )


def load_model_tables() -> set[str]:
    """从 app/models 里提取 __tablename__，得到「代码承认的表」白名单。"""
    names: set[str] = set()
    pattern = re.compile(r"__tablename__\s*=\s*[\"']([^\"']+)[\"']")
    for path in MODELS_DIR.glob("*.py"):
        names.update(pattern.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return names


def load_db_tables(conn) -> dict[str, dict]:
    """库里的基表 + 行数 + 体积。"""
    sql = """
        SELECT t.table_name,
               IFNULL(t.table_rows, 0),
               ROUND((IFNULL(t.data_length,0)+IFNULL(t.index_length,0))/1024, 1)
        FROM information_schema.tables t
        WHERE t.table_schema = DATABASE() AND t.table_type = 'BASE TABLE'
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return {
            row[0]: {"rows": int(row[1]), "kb": float(row[2])}
            for row in cur.fetchall()
        }


def load_fk(conn) -> dict[str, dict]:
    """表的外键关系：作为子表引用谁、作为父表被谁引用。下线前必须看清。"""
    sql = """
        SELECT k.table_name, k.constraint_name, k.column_name,
               k.referenced_table_name, k.referenced_column_name
        FROM information_schema.key_column_usage k
        WHERE k.table_schema = DATABASE() AND k.referenced_table_name IS NOT NULL
    """
    rel: dict[str, dict] = {}
    with conn.cursor() as cur:
        cur.execute(sql)
        for table, cname, col, ref_table, ref_col in cur.fetchall():
            rel.setdefault(table, {"out": [], "in": []})["out"].append(
                f"{col} -> {ref_table}.{ref_col}（{cname}）"
            )
            rel.setdefault(ref_table, {"out": [], "in": []})["in"].append(
                f"{table}.{col}"
            )
    return rel


def _iter_files(roots: list[Path]):
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() in CODE_SUFFIXES:
                    yield p


def scan_references(tables: list[str], include_docs: bool) -> dict[str, dict]:
    """在代码里搜索每个表名，区分「真 SQL 引用」和「顺口提到」。"""
    roots = list(SCAN_ROOTS) + (OPTIONAL_DOC_ROOTS if include_docs else [])
    files = list(_iter_files(roots))

    result: dict[str, dict] = {
        t: {"runtime": [], "migration": [], "recreate": False, "weak": []}
        for t in tables
    }

    # 强证据必须是 SQL 语义上下文，而不是「随便一个同名字符串」。
    # 踩过的坑：`"notification"` 在本项目里是主动触达的 action_type / 字典键，
    # 用字符串字面量做判据会把 notification 表误判成「仍在使用」。
    strong_pat = {
        t: re.compile(
            r"\b(?:from|join|into|update|table)\s+[`\"']?%s[`\"']?(?![a-z0-9_])"
            r"|__tablename__\s*=\s*[\"']%s[\"']"
            r"|\bop\.\w+\(\s*[\"']%s[\"']"
            r"|\bhas_table\(\s*[\"']%s[\"']"
            % (t, t, t, t),
            re.IGNORECASE,
        )
        for t in tables
    }
    recreate_pat = {
        t: re.compile(r"\bop\.create_table\(\s*[\"']%s[\"']" % t, re.IGNORECASE)
        for t in tables
    }
    weak_pat = {t: re.compile(r"\b%s\b" % re.escape(t), re.IGNORECASE) for t in tables}

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(PROJECT_DIR).as_posix()
        is_migration = "alembic/versions" in rel
        for t in tables:
            entry = result[t]
            if recreate_pat[t].search(text):
                entry["recreate"] = True
            hit = strong_pat[t].search(text)
            if hit:
                line = text[: hit.start()].count("\n") + 1
                bucket = "migration" if is_migration else "runtime"
                entry[bucket].append(f"{rel}:{line}")
            elif weak_pat[t].search(text):
                entry["weak"].append(rel)
    return result


def classify(rows: int, entry: dict) -> tuple[str, str]:
    """给出处置建议。宁可保守：能删的条件只有「运行时零引用且无数据」。"""
    if entry["runtime"]:
        return "禁止下线", "运行时代码里仍有 SQL 级引用，删表会直接 500，必须先改代码"
    if entry["recreate"]:
        return "需先备份", "迁移链会重建该表，删表前必须同时移除对应迁移分支"
    if entry["migration"]:
        return "需先备份", "仅迁移脚本引用（历史存在性检查），删表前确认迁移链不受影响"
    if rows > 0:
        return "需先备份", "代码已无引用，但表内仍有历史数据；备份并确认业务不需要后再下线"
    return "可下线", "代码零引用且无数据，可安全删除（建议先改名观察一个发布周期）"


def build_report(db: dict, models: set[str], fk: dict, refs: dict) -> tuple[str, list[dict]]:
    legacy = sorted(set(db) - models - {"alembic_version"})
    total_rows = sum(db[t]["rows"] for t in legacy)

    lines = [
        "# 遗留表下线评估",
        "",
        f"> 由 `backend/scripts/db_legacy_audit.py` 于 {datetime.now():%Y-%m-%d %H:%M:%S} 生成，请勿手工编辑。",
        "> 生成方式：库表清单 − 模型 `__tablename__` − `alembic_version`，再对每张表做代码引用扫描。",
        "",
        "## 结论摘要",
        "",
        f"- 库中基表 **{len(db)}** 张，模型承认 **{len(models)}** 张，遗留表 **{len(legacy)}** 张。",
        f"- 遗留表内数据合计约 **{total_rows}** 行。",
        "- 「运行时引用」= 表名出现在 SQL 上下文（FROM/JOIN/INTO/UPDATE/TABLE）、"
        "`__tablename__` 或 Alembic `op.xxx(\"表名\")` 调用里，等于真的会被执行。",
        "- 「迁移引用」= 只出现在 `alembic/versions/`。不是运行时依赖，但说明"
        "**新环境跑全量迁移时该表会被重建**，删表必须连迁移脚本一起处理。",
        "- 「弱证据」= 裸词出现（注释/文案/字典键/动作类型字符串），仅作复核线索，"
        "不作为禁用依据——本项目 `\"notification\"` 是主动触达的动作类型，极易误判。",
        "",
        "| 处置 | 含义 |",
        "|---|---|",
        "| 禁止下线 | 运行时代码仍引用，删表即故障 |",
        "| 需先备份 | 迁移链会重建，或表内仍有历史数据 |",
        "| 可下线 | 零引用且无数据 |",
        "",
        "## 逐表明细",
        "",
        "| 表名 | 行数 | 体积(KB) | 运行时 | 迁移 | 迁移重建 | 弱证据 | 处置 |",
        "|---|---:|---:|---:|---:|:--:|---:|---|",
    ]
    detail = []
    for t in legacy:
        info = db[t]
        entry = refs[t]
        verdict, reason = classify(info["rows"], entry)
        lines.append(
            f"| `{t}` | {info['rows']} | {info['kb']} | {len(entry['runtime'])} "
            f"| {len(entry['migration'])} | {'是' if entry['recreate'] else ''} "
            f"| {len(entry['weak'])} | {verdict} |"
        )
        detail.append({"table": t, **info, **entry, "verdict": verdict, "reason": reason})

    # 分组明细：只展开「禁止下线」和「需先备份」，可下线的无需再解释
    for group in ("禁止下线", "需先备份"):
        items = [d for d in detail if d["verdict"] == group]
        if not items:
            continue
        lines += ["", f"## {group}（{len(items)} 张）", ""]
        for d in items:
            lines.append(f"### `{d['table']}` — {d['reason']}")
            lines.append("")
            if d["runtime"]:
                lines.append("运行时引用位置（删表会 500）：")
                lines += [f"- `{loc}`" for loc in d["runtime"][:12]]
                if len(d["runtime"]) > 12:
                    lines.append(f"- …另有 {len(d['runtime']) - 12} 处")
                lines.append("")
            if d["migration"]:
                lines.append("迁移脚本引用位置：")
                lines += [f"- `{loc}`" for loc in d["migration"][:12]]
                if len(d["migration"]) > 12:
                    lines.append(f"- …另有 {len(d['migration']) - 12} 处")
                lines.append("")
            if d["weak"]:
                preview = ", ".join(f"`{p}`" for p in d["weak"][:6])
                more = f" 等 {len(d['weak'])} 个文件" if len(d["weak"]) > 6 else ""
                lines.append(f"弱引用（需人工确认是否为文案巧合）：{preview}{more}")
                lines.append("")
            rel = fk.get(d["table"])
            if rel and rel["out"]:
                lines.append("外键指向：" + "；".join(rel["out"]))
                lines.append("")
            if rel and rel["in"]:
                lines.append("被其他表引用：" + "；".join(rel["in"]))
                lines.append("")

    clean = [d for d in detail if d["verdict"] == "可下线"]
    if clean:
        lines += ["", f"## 可下线（{len(clean)} 张）", ""]
        lines += [f"- `{d['table']}`（0 行，代码零引用）" for d in clean]

    lines += [
        "",
        "## 下线流程（任一表都适用）",
        "",
        "1. **全量备份**：`mysqldump ... --databases smart_campus > backup/before_drop.sql`，校验 `Dump completed`。",
        "2. **先改名不删**：`RENAME TABLE old TO legacy_old;` 观察一个完整发布周期（覆盖所有定时任务与低频接口）。",
        "3. **确认无 500 后再删**：`DROP TABLE legacy_old;`，并把该表从本文档的遗留清单中移除。",
        f"4. **不要用 autogenerate 生成 DROP**：它会把本文档里的 {len(legacy)} 张表全部识别成"
        "「该删」，并顺带生成 `community_posts.favorite_count` 的 DROP COLUMN，见规范 §9.2.1。",
        "5. **迁移脚本要一起清理**：标了「迁移重建=是」的表，在新环境全量迁移时会被重新创建，"
        "只删表不改迁移等于没删。",
        "",
        "> 规范 §9 允许的下线顺序是「备份 → 改名 → 观察 → 删除」，任何跳步都会失去回滚能力。",
        "",
    ]
    return "\n".join(lines), detail


def main() -> int:
    ap = argparse.ArgumentParser(description="评估遗留表是否可下线")
    ap.add_argument("--write", action="store_true", help="写入 docs/遗留表下线评估.md")
    ap.add_argument("--include-docs", action="store_true",
                    help="把文档与前端源码也计入强证据（默认排除，避免规范文档自我命中）")
    args = ap.parse_args()

    conn = _connect()
    try:
        db = load_db_tables(conn)
        fk = load_fk(conn)
    finally:
        conn.close()

    models = load_model_tables()
    legacy = sorted(set(db) - models - {"alembic_version"})
    if not legacy:
        print("没有遗留表，无需评估。")
        return 0

    refs = scan_references(legacy, args.include_docs)
    report, detail = build_report(db, models, fk, refs)

    by_verdict: dict[str, int] = {}
    for d in detail:
        by_verdict[d["verdict"]] = by_verdict.get(d["verdict"], 0) + 1
    print(f"库表 {len(db)} / 模型 {len(models)} / 遗留 {len(legacy)}")
    for k in ("禁止下线", "需先备份", "可下线"):
        print(f"  {k}: {by_verdict.get(k, 0)}")

    if args.write:
        out = PROJECT_DIR / "docs" / "遗留表下线评估.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"已写入 {out}")
    else:
        print("\n" + report[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
