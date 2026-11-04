# deck/content.py 内容口径与来源说明

> 本文件供 Lead 抽查：每个数字都给出**计算命令 + 来源文件 + 一句结论**。
> 标 ⚠️演示 的为演示数据（允许编，但不得当成真实运营数据对外表述）。

---

## 0. 一句话结论

`deck/content.py` 是可 import 的**纯数据模块**（无第三方依赖、无 print、无文件 IO、无副作用）；
所有功能点在 `backend/app` 与 `frontend/src` 里都能找到页面 / 路由 / 接口 / 模型 / 服务作为依据；
所有长度上限已脚本校验通过（见第 6 节）。

---

## 1. 关键数字（全部现算，不抄 README）

⚠️ **README.md 里的数字已过期**（写「13 个 API 模块 / 26 张表」），本轮全部按代码重新统计。

| 指标 | 采用值 | 计算命令（项目根目录执行，PowerShell） | 来源 |
|---|---|---|---|
| 页面 | **46 个** | `(Select-String -Path frontend\src\router\index.ts -Pattern "component:\s*\(\)\s*=>\s*import\('@/views/" -AllMatches).Matches.Count` | `frontend/src/router/index.ts` |
| API 模块 | **51 个** | `(Get-ChildItem backend\app\api -Filter *.py).Count - 1` → 52-1 | `backend/app/api/` |
| 接口 | **357 个** | 统计 `backend/app/api/*.py` 中 `@router.(get\|post\|put\|patch\|delete\|websocket)` 装饰器出现次数 | 同上 |
| 数据表 | **79 张** | `(Select-String -Path backend\app\models\*.py -Pattern "__tablename__" -AllMatches).Matches.Count` | `backend/app/models/`（42 个模型文件） |
| AI 工具 | **53 个** | `TOOL_DEFINITIONS` 28 条（学生） + `TEACHER_TOOL_DEFINITIONS` 25 条（教师） | `backend/app/services/tools/definitions.py` |
| 角色 | **3 个** | `UserRole` 枚举 + 路由 `meta.role` 守卫 | `backend/app/models/user.py`、`router/index.ts:207-223` |
| 学院 | 7 个 | `colleges_data` 列表长度 | `backend/app/seed.py:77-85` |

**页面 46 的分布**（同一命令按目录拆分即可复核）：
公共/登录 4（Login / Welcome / ForgotPassword / ChangePassword）+ 分享 2（家长只读页、入群页）
+ 学生端 12 + 教师端 15 + 管理端 13 = **46**。
另有 11 条 `redirect`（旧路由收敛，如 `/student/growth` → `/student/schedule?tab=growth`），不计入页面。
`frontend/src/views/` 下共 71 个 `.vue`，其中含 teacher `Home*` 子组件与 admin `components/`，
**只有 46 个是可路由访问的页面**，故 FACTS 采用 46。

**AI 工具 53 的口径**：28（学生）+ 25（教师）= 53 条工具定义；其中 `query_knowledge`、
`query_announcements` 两端共用，**去重后 51 个唯一工具**。文案中「53 个工具」指工具定义数。

---

## 2. 能力事实（写进文案的每一条都有出处）

| 文案表述 | 代码依据 |
|---|---|
| SSE 流式回答 | `backend/app/api/agent.py:88-90`（`StreamingResponse`, `media_type="text/event-stream"`） |
| 深度思考 | `backend/app/api/agent.py` `deep_think` 参数；`frontend/src/components/agent/ChatPanel.vue:255-291` 胶囊按钮 |
| 语音通话（识别 + 合成） | `backend/app/api/voice.py:32` `@router.websocket("/ws")`；`services/voice_service.py:109` `qwen-audio-3.0-asr-flash`（STT）、:113 `TTS` |
| 文件 / 图片上传 | `backend/app/api/upload.py:65` `POST /api/upload`；`ChatPanel.vue:295-313` |
| 能看图（视觉识别） | `backend/app/services/llm_service.py:209-248` `recognize_image()`，视觉模型 `qwen-vl-plus` |
| 知识库检索（RAG） | `backend/app/api/knowledge.py`、`services/knowledge_service.py`、`models/document.py`（`documents` + `document_chunks` 向量索引）；`student/CampusPage.vue:1408`「RAG 混合检索」 |
| 工具调用（function calling） | `services/agent_service.py:311-319`（按角色选工具集、多轮工具执行） |
| 危机三级预警 | `services/crisis_service.py`（`normal/mild/moderate/severe`，关键词 + LLM 语义）; `admin/HomePage.vue:369-372` 严重/中等/轻微/正常 |
| 预警自动派单成教师任务 | `services/alert_pipeline_service.py:138-177`（规则可配置，命中生成 `TeacherTask(source_type=ALERT)`） |
| WebSocket 实时消息 | `backend/app/api/messages.py:38` `@router.websocket("/ws")`；`services/ws_manager.py` `ConnectionManager` |
| 5 维成长评分 | `services/scoring.py:64-70`：学术素养 / 创新能力 / 实践能力 / 社交素养 / 综合素质 |
| 5 类成长记录 | `services/scoring.py` `TYPE_LABELS`：荣誉 / 竞赛 / 实践 / 论文 / 成果 |
| 学生 6 标签学业中心 | `student/SchedulePage.vue:1299`（schedule / grades / growth / service / plan / ai） |
| 教师首页 KPI | `teacher/HomePage.vue:398-451`：我的学生、待批请假、心理预警、今日到期 / 逾期未办 / 高危预警 |
| 管理端 8 项看板 | `admin/HomePage.vue:401-408`：学生 / 教师 / 学院 / 知识库 / 文档 / AI 会话 / 消息 / 危机关注 |
| 家长只读分享链接 | `views/share/GuardianSharePage.vue` + `models/guardian.py` `guardian_share_links` |
| 上传格式校验 | `backend/app/api/upload.py:36` `_validate_archive` |
| 敏感配置加密存储 | `backend/app/core/crypto.py`（`encrypt_value` / `_SENSITIVE_KEYS`） |

---

## 3. ⚠️ 演示数据清单（可在文案里出现，但不得当作真实统计）

| 位置 | 字段 | 值 | 说明 |
|---|---|---|---|
| `STUDENT.chat[3]` | AI 气泡 | `GPA 3.62` | ⚠️演示对话数值 |
| `TEACHER.kpis` | 我的学生 / 待批请假 / 心理预警 / 今日到期 | 42 / 3 / 1 / 2 | ⚠️演示数字（真实接口为 `/api/teacher` 统计） |
| `TEACHER.approval` | 姓名 / 类型 / 时间 | 李思远 / 病假 · 2 天 / 今天 09:20 | ⚠️演示单据（姓名非种子库学生，避免与真实账号混淆） |
| `ADMIN.kpis` | 在册学生 / 教师账号 / 知识库条目 / 今日对话 | 12,480 / 986 / 1,286 / 8,642 及 delta | ⚠️演示数字（对应字段：`student_count` / `teacher_count` / `knowledge_count` / `conversation_count`） |

> 请假类型取自真实枚举：`LeaveType` = `sick` 病假 / `personal` 事假 / `other` 其他。

**数字自洽性**：提问页 `QUESTIONS[1]` 写「四十多个学生」是为了和 `TEACHER.kpis` 的演示值 42 对齐，
避免同一份 deck 里出现两套学生规模。若 Lead 要改 KPI，请同步改这一句。

---

## 4. 三端功能取舍说明（为什么选这些点）

**学生端**——选「对话 + 学业中心 + 成长画像 + 关怀」四件事，理由是这四项各自有独立的数据模型与页面，
且覆盖学生一天里最高频的三个动作（查课表 / 交请假 / 看成绩）。刻意**没写**：交流社区、失物招领、
AI 资源空间、学习计划细节——它们是真实功能（`community` / `lost_found` / `resources` / `plan`），
但对 10 页宣传片的叙事是噪音，改放进 chips 与功能矩阵第 9 页做「广度」证据。

**教师端**——只讲**班级驾驶舱**这一条主线：四张 KPI 卡（都有真实字段支撑）→ 请假闭环 → 危机工单
（预警自动派单，是这套系统最有说服力的一环）。没讲问卷互评、关怀记录细节，同样下放到 chips / 矩阵。

**管理端**——讲「全局看得见」：8 项看板指标 + 组织权限 + 知识库运营 + 系统监控。
没有把「系统设置 / 资讯源管理 / 参考库」当主点，因为它们是后台工具，不构成卖点。

**整体叙事取舍**：产品页（第 3 页）只保留 4 个能力支柱（对话 / 画像 / 办事 / 预警），
把 WebSocket 实时消息、家校沟通、群聊这些「能力」放进技术页（第 8 页）与矩阵页（第 9 页），
原因是 10 页的节奏里，产品页要给「一句话讲清这产品是什么」，不是列功能。

---

## 5. 文案与渲染约定

- **换行只有一处**：`SUMMARY.headline` 用了一个显式 `\n`（「让校园服务，/ 从一句话开始。」），
  因为 `build_deck.py:944` 对总结页是按 `\n` 切行渲染 50pt 大字。其余 headline 均为单行字符串，
  由 `build_deck.py` 的 `title_lines()` 在「，」处自动断成两行（学生/教师/技术页已验证断行位置合适）；
  管理端 headline 由渲染层单行渲染（34pt，6.6in 框宽内 10 字可容纳）。
- **长度口径**：所有上限按 `len(str)` 计，**含标点与空格、不含换行**。
- **图标白名单**（与 task-1 约定一致，共 8 个）：
  `chat / spark / chart / shield / heart / calendar / users / monitor`。
  本模块**只用了这 8 个**，实际用到：`chat, chart, calendar, shield, heart, users, spark, monitor`（8 个全覆盖）。
  → **asset-maker 需产出这 8 个 `icon_*.png`**；`theme.icon()` 在文件缺失时返回 `None`（不抛错），
  缺图只会少图标、不会挂页。
- **FACTS 只保留 5 个键**（pages / api_modules / models / roles / tech），避免渲染层遍历该 dict 时多出卡片。

---

## 6. 自检结果（可复跑）

校验脚本放在**临时目录**，未污染 `deck/`：

```
C:\Users\Avalon\AppData\Local\Temp\deckcheck\check_content.py
```

复跑命令：

```powershell
$py = "C:\Users\Avalon\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$env:PYTHONIOENCODING='utf-8'
& $py "C:\Users\Avalon\AppData\Local\Temp\deckcheck\check_content.py" "E:\studyScore\创意集市\WisPath_CampusMate_V2\deck"
```

最近一次结果：

```
PILLARS=4 MATRIX=8/8/8 NOTES=10
FACTS: 46 个页面 | 51 个 API 模块 | 79 张数据表 | 学生 / 教师 / 管理员

ERROR(0):

ALL CHECKS PASSED
```

任务验收命令（`deck/` 为 cwd 相对路径）：

```
python -c "import sys; sys.path.insert(0,'deck'); import content; print(len(content.PILLARS), len(content.FEATURES_MATRIX['student']))"
→ 4 8   （exit 0）
```

校验覆盖：import 成功 / 12 个顶层键齐全 / BRAND 固定值 / FACTS 5 键 / PILLARS 4 项 /
三端 eyebrow 与条目数 / 全部字符串长度上限 / icon 在 8 个白名单内 / 讲稿 80~120 字 / 无副作用。

---

## 7. 讲稿字数（NOTES，对应 10 页）

页序：1 问候 / 2 提问 / 3 产品 / 4 能力 / 5 学生 / 6 教师 / 7 管理员 / 8 技术 / 9 功能矩阵 / 10 总结。

全部落在 80~120 字区间（含标点），由校验脚本逐条检查；语速按每秒 3.5 字计，单页约 25~35 秒。
