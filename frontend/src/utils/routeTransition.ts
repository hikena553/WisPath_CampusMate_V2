import { ref } from 'vue'

/**
 * 下一个路由切换用的过渡名（布局层绑到 `<Transition :name>`）。
 *
 * 提到模块级是因为存在「谁先知道」的时序问题：页面点击返回时已经把退场方式定下来了，
 * 但布局层靠 `watch(route.path)` 才知道路由变了 —— 那时 Vue 可能已经开始 patch，
 * `<Transition>` 的 name 更新赶不上离场类名的挂载，离场页会用上一次的过渡名。
 * 由发起方在导航**之前**写一次，name 在导航发生时已经是新值，就不必赌调度顺序。
 *
 * 每次导航布局层都会重设，所以残留值不会带到下一条无关的路由里。
 */
export const pageTransition = ref('')

export function setPageTransition(name: string): void {
  pageTransition.value = name
}

/* ============================================================================
   路由过渡配置（全站唯一配置点）
   ============================================================================
   只有三种过渡，语义由「页面层级」决定，不再按路径逐条 if 判断：

   | 场景                       | 过渡名               | 观感                       |
   |----------------------------|----------------------|----------------------------|
   | 下钻（一级页 → 子页）       | route-subpage        | 子页从右滑入盖住旧页，旧页不动 |
   | 返回（子页 → 一级页）       | route-subpage-back   | 子页原路向右滑出，一级页露出来 |
   | 平级（页签之间 / 同级子页） | page-card            | 卡片浮起；移动端退化为纯淡入   |

   为什么按「深度」而不是「谁是谁的子路由」：路由表里消息搜索页与消息页是兄弟路由
   （同一层 children），但交互上是「子页」。层级表写在下面，谁是谁的子页一眼可见，
   加新页面时只改一处。

   唯一的例外是学业中心：/student/plan、/student/growth 等旧路由都 redirect 到
   /student/schedule?tab=xxx，路径本身是一级页签，只有 query.tab 能说明「这趟是
   下钻到功能子页」。resolvePageTransition 的第三个参数就是为此存在（见下方注释）。

   几何前提（见 animations.css 路由段）：
   - 移动端：进入/离场的子页自身是 fixed 整屏覆盖层（z-index 1500），离开的一级页
     留在流内也不会被分摊高度 —— 消息搜索 / 添加朋友两页为此在 ≤767px 里声明了
     position:fixed; inset:0（其余「快捷空间」子页本来就是这样）。
   - 桌面端：路由页是流内布局，离场页必须脱流（absolute + inset:0），否则两页在
     .main-area（flex column）里各分一半高度。
   ============================================================================ */

/** 页面层级：0 = 一级页（底部导航页签 / 模块落地页），1 = 二级子页；缺省按 0 */
export const ROUTE_NAV_DEPTH: Readonly<Record<string, number>> = {
  // ---- 一级：底部导航五个页签 + 常驻落地页 ----
  '/student': 0,
  '/student/agent': 0,
  '/student/campus': 0,
  '/student/schedule': 0,
  '/student/messages': 0,
  // 消息页「好友」视图是同一个组件的另一个视图（同一地址族），切过去不算下钻
  '/student/messages/friends': 0,
  '/student/profile': 0,

  // ---- 二级：校园资讯 ----
  // 搜索子页（CampusSearchPage）/ 详情（ArticleDetailPage）/ 阅读器（ArticleReader）
  // 都是页内挂载的全屏覆盖层，不占路由，因此不在这张表里 ——
  // 它们的动画由 `.subpage`（animations.css）负责，与下面两条路由级子页是同一套观感。

  // ---- 二级：消息 ----
  '/student/messages/search': 1, // 消息搜索子页（页头放大镜进入）
  '/student/messages/add': 1, // 添加朋友 / 建群（「＋」面板与通讯录空态进入）

  // ---- 二级：快捷空间 ----
  '/student/portfolio': 1, // 我的作品集
  '/student/files': 1, // 我的文件（聊天文件汇总，原工作台 files 子页）
  '/student/lost-found': 1, // 失物招领（原工作台宫格业务）
}

export type PageTransitionName = 'route-subpage' | 'route-subpage-back' | 'page-card'

/** 取路径的层级；未配置的一律按一级页处理（不会误触发横滑） */
export function navDepthOf(path: string): number {
  return ROUTE_NAV_DEPTH[path] ?? 0
}

/**
 * 学业中心「子页」的 tab 键（与 SchedulePage.vue 的 tabKeys 保持一致）。
 * /student/plan、/student/growth、/student/grade … 这些旧路由都是 redirect 到
 * /student/schedule?tab=xxx，从个人中心 / 驾驶舱点进去时语义是**下钻到子页**，
 * 但目标路径 /student/schedule 本身又是一级页（底部页签）——只看 path 分不出层级，
 * 于是过去一律判成平级 page-card（移动端纯淡入），与「编辑资料 / 我的作品集」等
 * 下层让位式子页动画不一致。这里用 query.tab 补上层级信息。
 */
const SCHEDULE_SUB_TABS: ReadonlySet<string> = new Set([
  'schedule', 'grades', 'growth', 'service', 'plan', 'study', 'ai',
])

/** 是否「学业中心的某个功能子页」（home / 无 tab 都是一级驾驶舱主页） */
export function isScheduleSubTab(path: string, tab?: string): boolean {
  return path === '/student/schedule' && !!tab && SCHEDULE_SUB_TABS.has(tab)
}

export interface PageTransitionContext {
  /** 目标地址的 ?tab=（redirect 之后的地址上就有） */
  toTab?: string
  /** 来源地址的 ?tab=（router.back() 时靠它认出「正在从子页返回」） */
  fromTab?: string
}

/**
 * 决定这次路由切换播哪一种过渡。
 * 注意 `from` 可能是 `/student/messages?chat=...` 这类带 query 的地址 —— 调用方传
 * `route.path`（不含 query），层级相关的 query 走 ctx，保持本函数无路由库依赖。
 */
export function resolvePageTransition(
  to: string,
  from: string,
  ctx: PageTransitionContext = {},
): PageTransitionName {
  // 同一路由内换 tab（plan → grades）组件不重建，Transition 本就不会触发；
  // 明确判为平级，避免误报下钻。
  if (to === from) return 'page-card'

  const toIsSubTab = isScheduleSubTab(to, ctx.toTab)
  const fromIsSubTab = isScheduleSubTab(from, ctx.fromTab)
  if (toIsSubTab && !fromIsSubTab) return 'route-subpage'
  if (fromIsSubTab && !toIsSubTab) return 'route-subpage-back'

  const toDepth = navDepthOf(to)
  const fromDepth = navDepthOf(from)
  if (toDepth > fromDepth) return 'route-subpage'
  if (toDepth < fromDepth) return 'route-subpage-back'
  return 'page-card'
}
