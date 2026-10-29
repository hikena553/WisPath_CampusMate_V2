import { nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { Ref } from 'vue'

/**
 * 悬浮胶囊导航的「底部让位」
 *
 * 背景：移动端底部导航是一个透明的悬浮胶囊（见 components/responsive/MobileTabBar.vue，
 * 离底 12px、高 62px）。原先把 86px 留白加在 `.main-area` 的 padding-bottom 上，
 * 那是**外层**内边距：滚动区被整体切短，内容永远到不了胶囊下方，
 * 于是胶囊看起来像坐在一条空白带上，而不是浮在内容上。
 *
 * 现在把这段留白加到**页面根元素**上：
 * - 根元素自己滚动时（campus / schedule / workbench / profile 等）：padding-bottom
 *   属于可滚动区间，内容可以滚到胶囊下面（真悬浮），滚到底时最后一块内容
 *   又能滑到胶囊上方，不会被遮住；
 * - 根元素是 flex 列（对话页这类）：留白退化成固定占位，输入栏照旧停在胶囊上方。
 *
 * 跳过 `position: fixed` 的整屏覆盖子页（资讯详情、搜索结果、作品集等）：它们本身
 * 就压在整个应用之上（含胶囊），强行加内边距只会在底部多出一条白边。
 *
 * 路由切换时新旧两个页面会同时在 DOM 里（Transition 默认「同时在场」），
 * 所以按「所有直接子元素」逐个处理，避免只认 firstElementChild 时补错节点。
 */
const DOCK_INSET = 'calc(86px + env(safe-area-inset-bottom, 0px))'

export function useDockInset(isMobile: Ref<boolean>) {
  const route = useRoute()
  const padded = new Set<HTMLElement>()

  function resetAll() {
    for (const el of padded) {
      el.style.removeProperty('padding-bottom')
      el.style.removeProperty('box-sizing')
    }
    padded.clear()
  }

  async function apply() {
    // 等页面组件挂上来再量，否则碰到的还是上一个路由的根节点
    await nextTick()
    const main = document.querySelector('.main-area')
    if (!isMobile.value || !main) {
      resetAll()
      return
    }
    const roots = Array.from(main.children) as HTMLElement[]
    for (const el of Array.from(padded)) {
      if (!roots.includes(el)) {
        el.style.removeProperty('padding-bottom')
        el.style.removeProperty('box-sizing')
        padded.delete(el)
      }
    }
    for (const el of roots) {
      if (getComputedStyle(el).position === 'fixed') continue
      el.style.setProperty('padding-bottom', DOCK_INSET)
      // 页面根元素常写死 height:100%，必须按 border-box 算，否则整体高度会被撑出 86px
      el.style.setProperty('box-sizing', 'border-box')
      padded.add(el)
    }
  }

  onMounted(apply)
  watch(() => route.fullPath, apply, { flush: 'post' })
  watch(isMobile, apply)
  onBeforeUnmount(resetAll)
}
