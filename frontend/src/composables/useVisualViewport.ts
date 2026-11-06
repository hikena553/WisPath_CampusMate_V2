import { onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 移动端软键盘可见区跟随。
 *
 * 键盘弹出时浏览器/WebView 的表现不止一种，这里统一归一成 keyboardOpen：
 * ① 原生把 WebView 缩到键盘上方（本项目 Android 1.7+ 的做法）→ window.innerHeight 变小；
 * ② 浏览器只缩 visualViewport → visualViewport.height 比窗口矮；
 * ③ 浏览器把可见区整体上移（adjustPan）→ visualViewport.offsetTop 变大。
 *
 * offsetTop / height 描述可见区在 layout 坐标系里的位置，供整屏 fixed 浮层贴边用；
 * keyboardOpen 供页面做「键盘展开时」的界面收敛（例如欢迎页收起吉祥物）。
 */
export function useVisualViewport() {
  const offsetTop = ref(0)
  const height = ref(0)
  const keyboardOpen = ref(false)
  let vv: VisualViewport | null = null
  /** 键盘收起时的窗口高度基准：旋转屏幕后重置，避免把横屏误判成键盘展开 */
  let baseline = 0
  let orientTimer: ReturnType<typeof setTimeout> | null = null

  function sync() {
    const innerH = window.innerHeight
    const vvH = vv ? vv.height : innerH
    const off = vv ? vv.offsetTop : 0
    offsetTop.value = off
    height.value = vvH
    if (!baseline) baseline = Math.max(innerH, vvH)
    const shrunk =
      Math.max(innerH, vvH) < baseline - 140 || // ① 窗口被压缩
      vvH < innerH - 140 || // ② 只有可见区被压缩
      off > 60 // ③ 可见区被整体上移
    keyboardOpen.value = shrunk
    // 键盘收起后把基准抬回真实窗口高度（也是首次拿到真实高度的地方）
    if (!shrunk) baseline = Math.max(baseline, innerH, vvH)
  }

  function onWindowResize() {
    sync()
  }

  function onOrientationChange() {
    if (orientTimer) clearTimeout(orientTimer)
    orientTimer = setTimeout(() => {
      baseline = Math.max(window.innerHeight, vv ? vv.height : 0)
      sync()
    }, 350)
  }

  onMounted(() => {
    vv = window.visualViewport ?? null
    baseline = Math.max(window.innerHeight, vv ? vv.height : 0)
    sync()
    window.addEventListener('resize', onWindowResize)
    window.addEventListener('orientationchange', onOrientationChange)
    vv?.addEventListener('resize', sync)
    vv?.addEventListener('scroll', sync)
  })

  onBeforeUnmount(() => {
    if (orientTimer) clearTimeout(orientTimer)
    window.removeEventListener('resize', onWindowResize)
    window.removeEventListener('orientationchange', onOrientationChange)
    vv?.removeEventListener('resize', sync)
    vv?.removeEventListener('scroll', sync)
  })

  return { offsetTop, height, keyboardOpen }
}

