#!/bin/sh
# 后端容器启动入口：
# 1. 执行数据库迁移（alembic upgrade head，幂等）；
# 2. 启动 uvicorn。
# 应用 lifespan 内部同样会执行 run_migrations()，双保险且幂等。
set -e

# AUTO_MIGRATE=false 时跳过入口迁移：多副本/流水线部署下，迁移应由发布步骤
# 用 DDL 账号单独跑一次，否则 N 个副本并发 upgrade 会抢 DDL 锁。
if [ "${AUTO_MIGRATE:-true}" = "false" ]; then
    echo "[entrypoint] AUTO_MIGRATE=false，跳过 alembic upgrade head"
else
    echo "[entrypoint] running alembic upgrade head ..."
    alembic upgrade head
fi

# --proxy-headers + --forwarded-allow-ips：容器跑在 nginx 之后，客户端真实 IP
# 由 nginx 通过 X-Forwarded-For 传入。不加这两个参数时 request.client.host
# 恒为 nginx 容器的内网 IP（限流、审计日志、封禁会因此把所有人当成同一个来源）。
echo "[entrypoint] starting uvicorn ..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-1}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
