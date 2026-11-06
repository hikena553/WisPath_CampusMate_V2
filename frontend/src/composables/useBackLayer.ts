import { onBeforeUnmount, watch, type Ref } from 'vue'

/**
 * 移动端「页内浮层」的返回层级（一级一层）。
 *
 * 背景：校园资讯详情、聊天会话、个人中心子页等是页内浮层（v-if + 本地状态），
 * 不占路由。系统返回键 / 浏览器返回只认路由历史，于是一次返回会跨过整摞浮层，
 * 直接回到上一个一级页面（用户感受就是「一次退回最大的页面」）。
 *
 * 做法：只要有浮层打开，就在浏览器历史顶部压 **一条** 同地址哨兵记录。
 * 系统返回先退掉这条记录，由本模块把最上面那层收掉，再补一条新哨兵 ——
 * 一次只退一层。用页内返回箭头关闭最后一层时，同步把哨兵退掉，历史里不留死记录。
 *
 * 始终只维护一条哨兵（而不是每层一条）：打开/关闭多层时不会有
 * 「先 back 再 push」的同帧竞争，也不会在历史里堆积多条同地址记录。
 *
 * 只在移动端登记（调用方传 `isMobile && open`），桌面端维持原有浏览器行为。
 */

interface BackLayer {
  close: () => void
  /** 该层当前是否仍处于打开状态（close 可能只退内层，例如群设置 → 群聊） */
  isOpen: () => boolean
}

const layers: BackLayer[] = []

/** 历史顶部是否压着我们的哨兵记录 */
let sentinelActive = false
/** 哨兵所属地址：只有还停在同一地址，退掉它才是安全的 */
let sentinelUrl = ''
/** 由本模块自己发起的 history.back() 次数：对应的 popstate 要吞掉，不能误关下一层 */
let suppressPops = 0
let syncQueued = false
let listening = false

function currentUrl(): string {
  return window.location.pathname + window.location.search
}

/**
 * 历史顶部那一条还是我们的哨兵吗？
 * 路由 replace 会把 state 换回它自己的（__mian02Layer 标记随之消失），
 * 但 sentinelActive 这个布尔值不会知道 —— 只信标记，才不会在哨兵已经没了
 * 的时候还去 history.back()（那会退到上一个真实页面，用户就「跳级」了）。
 */
function sentinelPresent(): boolean {
  const state: unknown = window.history.state
  return (
    !!state && typeof state === 'object' && (state as Record<string, unknown>).__mian02Layer === true
  )
}

function pushSentinel() {
  const state = window.history.state
  window.history.pushState(
    { ...(state && typeof state === 'object' ? state : {}), __mian02Layer: true },
    '',
    window.location.href,
  )
  sentinelActive = true
  sentinelUrl = currentUrl()
}

/**
 * 把「层数 / 哨兵」对齐。放进微任务里合并执行：
 * 同一帧里「关一层、开一层」（如搜索页 → 会话）时层数不变，就不必动历史。
 */
/**
 * 路由切换后重新对齐哨兵：router.replace 会用路由自己的 state 覆盖当前历史条目的 state，
 * 上一轮压进去的 __mian02Layer 标记随之消失 —— 哨兵名存实亡，返回键就会「跳级」到上一个页面。
 * 这里只在「有浮层但哨兵标记丢了」时补一条，不主动退历史，避免和路由提交抢历史。
 */
export function resyncBackLayer(): void {
  if (layers.length > 0 && (!sentinelActive || !sentinelPresent())) pushSentinel()
}

function scheduleSync() {
  if (syncQueued) return
  syncQueued = true
  queueMicrotask(() => {
    syncQueued = false
    if (layers.length > 0) {
      // 哨兵丢了（被 replace 吃掉 / 上一轮 popstate 已消费）就补一条，保证浮层始终有历史兜底
      if (!sentinelActive || !sentinelPresent()) pushSentinel()
      return
    }
    // 最后一层已关闭：把哨兵退掉，避免历史里留下一次「空按返回」
    if (!sentinelActive) return
    const sameUrl = currentUrl() === sentinelUrl
    const stillOurs = sentinelPresent()
    sentinelActive = false
    if (!sameUrl || !stillOurs) return
    suppressPops += 1
    window.history.back()
  })
}

function onPopState() {
  if (suppressPops > 0) {
    suppressPops -= 1
    return
  }
  const top = layers[layers.length - 1]
  if (!top) return
  // 系统返回已经替我们退掉了哨兵，收掉最上面那一层
  sentinelActive = false
  top.close()
  scheduleSync()
}

function ensureListener() {
  if (listening) return
  listening = true
  window.addEventListener('popstate', onPopState)
}

/**
 * 把一层页内浮层登记进返回链路。
 *
 * @param open  该层当前是否打开（通常会写成 `computed(() => isMobile && x)`）
 * @param close 关闭这一层的回调，必须只关当前层、不要顺手关掉它的父层
 */
export function useBackLayer(open: Ref<boolean>, close: () => void) {
  ensureListener()
  const layer: BackLayer = { close, isOpen: () => open.value }
  let registered = false

  function register() {
    if (registered) return
    registered = true
    layers.push(layer)
    scheduleSync()
  }

  function unregister(skipHistory = false) {
    if (!registered) return
    registered = false
    const index = layers.indexOf(layer)
    if (index >= 0) layers.splice(index, 1)
    if (skipHistory) {
      // 浮层随路由切换被卸载：哨兵留在了旧地址的历史里，这里只放弃跟踪，不能退历史
      sentinelActive = false
      return
    }
    scheduleSync()
  }

  watch(open, (value) => (value ? register() : unregister()), { immediate: true })
  onBeforeUnmount(() => unregister(true))
}


/**
 * 给 Android 原生层用的返回入口（MainActivity 的 OnBackInvokedCallback 会先调用它）。
 *
 * 为什么需要：原生只看得到 WebView 历史（canGoBack / goBack），而页内浮层是靠哨兵
 * 「间接」进历史的 —— 哨兵被路由 replace 吃掉、或页面本来就是历史第一条（深链 / 通知
 * 直接落到聊天窗口）时，canGoBack() 为 false，原生会判定「已在一级页面」直接退后台，
 * 用户看到的就是「在聊天里侧滑，App 直接回到桌面」。
 *
 * 所以让原生先问页面：有浮层就收掉最上面一层并返回 true；没有才让原生走历史 / 退后台。
 */
function handleNativeBack(): boolean {
  const top = layers[layers.length - 1]
  if (!top) return false
  top.close()
  // 关闭后由 unregister -> scheduleSync 负责把哨兵退掉（与页内返回箭头同一套）
  return true
}

if (typeof window !== 'undefined') {
  ;(window as Window & { __mian02HandleBack?: () => boolean }).__mian02HandleBack = handleNativeBack
}
