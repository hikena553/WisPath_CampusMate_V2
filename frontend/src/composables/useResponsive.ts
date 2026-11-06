import { ref, onMounted, onUnmounted } from 'vue'

const MOBILE_BREAKPOINT = 768
const TABLET_BREAKPOINT = 1024

// 响应式状态完全由真实视口驱动：
// - 移动视口（<768px）：师/生端显示 App 移动布局（440px 容器 + 底部导航）
// - 平板/桌面视口（>=768px）：显示完整网页布局（顶部导航/侧边栏）
// 注：不做角色级强制压缩，避免桌面浏览器下子页面媒体查询不触发而出现布局挤压。
const isMobile = ref(false)
const isTablet = ref(false)
const isDesktop = ref(true)

const MOBILE_QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`
const TABLET_QUERY = `(max-width: ${TABLET_BREAKPOINT - 1}px)`

function readViewport(): { mobile: boolean; tablet: boolean } {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return { mobile: false, tablet: false }
  }
  const mobile = window.matchMedia(MOBILE_QUERY).matches
  // 平板区间是「不满足手机、但满足最大 1023px」，两者互斥
  const tablet = !mobile && window.matchMedia(TABLET_QUERY).matches
  return { mobile, tablet }
}

function applyViewport(next: { mobile: boolean; tablet: boolean }) {
  isMobile.value = next.mobile
  isTablet.value = next.tablet
  isDesktop.value = !next.mobile && !next.tablet
}

// 模块加载时同步初始化，避免首帧先渲染桌面布局再翻转为移动端造成闪变
applyViewport(readViewport())

let mqlMobile: MediaQueryList | null = null
let mqlTablet: MediaQueryList | null = null
let refCount = 0

function update() {
  if (!mqlMobile || !mqlTablet) {
    // 监听尚未建立（或已释放）时以真实视口为准，不能退化成「一律桌面」。
    // 旧实现用 `mqlMobile?.matches ?? false`，一旦 mql 被释放就会把 isMobile
    // 强制刷成 false，导致移动端在页面切换瞬间误判为桌面布局。
    applyViewport(readViewport())
    return
  }
  const mobile = mqlMobile.matches
  const tablet = !mobile && mqlTablet.matches
  applyViewport({ mobile, tablet })
}

function attach() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
  mqlMobile = window.matchMedia(MOBILE_QUERY)
  mqlTablet = window.matchMedia(TABLET_QUERY)
  // addEventListener 在旧 Safari 上不存在，回退到 addListener
  if (typeof mqlMobile.addEventListener === 'function') {
    mqlMobile.addEventListener('change', update)
    mqlTablet!.addEventListener('change', update)
  } else {
    mqlMobile.addListener(update)
    mqlTablet!.addListener(update)
  }
  update()
}

function detach() {
  if (mqlMobile) {
    if (typeof mqlMobile.removeEventListener === 'function') {
      mqlMobile.removeEventListener('change', update)
    } else {
      mqlMobile.removeListener(update)
    }
  }
  if (mqlTablet) {
    if (typeof mqlTablet.removeEventListener === 'function') {
      mqlTablet.removeEventListener('change', update)
    } else {
      mqlTablet.removeListener(update)
    }
  }
  // 释放引用：下次 attach 会重新建立，避免持有已脱离文档的 MediaQueryList
  mqlMobile = null
  mqlTablet = null
}

export function useResponsive() {
  // mounted 标记：防止组件未成功挂载却执行了 onUnmounted 时把 refCount 减乱
  let mounted = false

  onMounted(() => {
    mounted = true
    if (refCount === 0) attach()
    refCount++
  })

  onUnmounted(() => {
    // 只对成功挂载过的组件减计数，保证 refCount 不会变负
    if (!mounted) return
    mounted = false
    refCount = Math.max(0, refCount - 1)
    if (refCount === 0) detach()
  })

  return { isMobile, isTablet, isDesktop }
}
