<template>
  <div class="app-shell" :class="{ 'app-mobile': isMobile }">
    <!-- ============ 桌面端（>=768px）============
         对齐管理端（AdminLayout）的工作台外壳规范：
         深色渐变侧边栏（可折叠）+ 白色顶栏（面包屑 + 时钟）+ 多页签 + 内容区 -->
    <template v-if="!isMobile">
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-brand" style="cursor:pointer" @click="goTo('/teacher')">
          <img :src="siteLogo" class="brand-logo" />
          <div class="brand-text sidebar-text">
            <span class="brand-name">{{ siteName }}</span>
            <span class="brand-motto">教师工作台</span>
          </div>
        </div>
        <nav class="sidebar-nav">
          <template v-for="g in navGroups" :key="g.title">
            <div class="nav-group-label sidebar-text">{{ g.title }}</div>
            <!-- 全部导航项均为路由跳转（个人中心已由弹窗改为整页，不再是 dialog 型） -->
            <router-link v-for="item in g.items" :key="item.path" :to="item.path" class="nav-item" :class="{ active: isActive(item) }">
              <el-tooltip v-if="sidebarCollapsed" :content="item.label" placement="right">
                <el-icon :size="20"><component :is="item.icon" /></el-icon>
              </el-tooltip>
              <el-icon v-else :size="20"><component :is="item.icon" /></el-icon>
              <span class="nav-label sidebar-text">{{ item.label }}</span>
              <el-badge
                v-if="item.badge && unreadCount > 0"
                :value="unreadCount"
                :type="urgentUnread > 0 ? 'danger' : 'primary'"
                class="nav-badge"
                title="点击清除未读提示"
                @click.stop.prevent="clearUnread"
              />
            </router-link>
          </template>
        </nav>
        <div class="sidebar-footer">
          <el-dropdown trigger="click" placement="top-start">
            <div class="teacher-info">
              <el-avatar :size="sidebarCollapsed ? 32 : 36" :src="auth.user?.avatar || ''">
                {{ auth.userName?.[0] }}
              </el-avatar>
              <div class="teacher-detail sidebar-text">
                <span class="teacher-name">{{ auth.userName }}</span>
                <span class="teacher-college">{{ auth.user?.college || '未知学院' }}</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-item @click="goProfilePage">
                <el-icon style="margin-right:6px"><User /></el-icon>个人中心
              </el-dropdown-item>
              <el-dropdown-item divided @click="logout">
                <el-icon style="margin-right:6px"><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </template>
          </el-dropdown>
        </div>
      </aside>

      <div class="main-column">
        <header class="topbar">
          <div class="topbar-left">
            <el-tooltip :content="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'" placement="bottom">
              <el-button text circle class="sidebar-toggle-btn" @click="toggleSidebar">
                <span class="toggle-icon" :class="{ collapsed: sidebarCollapsed }">
                  <el-icon :size="18" class="toggle-ic fold-ic"><PanelLeftClose /></el-icon>
                  <el-icon :size="18" class="toggle-ic expand-ic"><PanelLeftOpen /></el-icon>
                </span>
              </el-button>
            </el-tooltip>
            <el-breadcrumb separator="/" class="topbar-breadcrumb">
              <el-breadcrumb-item :to="{ path: '/teacher' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="currentTitle && currentTitle !== '首页'">{{ currentTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="topbar-right">
            <!-- 教师身份胶囊：教师端专属（管理端是「管理员」、学生端是「学生」，都没有这一行） -->
            <el-tooltip v-if="teacherIdentity" :content="teacherIdentity" placement="bottom">
              <span class="topbar-identity">
                <el-icon :size="14"><School /></el-icon>
                <span class="topbar-identity-text">{{ teacherIdentity }}</span>
              </span>
            </el-tooltip>
            <span class="topbar-clock">{{ now }}</span>
          </div>
        </header>

        <!-- 多页签：与管理端一致，已打开的页面在此切换/关闭 -->
        <div class="tabs-bar">
          <div class="tabs-scroll">
            <div
              v-for="tab in tabs"
              :key="tab.path"
              class="tab-item"
              :class="{ active: route.path === tab.path }"
              @click="goTo(tab.path)"
            >
              <span class="tab-dot"></span>
              <span class="tab-label">{{ tab.label }}</span>
              <el-icon v-if="tabs.length > 1" class="tab-close" :size="12" @click.stop="closeTab(tab.path)">
                <Close />
              </el-icon>
            </div>
          </div>
        </div>

        <!-- 系统公告：管理端下发的站点公告，各端同步展示 -->
        <SiteAnnouncementBar />

        <!-- teacher-scope：桌面端密度 / 组件规范的作用域开关 -->
        <main class="main-area teacher-scope">
          <router-view v-slot="{ Component }">
            <keep-alive :include="cachedNames">
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </main>
      </div>
    </template>

    <!-- ============ 移动端（<768px）：保持原有布局不变（公告条 + 主区 + 底部页签） ============ -->
    <template v-else>
      <SiteAnnouncementBar />
      <main class="main-area has-bottom-bar">
        <router-view v-slot="{ Component }">
          <keep-alive :include="cachedNames">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </main>
      <MobileTabBar
        v-if="showTabBar"
        :items="mobileNavItems"
        :active-key="activeNavKey"
        :unread-count="unreadCount"
        @select="handleNavSelect"
      />
    </template>

    <!-- 桌面桌宠：不跳转智能体页即可对话并驱动智能体执行功能。
         1) 挂在布局层而非页面内 —— 与 HomePage 的 .home-dashboard 是兄弟关系，
            不会被其「全局禁动效」规则冻住，路由切换也不会重置拖拽位置；
         2) 智能体页本身已有完整的 ChatShell，且两者复用同一组会话 store，
            同路由下同时挂两份 ChatPanel 会互相干扰流式回包，故此路由下隐藏桌宠；
         3) v-if="!isMobile" —— 移动端已有底部「绵小城」页签作为同等入口。 -->
    <DesktopPet v-if="!isMobile && route.path !== '/teacher/agent'" />

    <!-- 个人中心已改为整页（/teacher/profile），此处不再提供弹窗形态 -->

    <!-- 个人主页浮层：消息中心 / 通讯录点开某人即拉起，全端共用一份 -->
    <UserHomepage />

    <!-- 勋章奖励动画：进入应用时结算一次，新解锁的勋章在此播放获得动画 -->
    <BadgeAwardOverlay :badge="currentAward" :remaining="awardRemaining" @next="consume" @skip="skipAll" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import UserHomepage from '@/components/profile/UserHomepage.vue'
import BadgeAwardOverlay from '@/components/profile/BadgeAwardOverlay.vue'
import { useBadgeAward } from '@/composables/useBadgeAward'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { useResponsive } from '@/composables/useResponsive'
import { useDockInset } from '@/composables/useDockInset'
import { hasOpenSubPage } from '@/composables/useMobileSubPage'
import MobileTabBar from '@/components/responsive/MobileTabBar.vue'
import DesktopPet from '@/components/teacher/DesktopPet.vue'
import SiteAnnouncementBar from '@/components/common/SiteAnnouncementBar.vue'
import { prefetchDashboardData } from '@/utils/teacherDashboardCache'
import { confirmLogout } from '@/utils/logout'
import {
  HomeFilled, User, Message, Notebook,
  List, Stamp, WarningFilled, Bell, ChatDotRound, Sunny,
  SwitchButton, Close, School
} from '@element-plus/icons-vue'
// 桌面端折叠按钮图标：与管理端（AdminLayout）保持同一套线性图标
import { PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// 站点品牌（站点名称/Logo）与站点配置同源：管理端修改后教师端同步生效
const { siteName, siteLogo, loadSiteConfig } = useSiteConfig()
watch(
  siteName,
  (name) => {
    document.title = `${name} · 教师端`
  },
  { immediate: true }
)
// 进入端口时拉取最新站点配置，管理员更新设置后教师端立即同步
onMounted(() => { void loadSiteConfig(true) })

// 缓存 teacher 端重型页面，避免切换时 ECharts 重建与数据重拉
const cachedNames = ['teacher-home', 'teacher-students']

const sidebarCollapsed = ref(false)
/**
 * 全局未读提示（导航红点）：只统计单聊 + 群聊未读，WS 实时 + 5s 轮询兜底。
 * 站内通知在消息中心「通知」页内单独计数，不再让「消息」导航在无聊天消息时误亮红点。
 */
const {
  msgTotal: unreadCount,
  urgentUnread,
  start: startUnreadWatch,
  stop: stopUnreadWatch,
  clearAll: clearUnread,
} = useUnreadSummary()

/** 勋章结算 + 奖励动画队列（布局层触发，全端可见） */
const { currentAward, awardRemaining, sync: syncBadgeAwards, consume, skipAll } = useBadgeAward()

const { isMobile } = useResponsive()

/**
 * 侧边栏导航项：支持图标组件（Element Plus 图标）或站点 Logo 图片两种形态。
 * 显式声明类型，避免各分组因字段差异被推断成联合类型而丢失可选字段。
 */
interface NavItem {
  path: string
  label: string
  icon?: Component
  iconImg?: string
  badge?: boolean
}

/**
 * 未在侧边栏单列的子路由 → 其归属的侧边栏入口。
 * 例如成长档案 / 问卷互评 是「学生档案」的下钻能力，进入后高亮「学生档案」，
 * 保证页面归属清晰，而不是所有子页都亮「首页」。
 */
const SUB_ROUTE_PARENT: Record<string, string> = {
  '/teacher/portfolio': '/teacher/students',
  '/teacher/survey': '/teacher/students',
  '/teacher/ai': '/teacher',
  '/teacher/features': '/teacher',
}

/**
 * 桌面端侧边栏导航：按「工作 / 班级 / 我的」三组共 10 项。
 *
 * 顺序按教师的日常动线重排：先「工作」组（首页 → 今日要办 → 待批 → 预警 → 消息），
 * 这一组是每天必走的处理流；再把与学生/班级相关的四页收进「班级」组
 * （学生档案 → 班级公告 → 家校沟通 → 人文关怀），它是查阅与留痕类；
 * 最后「我的」组只放个人中心（绵小城已由桌面悬浮窗承载，不再单列）。
 *
 * 「个人中心」是普通整页路由（/teacher/profile），与其它导航项一致；
 * 低频设置不再使用弹窗形态，避免「同一个个人中心既有弹窗又有整页」两套入口。
 */
const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: '教学工作',
    items: [
      { path: '/teacher', label: '首页', icon: HomeFilled },
      { path: '/teacher/tasks', label: '任务清单', icon: List },
      { path: '/teacher/approval', label: '审批管理', icon: Stamp },
      { path: '/teacher/crisis', label: '心理预警', icon: WarningFilled },
      { path: '/teacher/messages', label: '消息', icon: Message, badge: true },
    ],
  },
  {
    title: '班级育人',
    items: [
      { path: '/teacher/students', label: '学生档案', icon: Notebook },
      { path: '/teacher/announcement', label: '班级公告', icon: Bell },
      { path: '/teacher/guardian', label: '家校沟通', icon: ChatDotRound },
      { path: '/teacher/care-center', label: '人文关怀', icon: Sunny },
    ],
  },
  {
    title: '我的工作台',
    items: [
      // 绵小城（智能体）不再占用侧边栏项：桌面端已有悬浮窗（DesktopPet）承载同一能力，
      // 侧边栏保留会与之重复；移动端底部页签仍保留该入口。
      { path: '/teacher/profile', label: '个人中心', icon: User },
    ],
  },
]


/**
 * 移动端底部导航（5 项）：中间为「绵小城」智能体，最右为「个人中心」。
 * 第 4 项由原「更多」改为「消息」，承载钉钉式消息中心（会话 / 通讯录 / 通知）；
 * 原「更多」内的其余模块已迁至首页「常用功能」宫格，不再占用页签。
 */
const mobileNavItems = computed(() => [
  { key: 'home', label: '首页', icon: HomeFilled, route: '/teacher' },
  { key: 'students', label: '学生', icon: Notebook, route: '/teacher/students' },
  { key: 'agent', label: siteName.value, iconImg: siteLogo.value, center: true, route: '/teacher/agent' },
  { key: 'messages', label: '消息', icon: Message, route: '/teacher/messages', badge: true },
  { key: 'profile', label: '个人中心', icon: User, route: '/teacher/profile' },
])

/** 首页内下钻的子页面：进入后仍归属「首页」页签，避免误亮「消息」 */
const HOME_SUB_ROUTES = ['/teacher/tasks', '/teacher/ai', '/teacher/features']

const activeNavKey = computed(() => {
  const p = route.path
  if (p === '/teacher' || HOME_SUB_ROUTES.some((sub) => p.startsWith(sub))) return 'home'
  if (p.startsWith('/teacher/students')) return 'students'
  if (p.startsWith('/teacher/agent')) return 'agent'
  if (p.startsWith('/teacher/profile')) return 'profile'
  if (p.startsWith('/teacher/messages')) return 'messages'
  // 原「更多」内的模块入口已迁至首页宫格，进入这些子页面时高亮「首页」
  return 'home'
})

/**
 * 底部悬浮导航只属于「一级页面」：即底部五个页签自身对应的路由。
 * 二级及更深层的页面（任务清单 / 审批 / 心理预警 / 成长档案 / 问卷互评 /
 * 家校沟通 / 人文关怀 / 班级公告 / 功能总览等）一律不挂全局导航 ——
 * 它们的返回由子页顶栏的返回键与面包屑承担。
 * 页内下钻的子页（学生详情、学生分析、个人中心设置、聊天详情、今日任务）
 * 通过 useMobileSubPage 登记，打开期间同样隐藏导航。
 */
const TAB_BAR_ROUTES = new Set([
  '/teacher',
  '/teacher/students',
  '/teacher/agent',
  '/teacher/messages',
  '/teacher/profile',
])

const showTabBar = computed(() => isMobile.value && TAB_BAR_ROUTES.has(route.path) && !hasOpenSubPage.value)

// 悬浮胶囊的底部让位（加到页面根元素上，而不是 .main-area 的外层内边距）
useDockInset(showTabBar)

function handleNavSelect(item: any) {
  router.push(item.route)
}

/**
 * 侧边栏高亮判定：
 * - 未单列的子路由先按其归属入口高亮（如 /teacher/portfolio → 学生档案）；
 * - 「首页」只精确匹配自身，避免所有子页都亮首页；
 * - 其余项按自身路径精确匹配或子路径前缀匹配。
 */
function isActive(item: NavItem) {
  const p = route.path
  const owner = SUB_ROUTE_PARENT[p]
  if (owner) return item.path === owner
  if (item.path === '/teacher') return p === '/teacher'
  return p === item.path || p.startsWith(item.path + '/')
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// ===== 多页签（对齐管理端）=====
// 桌面端以页签承载「已打开」的教师端页面；首页常驻，其余进入即追加（个人中心同样是整页，也占页签）。
interface TabItem { path: string; label: string }
const allNav = navGroups.flatMap((g) => g.items)
const tabs = ref<TabItem[]>([{ path: '/teacher', label: '首页' }])

/** 顶栏面包屑 / 页签标题：路由 meta.title 优先，其次按侧边栏归属项取名 */
const currentTitle = computed(() => {
  const metaTitle = route.meta.title as string | undefined
  if (metaTitle) return metaTitle
  const p = route.path
  const owner = SUB_ROUTE_PARENT[p]
  if (owner) return allNav.find((i) => i.path === owner)?.label || ''
  return allNav.find((i) => i.path === p)?.label || ''
})

watch(
  () => route.path,
  (p) => {
    if (!p.startsWith('/teacher')) return
    if (!tabs.value.some((t) => t.path === p)) {
      tabs.value.push({ path: p, label: currentTitle.value || p })
    }
    if (tabs.value.length > 10) tabs.value.shift()
  },
  { immediate: true }
)

function closeTab(path: string) {
  const idx = tabs.value.findIndex((t) => t.path === path)
  if (idx === -1) return
  tabs.value.splice(idx, 1)
  if (route.path === path) {
    const next = tabs.value[idx - 1] || tabs.value[idx] || tabs.value[tabs.value.length - 1]
    router.push(next ? next.path : '/teacher')
  }
}

// ===== 顶栏时钟 =====
const now = ref('')
let clockTimer: number | undefined
function updateClock() {
  const d = new Date()
  now.value = `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
onMounted(() => {
  updateClock()
  clockTimer = window.setInterval(updateClock, 30000)
})

/**
 * 教师身份胶囊：由登录态真实字段拼装（学院 · 职称 · 所带班级）。
 * 这是教师端与其它两端口最直接的视觉区分 —— 打开工作台第一眼就知道「我是谁、带哪个班」。
 */
const teacherIdentity = computed(() => {
  const u = auth.user
  if (!u) return ''
  const parts: string[] = []
  if (u.college) parts.push(u.college)
  if (u.title) parts.push(u.title)
  if (u.class_name) parts.push(`所带 ${u.class_name}`)
  return parts.join(' · ')
})

// 布局创建时立即启动预加载（比 onMounted 更早，确保子页面 setup 阶段缓存已就绪）
prefetchDashboardData()

// 下拉弹层（el-dropdown）会被 teleport 到 body，不在本布局 DOM 内，
// 因此在 body 上打一个端口标记类，供 teacher-ui.css 把下拉浮层样式限定在教师端
document.body.classList.add('teacher-app')

onMounted(() => {
  startUnreadWatch()
  // 勋章结算延后于首屏请求，避免抢占带宽
  window.setTimeout(() => { void syncBadgeAwards() }, 900)
})
onUnmounted(() => {
  stopUnreadWatch()
  if (clockTimer) window.clearInterval(clockTimer)
  document.body.classList.remove('teacher-app')
})

function goTo(path: string) { router.push(path) }

function logout() {
  confirmLogout()
}

/** 打开个人中心整页（桌面端不再是弹窗） */
function goProfilePage() {
  router.push('/teacher/profile')
}
</script>

<style>
body { overflow: hidden; margin: 0; background-color: #0f172a; }
</style>
<style scoped>
/* ============================================================
   教师端外壳：对齐管理端（AdminLayout）设计规范
   · 桌面端：深色渐变侧边栏（可折叠 216 → 64）+ 白色顶栏（折叠按钮/面包屑/时钟）
     + 多页签 + 内容区（.main-area.teacher-scope）
   · 移动端（.app-mobile）：保持原有手机容器行为，仅主区 + 底部页签
   ============================================================ */
.app-shell {
  display: flex;
  height: 100vh;
  background: #f4f6fa;

  /* 底部导航选中态变量：与学生端统一为近黑选中色 + 灰阶圆托 */
  --tab-active-color: #14171a;
  --tab-active-chip: #f0f1f4;
  --tab-idle-color: #4b5158;
  --tab-center-bg: radial-gradient(circle at 32% 26%, #ffffff 0%, #f7f8f9 58%, #eef0f2 100%);
  --tab-center-glow: rgba(20, 23, 26, 0.06);
  --tab-center-ring: rgba(20, 23, 26, 0.10);
  --tab-center-glow-strong: rgba(20, 23, 26, 0.10);
}

/* 移动(App)模式：宽屏下模拟手机容器，居中限宽，交互限制在窄屏内 */
.app-mobile {
  flex-direction: column;
  max-width: 440px;
  margin: 0 auto;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.08), 0 24px 48px rgba(0,0,0,0.4);
}

/* 底部导航是悬浮胶囊（见 MobileTabBar）：左右内缩、居中由组件自身的
   left:50% + translateX(-50%) 完成，宽屏预览时胶囊中心与手机容器中心重合，
   所以这里不再需要把 left/right 拉平到容器宽度。 */

/* ===== 右侧主列：顶栏 → 页签 → 内容区 ===== */
.main-column { flex: 1; display: flex; flex-direction: column; min-width: 0; }

/* ===== Topbar：白底 + 细分割线（与管理端同款高度与阴影） ===== */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; height: 52px; flex-shrink: 0; z-index: 100;
  background: #ffffff;
  border-bottom: 1px solid #eef2f7;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
}
.topbar-left { display: flex; align-items: center; gap: 8px; min-width: 0; }
.topbar-right { display: flex; align-items: center; gap: 12px; color: #64748b; font-size: 13px; white-space: nowrap; }
/* 教师身份胶囊：教师端专属标识，克制扁平（1px 描边 + 浅底，无投影） */
.topbar-identity {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  max-width: 340px;
  padding: 0 10px;
  border: 1px solid #e6e8ec;
  border-radius: 6px;
  background: #f7f8fb;
  color: #475467;
  font-size: 12.5px;
}
.topbar-identity-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:deep(.topbar-left .el-button) { color: #475569; }
.topbar-breadcrumb { font-size: 13px; }

/* 折叠按钮图标动画：折叠/展开两个图标交叉淡入淡出（对齐管理端） */
.sidebar-toggle-btn { flex-shrink: 0; }
.toggle-icon {
  position: relative; display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px;
}
.toggle-ic {
  position: absolute; top: 50%; left: 50%; margin: -9px 0 0 -9px;
  transition: opacity 0.18s ease, transform 0.3s cubic-bezier(0.33, 1, 0.68, 1);
}
.fold-ic { opacity: 1; transform: rotate(0deg); }
.expand-ic { opacity: 0; transform: rotate(-90deg); }
.toggle-icon.collapsed .fold-ic { opacity: 0; transform: rotate(90deg); }
.toggle-icon.collapsed .expand-ic { opacity: 1; transform: rotate(0deg); }

/* ===== 多页签 ===== */
.tabs-bar {
  flex-shrink: 0; background: #ffffff;
  border-bottom: 1px solid #eef2f7;
  padding: 6px 12px 0;
}
.tabs-scroll { display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; padding-bottom: 6px; }
.tabs-scroll::-webkit-scrollbar { display: none; }
.tab-item {
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
  padding: 5px 12px; border-radius: 6px; cursor: pointer;
  font-size: 13px; color: #64748b; user-select: none;
  border: 1px solid transparent; background: transparent;
  transition: all 0.15s ease;
}
.tab-item:hover { background: #f1f5f9; color: #334155; }
.tab-item.active {
  background: #eff6ff; color: #2563eb; font-weight: 600;
  border-color: #dbeafe;
}
.tab-dot { width: 7px; height: 7px; border-radius: 50%; background: #cbd5e1; flex-shrink: 0; transition: background 0.15s; }
.tab-item.active .tab-dot { background: #3b82f6; }
.tab-label { white-space: nowrap; }
.tab-close { border-radius: 50%; color: #94a3b8; }
.tab-close:hover { background: #e2e8f0; color: #334155; }

/* ===== Sidebar：深色渐变 + 职能分组 + 品牌色选中态（对齐管理端） ===== */
.sidebar {
  width: 216px; flex-shrink: 0; display: flex; flex-direction: column;
  background: linear-gradient(180deg, #0f172a 0%, #0b1222 100%);
  border-right: 1px solid rgba(148, 163, 184, 0.08);
  transition: width 0.26s cubic-bezier(0.33, 1, 0.68, 1);
  overflow: hidden;
  z-index: 10;
}
.sidebar.collapsed { width: 64px; }

/* 折叠时文字平滑淡出：只做水平方向（宽度 + 透明度）过渡，
   不引入高度/上下间距的纵向过渡，保证折叠时侧栏内容不上下跳动。 */
.sidebar-text {
  transition:
    opacity 0.2s ease 0.15s,
    width 0.26s cubic-bezier(0.33, 1, 0.68, 1) 0.1s;
}
.sidebar.collapsed .sidebar-text {
  transition:
    opacity 0.1s ease 0s,
    width 0.26s cubic-bezier(0.33, 1, 0.68, 1) 0s;
}

.sidebar-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 14px; flex-shrink: 0; white-space: nowrap;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}
.sidebar.collapsed .sidebar-brand {
  justify-content: center; gap: 0; padding: 14px 0;
  transition: padding 0.26s cubic-bezier(0.33, 1, 0.68, 1), gap 0.26s;
}
.brand-logo { height: 34px; width: 34px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.brand-text { display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.sidebar.collapsed .brand-text { width: 0; opacity: 0; }
.brand-name {
  font-size: 15px; font-weight: 700; color: #f1f5f9;
  letter-spacing: 0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.brand-motto {
  font-size: 11px; color: rgba(148, 163, 184, 0.7);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1; padding: 10px; display: flex; flex-direction: column; gap: 2px;
  overflow-y: auto; overflow-x: hidden;
  /* 隐藏侧边栏滚动框：功能不变，只去掉可见滚动条 */
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.sidebar-nav::-webkit-scrollbar { display: none; width: 0; height: 0; }

/* 分组标题：小号大写标签 + 向右延伸的发丝线，让「工作 / 班级 / 我的」成为清晰三段 */
.nav-group-label {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 10px 5px;
  font-size: 11px; font-weight: 600; letter-spacing: 1.2px;
  color: rgba(148, 163, 184, 0.55);
  white-space: nowrap; overflow: hidden;
}
.nav-group-label::after {
  content: ''; flex: 1; min-width: 8px; height: 1px;
  background: rgba(148, 163, 184, 0.14);
}
.nav-group-label:first-child { padding-top: 6px; }
/* 折叠态仅淡出文字（高度不变），避免内容向上跳动 */
.sidebar.collapsed .nav-group-label { opacity: 0; }

/* 导航项：a 与 button 两种宿主必须完全同款（原生 button 自带边框/灰底/居中） */
.nav-item {
  display: flex; align-items: center; gap: 11px;
  width: 100%; min-height: 36px;
  padding: 8px 11px; border-radius: 8px;
  border: none; background: transparent;
  font-family: inherit; font-size: 13.5px; font-weight: 500;
  text-align: left; cursor: pointer;
  text-decoration: none; color: rgba(203, 213, 225, 0.78);
  transition: background 0.15s ease, color 0.15s ease;
  position: relative; white-space: nowrap;
}
.sidebar.collapsed .nav-item {
  justify-content: center; gap: 0; padding: 8px;
  transition: background 0.15s ease, color 0.15s ease, gap 0.26s cubic-bezier(0.33, 1, 0.68, 1);
}
.nav-item:hover { background: rgba(255, 255, 255, 0.06); color: #ffffff; }
.nav-item.active { background: rgba(59, 130, 246, 0.2); color: #ffffff; font-weight: 600; }
.nav-item.active::before {
  content: ''; position: absolute; left: 0; top: 22%; bottom: 22%; width: 3px;
  border-radius: 0 3px 3px 0; background: #60a5fa;
  box-shadow: 0 0 8px rgba(96, 165, 250, 0.8);
}
.nav-item.active .el-icon { color: #93c5fd; }
.nav-label { flex: 1; overflow: hidden; text-overflow: ellipsis; }
.sidebar.collapsed .nav-label { flex: 0 1 0px; width: 0; opacity: 0; }
/* 侧边栏品牌图标（绵小城形象）：与 el-icon 统一 18px 视觉尺寸 */
.nav-icon-img { width: 18px; height: 18px; object-fit: contain; flex-shrink: 0; }
.nav-badge { position: absolute; top: 4px; right: 6px; }
.sidebar.collapsed .nav-badge { top: 2px; right: 2px; }

/* ===== Sidebar Footer ===== */
.sidebar-footer {
  padding: 10px 12px 14px; flex-shrink: 0;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
}
.teacher-info {
  display: flex; align-items: center; gap: 10px;
  padding: 8px; border-radius: 8px; cursor: pointer;
  transition: background 0.15s, gap 0.26s cubic-bezier(0.33, 1, 0.68, 1), padding 0.26s cubic-bezier(0.33, 1, 0.68, 1);
  white-space: nowrap;
}
.sidebar.collapsed .teacher-info { justify-content: center; gap: 0; padding: 8px 0; }
.teacher-info:hover { background: rgba(255, 255, 255, 0.06); }
.teacher-detail { display: flex; flex-direction: column; gap: 2px; min-width: 0; overflow: hidden; }
.sidebar.collapsed .teacher-detail { width: 0; opacity: 0; }
.teacher-name { font-size: 13px; font-weight: 600; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.teacher-college { font-size: 11px; color: rgba(148, 163, 184, 0.75); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ===== Main ===== */
.main-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
/* 底部让位改由 useDockInset() 加到页面根元素上（见该 composable 的注释），
   外层不再留白，内容才能滚到悬浮胶囊下面 */
.main-area.has-bottom-bar { padding-bottom: 0; }

/* ===== 移动端五页签：悬浮胶囊里等分，中间是绵小城 logo 圆托 ===== */
:deep(.mobile-tab-bar .tab-item) { flex: 1; }

/* ===== 网页端（桌面）整体大小：教师端按 100% 呈现（不再整体缩到 90%） =====
   与管理端同款机制：只缩两侧两列而非 .app-shell 本体，
   避免定高外壳出现底部留白，也让桌宠等布局层浮动件保持像素坐标一致。
   注意 --ui-zoom 不只是样式变量：页面内按视口/像素自行计算的组件
   （整屏对话面板、画布、浮层气泡）会用它换算，必须与下方 zoom 取同一值。
   想再整体放大/缩小，只改这一个数字即可。 */
@media (min-width: 1024px) {
  .app-shell { --ui-zoom: 1; }
  .sidebar,
  .main-column { zoom: var(--ui-zoom); }
}
</style>
