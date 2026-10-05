<template>
  <div class="app-shell" :class="{ 'app-mobile': isMobile }">
    <header v-if="!isMobile" class="topbar">
      <div class="topbar-left" style="cursor:pointer" @click="goTo('/teacher')">
        <img src="/images/校徽_圆形.png" class="topbar-badge" />
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
      <aside v-if="!isMobile" class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <nav class="sidebar-nav">
          <template v-for="g in navGroups" :key="g.title">
            <div v-if="!sidebarCollapsed" class="nav-group-title">{{ g.title }}</div>
            <router-link
              v-for="item in g.items"
              :key="item.path"
              :to="item.path"
              class="nav-item"
              :class="{ active: isActive(item.path) }"
            >
              <el-icon :size="18"><component :is="item.icon" /></el-icon>
              <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
              <el-badge
                v-if="item.badge && unreadCount > 0"
                :value="unreadCount"
                class="nav-badge"
              />
            </router-link>
          </template>
        </nav>
        <div class="sidebar-footer">
          <el-dropdown trigger="click" placement="top-start">
            <div class="teacher-info">
              <el-avatar :size="sidebarCollapsed ? 32 : 40" :src="auth.user?.avatar || ''">
                {{ auth.userName?.[0] }}
              </el-avatar>
              <div v-if="!sidebarCollapsed" class="teacher-detail">
                <span class="teacher-name">{{ auth.userName }}</span>
                <span class="teacher-college">{{ auth.user?.college || '未知学院' }}</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-item @click="openProfile">
                <el-icon style="margin-right:6px"><User /></el-icon>个人资料
              </el-dropdown-item>
              <el-dropdown-item divided @click="logout">
                <el-icon style="margin-right:6px"><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </template>
          </el-dropdown>
        </div>
      </aside>
      <main class="main-area" :class="{ 'has-bottom-bar': isMobile }">
        <router-view v-slot="{ Component }">
          <keep-alive :include="cachedNames">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </main>
    </div>

    <MobileTabBar
      v-if="isMobile"
      :items="mobileNavItems"
      :active-key="activeNavKey"
      :unread-count="unreadCount"
      @select="handleNavSelect"
    />

    <el-dialog v-model="showProfile" title="个人资料" width="800px" :close-on-click-modal="false">
      <div class="profile-layout">
        <div class="profile-avatar-col">
          <div class="avatar-upload-wrap" @click="triggerFileInput">
            <el-avatar :size="120" :src="profileForm.avatar" shape="square" class="profile-avatar">
              {{ profileForm.name?.[0] || '?' }}
            </el-avatar>
            <div class="avatar-overlay">
              <el-icon :size="24"><CameraFilled /></el-icon>
              <span>更换头像</span>
            </div>
          </div>
          <input ref="fileInputRef" type="file" accept="image/*" style="display:none" @change="onFileSelect" />
        </div>
        <div class="profile-form-col">
          <el-form :model="profileForm" label-width="90px">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="工号"><el-input v-model="profileForm.username" disabled /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="姓名"><el-input v-model="profileForm.name" disabled /></el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="性别" required>
                  <el-select v-model="profileForm.gender" placeholder="请选择性别" style="width:100%">
                    <el-option label="男" value="男" />
                    <el-option label="女" value="女" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="年龄">
                  <el-input-number v-model="profileForm.age" :min="1" :max="120" style="width:100%" placeholder="1-120" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="学院"><el-input v-model="profileForm.college" disabled /></el-form-item>
            <el-form-item label="班级"><el-input v-model="profileForm.class_name" placeholder="请输入所带班级" /></el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="职称"><el-input v-model="profileForm.title" placeholder="请输入职称/职务" /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="所属单位"><el-input v-model="profileForm.department" placeholder="请输入所属单位" /></el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="籍贯"><el-input v-model="profileForm.hometown" placeholder="请输入籍贯" /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="联系电话" required><el-input v-model="profileForm.phone" placeholder="请输入手机号" /></el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>
      <template #footer>
        <div style="display: flex; justify-content: space-between; width: 100%">
          <el-button type="warning" @click="showChangePassword = true">修改密码</el-button>
          <div>
            <el-button @click="showProfile = false">取消</el-button>
            <el-button type="primary" @click="handleSaveProfile" :loading="saving">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showCrop" title="裁剪头像" width="420px" :close-on-click-modal="false" @opened="onCropDialogOpened">
      <div class="crop-container">
        <img ref="cropImgRef" style="max-width:100%;display:block" />
      </div>
      <template #footer>
        <el-button @click="cancelCrop">取消</el-button>
        <el-button type="primary" @click="handleCropConfirm">确认裁剪</el-button>
      </template>
    </el-dialog>

    <!-- 改密对话框统一走公共组件（管理端同款），避免校验规则各处漂移 -->
    <ChangePasswordDialog v-model="showChangePassword" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { updateProfile } from '@/api/user'
import ChangePasswordDialog from '@/components/common/ChangePasswordDialog.vue'
import { uploadFile } from '@/api/upload'
import { getConversations, type ConversationOut } from '@/api/messages'
import { ElMessage } from 'element-plus'
import Cropper from 'cropperjs'
import { useResponsive } from '@/composables/useResponsive'
import MobileTabBar from '@/components/responsive/MobileTabBar.vue'
import { prefetchDashboardData } from '@/utils/teacherDashboardCache'
import {
  HomeFilled, ChatDotRound, User, Message, Notebook, Stamp, WarningFilled,
  SwitchButton, CameraFilled, Fold, Expand, Collection, EditPen, Sunny, Connection, Grid, Bell
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// 缓存 teacher 端重型页面，避免切换时 ECharts 重建与数据重拉
const cachedNames = ['teacher-home', 'teacher-students']

const sidebarCollapsed = ref(false)
const showProfile = ref(false)
const saving = ref(false)
const fileInputRef = ref<HTMLInputElement>()
const showCrop = ref(false)
const cropImgRef = ref<HTMLImageElement>()
let cropper: Cropper | null = null
let pendingImageSrc = ''
const unreadCount = ref(0)
let pollTimer: ReturnType<typeof setInterval> | null = null

const { isMobile } = useResponsive()

/**
 * 桌面端侧边栏导航：按职能分组（概览 / 学生 / 我的 / 其他），
 * 与移动端「首页 / 学生 / 更多」的分区口径一致，保证同一功能不重复出现。
 */
const navGroups = [
  {
    title: '概览',
    items: [{ path: '/teacher', label: '首页', icon: HomeFilled }],
  },
  {
    title: '学生',
    items: [
      { path: '/teacher/students', label: '学生档案', icon: Notebook },
      { path: '/teacher/approval', label: '审批管理', icon: Stamp },
      { path: '/teacher/crisis', label: '预警工作台', icon: WarningFilled },
      { path: '/teacher/announcement', label: '班级公告', icon: Bell },
    ],
  },
  {
    title: '我的',
    items: [
      { path: '/teacher/portfolio', label: '成长档案', icon: Collection },
      { path: '/teacher/survey', label: '问卷互评', icon: EditPen },
      { path: '/teacher/care-center', label: '关怀中心', icon: Sunny },
      { path: '/teacher/guardian', label: '家校沟通', icon: Connection },
    ],
  },
  {
    title: '其他',
    items: [
      { path: '/teacher/messages', label: '消息', icon: Message, badge: true },
      { path: '/teacher/agent', label: '智能助手', icon: ChatDotRound },
    ],
  },
]

/**
 * 移动端底部导航（5 项）：中间为「绵小城」智能体，最右为「个人中心」。
 * 首页 / 学生 / 更多 为功能页签；消息、审批、预警等模块统一收敛到「更多」宫格，避免重复入口。
 */
const mobileNavItems = [
  { key: 'home', label: '首页', icon: HomeFilled, route: '/teacher' },
  { key: 'students', label: '学生', icon: Notebook, route: '/teacher/students' },
  { key: 'agent', label: '绵小城', iconImg: '/images/校徽_圆形.png', center: true, route: '/teacher/agent' },
  { key: 'more', label: '更多', icon: Grid, route: '/teacher/more' },
  { key: 'profile', label: '个人中心', icon: User, route: '/teacher/profile' },
]

const activeNavKey = computed(() => {
  const p = route.path
  if (p === '/teacher') return 'home'
  if (p.startsWith('/teacher/students')) return 'students'
  if (p.startsWith('/teacher/agent')) return 'agent'
  if (p.startsWith('/teacher/profile')) return 'profile'
  // 其余模块（审批 / 预警 / 公告 / 成长档案 / 问卷互评 / 关怀 / 家校 / 消息）统一高亮「更多」
  return 'more'
})

function handleNavSelect(item: any) {
  router.push(item.route)
}

function isActive(path: string) {
  return route.path === path
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

async function pollUnread() {
  if (auth.role !== 'teacher' && auth.role !== 'admin') return
  try {
    const convs: ConversationOut[] = await getConversations()
    unreadCount.value = convs.reduce((sum, c) => sum + c.unread_count, 0)
  } catch {}
}

// 布局创建时立即启动预加载（比 onMounted 更早，确保子页面 setup 阶段缓存已就绪）
prefetchDashboardData()

onMounted(() => {
  pollUnread()
  pollTimer = setInterval(pollUnread, 5000)
})
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

function goTo(path: string) { router.push(path) }

function logout() {
  auth.logout()
  router.push('/')
}

const showChangePassword = ref(false)

const profileForm = reactive({
  username: '', name: '', college: '',
  avatar: '', gender: '', age: 30, title: '', hometown: '', phone: '', department: '',
  class_name: '',
})

function openProfile() {
  const u = auth.user
  if (!u) return
  profileForm.username = u.username
  profileForm.name = u.name
  profileForm.college = u.college || ''
  profileForm.avatar = u.avatar || ''
  profileForm.gender = u.gender || ''
  profileForm.age = u.age ?? 30
  profileForm.title = u.title || ''
  profileForm.hometown = u.hometown || ''
  profileForm.phone = u.phone || ''
  profileForm.department = u.department || ''
  profileForm.class_name = u.class_name || ''
  showProfile.value = true
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input?.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    pendingImageSrc = ev.target?.result as string
    showCrop.value = true
  }
  reader.readAsDataURL(file)
  input.value = ''
}

function onCropDialogOpened() {
  const img = cropImgRef.value
  if (!img || !pendingImageSrc) return
  img.src = pendingImageSrc
  const start = () => {
    if (cropper) { cropper.destroy(); cropper = null }
    cropper = new Cropper(img, { aspectRatio: 1, viewMode: 1, dragMode: 'move', minCropBoxWidth: 100 })
  }
  if (img.complete) { start() } else { img.onload = start }
}

function cancelCrop() {
  showCrop.value = false
  if (cropper) { cropper.destroy(); cropper = null }
}

async function handleCropConfirm() {
  if (!cropper) return
  const canvas = cropper.getCroppedCanvas({ width: 200, height: 200 })
  if (!canvas) { ElMessage.error('裁剪失败'); return }
  const blob = await new Promise<Blob | null>((r) => canvas.toBlob((b) => r(b), 'image/jpeg', 0.9))
  if (!blob) { ElMessage.error('裁剪失败'); return }
  const file = new File([blob], 'avatar.jpg', { type: 'image/jpeg' })
  try {
    const result: any = await uploadFile(file)
    profileForm.avatar = result.url
    showCrop.value = false
    if (cropper) { cropper.destroy(); cropper = null }
    ElMessage.success('头像已上传')
  } catch {
    ElMessage.error('头像上传失败')
  }
}

async function handleSaveProfile() {
  saving.value = true
  try {
    const updated = await updateProfile({
      avatar: profileForm.avatar || null,
      gender: profileForm.gender || null,
      age: profileForm.age || null,
      title: profileForm.title || null,
      hometown: profileForm.hometown || null,
      phone: profileForm.phone || null,
      department: profileForm.department || null,
      class_name: profileForm.class_name || null,
    })
    auth.updateUser(updated as any)
    ElMessage.success('保存成功')
    showProfile.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style>
body { overflow: hidden; margin: 0; background-color: #0f172a; }
</style>
<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f6f8;
}

/* 移动(App)模式：宽屏下模拟手机容器，居中限宽，交互限制在窄屏内 */
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

/* ===== Topbar：白底 + 细分割线（克制、主流的企业后台观感） ===== */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px;
  background: #ffffff;
  border-bottom: 1px solid #eaecf0;
  flex-shrink: 0; z-index: 100;
}
.topbar-left { display: flex; align-items: center; gap: 8px; position: relative; z-index: 101; }
.topbar-badge { height: 28px; width: 28px; border-radius: 8px; object-fit: contain; }
.logo { font-size: 16px; font-weight: 700; color: #101828; letter-spacing: 0.2px; }
.logo-divider { width: 1px; height: 18px; background: #eaecf0; margin: 0 6px; }
.motto {
  font-size: 13px; font-weight: 500;
  color: #667085;
  letter-spacing: 1px;
}
.topbar-right { display: flex; align-items: center; gap: 4px; }

/* ===== Body ===== */
.body-area { display: flex; flex: 1; min-height: 0; }

/* ===== Sidebar：白底 + 职能分组 + 浅底选中态（对齐主流后台侧边栏） ===== */
.sidebar {
  width: 216px; flex-shrink: 0; display: flex; flex-direction: column;
  background: #ffffff;
  border-right: 1px solid #eaecf0;
  transition: width 0.2s ease;
  overflow: hidden;
}
.sidebar.collapsed { width: 64px; }

.sidebar-nav {
  flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 2px;
  overflow-y: auto; overflow-x: hidden;
}

.nav-group-title {
  padding: 12px 10px 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: #98a2b3;
  letter-spacing: 0.4px;
}
.nav-group-title:first-child { padding-top: 6px; }

.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 8px;
  text-decoration: none; color: #475467; font-size: 13.5px; font-weight: 500;
  transition: background 0.15s ease, color 0.15s ease;
  position: relative; white-space: nowrap;
}
.sidebar.collapsed .nav-item { justify-content: center; padding: 9px; }
.nav-item:hover { background: #f9fafb; color: #101828; }
.nav-item.active { background: #eff4ff; color: #1d4ed8; font-weight: 600; }
.nav-item.active::before {
  content: '';
  position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: 18px; border-radius: 0 3px 3px 0;
  background: #2563eb;
}
.nav-item.active .el-icon { color: #1d4ed8; }
.nav-label { flex: 1; }
.nav-badge { position: absolute; top: 4px; right: 6px; }

/* ===== Sidebar Footer ===== */
.sidebar-footer {
  padding: 12px; border-top: 1px solid #eaecf0;
}
.teacher-info {
  display: flex; align-items: center; gap: 14px;
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  transition: background 0.15s;
}
.sidebar.collapsed .teacher-info { justify-content: center; padding: 10px 0; }
.teacher-info:hover { background: var(--hover-bg); }
.teacher-detail { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.teacher-name { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.teacher-college { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ===== Main ===== */
.main-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.main-area.has-bottom-bar { padding-bottom: 56px; }

/* ===== Profile Dialog ===== */
.profile-layout { display: flex; gap: 28px; }
.profile-avatar-col { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; padding-top: 12px; }
.avatar-upload-wrap { position: relative; cursor: pointer; border-radius: 8px; overflow: hidden; width: 120px; height: 120px; }
.avatar-upload-wrap .profile-avatar { width: 120px !important; height: 120px !important; font-size: 40px; }
.avatar-overlay {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 6px;
  background: rgba(0,0,0,0.5); color: #fff; font-size: 13px;
  opacity: 0; transition: opacity 0.2s;
}
.avatar-upload-wrap:hover .avatar-overlay { opacity: 1; }
.crop-container { max-height: 360px; overflow: hidden; }
:deep(.topbar-right .el-button) { color: #667085; }
:deep(.topbar-right .el-button:hover) { color: #101828; background: #f2f4f7; }

/* 移动端五页签：中间绵小城凸起，其余等分（主流移动端底部栏布局） */
:deep(.mobile-tab-bar .tab-item) { flex: 1; }
</style>
