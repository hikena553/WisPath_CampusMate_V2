# Agent 定时任务（学生端）设计文档

日期：2026-10-29
状态：已确认（用户逐节评审通过）
参考模型：ZCode 的定时任务（cron）——自然语言创建、到点 AI 真实执行、结果自动送达、可集中管理

## 背景与目标

学生端首页 `/student` 是 AI 对话壳（ChatShell/ChatPanel）。目标：学生可以给 AI 助手设定周期任务（如「每天早上 8 点帮我汇总校园新鲜事」「每周五下午帮我总结本周学习」），系统到点自动以该学生身份跑一轮 agent，结果落进任务专属会话并通过站内通知送达；另有管理子页集中查看/启停/删除/立即执行。

非目标（YAGNI）：
- 不向学生暴露 cron 表达式（周期粒度为人话级三种）
- 不做对话内暂停/删除工具（管理页承担）
- 不做教师端定时任务（工具体系当前分学生/教师两套，本期只加学生端）

## 1. 数据模型

新表 `agent_cron_tasks`（`app/models/cron_task.py`，alembic 迁移；本项目 schema 唯一事实源是 `alembic/versions`，应用启动时 `alembic upgrade head`，不再 create_all）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int PK | |
| user_id | FK users.id, index | 归属学生 |
| name | String(100) | 任务名（会话标题同源） |
| prompt | Text | 每次执行下发给 AI 的指令 |
| schedule_kind | Enum(daily/weekly/interval) | 周期类型，三选一 |
| hour / minute | int, nullable | daily/weekly 的触发时刻 |
| weekday | int 0-6, nullable | weekly 用（0=周一） |
| interval_hours | int, nullable | interval 用 |
| enabled | bool, default True | 暂停开关 |
| conversation_id | FK conversations.id | 任务专属会话，每次执行的消息都追加于此 |
| created_via | Enum(chat/manual) | 创建来源 |
| last_run_at / next_run_at | DateTime(timezone=True) | 存 UTC，与现有代码一致 |
| created_at / updated_at | DateTime | |

约束：每人上限 10 条，创建时校验（超限返回业务错误，由 agent 向学生说明）。

## 2. 创建路径（agent 工具）

`app/services/tools/definitions.py` 学生端 `TOOL_DEFINITIONS` 新增两个工具：

- `create_cron_task`：参数 name / prompt / schedule_kind / hour / minute / weekday / interval_hours。工具 description 明确要求 LLM：把学生的自然语言翻译为结构化参数，创建前先向学生复述确认；歧义（如"每隔一阵"）先追问。
- `list_cron_tasks`：无参，返回本人任务列表（名称/周期人话/启用状态/上次执行）。

`dispatcher.py` 新增执行分支：
- 校验参数合法性（三种周期的必填字段齐全、取值范围）与 10 条上限；
- 创建任务专属 `Conversation`（标题=任务名）与 `AgentCronTask`，按规则计算首个 `next_run_at`；
- 返回结构化确认 JSON（含任务 id 与下次执行时间），交 LLM 组织成自然语言答复。
- 参数非法时返回错误信息，LLM 据此向学生澄清，不落库。

暂停/恢复/删除/立即执行不进工具，统一走管理页（见 §4/§5）。

## 3. 调度执行内核

`app/tasks/periodic.py` 新增 `_periodic_cron_task_runner`，与现有四个周期任务同框架登记：

- 每 60 秒扫描 `enabled && next_run_at <= now` 的任务；
- **先推进 `next_run_at` 到下一周期点并提交，再执行**——防重入且崩溃安全（最多漏跑、不会重复跑）；进程内另设 `_running_ids` 集合兜底 run-now 与调度循环并发；
- 执行流程：往任务会话写一条 user 消息（「【定时任务】{name}：{prompt}」）→ 无头消费 `agent_service.chat(prompt, history=[], user, conv_id)` 生成器（异步生成器，直接在事件循环消费；回复自动落库会话）；
- 成功送达：`create_notification`（复用现有 `Notification`，SYSTEM 类型、level=normal），标题=任务名，正文=AI 结果前 200 字，`link=/student/agent?conv=<conversation_id>`；
- 失败处理：per-task try/except，记日志并发「执行失败」通知；`next_run_at` 已推进，不影响后续周期与其它任务；
- 学生不可用（会话/用户查询不到）则跳过该任务。

`next_run_at` 计算规则（hour/minute/weekday 一律是**学生口中的北京时间**，计算时按 Asia/Shanghai 换算后以 UTC 落库，避免触发时刻整体偏移 8 小时）：
- daily：明日（或今日未过触发时刻则为今日）hour:minute
- weekly：下一个指定 weekday 的 hour:minute
- interval：now + interval_hours

## 4. 管理 API

新增 `app/api/cron_task.py`，挂载于 `/api/cron-tasks`，全部仅限操作本人记录（越权返回 404）：

- `GET /api/cron-tasks`：本人列表（含周期的人话描述字段，由后端序列化）
- `PUT /api/cron-tasks/{id}`：启停（enabled）、改名
- `DELETE /api/cron-tasks/{id}`：删除（同时保留会话记录，不级联删会话）
- `POST /api/cron-tasks/{id}/run-now`：同步触发一次执行（复用 §3 执行函数，需会话归属校验）

## 5. 前端

- 管理子页 `frontend/src/components/agent/AgentCronPage.vue`：照抄 `CampusSearchPage` 的覆盖式子页模式——`Teleport + <Transition name="subpage">（duration 320）+ 根元素 fixed inset-0`，进出场动画统一走全局 `.subpage`（styles/animations.css），组件由 `ChatPanel` 挂载，首页 ChatShell 与 `/student/agent` 共用；移动端聊天顶栏加时钟图标入口。
- 列表项：任务名、周期人话描述（"每天 08:00"）、上次执行时间、启停 Switch、立即执行、删除；空态引导：「在对话框跟我说『每天早上 8 点…』就能建任务」。
- `ChatPanel` 小改：支持 `/student/agent?conv=<id>` 打开指定会话（onMounted 读 query），通知点击直达任务会话。

## 6. 错误处理与测试

错误处理：
- LLM 超时/异常 → 「执行失败」通知 + 日志；调度循环不中断；
- run-now 与调度循环并发同一任务 → `_running_ids` 去重，后到者直接返回"正在执行"；
- 删除任务时正在执行 → 执行完成落库照常，通知跳转的会话仍存在（不级联删），无悬空引用。

测试（pytest，后端）：
- dispatcher：参数校验（缺字段/越界/超限 10 条）、任务与会话同时落库、首算 next_run_at；
- next_run_at 计算：daily（今日已过/未过触发时刻）、weekly 跨周、interval；
- runner：到期触发、先推进再执行（模拟执行中异常仍推进）、防重入；
- API：越权访问他人任务返回 404、启停与 run-now 生效。

前端验证：playwright 手动脚本（种子账号 2024001/123456，登录页三坑：welcome 引导 init script、勾协议、placeholder「学号 / 工号」）截图验证子页覆盖与列表渲染；注意 ZCode 内置浏览器恒为 prefers-reduced-motion: reduce，动画以用户本机浏览器为准。

## 决策记录

- 选型 A（ZCode 式完整版）优于 B（对话即一切，无总览）与 C（表单优先，无 agent 味）——用户确认。
- 执行方式为「AI 每次执行」而非纯提醒——用户确认。
- 复用 `Notification`（SYSTEM 类型）而非新增枚举值：避免 PG enum ALTER 迁移，消息中心已良好渲染系统通知。
- 每任务绑定一个专属会话而非每次执行新建会话：会话列表不被定时输出刷屏，且历史执行在同一线程可回溯。
- 删除执行中任务返回 409（拒绝而非等待）：execute_once 收尾对任务行做 UPDATE，先删会 StaleDataError；服务层另对收尾更新容错兜底（双保险）。
- run-now 为同步等待执行完成（计划选定）：请求会挂住整个 LLM 运行时长，前端无 axios 超时无碍，但反向代理默认 60s 读超时会先回 504——部署时若遇到，改 202 + asyncio.create_task 即可，不动执行内核。
