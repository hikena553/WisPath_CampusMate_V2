"""按最小权限创建数据库多角色账号（幂等，可反复执行）。

对齐 docs/数据库规范.md 第 5 章「账号与权限」：

    campus_ro      只读      报表 / 排查 / BI 连接，物理上不可能改数据
    campus_rw      读写      应用运行时账号，不能改表结构
    campus_ddl     结构变更  仅 Alembic 迁移使用，能 DDL 但不碰备份
    campus_backup  备份      mysqldump 专用，能锁表但只能读

为什么要拆：应用账号一旦同时拥有 DDL 权限，任何一次 SQL 注入或误操作都能
DROP TABLE；而迁移账号不该出现在应用进程的配置里。拆开之后，出事时能靠
「是谁的账号」直接定位责任边界。

用法：
    # 预览将执行的 SQL，不落库
    python scripts/db_accounts.py --dry-run

    # 真正创建（用 .env 里的 DATABASE_URL 拿管理员连接，即当前 root 账号）
    python scripts/db_accounts.py

    # 额外把账号密码追加进 backend/.env（该文件已被 .gitignore 排除）
    python scripts/db_accounts.py --write-env

    # 指定密码（不给则生成 32 位随机串）；多个 host 用逗号分隔
    python scripts/db_accounts.py --password campus_rw=xxxx --hosts 127.0.0.1,localhost

注意：密码只在本次输出中出现一次，脚本不保存。丢了就重跑本脚本轮换。
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pymysql  # noqa: E402

from app.core.config import settings  # noqa: E402

# 账号名 -> (说明, 权限列表)
ROLES: dict[str, tuple[str, list[str]]] = {
    "campus_ro": ("只读：报表/排查", ["SELECT", "SHOW VIEW"]),
    "campus_rw": ("应用运行时读写", ["SELECT", "INSERT", "UPDATE", "DELETE", "EXECUTE"]),
    "campus_ddl": (
        "结构变更：仅 Alembic 迁移使用",
        [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "ALTER", "CREATE", "DROP", "INDEX", "REFERENCES",
            "CREATE TEMPORARY TABLES", "LOCK TABLES",
        ],
    ),
    "campus_backup": (
        "备份：mysqldump 专用",
        # 只授「库级」权限。PROCESS / RELOAD 是全局权限，一旦 GRANT ... ON `db`.*
        # 会直接报 1221 Incorrect usage of DB GRANT and GLOBAL PRIVILEGES；
        # 且 --single-transaction 备份并不需要它们，最小权限优先。
        ["SELECT", "SHOW VIEW", "LOCK TABLES", "TRIGGER", "EVENT"],
    ),
}


def _admin_conn():
    """用当前 DATABASE_URL 里的账号连库（要求有 CREATE USER / GRANT 权限）。"""
    parsed = urlparse(settings.DATABASE_URL)
    if parsed.scheme.startswith("sqlite"):
        raise SystemExit("当前 DATABASE_URL 是 SQLite，本脚本只处理 MySQL 多角色账号。")
    return pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=parsed.path.lstrip("/") or None,
        charset="utf8mb4",
        autocommit=True,
    )


def build_statements(db_name: str, hosts: list[str], passwords: dict[str, str]) -> list[str]:
    stmts: list[str] = []
    for role, (_desc, privs) in ROLES.items():
        for host in hosts:
            stmts.append(f"CREATE USER IF NOT EXISTS '{role}'@'{host}' IDENTIFIED BY {_q(passwords[role])}")
            # 已存在时也要把密码轮换到本次生成值，保证脚本输出即事实
            stmts.append(f"ALTER USER '{role}'@'{host}' IDENTIFIED BY {_q(passwords[role])}")
            stmts.append(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{role}'@'{host}'")
            grant = ", ".join(privs)
            stmts.append(f"GRANT {grant} ON `{db_name}`.* TO '{role}'@'{host}'")
    stmts.append("FLUSH PRIVILEGES")
    return stmts


def _q(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser(description="创建最小权限的数据库多角色账号")
    ap.add_argument("--dry-run", action="store_true", help="只打印 SQL，不执行")
    ap.add_argument("--hosts", default="127.0.0.1,localhost", help="账号 host，逗号分隔")
    ap.add_argument("--password", action="append", default=[], metavar="ROLE=PWD",
                    help="指定某角色密码，可重复；未指定的自动生成")
    ap.add_argument("--write-env", action="store_true", help="把账号密码追加到 backend/.env")
    args = ap.parse_args()

    parsed = urlparse(settings.DATABASE_URL)
    db_name = parsed.path.lstrip("/")
    hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]

    given: dict[str, str] = {}
    for item in args.password:
        role, _, pwd = item.partition("=")
        if role not in ROLES:
            raise SystemExit(f"未知角色 {role}，可选：{', '.join(ROLES)}")
        given[role] = pwd

    passwords = {role: given.get(role) or secrets.token_urlsafe(24) for role in ROLES}

    stmts = build_statements(db_name, hosts, passwords)

    if args.dry_run:
        print("\n".join(s + ";" for s in stmts))
        return 0

    conn = _admin_conn()
    try:
        with conn.cursor() as cur:
            for stmt in stmts:
                cur.execute(stmt)
    finally:
        conn.close()

    print("=" * 62)
    print(f"  已创建/轮换 {len(ROLES)} 个账号，授权库：{db_name}，host：{', '.join(hosts)}")
    print("=" * 62)
    for role, (desc, privs) in ROLES.items():
        print(f"  {role:<14} {desc}")
        print(f"  {'':<14} 密码 {passwords[role]}")
        print(f"  {'':<14} 权限 {', '.join(privs)}")
    print("=" * 62)
    print("  应用运行时建议连接串（替换 PWD 后写入 backend/.env）：")
    print(f"  mysql+pymysql://campus_rw:PWD@{parsed.hostname or '127.0.0.1'}:{parsed.port or 3306}/{db_name}?charset=utf8mb4")
    print("  注意：campus_rw 无 DDL 权限，启动时的 alembic upgrade 会失败。")
    print("        生产请把迁移拆成独立步骤，用 campus_ddl 执行（见规范第 7 章）。")

    if args.write_env:
        env_path = BACKEND_DIR / ".env"
        lines = [
            "",
            "# ===== 多角色数据库账号（由 scripts/db_accounts.py 生成，勿提交）=====",
            f"# 生成时间：{__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}",
        ]
        for role in ROLES:
            lines.append(f"DB_{role.upper()}_PASSWORD={passwords[role]}")
        lines.append(
            "# 切换到应用读写账号（取消下行注释即可；切换前务必改掉 root/123456）："
        )
        lines.append(
            f"# DATABASE_URL=mysql+pymysql://campus_rw:<上面的密码>@{parsed.hostname or '127.0.0.1'}:{parsed.port or 3306}/{db_name}?charset=utf8mb4"
        )
        with env_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  已追加凭据到 {env_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
