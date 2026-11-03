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
  '/student/workbench': 0,

  // ---- 二级：校园资讯 ----
  // 搜索子页（CampusSearchPage）/ 详情（ArticleDetailPage）/ 阅读器（ArticleReader）
  // 都是页内挂载的全屏覆盖层，不占路由，因此不在这张表里 ——
  // 它们的动画由 `.subpage`（animations.css）负责，与下面两条路由级子页是同一套观感。

  // ---- 二级：消息 ----
  '/student/messages/search': 1, // 消息搜索子页（页头放大镜进入）
  '/student/messages/add': 1, // 添加朋友 / 建群（「＋」面板与通讯录空态进入）

  // ---- 二级：快捷空间 ----
  '/student/portfolio': 1, // 我的作品集
}

export type PageTransitionName = 'route-subpage' | 'route-subpage-back' | 'page-card'

/** 取路径的层级；未配置的一律按一级页处理（不会误触发横滑） */
export function navDepthOf(path: string): number {
  return ROUTE_NAV_DEPTH[path] ?? 0
}

/**
 * 决定这次路由切换播哪一种过渡。
 * 注意 `from` 可能是 `/student/messages?chat=...` 这类带 query 的地址 —— 调用方传
 * `route.path`（不含 query），这里不做解析，保持纯函数。
 */
export function resolvePageTransition(to: string, from: string): PageTransitionName {
  const toDepth = navDepthOf(to)
  const fromDepth = navDepthOf(from)
  if (toDepth > fromDepth) return 'route-subpage'
  if (toDepth < fromDepth) return 'route-subpage-back'
  return 'page-card'
}
