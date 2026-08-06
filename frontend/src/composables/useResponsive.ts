import { ref, onMounted, onUnmounted } from 'vue'

const MOBILE_BREAKPOINT = 768
const TABLET_BREAKPOINT = 1024

const isMobile = ref(false)
const isTablet = ref(false)
const isDesktop = ref(true)

let mqlMobile: MediaQueryList | null = null
let mqlTablet: MediaQueryList | null = null

function update() {
  isMobile.value = mqlMobile?.matches ?? false
  isTablet.value = !isMobile.value && (mqlTablet?.matches ?? false)
  isDesktop.value = !isMobile.value && !isTablet.value
}

export function useResponsive() {
  onMounted(() => {
    if (typeof window === 'undefined') return
    mqlMobile = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    mqlTablet = window.matchMedia(`(max-width: ${TABLET_BREAKPOINT - 1}px)`)
    update()
    mqlMobile.addEventListener('change', update)
    mqlTablet.addEventListener('change', update)
  })

  onUnmounted(() => {
    mqlMobile?.removeEventListener('change', update)
    mqlTablet?.removeEventListener('change', update)
  })

  return { isMobile, isTablet, isDesktop }
}
