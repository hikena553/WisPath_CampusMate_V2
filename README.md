# 智慧校园 AI 服务平台 · WisPath CampusMate

> 绵阳城市学院智慧校园 AI 服务平台 —— 集校园信息查询、AI 对话助手、学生成长档案、教师管理于一体的全栈应用。

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Frontend-Vue%203-42b883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Build-Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![MySQL](https://img.shields.io/badge/Database-MySQL-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#开源协议)

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
  - [环境要求](#环境要求)
  - [一键启动（推荐）](#一键启动推荐)
  - [手动启动](#手动启动)
- [项目结构](#项目结构)
- [默认测试账号](#默认测试账号)
- [功能模块](#功能模块)
- [API 概览](#api-概览)
- [贡献指南](#贡献指南)
- [开源协议](#开源协议)
- [致谢](#致谢)

---

## 项目简介

**智慧校园 AI 服务平台** 面向高校师生，提供"查、问、管"一体化服务：

- **学生端**：AI 对话助手、成长档案、课表 / 成绩查询、办事服务、请假申请等；
- **教师端**：班级概览、学生管理、请假审批、实时消息（WebSocket）；
- **通用能力**：校园知识库问答、官网通知、基于对话分析的 AI 心理危机预警（严重 / 中等 / 轻微三级）。

后端基于 FastAPI + SQLAlchemy，前端基于 Vue 3 + TypeScript + Vite + Element Plus。

---

## 功能特性

- **AI 助手（绵小城）**：SSE 流式对话，支持语音输入、文件上传、项目式多轮对话；
- **学生成长档案**：荣誉 / 竞赛 / 实践 / 论文 / 成果记录，技能兴趣标签，综合评分雷达图；
- **学业管理**：课表查询、成绩查询与 GPA、成绩分析；
- **办事与审批**：在线办事服务、学生请假申请与教师审批流；
- **危机预警**：基于对话内容的 AI 心理预警，分级推送；
- **实时通信**：师生消息管理，基于 WebSocket 的即时通讯；
- **认证授权**：JWT 登录注册，学生 / 教师 / 管理员三角色权限。

---

## 技术栈

| 分层 | 技术 |
|------|------|
| 前端框架 | Vue 3（Composition API）+ TypeScript |
| 前端构建 | Vite 5 |
| UI 组件库 | Element Plus |
| 状态管理 | Pinia |
| 图表 | ECharts + vue-echarts |
| 网络请求 | Axios |
| 后端框架 | Python FastAPI |
| ORM | SQLAlchemy + Pydantic |
| 数据库 | MySQL（`mysql+pymysql`） |
| AI 能力 | 阿里云通义千问 DashScope（默认），`.env` 可覆盖模型 |
| 认证 | JWT（`python-jose` + `passlib`） |
| 数据库迁移 | Alembic |

---

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18
- MySQL 8.0+

### 一键启动（推荐）

项目根目录提供 `main.py` 一键启动脚本，会先后拉起后端（FastAPI，:8000）与前端（Vite，:5173），并在退出时清理所有子进程：

```bash
# 在项目根目录执行（需先装好前后端依赖，见下方“环境要求”）
python main.py
```

- 脚本会等待后端 `/api/health` 健康检查通过后再启动前端；
- 前端依赖未安装时会提示先执行 `cd frontend && npm install`；
- 按 `Ctrl+C` 可同时停止前后端服务。

### 手动启动

#### 后端

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（编辑 .env）
# DATABASE_URL=mysql+pymysql://root:password@localhost:3306/smart_campus
# LLM_API_KEY=your-dashscope-api-key

# 初始化数据库（会自动建表）
python -m app.seed

# 启动开发服务器
uvicorn app.main:app --reload
```

#### 前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev        # 默认 :5173，代理 /api → :8000

# 构建生产版本
npm run build      # vue-tsc 类型检查 + Vite 构建
```

---

## 项目结构

```
WisPath_CampusMate_v2.0/
├── main.py                 # 一键启动脚本（先后拉起前后端）
├── backend/
│   ├── app/
│   │   ├── main.py          # 入口，注册路由 + /api/health
│   │   ├── seed.py          # 种子数据
│   │   ├── api/             # 路由层（13 个模块）
│   │   ├── core/            # 核心配置（数据库、依赖注入）
│   │   ├── models/          # SQLAlchemy 模型（26 张表）
│   │   ├── schemas/         # Pydantic 数据模式
│   │   ├── services/        # 业务逻辑（auth、agent、llm、scoring、ws）
│   │   └── utils/           # 工具函数
│   ├── alembic/             # 数据库迁移
│   ├── tests/               # 后端测试
│   ├── .env.example         # 环境变量模板（复制为 .env 后填写）
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── main.ts           # Vue 入口
│       ├── router/           # 路由配置 + 守卫
│       ├── stores/           # Pinia 状态管理
│       ├── api/              # API 请求封装
│       ├── components/       # 通用组件
│       ├── composables/      # 组合式函数
│       ├── views/            # 页面组件
│       ├── utils/            # 工具函数
│       ├── styles/           # 全局样式
│       ├── directives/       # 自定义指令
│       ├── __tests__/        # 前端测试
│       └── types/            # TypeScript 类型定义
└── docs/                     # 设计文档（赛题要求、未实现功能等）
```

---

## 默认测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 学生 | 2024001 | 123456 |
| 教师 | t1001 | 123456 |
| 管理员 | admin | admin123 |

> 注意：生产环境请务必修改上述默认密码。

---

## 功能模块

### 学生端
- **AI 助手** — 绵小城智能对话，支持语音输入、文件上传、项目式对话
- **成长档案** — 成长记录（荣誉 / 竞赛 / 实践 / 论文 / 成果）、技能与兴趣标签、项目展示、综合评分雷达图
- **课表查询** — 查看学期课程安排
- **成绩查询** — 查看各科成绩与 GPA
- **校园风采** — 校园风景图片浏览
- **办事服务** — 在线申请服务
- **请假申请** — 提交请假审批

### 教师端
- **班级首页** — 班级概览、综合评分统计
- **AI 助手** — 绵小城智能对话（教师专项）
- **学生管理** — 名下学生列表、综合评分、成长档案详情查看（含危机预警和请假记录）
- **审批管理** — 请假申请审批
- **消息管理** — 与学生实时通信（WebSocket）

### 通用
- **校园知识库** — 办事流程、规章制度问答
- **官网通知** — 教务处最新公告
- **危机预警** — 基于对话分析的 AI 心理预警（严重 / 中等 / 轻微三级）

---

## API 概览

| 前缀 | 模块 | 说明 |
|------|------|------|
| `/api/auth` | auth | 登录注册 |
| `/api/agent/chat` | agent | AI 助手 SSE 流式聊天 |
| `/api/campus` | campus | 校园服务 |
| `/api/growth` | growth | 成长档案 CRUD |
| `/api/academic` | academic | 学业管理 |
| `/api/service` | service | 服务大厅 |
| `/api/leave` | leave | 请假审批 |
| `/api/crisis` | crisis | 危机预警 |
| `/api/teacher` | teacher | 教师端接口 |
| `/api/upload` | upload | 文件上传 |
| `/api/conversations` | conversations | 对话历史 |
| `/api/messages` | messages | 消息管理 + WebSocket |
| `/api/announcement` | announcement | 公告通知 |
| `/api/admin` | admin | 管理后台 |
| `/api/notification` | notification | 通知管理 |
| `/api/feedback` | feedback | 反馈管理 |
| `/api/setting` | setting | 系统设置 |
| `/api/grade-analysis` | grade_analysis | 成绩分析 |
| `/api/profile` | profile | 个人资料 |

---

## 贡献指南

欢迎提交 Issue 与 Pull Request！

1. Fork 本仓库并克隆到本地；
2. 基于 `main`（或 `develop`）分支新建特性分支：`git checkout -b feat/your-feature`；
3. 提交前请确保：后端 `pytest` 通过、前端 `npm run build` 通过；
4. 保持提交信息清晰（建议遵循 Conventional Commits，如 `feat:`、`fix:`、`docs:`）；
5. 提交 PR 并描述变更内容。

---

## 开源协议

本项目采用 **MIT License**，详见仓库根目录的 [`LICENSE`](LICENSE) 文件。

MIT 是一款宽松开源协议：任何人可自由使用、复制、修改、合并、发布、分发、再授权及销售本软件，但须保留原始版权声明与许可声明，且软件按"原样"提供，不附任何担保。

---

## 致谢

- 绵阳城市学院 —— 项目场景与赛题支持
- 阿里云通义千问 DashScope —— AI 大模型能力
- FastAPI / Vue / Element Plus / ECharts 等开源社区
