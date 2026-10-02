<!-- frontend/src/components/layout/AdminLayout.vue -->
<template>
  <div class="app-shell">
    <!-- 深色侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed, 'mobile-open': mobileOpen }">
      <div class="sidebar-brand" style="cursor:pointer" @click="goTo('/admin')">
        <img :src="brand.logo || DEFAULT_LOGO" class="brand-logo" />
        <div class="brand-text sidebar-text">
          <span class="brand-name">{{ brand.siteName || '绵小城' }}</span>
          <span class="brand-motto">智慧校园 · 管理端</span>
        </div>
      </div>
      <nav class="sidebar-nav">
        <template v-for="group in navGroups" :key="group.label">
          <div class="nav-group-label sidebar-text">{{ group.label }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
            @click="onNavClick"
          >
            <el-tooltip v-if="sidebarCollapsed" :content="item.label" placement="right">
              <el-icon :size="20"><component :is="item.icon" /></el-icon>
            </el-tooltip>
            <el-icon v-else :size="20"><component :is="item.icon" /></el-icon>
            <span class="nav-label sidebar-text">{{ item.label }}</span>
          </router-link>
        </template>
      </nav>
      <div class="sidebar-footer">
        <el-dropdown trigger="click" placement="top-start">
          <div class="admin-info">
            <el-avatar :size="sidebarCollapsed ? 32 : 36" :src="auth.user?.avatar || ''">
              {{ auth.userName?.[0] }}
            </el-avatar>
            <div class="admin-detail sidebar-text">
              <span class="admin-name">{{ auth.userName }}</span>
              <span class="admin-role">管理员</span>
            </div>
          </div>
          <template #dropdown>
            <el-dropdown-item @click="logout">
              <el-icon style="margin-right:6px"><LogOut /></el-icon>退出登录
            </el-dropdown-item>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <!-- 移动端抽屉遮罩 -->
    <transition name="mask-fade">
      <div v-if="mobileOpen" class="sidebar-mask" @click="toggleSidebar"></div>
    </transition>

    <!-- 右侧主区域 -->
    <div class="main-column">
      <header class="topbar">
        <div class="topbar-left">
          <el-tooltip :content="toggleState ? '展开侧边栏' : '折叠侧边栏'" placement="bottom">
            <el-button text circle @click="toggleSidebar" class="sidebar-toggle-btn">
              <span class="toggle-icon" :class="{ collapsed: toggleState }">
                <el-icon :size="18" class="toggle-ic fold-ic"><PanelLeftClose /></el-icon>
                <el-icon :size="18" class="toggle-ic expand-ic"><PanelLeftOpen /></el-icon>
              </span>
            </el-button>
          </el-tooltip>
          <el-breadcrumb separator="/" class="topbar-breadcrumb">
            <el-breadcrumb-item :to="{ path: '/admin' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle && currentTitle !== '首页'">{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="topbar-right">
          <span class="topbar-clock">{{ now }}</span>
        </div>
      </header>

      <!-- 多页签 -->
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
              <X />
            </el-icon>
          </div>
        </div>
      </div>

      <main class="main-area">
        <div class="page-container">
          <router-view v-slot="{ Component }">
            <component :is="Component" />
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getSettings } from '@/api/setting'
import {
  House, Library, TriangleAlert,
  User, Users, Building2,
  CalendarDays, MessageSquare, Settings,
  LogOut, PanelLeftClose, PanelLeftOpen, X
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const DEFAULT_LOGO = '/images/校徽_圆形.png'
const brand = reactive<{ siteName: string; logo: string }>({ siteName: '', logo: '' })

onMounted(async () => {
  try {
    const data = await getSettings()
    const map: Record<string, string> = {}
    data.forEach((s) => {
      if (s.key && s.value !== undefined) map[s.key] = s.value
    })
    brand.siteName = map['site_name'] || ''
    brand.logo = map['site_logo'] || ''
    document.title = `${brand.siteName || '绵小城'} · 管理后台`
  } catch (error) {
    // 设置读取失败时使用默认品牌
    document.title = '绵小城 · 管理后台'
  }
})

// ===== 管理端页面预加载：切换页面动画无延迟 =====
// 登录进入管理端后，利用浏览器空闲时间预取全部子页面 chunk，
// 切换时组件、样式与 CSS 动画均已就绪，避免懒加载下载造成的等待与动画延迟
const ADMIN_PAGE_LOADERS: Array<() => Promise<unknown>> = [
  () => import('@/views/admin/HomePage.vue'),
  () => import('@/views/admin/KnowledgePage.vue'),
  () => import('@/views/admin/CrisisMonitorPage.vue'),
  () => import('@/views/admin/TeachersPage.vue'),
  () => import('@/views/admin/StudentsPage.vue'),
  () => import('@/views/admin/OrganizationsPage.vue'),
  () => import('@/views/admin/CourseSchedulePage.vue'),
  () => import('@/views/admin/FeedbackPage.vue'),
  () => import('@/views/admin/SettingPage.vue'),
]

function prefetchAdminPages() {
  // 预取失败不影响正常使用（导航时仍会按需加载）
  ADMIN_PAGE_LOADERS.forEach((load) => load().catch(() => {}))
}

onMounted(() => {
  const win = window as Window & {
    requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => void
  }
  if (typeof win.requestIdleCallback === 'function') {
    win.requestIdleCallback(prefetchAdminPages, { timeout: 1500 })
  } else {
    setTimeout(prefetchAdminPages, 50)
  }
})

// ===== 侧边栏：桌面折叠 + 移动端抽屉 =====
const sidebarCollapsed = ref(false)
const mobileOpen = ref(false)

// 桌面/平板：窗口进入窄屏（<=900px）时自动折叠侧栏
const narrowQuery = window.matchMedia('(max-width: 900px)')
function applyNarrow(ev: MediaQueryList | MediaQueryListEvent) {
  if (ev.matches) sidebarCollapsed.value = true
}
applyNarrow(narrowQuery)
narrowQuery.addEventListener('change', applyNarrow)

// 移动端（<=480px）：侧栏变抽屉，默认隐藏
const mobileQuery = window.matchMedia('(max-width: 480px)')
const isMobile = ref(mobileQuery.matches)
function applyMobile(ev: MediaQueryList | MediaQueryListEvent) {
  isMobile.value = ev.matches
  if (!ev.matches) mobileOpen.value = false
}
applyMobile(mobileQuery)
mobileQuery.addEventListener('change', applyMobile)

// 按钮图标状态：移动端跟随抽屉开合，桌面跟随折叠
const toggleState = computed(() => (isMobile.value ? mobileOpen.value : sidebarCollapsed.value))

function toggleSidebar() {
  if (isMobile.value) {
    mobileOpen.value = !mobileOpen.value
    return
  }
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 移动端点击导航后自动收起抽屉
function onNavClick() {
  if (isMobile.value) mobileOpen.value = false
}

interface NavItem { path: string; label: string; icon: unknown }
interface NavGroup { label: string; items: NavItem[] }

const navGroups: NavGroup[] = [
  {
    label: '概览',
    items: [
      { path: '/admin', label: '首页', icon: House },
      { path: '/admin/knowledge', label: '知识库', icon: Library },
      { path: '/admin/crisis', label: '危机预警', icon: TriangleAlert },
    ],
  },
  {
    label: '人员管理',
    items: [
      { path: '/admin/teachers', label: '教师管理', icon: User },
      { path: '/admin/students', label: '学生管理', icon: Users },
      { path: '/admin/organizations', label: '院系班级', icon: Building2 },
    ],
  },
  {
    label: '系统管理',
    items: [
      { path: '/admin/courses', label: '课程表管理', icon: CalendarDays },
      { path: '/admin/feedbacks', label: '反馈管理', icon: MessageSquare },
      { path: '/admin/settings', label: '系统设置', icon: Settings },
    ],
  },
]

function isActive(path: string) {
  return route.path === path
}

function goTo(path: string) { router.push(path) }

function logout() {
  auth.logout()
  router.push('/')
}

// ===== 多页签 =====
interface TabItem { path: string; label: string }
const tabs = ref<TabItem[]>([{ path: '/admin', label: '首页' }])

const allNav = navGroups.flatMap((g) => g.items)

const currentTitle = computed(() => {
  const t = route.meta.title as string | undefined
  if (t) return t
  return allNav.find((i) => i.path === route.path)?.label || ''
})

watch(
  () => route.path,
  (p) => {
    if (!p.startsWith('/admin')) return
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
    router.push(next ? next.path : '/admin')
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
onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<style>
body { overflow: hidden; margin: 0; }
</style>
<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  background: #f4f6fa;
}

/* ===== 深色侧边栏：豆包式平滑收缩 ===== */
.sidebar {
  width: 220px; flex-shrink: 0; display: flex; flex-direction: column;
  background: linear-gradient(180deg, #0f172a 0%, #0b1222 100%);
  border-right: 1px solid rgba(148, 163, 184, 0.08);
  transition: width 0.26s cubic-bezier(0.33, 1, 0.68, 1);
  overflow: hidden;
  z-index: 10;
}
.sidebar.collapsed { width: 64px; }

/* 文字内容平滑淡入淡出（展开延迟淡入，折叠立即淡出）
   注意：只做水平方向（宽度 + 透明度）过渡，绝不引入高度/上下间距的
   纵向过渡，保证折叠时侧边栏内容不会上下移动 */
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
  padding: 14px 14px; flex-shrink: 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
  white-space: nowrap;
}
.sidebar.collapsed .sidebar-brand { justify-content: center; gap: 0; padding: 14px 0; transition: padding 0.26s cubic-bezier(0.33, 1, 0.68, 1), gap 0.26s; }
.brand-logo { height: 36px; width: 36px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.brand-text { display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.sidebar.collapsed .brand-text { width: 0; opacity: 0; }
.brand-name {
  font-size: 16px; font-weight: 700; color: #f1f5f9;
  letter-spacing: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.brand-motto {
  font-size: 11px; color: rgba(148, 163, 184, 0.7);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1; overflow-y: auto; padding: 10px 10px;
  display: flex; flex-direction: column; gap: 2px;
  scrollbar-width: none;
}
.sidebar-nav::-webkit-scrollbar { display: none; }

.nav-group-label {
  font-size: 11px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase;
  color: rgba(148, 163, 184, 0.5);
  padding: 10px 10px 4px;
  white-space: nowrap; overflow: hidden;
  max-height: 40px;
}
/* 折叠态：仅淡出文字（高度不变），避免分组标题收缩引起内容向上跳动 */
.sidebar.collapsed .nav-group-label {
  opacity: 0;
  max-height: 40px;
  padding: 10px 10px 4px;
}

.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 9px 12px; border-radius: 8px;
  text-decoration: none; font-size: 14px; font-weight: 500;
  color: rgba(203, 213, 225, 0.75);
  transition: all 0.15s ease; position: relative; white-space: nowrap;
}
.sidebar.collapsed .nav-item {
  justify-content: center; gap: 0; padding: 9px;
  transition: all 0.15s ease, gap 0.26s cubic-bezier(0.33, 1, 0.68, 1);
}
.nav-item:hover { background: rgba(255, 255, 255, 0.06); color: #ffffff; }
.nav-item.active {
  background: rgba(59, 130, 246, 0.2);
  color: #ffffff; font-weight: 600;
}
.nav-item.active::before {
  content: ''; position: absolute; left: 0; top: 22%; bottom: 22%; width: 3px;
  border-radius: 0 3px 3px 0; background: #60a5fa;
  box-shadow: 0 0 8px rgba(96, 165, 250, 0.8);
}
.nav-item.active .el-icon { color: #93c5fd; }
.nav-label { flex: 1; overflow: hidden; text-overflow: ellipsis; }
.sidebar.collapsed .nav-label { flex: 0 1 0px; width: 0; opacity: 0; }

.sidebar-footer {
  padding: 10px 12px 14px; flex-shrink: 0;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
}
.admin-info {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 8px; border-radius: 8px; cursor: pointer;
  transition: background 0.15s, gap 0.26s cubic-bezier(0.33, 1, 0.68, 1), padding 0.26s cubic-bezier(0.33, 1, 0.68, 1);
  white-space: nowrap;
}
.sidebar.collapsed .admin-info { justify-content: center; gap: 0; padding: 8px 0; }
.admin-info:hover { background: rgba(255, 255, 255, 0.06); }
.admin-detail { display: flex; flex-direction: column; gap: 2px; min-width: 0; overflow: hidden; }
.sidebar.collapsed .admin-detail { width: 0; opacity: 0; }
.admin-name { font-size: 13px; font-weight: 600; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.admin-role { font-size: 11px; color: rgba(148, 163, 184, 0.75); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ===== 移动端抽屉模式 ===== */
.sidebar-mask {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 1100;
}
.mask-fade-enter-active, .mask-fade-leave-active { transition: opacity 0.26s ease; }
.mask-fade-enter-from, .mask-fade-leave-to { opacity: 0; }

/* ===== 折叠按钮图标动画 ===== */
.sidebar-toggle-btn {
  flex-shrink: 0;
}
.toggle-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
}
.toggle-ic {
  position: absolute;
  top: 50%;
  left: 50%;
  margin: -9px 0 0 -9px;
  transition: opacity 0.18s ease, transform 0.3s cubic-bezier(0.33, 1, 0.68, 1);
}
.fold-ic { opacity: 1; transform: translate(0, 0) rotate(0deg); }
.expand-ic { opacity: 0; transform: translate(0, 0) rotate(-90deg); }
.toggle-icon.collapsed .fold-ic { opacity: 0; transform: translate(0, 0) rotate(90deg); }
.toggle-icon.collapsed .expand-ic { opacity: 1; transform: translate(0, 0) rotate(0deg); }

/* ===== 右侧主区域 ===== */
.main-column { flex: 1; display: flex; flex-direction: column; min-width: 0; }

.topbar {
  height: 52px; flex-shrink: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px;
  background: #ffffff;
  border-bottom: 1px solid #eef2f7;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
}
.topbar-left { display: flex; align-items: center; gap: 8px; min-width: 0; }
.topbar-right { display: flex; align-items: center; gap: 12px; color: #64748b; font-size: 13px; white-space: nowrap; }
:deep(.topbar-left .el-button) { color: #475569; }

.tabs-bar {
  flex-shrink: 0; background: #ffffff;
  border-bottom: 1px solid #eef2f7;
  padding: 6px 12px 0;
}
.tabs-scroll {
  display: flex; gap: 6px; overflow-x: auto;
  scrollbar-width: none; padding-bottom: 6px;
}
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

.main-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.page-container {
  /* 允许水平方向滚动：宽表格（如反馈管理）超出容器时可横向滑动查看 */
  flex: 1; overflow: auto;
}

/* 所有管理页统一内边距（通配路由组件根节点，保证各页一致） */
.page-container > :deep(div) {
  padding: 24px 28px;
  min-height: 100%;
}

/* ===== 页面切换过渡：已按需求取消入场动画（保留词云、图表动画） ===== */

/* ===== 响应式断点：布局自适应，不改变内容样式 ===== */
@media (max-width: 1200px) {
  .sidebar { width: 200px; }
  .sidebar.collapsed { width: 64px; }
}

@media (max-width: 768px) {
  .topbar { padding: 0 10px; height: 48px; }
  .topbar-breadcrumb { display: none; }
  .topbar-clock { font-size: 12px; }
  .tabs-bar { padding: 4px 8px 0; }
  .page-container > :deep(div) { padding: 14px 16px; }
}

@media (max-width: 480px) {
  /* 侧栏变为抽屉：固定定位、滑入滑出，展开时显示完整菜单 */
  .sidebar,
  .sidebar.collapsed {
    position: fixed; left: 0; top: 0; bottom: 0;
    width: 220px !important;
    transform: translateX(-100%);
    transition: transform 0.26s cubic-bezier(0.33, 1, 0.68, 1);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.28);
  }
  .sidebar.mobile-open,
  .sidebar.mobile-open.collapsed { transform: translateX(0); }

  /* 抽屉内强制显示完整菜单（覆盖折叠态隐藏规则） */
  .sidebar.collapsed .sidebar-brand { justify-content: flex-start; gap: 10px; padding: 14px 14px; }
  .sidebar.collapsed .brand-text,
  .sidebar.collapsed .admin-detail { width: auto; opacity: 1; }
  .sidebar.collapsed .nav-label { width: auto; opacity: 1; flex: 0 0 auto; }
  .sidebar.collapsed .nav-group-label { opacity: 1; max-height: 40px; padding: 10px 10px 4px; }
  .sidebar.collapsed .nav-item { justify-content: flex-start; gap: 12px; padding: 9px 12px; }
  .sidebar.collapsed .admin-info { justify-content: flex-start; gap: 12px; padding: 8px 8px; }

  .brand-logo { height: 30px; width: 30px; }
  .topbar-clock { display: none; }
  .page-container > :deep(div) { padding: 12px 12px; }
}
</style>