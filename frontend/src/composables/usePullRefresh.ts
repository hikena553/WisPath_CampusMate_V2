/**
 * 移动端下拉刷新（touch 手势）
 *
 * 用法：把 onStart / onMove / onEnd / onCancel 绑到滚动容器的 touch 事件上，
 * 容器用 scrollStyle 跟随手指位移，容器上方的指示器用 indicatorStyle 撑开高度。
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

  const scrollStyle = computed<CSSProperties>(() => {
    if (!distance.value) return {}
    return {
      transform: `translateY(${distance.value}px)`,
      transition: dragging.value ? 'none' : `transform ${SETTLE}`,
    }
  })

  const indicatorStyle = computed<CSSProperties>(() => ({
    height: `${distance.value}px`,
    transition: dragging.value ? 'none' : `height ${SETTLE}`,
  }))

  function onStart(e: TouchEvent) {
    if (refreshing.value) return
    if (options.enabled && !options.enabled()) return
    const el = e.currentTarget as HTMLElement
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

  return reactive({ ready, refreshing, scrollStyle, indicatorStyle, onStart, onMove, onEnd, onCancel })
}