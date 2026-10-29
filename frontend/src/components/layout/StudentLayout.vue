<template>
  <div class="app-shell" :class="{ 'app-mobile': isMobile }">
    <header class="topbar" :class="{ 'topbar-mobile': isMobile }">
      <div class="topbar-left" style="cursor:pointer" @click="goHome">
        <img src="/images/校徽_圆形.png" class="topbar-badge" />
        <span class="logo">绵小城</span>
        <template v-if="!isMobile">
          <span class="logo-divider"></span>
          <span class="motto">博学、笃行、严谨、创新</span>
        </template>
      </div>
      <div class="topbar-nav">
        <template v-if="!isMobile">
          <div class="nav-item" :class="{ 'nav-active': route.path === '/student' }" @click="navTo('/student', '和绵小城对话')">
            <el-icon :size="16"><ChatDotRound /></el-icon>
            <span>绵小城</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/campus') }" @click="navTo('/student/campus', '浏览校园资讯')">
            <el-icon :size="16"><Memo /></el-icon>
            <span>校园资讯</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/schedule') || route.path.startsWith('/student/growth') || route.path.startsWith('/student/grade') || route.path.startsWith('/student/plan') || route.path.startsWith('/student/portfolio') }" @click="navTo('/student/schedule', '进入学业中心')">
            <el-icon :size="16"><Odometer /></el-icon>
            <span>学业中心</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/messages') }" @click="navTo('/student/messages', '查看消息')" style="position:relative">
            <el-icon :size="16"><Message /></el-icon>
            <span>消息</span>
            <el-badge v-if="unreadCount" :value="unreadCount > 99 ? '99+' : unreadCount" class="contact-badge" title="点击清除未读提示" @click.stop="clearUnread" />
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/profile') }" @click="navTo('/student/profile', '进入个人中心')">
            <el-icon :size="16"><User /></el-icon>
            <span>个人中心</span>
          </div>
        </template>
      </div>
      <div class="topbar-right">
        <button v-if="auth.guest" type="button" class="guest-login-btn" @click="goLogin">
          登录<span v-if="!isMobile"> / 解锁全部功能</span>
        </button>
        <template v-if="!isMobile">
          <el-dropdown v-if="!auth.guest" trigger="click">
            <span class="user-btn">
              <el-avatar :size="28" :src="auth.user?.avatar || ''">{{ auth.userName?.[0] }}</el-avatar>
              <span class="user-name">{{ auth.userName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-item @click="goTo('/student/profile')">
                <el-icon style="margin-right:6px"><User /></el-icon>个人资料
              </el-dropdown-item>
              <el-dropdown-item divided @click="logout">
                <el-icon style="margin-right:6px"><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </template>
          </el-dropdown>
        </template>
      </div>
    </header>
    <main class="main-area" :class="{ 'has-bottom-bar': isMobile }">
      <router-view v-slot="{ Component }">
        <!-- 两种过渡都用默认的「同时」模式（新旧同时在场），因此两者都必须让离场页脱流，
              否则两个整页组件会在 .main-area（flex column）里分摊高度、互相挤压：
              - route-subpage：离场页 absolute + inset:0（见 animations.css）
              - page-card：离场页同样 absolute + inset:0
              :duration 仅覆盖式滑动显式兜底移除，卡片切换交给 Vue 自动检测 -->
        <Transition :name="pageTransition" :duration="transitionDuration">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>

    <!-- 移动端底部导航栏 -->
    <MobileTabBar v-if="isMobile" :items="mobileNavItems" :active-key="activeNavKey" :unread-count="unreadCount" @select="handleNavSelect" />

    <!-- 个人主页浮层：消息中心 / 社区等入口调用 openUserHomepage() 即拉起，全端共用一份 -->
    <UserHomepage />

    <!-- 勋章奖励动画：进入应用时结算一次，新解锁的勋章在此播放获得动画 -->
    <BadgeAwardOverlay :badge="currentAward" :remaining="awardRemaining" @next="consume" @skip="skipAll" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { getCourses } from '@/api/academic'
import { getGrowthProfile } from '@/api/growth'
import { fetchProactiveActions } from '@/api/agent'
import { getToday } from '@/api/plan'
import { studentDataCache } from '@/utils/studentDataCache'
import type { Course } from '@/types'
// 校园资讯 Tab 图标用 Memo（册页/刊物）而不是 PictureFilled（相册）：
// 这页现在是「资讯流 + 分类 + 互动」，图片图标会把人引到「校园图库」的错误预期。
import { ChatDotRound, Memo, Message, User, SwitchButton, Odometer } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import { useDockInset } from '@/composables/useDockInset'
import MobileTabBar from '@/components/responsive/MobileTabBar.vue'
import UserHomepage from '@/components/profile/UserHomepage.vue'
import BadgeAwardOverlay from '@/components/profile/BadgeAwardOverlay.vue'
import { useBadgeAward } from '@/composables/useBadgeAward'
import { promptLogin } from '@/utils/loginGate'
import { confirmLogout } from '@/utils/logout'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isMobile } = useResponsive()
// 悬浮胶囊的底部让位（加到页面根元素上，而不是 .main-area 的外层内边距）
useDockInset(isMobile)

// 路由过渡分方向（2026-10 起，与页内子页的覆盖式观感对齐）：
// 1) 推入（主页 → 快捷子页、子页 ↔ 子页）：.route-subpage —— 新页从右滑入盖住旧页，
//    旧页原地不动。**不能用 .subpage** —— 那个类给页内场景设计（主页面在
//    Transition 之外、没有 leave 元素）。桌面端路由页是流内布局，离场页不脱流就会
//    与进场页分摊高度（各约 50%）→ 高度塌陷抽搐；移动端快捷页自身是 fixed 整屏
//    覆盖层（见各页根元素样式），离场主页留在流内也不会被分摊高度，
//    几何规则见 animations.css 路由段的断点拆分。
// 2) 返回（子页 → 主页）：.route-subpage-back —— 离场的子页**原路向右滑出**，
//    进入的主页面原地不动地露出来。此前路由级不分方向，返回也播「新页滑入」，
//    观感是「又前进了一页」，与搜索/详情页「子页滑出」的返回不一致。
//    旧页不能跟新页一起动：两页同时位移是「传送带」穿帮（此前用户反馈过「退出动画不对」），
//    所以滑动的只有离场页自己。
// 3) 其余同级页面切换（底部导航/顶栏之间，如校园资讯↔驾驶舱）：卡片式切换（新页浮起放大到位，旧页缩小退后）
const quickPagePaths = ['/student/plan', '/student/portfolio', '/student/growth', '/student/emotion']
const pageTransition = ref('')
watch(
  () => route.path,
  (to, from) => {
    const toQuick = quickPagePaths.includes(to)
    const fromQuick = quickPagePaths.includes(from)
    if (toQuick || fromQuick) {
      pageTransition.value = fromQuick && !toQuick ? 'route-subpage-back' : 'route-subpage'
    } else {
      pageTransition.value = 'page-card'
    }
  },
  { flush: 'pre' }
)

/** 只有覆盖式滑动需要显式时长兜底移除（离场页脱流，见 animations.css）；
    卡片切换交给 Vue 自动检测，与 CSS 时长精确对齐 */
const transitionDuration = computed(() =>
  pageTransition.value === 'route-subpage' || pageTransition.value === 'route-subpage-back' ? 320 : undefined
)

// 移动端底部导航
// 「工作台」页签位已改为「消息」：会话 / 通讯录 / 论坛互动集中在这里，
// 办事入口（请假 / 证明 / 失物招领等）暂时保留 /student/workbench 路由但不再占页签。
const mobileNavItems = [
  { key: 'campus', label: '校园资讯', icon: Memo, route: '/student/campus' },
  { key: 'schedule', label: '学业中心', icon: Odometer, route: '/student/schedule' },
  { key: 'agent', label: '绵小城', iconImg: '/images/校徽_圆形.png', center: true, route: '/student' },
  { key: 'messages', label: '消息', icon: Message, route: '/student/messages', badge: true },
  { key: 'profile', label: '个人中心', icon: User, route: '/student/profile' },
]

const activeNavKey = computed(() => {
  const path = route.path
  if (path === '/student' || path.startsWith('/student/agent')) return 'agent'
  if (path.startsWith('/student/campus')) return 'campus'
  if (path.startsWith('/student/schedule') || path.startsWith('/student/growth') || path.startsWith('/student/grade') || path.startsWith('/student/plan') || path.startsWith('/student/portfolio')) return 'schedule'
  if (path.startsWith('/student/profile')) return 'profile'
  if (path.startsWith('/student/messages')) return 'messages'
  return 'agent'
})

function handleNavSelect(item: { route: string; label?: string }) {
  if (item.route.startsWith('/student/campus')) {
    router.push(item.route)
    return
  }
  void navTo(item.route, item.label ? `进入${item.label}` : '使用该功能')
}

/** 游客点按受限入口：先提示登录，同意后回登录页；登录用户正常跳转 */
async function navTo(path: string, feature: string) {
  if (auth.guest && !path.startsWith('/student/campus')) {
    await promptLogin(feature)
    return
  }
  router.push(path)
}

function goHome() {
  router.push(auth.guest ? '/student/campus' : '/student')
}

function goLogin() {
  auth.exitGuest()
  router.push({ path: '/login', query: { reason: 'login' } })
}

/**
 * 全局未读提示：单聊 + 群聊 + 站内通知三路汇总（此前漏算站内通知），
 * WS 实时 + 5s 轮询兜底；红点可点击清除。
 * 用 msgTotal 而不是 total：论坛互动未读归交流社区页的互动消息入口，
 * 不该让底部「消息」页签亮红点（否则又变成两套消息在同一处提示）。
 */
const {
  msgTotal: unreadCount,
  start: startUnreadWatch,
  stop: stopUnreadWatch,
  clearAll: clearUnread,
} = useUnreadSummary()

/**
 * 勋章结算与奖励动画：布局层只负责「进应用时结算一次」，
 * 动画本身由 BadgeAwardOverlay 渲染，因此切到任何页面都能看到获得动画。
 */
const { currentAward, awardRemaining, sync: syncBadgeAwards, consume, skipAll } = useBadgeAward()

// 驾驶舱首屏数据预热：布局常驻，登录后空闲时先把课程/画像/AI 主动发现/待办灌入模块级缓存，
// 这样首次切到驾驶舱也能首帧渲染真实内容，不会出现「骨架 → 内容」的高度跳变（卡片抽搐）
let warmTimer: number | undefined
function warmDashboardCache() {
  // 已缓存或当前就在驾驶舱（页面自己会拉）则不重复请求
  if (route.path === '/student/schedule') return
  if (!studentDataCache.courses) void getCourses().then(list => { studentDataCache.courses = list as Course[] }).catch(() => {})
  if (!studentDataCache.profile) void getGrowthProfile().then(p => { studentDataCache.profile = p }).catch(() => {})
  if (!studentDataCache.actions) void fetchProactiveActions().then(all => { studentDataCache.actions = all.filter(a => a.target_role === 'student') }).catch(() => {})
  if (!studentDataCache.tasks) void getToday().then(t => { studentDataCache.tasks = t }).catch(() => {})
}

onMounted(() => {
  // 游客只浏览公开内容，跳过所有需要登录态的请求（未读/勋章/数据预热）
  if (auth.guest) return
  startUnreadWatch()
  // 勋章结算放在首屏请求之后，避免与页面自身的数据请求抢占带宽
  window.setTimeout(() => { void syncBadgeAwards() }, 900)
  // 延迟 1.2s 让当前页首屏请求先走，再后台预热
  warmTimer = window.setTimeout(warmDashboardCache, 1200)
})

onUnmounted(() => {
  stopUnreadWatch()
  if (warmTimer) window.clearTimeout(warmTimer)
})

function goTo(path: string) { router.push(path) }

function logout() {
  confirmLogout()
}
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  /* 中性灰底。原来是 3 段淡蓝渐变（#f5faff → #f0f8ff → #f8fbff）——
     它铺满整屏，是「大面积蓝」最主要的来源，比任何卡片配色都更显眼 */
  background: #f5f6f7;

  /* 底部导航选中态变量：MobileTabBar 是学生/教师共用组件，
     这里只覆盖学生端，其它端仍是品牌蓝 */
  --tab-active-color: #14171a;
  --tab-center-bg: radial-gradient(circle at 32% 26%, #ffffff 0%, #f7f8f9 58%, #eef0f2 100%);
  --tab-center-glow: rgba(20, 23, 26, 0.06);
  --tab-center-ring: rgba(20, 23, 26, 0.10);
  --tab-center-glow-strong: rgba(20, 23, 26, 0.10);

  overflow: hidden;
}

/* 移动(App)模式：宽屏下模拟手机容器，居中限宽。
   注意这两个条件是「且」：
   - 视口够宽（≥600px）：否则真机上容器被限到 440px 后撑不满屏幕，
     两侧会露出 .app-shell 的浅蓝渐变底，加上下面那圈大投影，
     看上去就是页面四周浮着一圈蓝黑边框；
   - 视口是移动布局（isMobile，由 .app-mobile 类保证）。
   真机（常见 360~430px）两个条件不同时成立，因此容器铺满全屏、无描边无投影。 */
@media (min-width: 600px) {
  .app-mobile {
    max-width: 440px;
    margin: 0 auto;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.08), 0 24px 48px rgba(0,0,0,0.4);
  }
}

/* 底部导航是悬浮胶囊（见 MobileTabBar）：左右内缩、居中由组件自身的
   left:50% + translateX(-50%) 完成，宽屏预览时胶囊中心与手机容器中心重合，
   所以这里不再需要把 left/right 拉平到容器宽度。 */

/* 真机全屏时容器铺满，`.app-shell` 的浅蓝渐变会在卡片四周透出来一圈 —— 那正是
   「页面外一圈蓝边」的另一半。移动布局下把它改成纯白：页面白卡与屏边之间是白色留白，
   不是蓝色留白。宽屏预览（≥600px）仍保留渐变，让居中的手机容器浮起来。 */
@media (max-width: 599px) {
  .app-shell { background: #fff; }
}
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px;
  background: linear-gradient(135deg, #1d4ed8, #2563eb, #3b82f6);
  flex-shrink: 0; z-index: 100;
  box-shadow: 0 2px 12px rgba(29,78,216,0.35);
}
/* 移动(App)模式隐藏顶部抬头 */
.topbar-mobile { display: none !important; }
@media (max-width: 767px) {
  .topbar { display: none; }
}
.topbar-left { display: flex; align-items: center; gap: 8px; cursor: pointer; position: relative; z-index: 101; }
.topbar-badge { height: 36px; width: 36px; border-radius: 50%; object-fit: cover; filter: brightness(0.85) saturate(1.3); }
.logo { font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: 1px; }
.logo-divider { width: 1px; height: 20px; background: rgba(255,255,255,0.3); margin: 0 6px; }
.motto {
  font-size: 14px; font-weight: 600;
  color: rgba(255,255,255,0.85);
  letter-spacing: 4px;
}
.topbar-nav {
  display: flex; align-items: center; gap: 4px;
  margin-left: auto;
}
.nav-item {
  display: flex; align-items: center; gap: 3px;
  padding: 4px 6px; border-radius: 6px;
  color: rgba(255,255,255,0.85); font-size: 12px; font-weight: 500;
  cursor: pointer; transition: all 0.25s ease; white-space: nowrap;
}
.nav-item:hover {
  background: rgba(255,255,255,0.15); color: #ffffff;
}
.nav-active {
  background: rgba(255,255,255,0.95) !important; color: #1e40af !important;
}
.nav-active .el-icon { color: #1e40af; }
.topbar-right { display: flex; align-items: center; gap: 4px; }
.user-btn { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 8px; border-radius: 8px; color: #ffffff; }
.user-btn:hover { background: rgba(255,255,255,0.2); }
.user-name { font-size: 14px; color: #ffffff; }
.main-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; position: relative; -ms-overflow-style: none; scrollbar-width: none; }
.main-area::-webkit-scrollbar { display: none; }
/* 底部让位不再由 .main-area 承担：外层内边距会把滚动区整体切短，
   内容到不了胶囊下面，胶囊就成了「坐在白带上」。改由 useDockInset() 把留白
   加到页面根元素（滚动容器）上，内容可以滚到胶囊下方，滚到底也不会被遮。 */
.main-area.has-bottom-bar { padding-bottom: 0; }

.contact-badge { position: absolute; top: 2px; right: 2px; }
.guest-login-btn {
  border: 1px solid rgba(255,255,255,0.45);
  background: rgba(255,255,255,0.12);
  color: #fff;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: background .2s ease;
}
.guest-login-btn:hover { background: rgba(255,255,255,0.22); }
:deep(.topbar-right .el-button) { color: rgba(255,255,255,0.85); }
:deep(.topbar-right .el-button:hover) { color: #ffffff; background: rgba(255,255,255,0.2); }
:deep(.topbar-right .el-divider--vertical) { border-color: rgba(255,255,255,0.3); }
</style>

<style>
html, body, #app {
  height: 100vh;
  overflow: hidden;
  margin: 0;
  background-color: #0f172a;
}
.el-drawer__header { margin-bottom: 0 !important; padding: 6px 16px !important; }
.el-drawer__body { padding: 0 !important; }
</style>