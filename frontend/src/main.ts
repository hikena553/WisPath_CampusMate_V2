import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus, { messageConfig } from 'element-plus'
import 'element-plus/dist/index.css'
import 'cropperjs/dist/cropper.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import App from './App.vue'
import router from './router'
import './styles/theme.css'
import './styles/animations.css'
import './styles/responsive.css'
import './styles/admin-components.css'
import './styles/teacher-ui.css'
import './styles/dingtalk.css'
import './styles/dialog-minimal.css'
import './styles/scrollbar-hide.css'
import './styles/subpage-transition.css'
import './styles/teacher-mobile-kit.css'
import { permissionDirective, roleDirective } from './directives/permission'
import { startSiteConfigSync } from './composables/useSiteConfig'
import { setupAndroidBack } from './composables/useAndroidBack'
import { resyncBackLayer } from './composables/useBackLayer'

// 启动站点品牌同步：登录页与各端口统一读取管理端下发的站点名称/Logo/吉祥物/公告
startSiteConfigSync()

/**
 * 浮层层级与安全区（Element Plus 全局口径）。
 *
 * 1）z-index：App 的整屏子页（聊天页 / 帖子详情 / 个人中心子页 / 计划页…）是
 *    z-index: 2600 的覆盖层，而 Element Plus 默认从 2000 起步 —— 提示（ElMessage）、
 *    确认框、全屏 loading 全被压在下面，表现就是「操作了但通知看不见 / 被挡住」。
 *    把 EP 的起始层级抬到 2600 之上（2700），提示与弹窗才真正浮在页面之上。
 * 2）安全区：ElMessage 固定在顶部 16px，App 内 edge-to-edge 会正好压在状态栏 / 挖孔下面，
 *    这里把基准 offset 下移一个安全区高度；桌面端读出 0，行为不变。
 */
const EP_Z_INDEX_BASE = 2700
const TOAST_OFFSET = 16

/** 读状态栏 / 挖孔高度：env(safe-area-inset-top) 只有真机 WebView 里才不为 0 */
function readSafeAreaTop(): number {
  if (typeof document === 'undefined') return 0
  const probe = document.createElement('div')
  probe.style.cssText =
    'position:fixed;top:0;left:0;width:0;height:env(safe-area-inset-top,0px);visibility:hidden;pointer-events:none'
  document.body.appendChild(probe)
  const height = probe.getBoundingClientRect().height || 0
  probe.remove()
  return Math.round(height)
}

/** 提示的基准 offset：状态栏高度 + 16px（多条提示仍由 EP 自己按 offset 递增堆叠） */
function syncMessageOffset(): void {
  ;(messageConfig as unknown as { offset?: number }).offset = TOAST_OFFSET + readSafeAreaTop()
}

syncMessageOffset()
window.addEventListener('resize', syncMessageOffset)
window.addEventListener('orientationchange', syncMessageOffset)

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Android 物理返回键 / 侧滑返回：App 壳内接管，避免误退出
setupAndroidBack(router)

// 每次路由落定后对齐「页内浮层哨兵」：replace 会把历史条目的 state 换成路由自己的，
// 标记丢了就补一条 —— 否则浮层开着时按返回会直接跳到上一个页面（App 内甚至退到桌面）。
router.afterEach(() => { resyncBackLayer() })
app.use(ElementPlus, { locale: zhCn, zIndex: EP_Z_INDEX_BASE })

// 注册权限指令
app.directive('permission', permissionDirective)
app.directive('role', roleDirective)

app.mount('#app')
