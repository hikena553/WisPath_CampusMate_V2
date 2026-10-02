#!/bin/sh
# 后端容器启动入口：
# 1. 执行数据库迁移（alembic upgrade head，幂等）；
# 2. 启动 uvicorn。
# 应用 lifespan 内部同样会执行 run_migrations()，双保险且幂等。
set -e

echo "[entrypoint] running alembic upgrade head ..."
alembic upgrade head

echo "[entrypoint] starting uvicorn ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"