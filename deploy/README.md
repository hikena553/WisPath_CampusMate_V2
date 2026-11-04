# Smart Campus 部署手册（Docker Compose）

> **马上要上线？直接看 [上线检查清单.md](./上线检查清单.md)** —— 按阶段可勾选的执行清单，
> 含上线后必做的安全项（改初始密码、配备份）与验证动作。
>
> 首次把服务搬到云服务器、并需要把本地 SQLite 数据一起迁过去时，
> 请先看 **[上云部署与数据迁移.md](./上云部署与数据迁移.md)**（含服务器初始化、
> 生产 `.env` 配置、`scripts/db_migrate.py` 数据搬运与核对流程）。
> 本文档聚焦 compose 本身的启动、持久化与升级。

## 1. 前置要求

- Docker Engine 20.10+ / Docker Desktop
- Docker Compose v2（`docker compose` 子命令）
- 建议 >= 4GB 内存的服务器（MySQL + 后端 + 前端）

## 2. 快速开始

```bash
# 1) 准备环境变量（模板不入库，真实 .env 已被 .gitignore 排除）
cp .env.example .env
# 编辑 .env：务必修改 MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD / SECRET_KEY

# 2) 构建并启动（首次构建前端约需 3-5 分钟）
docker compose up -d --build

# 3) 查看启动状态
docker compose ps

# 4) 访问
#    http://<服务器IP>/    （nginx 对外端口由 .env 的 NGINX_PORT 控制，默认 80）
```

## 3. 启动流程（自动完成，无需手工步骤）

`docker compose up` 后各容器的启动顺序与自动化动作：

| 服务 | 启动动作 |
|---|---|
| db | MySQL 8 初始化（utf8mb4），健康检查通过后 backend 才会启动 |
| backend | 入口脚本先执行 `alembic upgrade head`（建表/迁移，幂等），再启动 uvicorn；应用 lifespan 内部也会再跑一次 `run_migrations()` 双保险；随后自动执行幂等种子数据初始化 |
| frontend | nginx 托管构建产物，反向代理 `/api`、`/uploads`、`/ws` |

首次启动后自动生成初始账号（**首次登录会提醒修改初始密码，不阻断使用**，见《开发规范.md》）：

| 账号 | 初始密码 | 角色 |
|---|---|---|
| admin | admin123 | 系统管理员 |
| t1001 ~ t1007 | 123456 | 教师 |
| 2024001 等学号 | 123456 | 学生 |

> 上线后请立即登录并修改初始密码；管理员账号建议在后台重新创建专用账号并停用默认 admin。

## 4. 环境变量清单（.env）

| 变量 | 必填 | 说明 |
|---|---|---|
| MYSQL_ROOT_PASSWORD | 是 | MySQL root 密码 |
| MYSQL_DATABASE | 否 | 库名，默认 `smart_campus` |
| MYSQL_USER / MYSQL_PASSWORD | 是 | 应用专用账号（勿用 root 直连） |
| SECRET_KEY | 是 | JWT 签名密钥，≥32 位随机串；生成：`python -c "import secrets; print(secrets.token_hex(32))"` |
| TZ | 否 | 默认 `Asia/Shanghai`，三服务与 MySQL 统一注入；不设会让课表/日程差 8 小时 |
| LLM_API_KEY / DASHSCOPE_API_KEY | 否 | LLM 密钥；不配置则 AI 对话/分析类功能不可用，平台其余功能正常 |
| LLM_BASE_URL / LLM_MODEL / LLM_AGENT_MODEL / LLM_VISION_MODEL | 否 | 模型端点与型号。**默认值须与 `backend/app/core/config.py` 保持一致**，漏写即静默换模型 |
| GITHUB_TOKEN / GITEE_TOKEN | 否 | 外部资讯抓取令牌（可选） |
| NGINX_PORT | 否 | 对外端口，默认 80 |
| UVICORN_WORKERS | 否 | 默认 **1**，勿随意调大：周期任务由应用进程内调度，多 worker 会重复执行 |
| AUTO_MIGRATE | 否 | 默认 `true`（容器启动时自动迁移）；多副本部署须改 `false` |
| LOG_LEVEL / SENTRY_DSN | 否 | 日志级别与可观测性（可选） |

## 5. 数据持久化与备份

两个命名卷：

- `db_data`：MySQL 数据（`/var/lib/mysql`）
- `uploads_data`：上传文件（`/app/uploads`，头像/公告图/文档/品牌图等）

```bash
# 备份
docker run --rm -v smart-campus_db_data:/data -v "$PWD":/backup alpine tar czf /backup/db_$(date +%F).tar.gz -C /data .
docker run --rm -v smart-campus_uploads_data:/data -v "$PWD":/backup alpine tar czf /backup/uploads_$(date +%F).tar.gz -C /data .
```

## 6. 升级与常见操作

```bash
# 升级（拉新代码 → 重建 → 迁移自动执行）
git pull
docker compose up -d --build

# 查看日志
docker compose logs -f backend

# 停止 / 完全清理（保留数据卷）
docker compose down
docker compose down -v   # 危险：连同数据卷一起删除
```

## 7. HTTPS 建议

nginx 仅监听 80。生产环境推荐二选一：

1. 前置一层负载均衡/网关（如云厂商 LB、Caddy、宝塔）终结 TLS，转发到本机 nginx 80 端口；
2. 自行扩展 `deploy/nginx.conf` 增加 443 server 块，并用 docker compose 挂载证书：
   ```yaml
   frontend:
     volumes:
       - ./deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro
       - ./deploy/certs:/etc/nginx/certs:ro   # 证书挂载点（已预留）
   ```
   证书续期建议使用 certbot/caddy 自动续期，或云厂商托管证书。

## 8. 注意事项

- **数据库密码含特殊字符**：`DATABASE_URL` 由 compose 拼装，`@ : / ?` 等字符需 URL 编码（如 `p%40ss`），否则连接失败；建议直接用纯字母数字密码；
- **迁移失败排查**：backend 启动即退出时先 `docker compose logs backend`，确认 `alembic upgrade head` 报错信息（连接串、权限、字符集）；chmod 无碍：入口脚本以 `sh` 显式执行，不依赖可执行位；
- **时区**：compose 已为三服务注入 `TZ=Asia/Shanghai`，MySQL 侧为 `--default-time-zone=+08:00`，开箱即为国内时区；
- **客户端真实 IP**：入口脚本已带 `--proxy-headers --forwarded-allow-ips "*"`，后端能拿到 nginx 透传的真实 IP。若登录防爆破计数出现「一个人输错、全校被锁」，说明该参数丢失；
- **构建上下文**：`backend/.dockerignore` 排除 `.venv`、`frontend/.dockerignore` 排除 `node_modules`。删掉会导致镜像把本机 Windows 依赖带进 Linux 容器，构建失败；
- **换行符**：`.gitattributes` 已对 `.sh`/`.dockerignore`/`Dockerfile`/`*.conf` 锁定 LF。缺了它，Windows 上 `core.autocrlf=true` 会让入口脚本变 CRLF，容器内 `sh` 报 `: not found`；
- **后端直连调试**：`docker compose exec backend sh` 进入容器。