<!-- frontend/src/components/layout/AdminLayout.vue -->
<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-left" style="cursor:pointer" @click="goTo('/admin')">
        <img src="/images/校徽.png" class="topbar-badge" />
        <span class="logo">绵小城</span>
        <span class="logo-divider"></span>
        <span class="motto">博学、笃行、严谨、创新</span>
      </div>
      <div class="topbar-right">
        <el-tooltip :content="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'" placement="bottom">
          <el-button text circle @click="toggleSidebar">
            <el-icon :size="18"><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </header>
    <div class="body-area">
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <nav class="sidebar-nav">
          <div v-if="!sidebarCollapsed" class="nav-group-label">管理</div>
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            <el-tooltip v-if="sidebarCollapsed" :content="item.label" placement="right">
              <el-icon :size="20"><component :is="item.icon" /></el-icon>
            </el-tooltip>
            <el-icon v-else :size="20"><component :is="item.icon" /></el-icon>
            <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
          </router-link>
        </nav>
        <div class="sidebar-footer">
          <el-dropdown trigger="click" placement="top-start">
            <div class="admin-info">
              <el-avatar :size="sidebarCollapsed ? 32 : 40" :src="auth.user?.avatar || ''">
                {{ auth.userName?.[0] }}
              </el-avatar>
              <div v-if="!sidebarCollapsed" class="admin-detail">
                <span class="admin-name">{{ auth.userName }}</span>
                <span class="admin-role">管理员</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-item @click="logout">
                <el-icon style="margin-right:6px"><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </template>
          </el-dropdown>
        </div>
      </aside>
      <main class="main-area">
        <div class="page-container">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  HomeFilled, Document, User, UserFilled,
  SwitchButton, Fold, Expand, ChatDotRound, Setting, Star
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const sidebarCollapsed = ref(false)

const navItems = [
  { path: '/admin', label: '首页', icon: HomeFilled },
  { path: '/admin/knowledge', label: '知识库', icon: Document },
  { path: '/admin/teachers', label: '教师管理', icon: User },
  { path: '/admin/students', label: '学生管理', icon: UserFilled },
  { path: '/admin/organizations', label: '院系班级', icon: HomeFilled },
  { path: '/admin/courses', label: '课程表管理', icon: Document },
  { path: '/admin/figures', label: '人物风采', icon: Star },
  { path: '/admin/feedbacks', label: '反馈管理', icon: ChatDotRound },
  { path: '/admin/settings', label: '系统设置', icon: Setting },
]

function isActive(path: string) {
  return route.path === path
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function goTo(path: string) { router.push(path) }

function logout() {
  auth.logout()
  router.push('/')
}
</script>

<style>
body { overflow: hidden; margin: 0; }
</style>
<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #f5faff 0%, #f0f8ff 50%, #f8fbff 100%);
}

.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px; border-bottom: 1px solid rgba(64,158,255,0.1);
  background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
  flex-shrink: 0; z-index: 100;
  box-shadow: 0 1px 8px rgba(64,158,255,0.06);
}
.topbar-left { display: flex; align-items: center; gap: 8px; }
.topbar-badge { height: 32px; width: auto; border-radius: 4px; }
.logo { font-size: 20px; font-weight: 700; color: var(--accent-blue); letter-spacing: 1px; }
.logo-divider { width: 1px; height: 20px; background: var(--border-color); margin: 0 6px; }
.motto {
  font-size: 14px; font-weight: 600;
  background: linear-gradient(135deg, #c41d7f, #e8a020);
  background-clip: text; -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 4px;
}
.topbar-right { display: flex; align-items: center; gap: 4px; }

.body-area { display: flex; flex: 1; min-height: 0; }

.sidebar {
  width: 220px; flex-shrink: 0; display: flex; flex-direction: column;
  background: rgba(255,255,255,0.85); backdrop-filter: blur(24px);
  border-right: 1px solid rgba(64,158,255,0.08);
  box-shadow: 1px 0 12px rgba(0,0,0,0.03);
  transition: width 0.2s ease;
  overflow: hidden;
}
.sidebar.collapsed { width: 64px; }

.sidebar-nav { flex: 1; padding: 16px 10px; display: flex; flex-direction: column; gap: 2px; }

.nav-group-label {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 1.5px;
  padding: 8px 12px 6px; margin-top: 4px;
}

.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-radius: 10px;
  text-decoration: none; color: var(--text-secondary); font-size: 14px; font-weight: 500;
  transition: all 0.15s ease; position: relative; white-space: nowrap;
}
.sidebar.collapsed .nav-item { justify-content: center; padding: 10px; border-radius: 10px; }
.nav-item:hover { background: var(--hover-bg); color: var(--accent-blue); }
.nav-item.active {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff; font-weight: 600;
  box-shadow: 0 4px 12px rgba(64,158,255,0.3);
}
.nav-item.active .el-icon { color: #fff; }
.nav-label { flex: 1; }

.sidebar-footer {
  padding: 12px 12px 16px; border-top: 1px solid rgba(64,158,255,0.06);
}
.admin-info {
  display: flex; align-items: center; gap: 14px;
  padding: 10px 12px; border-radius: 10px; cursor: pointer;
  transition: background 0.15s;
}
.sidebar.collapsed .admin-info { justify-content: center; padding: 10px 0; }
.admin-info:hover { background: var(--hover-bg); }
.admin-detail { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.admin-name { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.admin-role { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.main-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.page-container {
  flex: 1; overflow-y: auto; overflow-x: hidden;
  padding: 0;
}
.page-container > :deep(.students-page),
.page-container > :deep(.teachers-page),
.page-container > :deep(.knowledge-page),
.page-container > :deep(.data-page),
.page-container > :deep(.setting-page),
.page-container > :deep(.feedback-page),
.page-container > :deep(.figures-page),
.page-container > :deep(.admin-home) {
  padding: 24px 28px;
  min-height: 100%;
}
</style>
