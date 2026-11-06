# 教师端「学生名单」改造方案：班级 → 名单 → 详情 → 分层

| 项 | 内容 |
|---|---|
| 文档版本 | v1.1（**已实施**） |
| 日期 | 2026-11-06 |
| 改造范围 | 教师端 `/teacher/students`（工作台 · 学生名单） |
| 目标形态 | 班级列表（带「重点关注 N 人」）→ 班级名单 → 学生详情（可选分层） |
| 复用原则 | 详情页 7 个 Tab、联系、预警处置、家校沟通、关怀记录、AI 诊断全部原样复用 |

---

## 实施结果（v1.1 补记）

### 新增文件

| 文件 | 行数 | 作用 |
|---|---|---|
| `frontend/src/composables/useClassSummaries.ts` | ~160 | 学生按班级聚合为 `ClassSummary[]`；`triageOf()` 是唯一分档入口 |
| `frontend/src/components/teacher/students/ClassOverview.vue` | ~430 | L1 班级卡网格 + 跨班搜索 |
| `frontend/src/components/teacher/students/ClassStatsBar.vue` | ~160 | L2 头部：返回 / 班级名 / 「重点关注 N 人」开关条 |
| `frontend/src/components/teacher/students/LayerToggle.vue` | ~95 | 分层开关（不分层 / 危机分层），localStorage 记忆 |
| `frontend/src/components/teacher/students/LayeredRoster.vue` | ~390 | 三档折叠名单，桌面/移动共用一套分档，只切行样式 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `frontend/src/views/teacher/StudentsPage.vue` | 2965 → 2937 行。桌面端 L1/L2 二选一；移动端子页改为「班级总览 → 班级名单」两层；下线旧四筛选器与移动端专属 `triageGroups` |
| `frontend/src/api/teacher.ts` | `StudentSummary` 增 `class_group_id` / `class_name` |
| `backend/app/api/teacher.py` | `StudentOut` 增 `class_group_id` / `class_name`，`list_students` 回填 |

### 实施中修正的几处设计

1. **`selectedClass` 存 id 而非对象快照。** 原方案写「选中班级」，实施时改为 `selectedClassId: number | null` + `computed` 派生。原因：数据一变（导入、智能体新增、SSE 推送），快照里的「重点关注 N 人」会停在旧值，而下面名单已是新的 —— 教师会看到「提示条说 3 人、列表有 4 条红」。
2. **`loadStudents()` 去掉 search 参数。** 原实现带搜索词请求后端。在三层结构下，`students` 被搜索词裁剪会让班级卡统计与名单行出自不同数据源。改为始终拉全量、前端过滤（教师名下学生规模完全撑得住）。
3. **`triageOf()` 单一入口。** 班级卡计数与分层列表都调用它，「重点关注」口径不可能漂移。
4. **移动端分层开关独占一行。** 全宽分段控件与搜索框同行会互相挤，`.ms-list-search.is-stacked` 改为上下两行。
5. **移动端页头计数用班级总人数**，不是筛选后条数 —— 页头是身份说明，不是筛选结果。

### 验证

- `vue-tsc --noEmit`：改造涉及 6 个文件 **0 错误**（仓库里 `ApprovalPage.vue` 有 4 条既有 TS6133/类型错误，与本次无关）。
- `vite build` 通过，`StudentsPage` chunk 103.94 kB / gzip 33.62 kB。
- Vite dev server 能正常编译并返回全部 5 个新文件。
- 后端 `py_compile` 通过。
- **未做浏览器实机点击验证**（环境无浏览器自动化能力），建议手动过一遍：L1 卡片数字 → L2 三层展开 → 分层开关切换 → 详情 7 Tab → 移动端返回键逐层退。

### 口径说明（实施采用）

- 重点关注 = `severe` + `moderate`。
- **已闭环的预警仍计入**（`AIDialogSummary` 未按 resolved 降档），卡片脚注已明示「已闭环的预警仍计入，处置状态请进入班级查看」。
- 低分 / 长期无互动未纳入分档（保持口径单一）。

---

## 1. 一句话方案

把现在「一锅端」的学生名单拆成三层：**第一层看班级（每班提示有几人要重点关注）→ 第二层看该班的学生（默认按危机分层展示，也可切换为不分层）→ 第三层进详情**。详情页及其所有跳转逻辑一行不改。

---

## 2. 现状盘点（已读代码确认）

### 2.1 文件与体量

| 文件 | 行数 | 说明 |
|---|---|---|
| `frontend/src/views/teacher/StudentsPage.vue` | 2965 | 桌面 + 移动端两套模板 + 全部业务逻辑 + 样式，单文件承接过重 |
| `frontend/src/api/teacher.ts` | — | `getStudents(search, classGroupId)`、`getStudentDetail(id)` 等 |
| `backend/app/api/teacher.py` | 850+ | `/students`、`/students/{id}`、`/dashboard`、`/class-stats` 等 |
| `backend/app/api/organization.py` | — | `/admin/class-groups`（教师可读） |

### 2.2 现有交互

- **桌面端**：页头 → 指标条（在册/高危/待批请假/有成果）→ 筛选条（搜索 + 危机等级/成长/评分/技能）→ 分页卡片网格（12/24/36/48）→ 弹窗展示学生详情（7 个 Tab）。
- **移动端**：首屏看板（`HomeMobileBoard`）→ 「学生名单」子页 → 搜索 + 排序 + 危机等级 chips + **分诊队列三档折叠**（必须今天处理 / 这周要跟进 / 状态平稳）→ 学生详情全屏子页。
- 分层能力现状：移动端已有一版「危机分诊」折叠分组（`triageGroups`），但是**前端临时推导**（代码注释已说明后端没有 `triage_bucket` 字段）；桌面端完全没有分层，只有筛选器。

### 2.3 数据基础

- `User.class_group_id` / `User.class_name` 字段已存在，`ClassGroup` 表（major_id / grade / name）已存在。
- `GET /api/teacher/students` **已支持 `class_group_id` 参数**，且此路径下不套「仅本人名下学生」的过滤（为了通讯录班级下钻可用）。
- `GET /api/admin/class-groups` 已对 TEACHER 开放，带 `college_id` / `major_id` 过滤，且 `student_count` 是按真实归属重算的。

**结论：后端不需要任何新接口就能跑通这条链路。** 只需要一个前端聚合方法补上「班级维度摘要」。

### 2.4 现状问题（为什么值得改）

1. 教师名下学生可能横跨多个班级，混在一张网格里，**看不出「哪个班出事了」**。
2. 「高危 3 人」是全校口径，**不是班级口径**，无法回答「二班有几个人要盯」。
3. 移动端分层是前端硬编码 `crisis_level === 'severe'` 推导的，与桌面端不一致，且无法关闭。
4. 学生所属班级在卡片上根本没展示（卡片显示的是 `college`，学院），同名的班级归属信息在名单层丢失。

---

## 3. 目标信息架构

```
教师工作台 /teacher/students
│
├─ L1  班级总览（默认落地页）
│     每张班级卡：班级名 · 专业 · 学生数 · 「重点关注 N 人」红标 · 高危/中度/轻度分布条 · 最近预警时间
│     搜索框可跨班搜学生（搜到直接跳到该生详情）
│     兜底卡：「未分班学生」—— class_group_id 为空的学生不能消失
│
├─ L2  班级名单（选中某班后）
│     头部：← 返回 · 班级名 · N 人 · 「重点关注 N 人」提示条（可点击筛到该组）
│     ┌ 分层切换：不分层 ｜ 危机分层（默认）
│     ├ 不分层 → 复用现有桌面卡片网格 / 分页（一模一样，零改动）
│     └ 危机分层 → 三档折叠分组：必须今天处理(severe) / 这周要跟进(moderate) / 状态平稳(其余)
│     
└─ L3  学生详情（点卡片 / 点行）
      桌面：现有 el-dialog（7 Tab 全保留）
      移动：现有全屏子页（7 Tab 全保留）
```

层级导航方式：

- 桌面端 L1→L2：页内切换 + 顶部面包屑 `全部班级 / 2024级软件工程1班`，URL 带 `?class=<class_group_id>`，刷新可还原、可分享。
- 移动端 L1→L2：沿用现有 `subpage` 滑入子页（`rosterSubPage` 改为 `classSubPage`），系统返回键逐层退（`useBackLayer` 再加一层）。
- L2→L3：完全不动，仍走 `openDetail(s)`。

---

## 4. 关键设计点

### 4.1 「重点关注」的口径（必须先定，否则前后端会打架）

分层只做**一个维度：危机等级**（与用户描述「如今现在的情况危急分层」一致）。定义：

| 档位 | 判定 | 语义 |
|---|---|---|
| 必须今天处理 | 最新危机 `crisis_level === 'severe'` | 红色 · 今天就要动 |
| 这周要跟进 | `crisis_level === 'moderate'` | 橙色 · 本周内跟进 |
| 状态平稳 | 其余（mild / 无预警 / 已闭环） | 绿色 · 常规关注 |

**重点关注人数 = severe + moderate。** 班级卡上的红标即此数；`severe` 单独用更深的红点二次强调。

> 需要确认的两点：
> 1. 现在「最新危机」取的是 `AIDialogSummary` 最新一条，**不区分是否已闭环**。若某生最后一次预警已 resolved，是否还计入重点关注？建议：`resolved` 的降一档（severe 且已闭环 → 这周要跟进），并在卡片上标「已闭环」。这一条要产品确认。
> 2. 是否要纳入「无预警但综合评分过低 / 长期无互动」的学生？建议本期不做，保持口径单一，避免口径膨胀。

### 4.2 「分层/不分层」的实现方式

- 前端本地开关，默认 **危机分层**（贴合教师「先看要紧的」的使用动线）。
- 状态记在 `localStorage`（key: `teacher.roster.layerMode`），下次进来保持上次选择。
- 不分层时**完全复用现有 `student-grid` + `el-pagination`**；分层时复用现有移动端 `tm-tri` 折叠样式（提升为共用组件），**不新造一套卡片**。
- 分层视图不翻页（每档内全量展开、可折叠），不分层视图保留分页。

### 4.3 多班级 = 多组学生数据，如何取数

教师名下学生可能跨多个班。取数策略：

- L1 班级总览：**一次性取全量学生**（`getStudents()`，本来就是全量），前端按 `class_group_id` 分组聚合出每班的 `total / severe / moderate / mild / latest_time`，同时保证与 `/dashboard` 的全局数字一致。
- L2 班级名单：复用同一份数据，按班级过滤；**不再发请求**（切换班级零等待）。
- 只有班级数量很多（>20 个班或 >2000 人）才考虑改成后端聚合接口 —— 本期不需要，规模远未到。

> 这样做的额外好处：班级卡上的数字与名单里的行**永远一致**，不会出现「卡片说 3 人、点进去只有 2 人」的经典问题（因为不是两次独立统计）。

### 4.4 详情页零改动

`openDetail`、`detailVisible`、`detailTab`、7 个 Tab、`gotoCrisisCenter`、`feedbackGuardian`、`gotoFeature`、`CareRecordPanel`、`StudentInsightPanel` 全部保留。新增的只是「进入详情之前多了一层上下文」，详情里可以多带一个 `class_name` 显示在头部，但不影响任何跳转参数。

---

## 5. 改造清单（文件级）

### 5.1 新增

| 文件 | 作用 |
|---|---|
| `frontend/src/components/teacher/students/ClassOverview.vue` | L1 班级卡网格；props: `groups`，emit: `select(classGroupId)` |
| `frontend/src/components/teacher/students/ClassStatsBar.vue` | L2 头部：班级名 + N 人 + 「重点关注 N 人」提示条 |
| `frontend/src/components/teacher/students/LayerToggle.vue` | 分层开关（不分层 / 危机分层）+ 口径说明 tooltip |
| `frontend/src/components/teacher/students/LayeredRoster.vue` | 危机分层三档折叠列表（从移动端 `tm-tri` 提取，桌面/移动共用） |
| `frontend/src/composables/useClassGroups.ts` | 拉 `getClassGroups({college_id})` + 把学生按 class_group_id 聚合为 `ClassSummary[]`（含未分班兜底） |

### 5.2 修改

| 文件 | 改动 |
|---|---|
| `StudentsPage.vue` | ① 删掉桌面首屏直接铺学生网格的逻辑，改为 L1/L2 两态（`selectedClassId: ref<number \| null \| 'unassigned'>`）；② 移动端 `rosterSubPage` 语义改为 `classSubPage`；③ 分层开关与分层视图接入；④ 指标条、筛选条在新结构下重新落位（详见 §5.3）；⑤ 底部指标区（班级数据分析折叠区）保留在 L2 |
| `api/teacher.ts` | 无需新增函数；`getStudents` 已支持 `class_group_id`（备用，本期前端聚合，不调用） |
| `router/index.ts` | `/teacher/students` 增加 `?class=` 查询参数约定（不改路由结构） |

### 5.3 各层元素落位（避免信息堆在一屏）

**L1 班级总览**

- 顶部：现有品牌页头（标题改为「学生名单」，副标题状态胶囊保留，指向全局高危数）。
- 工具条：搜索框（跨班搜人，命中直接进详情）+ 「按危机倒序 / 按班级名」排序。
- 主体：班级卡网格（2–3 列自适应）；卡片内容 = 班级名 / 专业 / 「共 N 人」/ **重点关注 N 人（红）** / 一行分布条（红橙绿三段）/ 最近预警时间。
- 无班级时：显示「未分班学生 N 人」兜底卡。
- 页脚：保留「班级数据分析」折叠区入口。

**L2 班级名单**

- 头部：`← 全部班级` / 班级名 / `共 N 人` / **「重点关注 N 人」提示条**（点击 = 只显示重点关注，再点取消）。
- 控制行：搜索（班内）+ 分层开关 + 排序。
- 主体：分层视图（默认）或不分层网格。
- 分页：仅不分层视图有。

**L3 详情**：现状不变。

### 5.4 移动端

- 首屏看板的「学生名单」入口 → L1 班级总览子页（`subpage` 滑入）。
- 班级总览用单列列表样式（复用 `ms-row` 语汇），每行右侧显示红标数字。
- L2 直接复用现有 `ms-chip + tm-tri` 结构，只需把 `triageGroups` 数据源从「全部学生」换成「当前班级学生」。
- 分层开关放在 L2 控制行，同样的 `localStorage` 记忆。

---

## 6. 交互细节与边界

| 场景 | 处理 |
|---|---|
| 教师只有 1 个班 | L1 仍展示（只有一张卡），但卡片上加「进入」主按钮，不做自动跳过 —— 自动跳过会让老师失去「我到底带几个班」的认知 |
| 教师带很多班（>8） | L1 按学院/年级分组，或顶部加班级搜索 |
| 学生未分班 | 独立兜底卡「未分班学生」，永远排在最后 |
| 搜索跨班命中 | 直接 `openDetail`，返回时回到 L1 且清空搜索 |
| 深链 `?student=<id>` | 保留现有逻辑，额外把 L2 班级上下文补齐（从学生反查班级） |
| 深链 `?class=<id>` | 进入 L2；无效 id 回 L1 并 toast |
| 数据变更（导入/智能体新增） | `onDataChange` 已监听，重拉后班级卡数字自动刷新 |
| 空态 | L1 无任何学生 → 现有吉祥物空态；L2 某档为空 → 「这一档现在是空的」 |
| 导出学生数据 | 保持全量导出；后续可加「导出本班」 |

---

## 7. 实施步骤（建议顺序，每步都可独立验收）

1. **抽 composable**：`useClassGroups` 生成 `ClassSummary[]`，先在 L1 只读展示，不改任何现有逻辑（可先加一个隐藏入口验证数字对不对）。
2. **加 L1 层**：`ClassOverview.vue` 接入 `StudentsPage`，默认展示班级卡；点击进入 L2 时暂时复用现有桌面网格（即先把「班级过滤」串起来）。
3. **加分层开关 + 分层视图**：`LayerToggle` + `LayeredRoster`，把移动端 `tm-tri` 提为公共组件；桌面与移动共用一套分层渲染。
4. **移动端链路打通**：`rosterSubPage` → `classSubPage`，补 `useBackLayer` 一层。
5. **URL 与深链**：`?class=` 双向同步；`?student=` 兼容。
6. **回归**：详情 7 Tab、预警跳转、家校反馈、导入导出、下拉刷新、keepAlive 刷新。

预估改动量：新增约 600–800 行（含样式），`StudentsPage.vue` 净减少约 150–250 行（桌面网格与移动 tabs 拆出）。

---

## 8. 风险与对策

| 风险 | 说明 | 对策 |
|---|---|---|
| 「重点关注」口径与教师直觉不一致 | 教师可能认为「中度也该算」或「已闭环不算」 | 卡片 tooltip 直接写口径文案；口径放前端常量一处，方便调整 |
| 学生跨班导致重复计数 | 本模型一个学生只有一个 `class_group_id`，不会重复 | 无风险；若未来支持多班需重算 |
| 迁移到后端聚合 | 班级多时前端全量计算有压力 | 预留后端 `GET /teacher/class-summary` 的位置，前端 composable 内部留替换点 |
| 移动端返回键层级混乱 | 三层页面 | 严格按 `useBackLayer` 后进先出注册，L3 先于 L2 于 L1 |
| 这次改动与「工作台」定位冲突 | 页头标题现在是「工作台」 | L1 标题统一为「学生名单」，避免老师以为进了另一个模块 |

---

## 9. 待确认问题（需产品/老师拍板）

1. 「重点关注」是否包含**中度**？（本方案默认包含：severe + moderate）
2. **已闭环**的 severe/moderate 是否仍计入重点关注？（本方案建议降档但保留标记）
3. 分层视图是否需要「只看重点关注」的一键筛选？（本方案：头部提示条可点击，等价于筛选）
4. 是否保留「无预警但低分 / 长期无互动」的第四条分档？（本期不做）
5. L1 默认排序：按「重点关注人数倒序」还是「班级名」？（本方案默认按重点关注倒序，让有事的班浮到最上面）
