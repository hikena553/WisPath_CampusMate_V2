# syntax=docker/dockerfile:1
# 后端镜像：python:3.11-slim + 非 root 用户 + 健康检查
# 启动流程：docker-entrypoint.sh 内先 `alembic upgrade head` 再启动 uvicorn
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libmagic1：python-magic（文件类型识别）运行时依赖的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 非 root 运行；uploads 目录（持久卷挂载点）预创建并授权
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 健康检查：/api/health（slim 镜像无 curl，用标准库 urllib）
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]