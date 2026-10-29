# 落地映射 — 从原型到 `frontend/` 真实组件（v2）

本文件回答一个问题：**这个原型怎么落到现有 Vue3 代码里，且不破坏已有约定。**

> **执行状态：主页驾驶舱已落地（2026-10-29）。**
> 实际改动：`components/growth/GrowthDashboard.vue`（模板+样式整体改造）、
> `views/student/SchedulePage.vue`（页面底色）、`components/layout/StudentLayout.vue`（根背景 + tabbar 变量）、
> `components/responsive/MobileTabBar.vue`（选中色改为变量）。
> 与本文原计划的差异：**没有拆成 TodayHead/QuickCells 等多个子组件**，而是在 `GrowthDashboard.vue` 内就地改，
> 因为该文件已有 700+ 行的卡片配置逻辑（排序/显隐/FLIP 动画），拆分会牵动 `ref` 与本地存储契约，收益不抵风险。

> v2 差异提示：主页 Hero 已从「渐变大卡 + 圆环」改为 `.gd-today`（一句话 + 4 数字，原型里叫 `.today-head`）；
> 功能入口从 3×3 彩色图标网格改为 `.gd-cell-list` 两列 Cell（原型里叫 `.fn-list`）。

---

> ## 执行状态 v3：三个学业子页已落地（2026-10-29）
>
> v2 把主页做成了「中性灰 + 单色」的克制风格，用户反馈 **「不要这种全黑白」**，同时提出另外三条硬约束：
> 子页 Head 必须**三页等高且吸顶**、子页版式**重新设计**、图表**不许大面积独占一屏**。
> v3 因此不再走「纯去色」路线，改为 **中性底 + 每页一个低饱和模块识别色**：卡片仍是白底，颜色只出现在
> 图标、进度条、迷你图表、热力格这些「信息载体」上。
>
> 实际改动集中在 **`views/student/SchedulePage.vue` 单文件**（三页都在这里面，`activeTab` 切换），
> `GrowthDashboard.vue` 未动。

### 页面 → 参考软件对照

| 落点 | 参考对象 | 抄的是哪一点 |
|---|---|---|
| 子页顶栏 Head（三页共用） | **Apple Health** 分类详情页 + **Keep 9.0** 二级页 | 48px 定高、返回键独占左侧 48px 槽位、标题严格几何居中；滚动后才浮出底部分隔线 |
| 顶栏副标题 | **Apple Health** | 标题下一行 11px 灰色上下文（「第 6 周」/「4 个学期」/「成长档案」）；滚动时收起，给内容让位 |
| 成长页总览 | **Keep 9.0「数据概览」** + **Apple Health 摘要** | 分值用 60px 小环形而非 280px 大图，右侧紧跟一句人话结论 + 主行动按钮；下方 4×2 数字网格吸收 8 项统计 |
| 五维能力 | **Keep 上周运动周报** | 小雷达与文字数值**并排**：雷达只负责形状直觉，精确读数交给右侧五条横条，不重复占两屏 |
| 记录构成柱状 | **Apple Health 噪音模块** + **TickTick 习惯统计** | 高度 56px 的迷你柱，`grid` 四边归零 + `containLabel`，数值标在柱顶，去掉坐标轴与网格线 |
| 坚持情况热力 | **Duolingo 连续记录日历** | 8 列 × 7 行按自然周分列，四级暖度，未来日期不渲染灰块（避免「一片空」的挫败感）；连续天数单独用文字表达 |
| 成长历程折线 | **Keep 数据趋势** | 单序列总量折线 + 104px 高，5 条分类型序列合并（原图例溢出卡外） |
| 成绩页指标 | **Apple Health 分类浏览** | 4 项指标塞进**同一张白卡**用 `overflow:hidden` 做等分，靠 1px 竖线分隔，而不是 4 张彩色大卡 |
| 成绩页图表 | **Keep 全部数据** | 青绿单色系，分数段用**同色深浅梯度**表达有序关系，不用彩虹色 |
| 课程表 | **TickTick 日历视图** | 移动端只渲染到「本周最后一节课结束的节次」且最少 8 节，一屏放下不用滚；今天列浅赭橙底 |
| 配色 | **Apple Health** | 中性灰底 `#f5f6f7` + 白卡 `#fff`，强调色只出现在信息载体上 |

### 模块识别色（每页一个，互不串色）

| 页面 | 主色 | 浅底 | 深字 | 用途 |
|---|---|---|---|---|
| 课程表 | `#b45309` 赭橙 | `#fdf3e4` | `#8a3f07` | 今天列底色、今日课程描边 |
| 成绩分析 | `#0f7a58` 青绿 | `#e8f5ef` | `#0a5b41` | GPA 折线、类型柱、分数段梯度 |
| 成长轨迹 | `#1a4fd6` 靛蓝 | `#edf2fd` | `#143da3` | 分值环、雷达、迷你柱、低分警示 |
| 状态色 | 警示 `#c2410c` / 达成 `#15803d` | — | — | 最低维度、连续天数 |

### 图表压缩对照（改前 → 改后）

| 图表 | v2 | v3 | 手法 |
|---|---|---|---|
| 分值环 | 92px SVG 渐变大环 | 60px 细环（`stroke-width: 5`）+ 数字居中 | 与「状态良好」文案横向并排 |
| 雷达 | 独占 280px 高整屏 | 96×96，`radius: '72%'`、`axisName.show:false`、`splitArea.show:false` | 与五维横条左右分栏 |
| 记录构成 | 220px 柱状 + 图例 | 56px 迷你柱，`grid` 全 0 | 数值标柱顶，轴全隐 |
| 成长历程 | 230px 五序列折线 + 图例 | 110px 单序列折线 | 合并总量、去 legend |
| 成绩页三图 | 148px + 完整坐标轴 | 118px，y 轴刻度/网格线全隐，数值标图上 | 读者看形状，精确值在点上 |
| 分数分布饼 | 有 | **删除** | 分布已由柱状承担，饼图冗余 |

> **折线 y 轴必须自适应**：绩点集中在 3.0–3.8，写死 `min:0, max:4` 会把趋势压成直线。
> 现按 `pad = max(0.12, 极差*0.35)` 取 `yMin/yMax`，起伏可见且不放大噪声。压缩图表时最容易连带删掉自适应区间。

### 版面坑（改这里之前先看）

- **子页 Head 必须 `position: fixed`，不能用 sticky。** sticky 只「参与流的固定」，
  不会在自身底部额外裁剪内容 —— 内容会从顶栏背面滑过，轴标签贴着标题下方露出来。
  正确组合：顶栏 `fixed` + `z-index: 100`（高于同级的滚动内容）+ 滚动容器 `.content-row` 用 `top: 52px` 自己让出高度。
  另外 sticky 贴的是父容器 **padding 内边界**，`.content-row` 一旦有 `padding-top` 顶栏就会悬空。
- **fixed 元素的 `z-index` 只在最近堆叠上下文内比较。** `.content-row` 是 `z-index:1500` 的 fixed 容器，
  顶栏写 `20` 会被同层的内容盖住（`elementsFromPoint` 首位不是顶栏），必须抬到 `100`。
- 移动端隐藏了 `.panel-divider`，两张图之间**没有间隙**；`.panel + .panel { margin-top }` 在 flex 列布局里**无效**，
  间距必须写在父容器 `.grades-view .analytics-body.duo { gap: 14px }`。回归脚本已加断言（实测 14px）。
- `SchedulePage.vue` 单文件 2900+ 行、有多段 `@media`。**改任何 CSS 前先 `grep` 同名选择器**，
  后定义的 `@media` 会静默覆盖前面的规则（成绩卡 `repeat(4,1fr)` 就这样失效过）。

### 无障碍

- `--sp-ink-3` 由 `#8b939e`(3.10:1) 改为 `#6b737c`（白卡 4.81:1 / 浅底 4.44:1），正文全部达标 AA。
- `--sp-ink-quiet #a8aeb6` 只有 2.24:1，**降级为纯装饰色**，代码里已注明禁止承载文字（现仅用于热力格 today 描边与箭头图标）。
- 返回按钮 40×40、`aria-label="返回驾驶舱"`、`:focus-visible` outline 2px。
- 热力网格 `role="img"` + 动态 `aria-label`（「近 8 周共 N 条记录，M 天有记录」），每格 `title`，未来格不发音。

### 未做 / 下一轮

- 子页 Head **仍留在 `SchedulePage.vue` 内**，三页共用一份 `.subpage-bar` 样式；若后续子页移动到独立路由文件，需抽成 `components/layout/SubPageBar.vue`。
- AI 详情页、待办页仍是驾驶舱内的抽屉/弹层，未按本文第 1 节拆成 `AiInsightsPage.vue` / `TodoPage.vue`。
- 深色模式未覆盖（token 已集中在 `.schedule-page` 一处，后续加一段 `@media (prefers-color-scheme: dark)` 覆盖即可）。

对应原型：`prototypes/student-app-redesign/`（pure-static 评审版）
目标代码：`frontend/src/views/student/SchedulePage.vue` + `frontend/src/components/growth/`

---

## 1. 组件拆分（对应原型各区块）

| 原型区块 | 落点文件 | 说明 |
|---|---|---|
| 主页 5 区块容器 | `components/growth/GrowthDashboard.vue`（重写） | 保留 `defineExpose({ refresh })` 契约，父级 `refreshAll()` 不用改 |
| ① 今天（无标题区） | `growth/dashboard/TodayHead.vue`（新） | 日期行 + 一句话 + 4 数字。**替代原 DashboardHero**，无渐变无圆环 |
| ② 今天 | `growth/dashboard/TodaySchedule.vue`（新） | 下一节摘要 + 竖向时间条，`emit('open','schedule')` |
| ③ 要交的 | `growth/dashboard/TodayTasks.vue`（新） | 最多 3 条 + 进度条，`emit('open','tasks')` |
| ④ 成长 | `growth/dashboard/GrowthBrief.vue`（新） | 五维灰条（仅最低项赭红）+ AI 洞察引用块，`emit('open','growth' / 'ai')` |
| ⑤ 更多 | `growth/dashboard/QuickCells.vue`（新，**替换** QuickGrid） | 两列单色 Cell，非图标网格 |
| 子页 A 课程表 | `SchedulePage.vue` 内既有 `activeTab==='schedule'` | 只换样式，逻辑不动 |
| 子页 B AI 详情 | `views/student/growth/AiInsightsPage.vue`（新，路由或页内子页） | 承接原 `ProactiveFeed` 全量列表 + 刷新 |
| 子页 C 待办 | `views/student/growth/TodoPage.vue`（新） | `getToday()` 数据，勾选写回 |
| 子页 D 成长详情 | `SchedulePage.vue` 内既有 `activeTab==='growth'` | 升级为雷达 + 维度卡 |
| 子页 E 成绩分析 | `SchedulePage.vue` 内既有 `activeTab==='grades'` | 只换样式 |

> `KpiStat.vue` 在 v2 中不再需要——4 项 KPI 全部吸收进 `TodayHead` 的 `.metrics` 四等分数字，确认无其他引用后可删除。
> `CardToolbar.vue` 保留，改为顶部 appbar 右上「···」触发底部 ActionSheet。
> **`QuickGrid.vue` 必须删除**，其 6 个彩色圆角方块正是 v2 评审否决的「工具箱式入口」。

---

## 2. 与既有约束的对接（逐条）

### 2.1 子页动画（`styles/animations.css` 的 `.subpage`）

原型用 `.layer` 自己实现了滑入/滑出。落地时**复用全局 `.subpage` 类，不要新建动画**：

```vue
<Transition name="subpage" :duration="320">
  <div v-if="activeTab !== 'home'" class="subpage">…</div>
</Transition>
```

硬约束（历史踩坑，已在 `animations.css` 注释中记录）：
- `.subpage-leave-active` **只能**加 `pointer-events: none`；
- **禁止**给离场元素加 `position / inset / overflow`，否则工作台 fixed 被覆盖、驾驶舱高度塌陷 + 滚动重置 + 12~16px 错位。

原型里 `.layer.anim-out` 的写法就是这条规则的实现示例。

### 2.2 子页态 `position: fixed`

`SchedulePage.vue` 现在的写法：

```css
@media (max-width: 767px) {
  .schedule-page .content-row { position: fixed; inset: 0; z-index: 1500; }
}
```

**必须保持常驻、不能挂在 `.has-subpage` 条件下**，否则返回动画第一帧会从整屏跳回流内。
原型中主内容 `#scr-home` 始终占据 `inset: 0`、只有子页层滑动，是同一思路。

### 2.3 数据缓存首帧（`utils/studentDataCache.ts`）

- `null = 未加载` → 渲染骨架；`空数组 = 合法空态` → 渲染空态。
- 骨架尺寸必须与真实内容**逐行对齐**，否则会复现历史的「卡片高度跳变」。
  原型里的 `.sk-h1 / .sk-line` 已按 20px / 12px 行高设定，落地时照抄尺寸。
- 加载失败**不回写 null**（保持上一次数据），只提示错误。

### 2.4 下拉刷新（`usePullRefresh`）

原型为演示自写了轻量实现。落地仍用 `usePullRefresh(refreshAll, { enabled: () => isMobile.value })`，
绑定到**真正的滚动容器** `.content-row`，并保留 `overscroll-behavior-y: contain`。

### 2.5 设计令牌

原型 `:root` 的变量名与 `frontend/src/styles/teacher-ui.css` 的 `--tui-*` 一一对应，落地时：

| 原型（v2） | 产品 | 备注 |
|---|---|---|
| `--accent` `#1a4fd6` | `--tui-brand`（需改值或新增 `--stu-accent`） | **唯一强调色**，仅用于「进行中」标签与选中指示线 |
| `--alert` `#c2410c` | `--stu-alert`（新增） | 截止 / 逾期 / 低分 |
| `--ok` `#15803d` | `--tui-success` | GPA 上升 |
| `--bg` / `--surface` / `--surface-muted` | `--tui-bg` / `--tui-surface` / 新增 | 三层中性面 |
| `--text` / `--text-2` / `--text-3` / `--text-quiet` | `--tui-text` / `--tui-text-secondary` / `--tui-text-tertiary` / 新增 | 四级文字 |
| `--line` / `--line-strong` / `--hairline` | `--tui-border` / `--tui-border-strong` / `--tui-hairline` | |
| `--r` / `--r-lg` | `--tui-radius` / `--tui-radius-lg` | |
| `--bar-1…5` | 新增 `--stu-bar-*` | **仅**课表 2px 竖条，禁止用于填充 |

**v2 必须明确删除的旧变量**：`--brand-strong / --brand-soft / --warn / --danger / --violet / --cyan`
以及它们的 soft 变体。v1 的「6 语义色并存」正是大面积蓝色的根源。

**禁止**在组件内继续写 `#409eff / #f56c6c / #e6a23c`。
Element Plus 的消息/弹窗如需统一，在 `StudentLayout` 外层加一次主题变量覆盖即可，不必逐个改。

### 2.6 图标

原型 122 枚图标来自 Lucide `lucide-static`（ISC），内联在 `index.html` 的 `<svg id="sprite">`。
落地时不建议内联进 Vue（体积/可维护性），改为：

```bash
npm i lucide-vue-next
```

```vue
<script setup lang="ts">
import { Database, ChevronRight, TriangleAlert } from 'lucide-vue-next'
</script>
<template>
  <ChevronRight :size="14" :stroke-width="2" aria-hidden="true" />
</template>
```

v2 改为 **`stroke-width: 1.75`**（更精致的线性重量）、`currentColor`、尺寸只取 16 / 17 / 20 / 22。

### 2.7 底部导航（`MobileTabBar.vue`）

v2 调整：高度 `56`（`--tabbar-h`）、未选中色 `--text-quiet`、选中色 **`--text` 近黑（不再是蓝色）** + 顶部 2px 短线 `.tab.active::after`；
居中吉祥物未选中时 `filter: grayscale(1); opacity: .5`。
`data-tab` 顺序、图标、路由**一律不动**（对应原型注释「冻结导航」）。

---

## 3. 功能等价核对（上线前逐条打勾）

| # | 原能力 | v2 落地位置 | 状态 |
|---|---|---|---|
| 1 | 问候语 | 顶部 appbar 标题（`homeTitle`） | ☐ |
| 2 | 下一节课卡（点击进课程表） | TodaySchedule `.next-row` | ☐ |
| 3 | 成长指数环 | **已取消**，改为 TodayHead `.metrics` 首格「综合评分」 | ☐ |
| 4 | KPI 今日课程 | TodayHead 第 1 句（「今天有 2 节课」）+ 区块标题 `2 节课` | ☐ |
| 5 | KPI 待办 | TodayHead 第 2 句 + `.metrics` 第 3 格 | ☐ |
| 6 | KPI 综合评分 | TodayHead `.metrics` 第 1 格 `#mScore` | ☐ |
| 7 | KPI 成长记录 | TodayHead `.metrics` 第 4 格 `#mRecord` | ☐ |
| 8 | AI 动作列表 | GrowthBrief 引用块首条 + AiInsightsPage 全量 | ☐ |
| 9 | AI LLM 洞察 | GrowthBrief `.insight-block` 截断 2 行 + 详情页全文 | ☐ |
| 10 | AI 刷新 | AiInsightsPage `#btnAiRefresh` | ☐ |
| 11 | AI 空态 | 两处各自空态（`emptyState`） | ☐ |
| 12 | 五维进度条 | GrowthBrief `.dim-row`（灰条 + 低分赭红）+ 成长详情 `.dim-detail` | ☐ |
| 13 | 五维折叠 | 成长详情改为展开卡（无折叠需求） | ☐ |
| 14 | 快捷空间 6 入口 | **QuickCells**（两列 Cell，非图标网格） | ☐ |
| 15 | 卡片排序 | appbar「···」→ ActionSheet，操作 `cm.dashboard.cards.v2.<uid>` 的 `order` | ☐ |
| 16 | 卡片显隐 | 同上，操作 `hidden` | ☐ |
| 17 | 下拉刷新 | usePullRefresh | ☐ |
| 18 | 课程表子页 | `activeTab==='schedule'` | ☐ |
| 19 | 成绩分析子页 | `activeTab==='grades'` | ☐ |
| 20 | 成长轨迹子页 | `activeTab==='growth'` | ☐ |
| 21 | 学习计划 / 作品集 / 成长档案 / 情绪树洞 | 路由跳转 | ☐ |

> **勾选联动必须三处同步**：原型踩过一次坑——`refreshTasks()` 只重渲待办列表，
> 导致勾完后「待办未完成 5 项」和「今天有 2 节课，2 项作业今晚截止」都不更新。
> 落地时 `todayHead` 的文案与 `metrics` 必须订阅同一份 `todayTasks` computed，不要各自缓存。

---

## 4. 建议实施顺序

1. **令牌与图标先行**：引入 `lucide-vue-next`，确认 `--tui-*` 覆盖无误（不改任何业务）。
2. **拆 `GrowthDashboard.vue`**：先原地拆成 5 个子组件，样式沿用旧的，跑通再说。
3. **逐个换皮**：TodayHead → TodaySchedule → TodayTasks → GrowthBrief → QuickCells，每步截图对比。
4. **新增两个子页**（AI 详情、待办），复用 `.subpage` 动画。
5. **升级成长详情 / 成绩分析**版式。
6. **删除 `KpiStat.vue` 与 `QuickGrid.vue`**；全局搜 `#409eff` / `#f56c6c` / `--brand-soft` / `--violet` 清零。
7. 跑一遍 320 / 390 / 768 三档 + 键盘 Tab + `prefers-reduced-motion`。

> 不做的事：不动后端接口、不动路由结构（除新增两个可选子页）、不动 `studentDataCache` 契约、
> 不动底部 5 页签。

---

> ## 执行状态 v3.1：技能卡压缩 + 请假服务子页 + 改名（2026-10-29）

### 请假服务子页（新增第 4 个子页）

工作台三个申请（请假/证明/项目）融合为 `activeTab === 'service'` 子页，进驾驶舱入口列表第三位。
- **模块识别色**：葡萄紫 `#6d28d9` / 浅底 `#f3effd` / 深字 `#553c9a`（白底对比 6.6:1，AA 达标）
- **布局**：分段控制（3 等分 seg）+ 白卡表单 + 通栏 44px 提交按钮，延续 v3 子页设计语言
- **实现要点**：三表单 `v-show` 常驻（保状态）；请假走 `createLeave`，证明/项目走 `createTicket`；
  请假类型映射 课假→other / 公假→competition / 宿假·事假→personal / 病假→sick，reason 前缀 `[类型]`
- **模板约束**：service 用独立 `v-if`（不能挂 schedule/grades/growth 的 v-else-if 链，中间隔着
  内层 Transition 边界与 formulaDialog el-dialog，链会断）

### 技能与兴趣卡压缩（成长页）

预设 26 标签 + 自定义输入移入 el-dialog，卡片只留已选 chips，高度 ~400px → 97px。
坑：紧凑 padding 需 3 类选择器 `.skills-card .skills-body.skills-body-compact` 才能压过旧 `!important` 规则。

### 改名对照表

| 位置 | 旧 | 新 |
|---|---|---|
| tabbar / 桌面导航 / 欢迎页 / 学习计划 hero | 驾驶舱 | 学业中心 |
| 子页 Head 标题映射 | —（3 项） | 新增 `service: '请假服务'`，副标题「请假 · 证明 · 项目」 |

### 测试注意（v-show 带来的）

Playwright 选择器必须 `:visible` 过滤（`.sv-card:visible .sv-submit`）；date-picker 用
`.el-date-editor input` fill+Enter；提交后 ElMessage toast 会挡顶部检测点，等 ~2.6s。

**回归脚本**：`frontend/_verify-v31.cjs`（全流程）、`frontend/_bar-verify.cjs`（三页吸顶）。
`vue-tsc --noEmit` 0 错误。主页版式（v2 白卡+识别色）已符合子页设计语言，本轮未整体重做。
