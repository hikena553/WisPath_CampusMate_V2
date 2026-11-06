import { App as CapacitorApp } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'
import type { Router } from 'vue-router'

/** 一级页面（App 内的「首页」）：这些页面上按返回 = 退到后台，而不是直接杀进程 */
const ROOT_PATHS = new Set(['/', '/login', '/welcome', '/download', '/student', '/teacher', '/admin'])

/**
 * 适配 Android 物理返回键 / 全面屏侧滑返回手势（仅 App 壳内生效）。
 *
 * 退栈顺序（一级一级退）：
 * 1) 打开着页内浮层（聊天会话、资讯详情、个人中心子面板…）：
 *    useBackLayer 已在历史顶部压了同地址哨兵，history.back() 先退哨兵，
 *    由 useBackLayer 收掉最上面那一层；
 * 2) 普通子页面：history.back() 交给 vue-router 回退一页；
 * 3) 已在一级页面：最小化到后台，不退出、不丢登录态；
 * 4) 兜底：深链直接落到子页、历史为空（canGoBack=false）时，回一级页面。
 *
 * 兼容：同时监听 Capacitor 的 backButton 与 document 上的 backbutton 事件
 * （插件两者都会触发），300ms 去重，避免个别 ROM 上一次退两级。
 */
export function setupAndroidBack(router: Router): void {
  if (!Capacitor.isNativePlatform()) return

  let lastHandledAt = 0

  function handleBack(event?: unknown): void {
    const now = Date.now()
    if (now - lastHandledAt < 300) return
    lastHandledAt = now

    const path = router.currentRoute.value.path.replace(/\/+$/, '') || '/'
    if (ROOT_PATHS.has(path)) {
      void CapacitorApp.minimizeApp()
      return
    }

    // 历史里没有可退记录（例如从外部链接直接打开子页）→ 回一级页面
    const canGoBack =
      typeof (event as { canGoBack?: boolean } | undefined)?.canGoBack === 'boolean'
        ? (event as { canGoBack: boolean }).canGoBack
        : undefined
    if (canGoBack === false) {
      void router.replace('/')
      return
    }

    window.history.back()
  }

  void CapacitorApp.addListener('backButton', handleBack)
  // 部分 ROM / 旧版插件只发 document 事件，这里做一层兜底
  document.addEventListener('backbutton' as unknown as keyof DocumentEventMap, handleBack as EventListener)
}
