import { ref, onMounted, onUnmounted } from 'vue'
import { getUser } from '@/utils/token'

const MOBILE_BREAKPOINT = 768
const TABLET_BREAKPOINT = 1024

// 教师端/学生端强制移动端布局（v3.0 规划：师/生仅保留 App 移动端，管理员用网页大屏）
function detectForceMobile(): boolean {
  const u = getUser()
  const role = u?.role
  return role === 'teacher' || role === 'student'
}

const forceMobile = detectForceMobile()

const isMobile = ref(forceMobile)
const isTablet = ref(false)
const isDesktop = ref(!forceMobile)

// 模块加载时同步初始化，避免首帧先渲染桌面布局再翻转为移动端造成闪变
if (typeof window !== 'undefined') {
  const m = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`).matches
  const t = !m && window.matchMedia(`(max-width: ${TABLET_BREAKPOINT - 1}px)`).matches
  if (forceMobile) {
    isMobile.value = true
    isTablet.value = false
    isDesktop.value = false
  } else {
    isMobile.value = m
    isTablet.value = t
    isDesktop.value = !m && !t
  }
}

let mqlMobile: MediaQueryList | null = null
let mqlTablet: MediaQueryList | null = null
let refCount = 0

function update() {
  if (forceMobile) {
    isMobile.value = true
    isTablet.value = false
    isDesktop.value = false
    return
  }
  isMobile.value = mqlMobile?.matches ?? false
  isTablet.value = !isMobile.value && (mqlTablet?.matches ?? false)
  isDesktop.value = !isMobile.value && !isTablet.value
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