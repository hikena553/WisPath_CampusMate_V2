<template>
  <div class="app-shell" :class="{ 'app-mobile': isMobile }">
    <header class="topbar" :class="{ 'topbar-mobile': isMobile }">
      <div class="topbar-left" style="cursor:pointer" @click="goTo('/student')">
        <img src="/images/校徽_圆形.png" class="topbar-badge" />
        <span class="logo">绵小城</span>
        <template v-if="!isMobile">
          <span class="logo-divider"></span>
          <span class="motto">博学、笃行、严谨、创新</span>
        </template>
      </div>
      <div class="topbar-nav">
        <template v-if="!isMobile">
          <div class="nav-item" :class="{ 'nav-active': route.path === '/student' }" @click="goTo('/student')">
            <el-icon :size="16"><ChatDotRound /></el-icon>
            <span>绵小城</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/campus') }" @click="goTo('/student/campus')">
            <el-icon :size="16"><PictureFilled /></el-icon>
            <span>校园资讯</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/schedule') || route.path.startsWith('/student/growth') || route.path.startsWith('/student/grade') || route.path.startsWith('/student/plan') || route.path.startsWith('/student/portfolio') }" @click="goTo('/student/schedule')">
            <el-icon :size="16"><Odometer /></el-icon>
            <span>驾驶舱</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/workbench') || route.path.startsWith('/student/service') || route.path.startsWith('/student/resources') || route.path.startsWith('/student/community') || route.path.startsWith('/student/feedback') }" @click="goTo('/student/workbench')" style="position:relative">
            <el-icon :size="16"><Grid /></el-icon>
            <span>工作台</span>
            <el-badge v-if="unreadCount" is-dot class="contact-badge" />
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path.startsWith('/student/profile') }" @click="goTo('/student/profile')">
            <el-icon :size="16"><User /></el-icon>
            <span>个人中心</span>
          </div>
        </template>
      </div>
      <div class="topbar-right">
        <template v-if="!isMobile">
          <el-dropdown trigger="click">
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
        <!-- 两种过渡都用默认的「同时」模式：离场页都是绝对定位（脱离文档流），
             因此新旧同时在场也不会互相挤压，只是各自做动画；
             :duration 仅整屏推入显式兜底移除，卡片切换交给 Vue 自动检测 -->
        <Transition :name="pageTransition" :duration="transitionDuration">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>

    <!-- 移动端底部导航栏 -->
    <MobileTabBar v-if="isMobile" :items="mobileNavItems" :active-key="activeNavKey" @select="handleNavSelect" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getConversations } from '@/api/messages'
import { getGroups } from '@/api/groups'
import { getCourses } from '@/api/academic'
import { getGrowthProfile } from '@/api/growth'
import { fetchProactiveActions } from '@/api/agent'
import { getToday } from '@/api/plan'
import { studentDataCache } from '@/utils/studentDataCache'
import type { Course } from '@/types'
import { ChatDotRound, PictureFilled, Grid, User, SwitchButton, Odometer } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import MobileTabBar from '@/components/responsive/MobileTabBar.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isMobile } = useResponsive()

// 路由过渡分两种：
// 1) 快捷空间子页面（学习计划/作品集/成长档案/情绪树洞）：整屏推入/退出（进入=前进，离开=返回）
// 2) 其余同级页面切换（底部导航/顶栏之间，如校园资讯↔驾驶舱）：卡片式切换（新页浮起放大到位，旧页缩小退后）
const quickPagePaths = ['/student/plan', '/student/portfolio', '/student/growth', '/student/emotion']
const pageTransition = ref('')
watch(
  () => route.path,
  (to, from) => {
    if (quickPagePaths.includes(to)) pageTransition.value = 'page-slide'
    else if (quickPagePaths.includes(from)) pageTransition.value = 'page-slide-back'
    else pageTransition.value = 'page-card'
  },
  { flush: 'pre' }
)

/** 只有整屏推入需要显式时长兜底移除（离场页整屏滑出，见 animations.css）；
    卡片切换交给 Vue 自动检测，与 CSS 时长精确对齐 */
const transitionDuration = computed(() =>
  pageTransition.value.startsWith('page-slide') ? 460 : undefined
)

// 移动端底部导航
const mobileNavItems = [
  { key: 'campus', label: '校园资讯', icon: PictureFilled, route: '/student/campus' },
  { key: 'schedule', label: '驾驶舱', icon: Odometer, route: '/student/schedule' },
  { key: 'agent', label: '绵小城', iconImg: '/images/校徽_圆形.png', center: true, route: '/student' },
  { key: 'workbench', label: '工作台', icon: Grid, route: '/student/workbench' },
  { key: 'profile', label: '个人中心', icon: User, route: '/student/profile' },
]

const activeNavKey = computed(() => {
  const path = route.path
  if (path === '/student' || path.startsWith('/student/agent')) return 'agent'
  if (path.startsWith('/student/campus')) return 'campus'
  if (path.startsWith('/student/schedule') || path.startsWith('/student/growth') || path.startsWith('/student/grade') || path.startsWith('/student/plan') || path.startsWith('/student/portfolio')) return 'schedule'
  if (path.startsWith('/student/profile')) return 'profile'
  if (path.startsWith('/student/workbench') || path.startsWith('/student/service') || path.startsWith('/student/feedback') || path.startsWith('/student/resources') || path.startsWith('/student/community')) return 'workbench'
  return 'agent'
})

function handleNavSelect(item: { route: string }) {
  router.push(item.route)
}

const unreadCount = ref(0)

async function pollUnread() {
  try {
    const convs: any[] = await getConversations()
    const groupConvs: any[] = await getGroups()
    unreadCount.value =
      convs.reduce((sum: number, c: any) => sum + (c.unread_count ?? 0), 0) +
      groupConvs.reduce((sum: number, g: any) => sum + (g.unread_count ?? 0), 0)
  } catch {}
}

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
  pollUnread()
  setInterval(pollUnread, 5000)
  // 延迟 1.2s 让当前页首屏请求先走，再后台预热
  warmTimer = window.setTimeout(warmDashboardCache, 1200)
})

onUnmounted(() => {
  if (warmTimer) window.clearTimeout(warmTimer)
})

function goTo(path: string) { router.push(path) }

function logout() {
  auth.logout()
  router.push('/')
}
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #f5faff 0%, #f0f8ff 50%, #f8fbff 100%);
  overflow: hidden;
}

/* 移动(App)模式：宽屏下模拟手机容器，居中限宽 */
.app-mobile {
  max-width: 440px;
  margin: 0 auto;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.08), 0 24px 48px rgba(0,0,0,0.4);
}

/* 底部导航同样限宽居中，贴合手机容器 */
.app-mobile :deep(.mobile-tab-bar) {
  width: 100%;
  max-width: 440px;
  margin: 0 auto;
  left: 0;
  right: 0;
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
.main-area.has-bottom-bar { padding-bottom: 56px; }

.contact-badge { position: absolute; top: 2px; right: 2px; }
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