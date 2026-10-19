/**
 * 移动端下拉刷新（touch 手势）
 *
 * 用法：把 onStart / onMove / onEnd / onCancel 绑到**真正滚动**的容器上（touchmove 不能加 `.passive`），
 * 容器内放 `PullRefreshIndicator`：指示器自身高度即下拉位移，其下方内容随之整体下移。
 * 手势逻辑与指示器动画由模块统一提供，各页面只需选好滚动容器：
 *
 *   <div class="x-scroll" @touchstart.passive="pull.onStart" @touchmove="pull.onMove"
 *     @touchend="pull.onEnd" @touchcancel="pull.onCancel">
 *     <header class="x-head">...</header>                              <!-- 有吸顶头才需要 -->
 *     <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />
 *     ...列表内容...
 *   </div>
 *
 * 固定头部约定：页面若有吸顶头（如教师端首页的 HomeTopBanner），指示器必须放在**头部之后**。
 * 指示器靠自身高度把后续内容下推，头部留在流程原位 → 吸顶头在下拉过程中保持不动。
 *
 * 约定：
 * - 只在容器 scrollTop === 0 且手指向下拖时接管手势，其余情况原样交还原生滚动；
 * - 容器需加 `overscroll-behavior-y: contain`，否则浏览器的原生下拉刷新会抢手势。
 */
import { computed, reactive, ref } from 'vue'
import type { CSSProperties } from 'vue'

interface PullRefreshOptions {
  /** 触发刷新所需的下拉距离（px） */
  threshold?: number
  /** 最大下拉距离（px） */
  max?: number
  /** 阻尼系数，越小越"拉不动" */
  damping?: number
  /** 是否响应手势（例如仅移动端） */
  enabled?: () => boolean
}

const EASE = 'cubic-bezier(.22,.61,.36,1)'
const SETTLE = `.26s ${EASE}`
/** 刷新指示器的最短停留时间，避免接口极快时"闪一下" */
const MIN_SPIN = 420

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * 触摸是否落在固定定位的浮层内（不含滚动容器自身）。
 * 首页的「去安排」任务子页、聊天页的语音浮层等都是 `position: fixed` 的整屏子页，
 * 它们 DOM 上仍是滚动容器的后代会冒泡上来，但有自己的滚动，不能被下拉刷新接管。
 */
function insideFixedLayer(target: EventTarget | null, container: HTMLElement): boolean {
  let el = target instanceof HTMLElement ? target : null
  while (el && el !== container) {
    if (getComputedStyle(el).position === 'fixed') return true
    el = el.parentElement
  }
  return false
}

export function usePullRefresh(onRefresh: () => Promise<unknown> | unknown, options: PullRefreshOptions = {}) {
  const threshold = options.threshold ?? 56
  const max = options.max ?? 88
  const damping = options.damping ?? 0.5

  const distance = ref(0)
  const dragging = ref(false)
  const refreshing = ref(false)
  let startY = 0
  let tracking = false

  /** 已拉过阈值：松手即刷新（页面用它触发吉祥物起跳） */
  const ready = computed(() => distance.value >= threshold)

  /** 指示器是否需要起跳：拉过阈值或刷新中 */
  const active = computed(() => ready.value || refreshing.value)

  const indicatorStyle = computed<CSSProperties>(() => ({
    height: `${distance.value}px`,
    transition: dragging.value ? 'none' : `height ${SETTLE}`,
  }))

  function onStart(e: TouchEvent) {
    if (refreshing.value) return
    if (options.enabled && !options.enabled()) return
    const el = e.currentTarget as HTMLElement
    // 页面内可能叠着固定浮层（如首页任务子页、聊天页语音浮层）：浮层自带滚动，不参与下拉刷新
    if (insideFixedLayer(e.target, el)) return
    if (el.scrollTop > 0) return
    startY = e.touches[0].clientY
    tracking = true
  }

  function onMove(e: TouchEvent) {
    if (!tracking) return
    const el = e.currentTarget as HTMLElement
    const delta = e.touches[0].clientY - startY
    // 手指向上，或过程中已经滚离顶部：放弃接管，交还原生滚动
    if (delta <= 0 || el.scrollTop > 0) {
      tracking = false
      dragging.value = false
      distance.value = 0
      return
    }
    e.preventDefault()
    dragging.value = true
    distance.value = Math.min(max, delta * damping)
  }

  async function onEnd() {
    if (!tracking) return
    tracking = false
    dragging.value = false

    if (distance.value < threshold) {
      distance.value = 0
      return
    }

    refreshing.value = true
    distance.value = threshold
    try {
      // 刷新失败由调用方静默兜底，指示器照常收起
      await Promise.all([Promise.resolve().then(onRefresh).catch(() => {}), wait(MIN_SPIN)])
    } finally {
      refreshing.value = false
      distance.value = 0
    }
  }

  function onCancel() {
    if (!tracking) return
    tracking = false
    dragging.value = false
    distance.value = 0
  }

  return reactive({ ready, refreshing, active, indicatorStyle, onStart, onMove, onEnd, onCancel })
}