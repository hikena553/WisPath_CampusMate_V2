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

// 模块加载时同步初始化，避免首帧先渲染桌面布局再翻转为移动端造成闪变
if (typeof window !== 'undefined') {
  const m = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`).matches
  const t = !m && window.matchMedia(`(max-width: ${TABLET_BREAKPOINT - 1}px)`).matches
  isMobile.value = m
  isTablet.value = t
  isDesktop.value = !m && !t
}

let mqlMobile: MediaQueryList | null = null
let mqlTablet: MediaQueryList | null = null
let refCount = 0

function update() {
  const m = mqlMobile?.matches ?? false
  const t = !m && (mqlTablet?.matches ?? false)
  isMobile.value = m
  isTablet.value = t
  isDesktop.value = !m && !t
}

export function useResponsive() {
  onMounted(() => {
    if (typeof window === 'undefined') return
    if (refCount === 0) {
      mqlMobile = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
      mqlTablet = window.matchMedia(`(max-width: ${TABLET_BREAKPOINT - 1}px)`)
      update()
      mqlMobile.addEventListener('change', update)
      mqlTablet.addEventListener('change', update)
    }
    refCount++
  })

  onUnmounted(() => {
    refCount--
    if (refCount <= 0) {
      refCount = 0
      mqlMobile?.removeEventListener('change', update)
      mqlTablet?.removeEventListener('change', update)
    }
  })

  return { isMobile, isTablet, isDesktop }
}