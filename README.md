# 智慧校园 AI 服务平台 · WisPath CampusMate

> 绵阳城市学院智慧校园 AI 服务平台 —— 以「绵小城」AI 助手为核心，串联学生成长、学业规划、校园生活、心理关怀与教师协同的全栈应用。

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Frontend-Vue%203-42b883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Build-Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![MySQL](https://img.shields.io/badge/Database-MySQL%208-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Docker](https://img.shields.io/badge/Deploy-Docker%20Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#开源协议)

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
  - [环境要求](#环境要求)
  - [一键启动（推荐）](#一键启动推荐)
  - [Docker Compose 部署](#docker-compose-部署)
  - [手动启动](#手动启动)
  - [数据库迁移与自检](#数据库迁移与自检)
- [项目结构](#项目结构)
- [默认测试账号](#默认测试账号)
- [功能模块](#功能模块)
- [API 概览](#api-概览)
- [开发约定](#开发约定)
- [贡献指南](#贡献指南)
- [开源协议](#开源协议)
- [致谢](#致谢)

---

## 项目简介

**智慧校园 AI 服务平台** 面向高校师生与管理者，提供"查、问、记、管、预警"一体化服务：

- **学生端**：AI 对话助手、成长档案与作品集、学习计划与自习室、课表 / 成绩 / GPA、办事服务与请假、交流社区与校园资讯、失物招领、心理关怀、勋章主页、消息中心；
- **教师端**：班级首页工作台、学生画像与 AI 洞察、请假与统一审批、危机工作台、关怀中心与家访记录、家长共享、同伴互评、教师任务、师生消息与语音通话；
- **管理端**：知识库、外部资讯源、教师 / 学生 / 院系班级、课程表、危机监控、意见反馈、系统监控与设置、品牌设计、微信小程序配置、开源参考库；
- **通用能力**：SSE 流式 AI 对话与工具调用、校园知识库问答、官网通知聚合、基于对话语义的心理危机分级预警、全局审批流程引擎。

后端基于 FastAPI + SQLAlchemy 2.x，前端基于 Vue 3 + TypeScript + Vite + Element Plus；当前仓库包含 **52 个 API 路由模块**（统一登记于 `backend/app/api/registry.py`）与 **81 张数据表**（结构见 `docs/数据库数据字典.md`）。

---

## 功能特性

- **AI 助手（绵小城）**：SSE 流式对话、深度思考模式、函数调用工具集（请假 / 成绩 / 课表 / 成长档案等）、语音输入、文件与图片多模态理解、项目式多轮对话与记忆摘要；
- **成长档案与作品集**：荣誉 / 竞赛 / 实践 / 论文 / 成果记录、技能兴趣标签自动提取、项目展示、综合评分五维雷达图、简历向导与导出（DOCX / PDF）；
- **学习规划**：阶段化学习计划、任务看板、每日打卡与连击、自习室番茄钟、学习行为事件流；
- **学业管理**：课表、成绩与 GPA、成绩分析、成绩批量导入；
- **校园生活**：校园资讯聚合与互动（点赞 / 收藏 / 评论 / 转发）、交流社区、资源中心、失物招领、办事服务、请假与统一审批；
- **心理关怀闭环**：对话危机关键词 + LLM 语义分级（severe / moderate / mild）、教师危机工作台、关怀中心、家访与谈心记录、家长共享链接（二维码 / 免登录页面）、同伴互评问卷；
- **实时通信**：基于 WebSocket 的师生消息、语音通话房、通讯录与关注关系、群组、系统通知、置顶会话与「小绵管家」资讯简报 / 会话摘要；
- **成长激励**：勋章体系、个人主页、学习连击与周报；
- **认证授权**：JWT 登录注册（含找回密码、强制改密）、学生 / 教师 / 管理员三角色路由隔离、按钮级权限指令、令牌吊销。

---

## 技术栈

| 分层 | 技术 |
|------|------|
| 前端框架 | Vue 3（Composition API）+ TypeScript |
| 前端构建 | Vite 5 |
| UI 组件库 | Element Plus 2.x + Lucide Icons |
| 状态管理 | Pinia |
| 图表与可视化 | ECharts 6 + vue-echarts、d3-cloud（词云） |
| 3D / 动效 | Three.js、OGL |
| 端侧 AI | face-api.js + onnxruntime-web（表情 / 情绪识别） |
| 其他前端能力 | Axios、cropperjs（图片裁剪）、qrcode（家长共享码） |
| 后端框架 | Python 3.11+ / FastAPI |
| ORM / 校验 | SQLAlchemy 2.x + Pydantic v2 |
| 数据库 | MySQL 8.0（`mysql+pymysql`，utf8mb4） |
| AI 能力 | OpenAI 兼容协议（默认通义千问 DashScope 代理，`.env` 可切 DeepSeek 等），支持多模态与视觉模型 |
| 文档解析 / 导出 | pdfplumber、PyPDF2、python-docx、openpyxl、jieba |
| 认证 | JWT（`python-jose` + `passlib[bcrypt]`） |
| 数据库迁移 | Alembic（双账号：运行时 `campus_rw` / 迁移 `campus_ddl`） |
| 实时通信 | WebSocket（消息、语音房） |
| 部署 | Docker Compose（MySQL + 后端 + Nginx 前端） |

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│  前端 Vue 3 SPA（学生端 / 教师端 / 管理端，角色路由隔离）      │
│  SSE 流式对话 · WebSocket 消息 · ECharts 看板 · 响应式三端    │
└───────────────┬──────────────────────────┬───────────────────┘
                │ /api/*（Vite 代理 / Nginx）│ WS：/api/messages/ws、/api/voice/ws
┌───────────────▼──────────────────────────▼───────────────────┐
│  FastAPI 应用（单进程，UVICORN_WORKERS=1，进程内周期任务调度）  │
│  api/（薄路由，52 模块）→ services/（业务）→ models/（ORM）    │
│  agent_service · llm_service · tool_registry · crisis_service │
└───────────────┬──────────────────────────┬───────────────────┘
                │ SQLAlchemy               │ OpenAI 兼容 API
┌───────────────▼──────────────┐  ┌────────▼──────────────────┐
│  MySQL 8（81 张表，Alembic）  │  │  LLM（DashScope / 其他）   │
└──────────────────────────────┘  └───────────────────────────┘
```

> 周期任务（学习预警、资讯抓取、Agent 定时任务等）在应用进程内调度，因此**必须单 worker**；水平扩容时需把周期任务拆成独立进程。

---

## 快速开始

### 环境要求

- Python >= 3.11（推荐 conda 环境 `ai`）
- Node.js >= 18
- MySQL 8.0+
- 可选：Docker + Docker Compose（一键容器化部署）

### 一键启动（推荐）

项目根目录的 `main.py` 会依次拉起后端（FastAPI，:8000）与前端（Vite，:5173），并在退出时清理全部子进程：

```bash
conda activate ai
python main.py
```

启动器的稳定性约定：

- 启动前预检 8000 / 5173 端口，被占用时报出 PID 与 `taskkill` 处置命令；
- 等后端 `/api/health` 通过后再启动前端；
- 子进程输出双写 `backend/logs/backend.out.log` / `frontend.out.log`，应用日志落 `backend/logs/app.log`（JSON，10MB × 5 轮转），原生崩溃栈落 `crash.log`；
- 后端异常退出按指数退避自动重启（默认上限 5 次）；
- Windows 下用 Job Object 兜底，关闭窗口不会留下占端口的孤儿进程。

可选环境变量：

```bash
RELOAD=1 python main.py        # 后端热重载（仅监控 app/ 目录，默认关闭）
MAX_RESTARTS=0 python main.py  # 崩溃不自动重启，便于查看首次错误现场
```

### Docker Compose 部署

```bash
cp .env.example .env           # 填写 MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD / SECRET_KEY / LLM_API_KEY
docker compose up -d --build
# 前端 http://localhost（NGINX_PORT 可改），后端容器内 :8000
```

- `db`：MySQL 8.0，`utf8mb4_0900_ai_ci`，首次启动自动建库；
- `backend`：启动时执行 `alembic upgrade head`（`AUTO_MIGRATE=true`；多副本时必须改为 `false` 并把迁移放到发布流水线）；
- `frontend`：多阶段构建 + Nginx，反代 `/api` 并托管 SPA 静态资源（配置见 `deploy/nginx.conf`）。

上云与数据迁移细节见 [`deploy/上云部署与数据迁移.md`](deploy/上云部署与数据迁移.md)。

### 手动启动

#### 后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量：编辑 backend/.env（模板见 backend/.env.example）
# DATABASE_URL=mysql+pymysql://campus_rw:password@localhost:3306/smart_campus?charset=utf8mb4
# MIGRATION_DATABASE_URL=mysql+pymysql://campus_ddl:password@localhost:3306/smart_campus?charset=utf8mb4
# AUTO_MIGRATE=true
# SECRET_KEY=至少32位随机串
# LLM_API_KEY=sk-xxx

# 首次接入：建库 + 迁移到 head（--accounts 顺带创建最小权限账号）
python scripts/db_bootstrap.py --init

# 每次拉完代码后自检：库结构与仓库迁移是否一致，不一致返回 1 并列出缺失项
python scripts/db_bootstrap.py --check

# 初始化种子数据（幂等，可重复执行）
python -m app.seed

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

> 建表只走 Alembic 迁移，任何手工 DDL 都会导致他人库结构缺东西。规范见 `docs/数据库规范.md`，数据字典 `docs/数据库数据字典.md` 由脚本生成（**勿手改**）。

#### 前端

```bash
cd frontend
npm install
npm run dev        # 默认 :5173，代理 /api → :8000
npm run build      # vue-tsc 类型检查 + Vite 构建（提交前必须零报错）
npm run test       # vitest run
```

### 数据库迁移与自检

```bash
cd backend
alembic upgrade head                        # 执行迁移（使用 MIGRATION_DATABASE_URL）
alembic revision --autogenerate -m "描述"   # 生成迁移脚本（生成后需人工复核）
python scripts/db_bootstrap.py --check      # 结构对账
```

---

## 项目结构

```
WisPath_CampusMate_V2/
├── main.py                  # 一键启动器（端口预检 / 日志 / 崩溃重启）
├── docker-compose.yml       # db + backend + frontend 编排
├── 开发规范.md              # 分层、命名、Git 约定（唯一依据）
├── 提示词工程规范.md         # 修改 AI prompt 前必读
├── backend/
│   ├── app/
│   │   ├── main.py          # 应用入口，装配路由 + /api/health
│   │   ├── seed.py          # 种子数据（幂等）
│   │   ├── api/             # 路由层（52 个模块，registry.py 统一登记）
│   │   ├── core/            # 配置、数据库、依赖注入、安全、加解密、限流
│   │   ├── models/          # SQLAlchemy 模型（81 张表）
│   │   ├── schemas/         # Pydantic DTO
│   │   ├── services/        # 业务逻辑（agent / llm / tool_registry / crisis / scoring …）
│   │   ├── tasks/           # 进程内周期任务（学习预警、定时调度）
│   │   └── utils/           # 工具（枚举兼容、日期、日志等）
│   ├── alembic/             # 数据库迁移
│   ├── scripts/             # db_bootstrap、字典生成等运维脚本
│   ├── tests/               # pytest 测试
│   ├── ml/                  # 表情识别模型训练（可选，运行时惰性导入）
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/             # 请求封装（按模块拆分，组件内禁止裸 axios）
│       ├── stores/          # Pinia（auth / agent / conversation …）
│       ├── views/           # 页面：student / teacher / admin / login / share
│       ├── components/      # 通用组件与布局
│       ├── composables/     # 组合式函数
│       ├── router/          # 路由 + 角色守卫
│       ├── directives/      # v-permission / v-role
│       ├── styles/ types/ utils/
│       └── __tests__/       # vitest 测试
├── deploy/                  # nginx.conf、上云部署与数据迁移文档
├── docs/                    # 数据库规范 / 数据字典 / 遗留表评估 / 设计稿
├── prototypes/              # 交互原型（HTML）
├── campus-cockpit/          # 数据大屏设计稿
└── deck/                    # 宣传片与 PPT 生成脚本
```

---

## 默认测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 学生 | 2024001 | 123456 |
| 教师 | t1001 | 123456 |
| 管理员 | admin | admin123 |

> 种子数据中的师生账号统一初始密码为 `123456`，管理员为 `admin123`。生产环境请务必修改。

---

## 功能模块

### 学生端

| 模块 | 说明 |
|------|------|
| AI 助手 | 绵小城对话：流式输出、深度思考、工具调用、语音输入、文件与图片提问、对话项目化归档 |
| 校园资讯 | 官网 / 教务处资讯聚合、点赞收藏评论转发、社区帖子互动 |
| 学习规划 | 学习计划阶段与任务、每日打卡与连击、番茄钟自习室、学习行为记录 |
| 课表与成绩 | 学期课表、成绩与 GPA、成绩分析、考试安排 |
| 成长档案 / 作品集 | 成长记录、技能兴趣标签、项目展示、综合评分雷达图、简历向导与导出 |
| 材料档案 | 证明材料归档与分类管理 |
| 资源中心 | 学习资源检索与收藏 |
| 办事与请假 | 服务大厅在线申请、请假提交与进度跟踪、统一审批流转 |
| 关怀与情绪 | 心理关怀入口、情绪记录、危机自评与求助 |
| 失物招领 | 发布 / 检索 / 评论失物与拾物信息 |
| 社交与消息 | 好友通讯录、关注关系、群组、消息中心、语音通话、小绵管家简报 |
| 个人主页 | 勋章墙、个性签名、资料维护、意见反馈 |

### 教师端

| 模块 | 说明 |
|------|------|
| 班级工作台 | 首页 KPI、今日任务、待审批、危机摘要、桌面 / 移动双布局 |
| 学生管理 | 名下学生列表、综合评分、成长档案详情、关怀记录 |
| AI 助手 | 教师专项对话，可查询班级与学生数据 |
| 审批管理 | 请假审批 + 统一审批（流程引擎实例） |
| 危机工作台 | 三级预警处置、跟进记录、闭环状态 |
| 关怀中心 | 谈心 / 家访记录、家长共享链接与二维码、家长端免登录页面 |
| 同伴互评 | 问卷发布、学生互评结果统计 |
| 教师任务 | 任务派发、进度跟踪、自动生成待办 |
| AI 洞察 | 学生画像洞察、行为模式与风险提示、周报 |
| 教师作品集 | 教学成果与荣誉归档 |
| 通知与消息 | 班级公告、师生消息、语音通话 |

### 管理端

| 模块 | 说明 |
|------|------|
| 知识库 | 校园问答语料与文档分块管理 |
| 资讯管理 | 外部资讯源配置、抓取调度与内容审核 |
| 组织架构 | 学院 / 专业 / 班级 / 课程表维护 |
| 用户管理 | 教师、学生账号与导师绑定关系 |
| 危机监控 | 全校预警总览与分级统计 |
| 反馈管理 | 用户意见反馈处理 |
| 系统监控 | 服务健康、日志与运行指标 |
| 系统设置 | LLM 动态配置（加密存储）、品牌设计、微信小程序 AppID / 部署链路 |
| 开源参考库 | 参考项目维护与页面脚手架生成 |
| 模型训练 | 表情识别模型训练任务与产物管理（可选依赖） |

### 微信小程序

管理端「系统设置 → 微信小程序」支持配置 AppID / AppSecret 并走「读取配置 → 校验 → 生成工程 → 上传代码（miniprogram-ci）」链路，敏感值加密存储、接口脱敏返回。

---

## API 概览

所有接口统一前缀 `/api`，交互式文档：`http://localhost:8000/docs`。健康检查：`GET /api/health`。

| 前缀 | 能力 |
|------|------|
| `/api/auth` | 登录、注册、找回密码、修改密码、令牌吊销 |
| `/api/agent` | AI 对话（SSE）、对话列表 / 重命名 / 置顶 / 归档 / 软删除、共享会话 |
| `/api/cron-tasks` | Agent 定时任务（周期提醒、自动洞察） |
| `/api/campus` | 校园资讯、校园风采、文章互动（赞 / 藏 / 评 / 转） |
| `/api/community` | 交流社区帖子、评论、点赞 |
| `/api/growth` | 成长档案 CRUD、成长目标 |
| `/api/academic` | 课表、成绩、GPA、成绩分析、考试 |
| `/api/plan` | 学习计划：阶段、任务、打卡、连击 |
| `/api/study-room` | 自习室番茄钟专注记录与统计 |
| `/api/portfolio` | 学生作品集、简历导出 |
| `/api/materials` | 材料档案 |
| `/api/resources` | 资源中心与收藏 |
| `/api/lost-found` | 失物招领 |
| `/api/service` | 服务大厅办事工单 |
| `/api/leave` | 请假申请与审批 |
| `/api/approval` · `/api/workflows` | 统一审批、流程定义与实例引擎 |
| `/api/crisis` | 危机预警分级与处置 |
| `/api/care-center` · `/api/care-records` · `/api/student/care` · `/api/guardians` | 关怀中心、谈心家访记录、家长共享 |
| `/api/peer-surveys` | 同伴互评问卷与结果 |
| `/api/messages` | 消息会话、系统通知、WebSocket 实时通道 |
| `/api/voice` | 语音通话房（WebSocket） |
| `/api/butler` | 小绵管家：资讯简报、会话摘要 |
| `/api/social` | 关注 / 取关 / 通讯录 / 推荐 / 论坛互动消息 |
| `/api/groups` | 群组创建、邀请码加入、群消息 |
| `/api/notifications` | 站内通知 |
| `/api/badges` | 勋章墙、个人主页、个性签名 |
| `/api/emotions` | 情绪记录与回收站 |
| `/api/help-requests` | 求助工单 |
| `/api/learning-events` | 学习行为事件上报与统计 |
| `/api/feedbacks` | 意见反馈 |
| `/api/knowledge` | 知识库检索与管理 |
| `/api/feeds` | 外部资讯源与抓取条目 |
| `/api/references` | 开源参考库与页面脚手架 |
| `/api/ml` | 表情识别模型训练任务 |
| `/api/teacher` · `/api/teacher-tasks` · `/api/teacher-portfolio` | 教师端数据、任务、作品集 |
| `/api/admin` | 管理后台：教师 / 学生 / 院系 / 课程 / 监控 |
| `/api/settings` · `/api/settings/branding` · `/api/settings/wechat-mp` | 系统设置、品牌设计、微信小程序 |
| `/api/profile` · `/api/files` · `/api/upload` | 个人资料、鉴权文件下载、文件上传 |

---

## 开发约定

完整规范见 [`开发规范.md`](开发规范.md)，改 AI prompt 前另见 [`提示词工程规范.md`](提示词工程规范.md)。要点：

- **分层单向依赖**：`api/`（薄路由，禁止直接 `db.query` 与内联 DTO）→ `services/` → `models/`，`services/` 不 import FastAPI；
- **新业务域四件套**：`api/ services/ models/ schemas/` 同步补齐，并在 `app/api/registry.py` 的 `ROUTERS` 登记一行（参照 `feedback` / `portfolio` / `material`）；
- **建表只走 Alembic 迁移**，禁止手工 DDL；运行时账号 `campus_rw` 与迁移账号 `campus_ddl` 分离；
- **公共契约破坏性变更**（URL、DTO 字段）必须先同步前端调用方；枚举对外统一输出字符串（`app.utils.enum_helpers`）；
- **前端请求一律封装到 `src/api/`**，组件内禁止裸 axios；
- **Git**：工作分支 `develop`，禁止直推 `main`/`master`，Conventional Commits，推送前 `git pull --rebase origin develop`；
- **提交前验证**：后端 `python -c "import app.main"` 冒烟 + 前端 `npm run build` 零报错。

---

## 贡献指南

1. Fork 本仓库并克隆到本地；
2. 基于 `develop` 新建特性分支：`git checkout -b feat/your-feature`；
3. 提交前确保后端测试与前端构建通过：

   ```bash
   cd backend && .venv/Scripts/python.exe -m pytest
   cd frontend && npm run build
   ```

4. 提交信息遵循 Conventional Commits（`feat:` / `fix:` / `refactor:` / `docs:`）；
5. 提交 PR 并说明变更内容与验证方式。

---

## 开源协议

本项目采用 **MIT License**，详见 [`LICENSE`](LICENSE)。

MIT 是一款宽松开源协议：任何人可自由使用、复制、修改、合并、发布、分发、再授权及销售本软件，但须保留原始版权声明与许可声明，且软件按"原样"提供，不附任何担保。

---

## 致谢

- 绵阳城市学院 —— 项目场景与赛题支持
- 通义千问 DashScope / 兼容 OpenAI 协议的大模型服务 —— AI 能力支撑
- FastAPI / Vue / Element Plus / ECharts / Three.js 等开源社区
