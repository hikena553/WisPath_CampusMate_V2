import { onBeforeUnmount, onMounted, watch, type Ref } from 'vue'

/**
 * 底部悬浮胶囊（MobileTabBar）占位的统一实现
 *
 * 为什么不能给 .main-area 加 padding-bottom：
 * 外层内边距会把滚动区整体切短，内容永远滚不到胶囊下方，胶囊就像「坐在白带上」。
 * 所以留白要加在**页面根元素**（滚动容器）上 —— 这样内容可以滚到胶囊底下，
 * 滚到底时最后一行也不会被胶囊遮住。
 *
 * 只在移动端生效；桌面端胶囊不渲染，留白必须为 0。
 * 82px = 胶囊高度 62px + 底部间距 12px + 8px 呼吸位；安全区单独叠加。
 */
const STYLE_ID = 'dock-inset-style'

const CSS = `
html.dock-inset .main-area > *:not(.no-dock-inset) {
  box-sizing: border-box;
  padding-bottom: calc(82px + env(safe-area-inset-bottom, 0px));
}
`

function ensureStyle() {
  if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) return
  const style = document.createElement('style')
  style.id = STYLE_ID
  style.textContent = CSS
  document.head.appendChild(style)
}

export function useDockInset(isMobile: Ref<boolean>) {
  function apply(on: boolean) {
    if (typeof document === 'undefined') return
    document.documentElement.classList.toggle('dock-inset', on)
  }

  onMounted(() => {
    ensureStyle()
    apply(!!isMobile.value)
  })

  watch(isMobile, (v) => apply(!!v))

  onBeforeUnmount(() => apply(false))
}
