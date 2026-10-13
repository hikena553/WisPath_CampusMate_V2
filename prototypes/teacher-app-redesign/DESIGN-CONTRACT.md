# Design Contract — 教师端「常用功能」子页面 & 弹窗重构

## 0. 意图
iterate（在既有原型 `prototypes/teacher-app-redesign/` 内就地重构）。
目标：教师端「常用功能 / 全部功能」下钻的 **全部 9 个功能子页面** 与 **对应弹窗**，重做版式与配色，
让每个功能拥有「产品特色」，并统一调整页面/组件尺寸与图标色调。
技术栈：vanilla HTML/CSS/JS · pure-static（保持 file:// 双击可开、零外部依赖）。

## 1. 采用的开源成熟体系（"采用开源成熟的项目"）
- **Lucide**（ISC）图标库 —— 全部图标改为 Lucide 官方 `lucide-static` sprite 抽取的真实 path，内联 SVG，122 枚。
- **Untitled UI**（开源设计系统）色彩/圆角/灰阶令牌 —— 与真实产品 `frontend/src/styles/teacher-ui.css` 同源。
- **Ant Design Mobile** 交互范式 —— Popup / ActionSheet（底部弹窗）、NavBar、Steps、Timeline、Progress、Badge、Empty。

## 2. 风格与美学
- style: minimal-light + business-international（移动工作台）
- aesthetic: 「克制的移动工作台」——高信息密度、清晰语义色阶、每模块专属签名色与专属版式；不做居中式通用模板。
- tone: calm / restrained / high information density
- bg-texture: 顶栏毛玻璃 + 极浅径向渐变（不做纯色平铺）

## 3. 设计令牌（调整后）
color.primary #2563eb / hover #1d4ed8 / soft #eff4ff
color.bg #f2f3f5  surface #ffffff  sunken #eceef1  muted #f7f8fa
color.border #f0f1f3 / strong #e5e7eb / hairline rgba(15,17,21,.06)
color.text #0f1115 / sub #4b5563 / tertiary #6b7280 / quiet #9ca3af
semantic: success #079455 / warn #b54708 / danger #d92d20 / violet #6941c6 / cyan #0891b2
radius: xs 10 / sm 12 / 14 / lg 18 / xl 22
shadow: 1 0 1px 2px .04 / 2 0 2px 10px .06 / 3 0 10px 32px .14
spacing: 4 基准 (4/8/12/16/20/24/32)
font: PingFang SC / HarmonyOS Sans SC / Microsoft YaHei（系统可用，离线）
mono: ui-monospace / SF Mono / Cascadia Mono
icon: lucide, size 16/18/20/22, stroke 2, currentColor

### 尺寸调整（本轮）
tabbar-h 56→58 ; appbar 52→54 ; appbar-title 16→17
nav-cell 72→78 ; nav-icon 46→52 (r14→16)
row min-h 58→62 ; row-icon 36→40 (r10→12)
kpi-ic 38→42 ; shortcut-ic 30→34 ; stat-num 21→22
btn min-h 42 ; btn-sm min-h 34

### 图标色调（本轮）
每枚图标块统一为「soft 底 + strong 前景 + 内描边 hairline + 极浅渐层」，
色只取 6 个签名色（brand/success/warn/danger/violet/cyan）+ quiet；
禁止 #409eff / #f56c6c 等 Element 默认散色。

## 4. 每模块签名版式 & 弹窗
| 模块 | 签名色 | 子页面特色版式 | 弹窗 |
|---|---|---|---|
| approval 审批 | warn | 待办优先顶条 + 审批票据卡（含审批流时间轴/附件/SLA）+ 底部审批条 | 审批处理弹窗（同意/驳回+理由+转办） |
| crisis 预警 | danger | 风险分布环 + SLA 倒计时条 + 等级色带卡片 + 处置步骤条 | 预警处置弹窗（Steps 流程 + 跟进记录） |
| announcement 公告 | brand | 触达率进度 + 公告卡（置顶/紧急角标）+ 已读统计 | 新建公告弹窗（多班级选择+优先级+定时） |
| portfolio 成长档案 | violet | 学生横向选择器 + 成长时间轴 + 徽章墙 | 新增档案弹窗（分类/时间/附件/可见范围） |
| survey 问卷互评 | cyan | 回收率环形进度卡 + 匿名标识 + 维度标签 | 新建问卷弹窗（题型+匿名开关+截止时间） |
| care 关怀中心 | warn | 关怀温度条 + 待回访提醒 + 三类记录时间轴 | 新增关怀记录弹窗（类型/对象/方式/内容/后续） |
| guardian 家校沟通 | cyan | 家长联系人卡（通话/短信/微信）+ 沟通台账时间轴 | 发起沟通弹窗（渠道+话术模板+留痕） |
| tasks 今日任务 | success | 完成度进度 + 今日/逾期/本周分段 + 可勾选清单 | 新建任务弹窗（优先级/截止/关联） |
| ai AI 洞察 | violet | AI 建议卡（置信度）+ 洞察指标 + 一键行动 | 生成洞察/周报弹窗 |

## 5. 弹窗体系（统一，Ant Design Mobile Popup 范式）
- `.sheet` 底部弹窗：顶部 20px 圆角 + 抓手条 + `.sheet-head` + `.sheet-body`(滚动) + `.sheet-foot`(常驻主按钮)
- 变体：`.sheet--tall`(88vh) / `.sheet--form`（表单行）/ chips 单选 / 选项列表 / 时间轴
- 遮罩 `.sheet-mask`；关闭：点遮罩 / 右上关闭
- 桌面（≥1024）弹窗改为居中卡片，共用同一套皮肤

## 6. App Shell + 冻结导航（不变）
底部 5 页签：首页 / 学生 / 绵小城 / 消息 / 个人中心（顺序、图标、data-tab 冻结）。
二级页统一 `.layer` overlay；导航不参与各功能页重写。

## 7. 图标清单（122，Lucide 真实名）
house users user users-round user-plus message-circle message-square bell clock calendar
layout-grid search plus x chevron-right chevron-left chevron-down chevron-up arrow-left
arrow-right arrow-up-right ellipsis settings phone video image camera file-text mic folder
map-pin volume-x log-out shield-alert triangle-alert circle-check circle-x circle-dot
circle-question-mark badge-check shield-check shield-plus info flag target activity
trending-up trending-down gauge zap timer hourglass flame percent clipboard-check
clipboard-list clipboard-pen send trash pencil square-pen eye lock download upload share-2
refresh-cw funnel sliders-horizontal paperclip file-plus external-link copy star thumbs-up
circle-plus check check-check rotate-ccw megaphone bell-ring award trophy medal graduation-cap
heart heart-pulse heart-handshake link chart-column chart-line chart-pie sparkles wand-sparkles
lightbulb brain school building book-open bookmark notebook-pen briefcase layers list-checks
list-ordered calendar-plus calendar-check calendar-days calendar-clock messages-square
message-square-plus phone-call phone-outgoing phone-incoming mail contact user-check rocket
face-slightly-smiling sun compass scale

## 8. Mock 约定
唯一数据源 `mock.js` → `DB.modules.<key>`；异步桩层 `api.js` `getModule(key)`；
业务文案真实（绵阳城市学院 · 信息工程学院 · 辅导员李静视角），列表 3~5 条覆盖长短文案与空态。