<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-left" style="cursor:pointer" @click="goTo('/teacher')">
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
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
            <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
            <el-badge
              v-if="item.badge && unreadCount > 0"
              :value="unreadCount"
              class="nav-badge"
            />
          </router-link>
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
      <main class="main-area">
        <router-view />
      </main>
    </div>

    <el-dialog v-model="showProfile" title="个人资料" width="560px" :close-on-click-modal="false">
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
          <el-form :model="profileForm" label-width="90px" size="small">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="工号"><el-input v-model="profileForm.username" disabled /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="姓名"><el-input v-model="profileForm.name" disabled /></el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="性别">
                  <el-select v-model="profileForm.gender" placeholder="请选择" style="width:100%">
                    <el-option label="男" value="男" />
                    <el-option label="女" value="女" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="年龄">
                  <el-input-number v-model="profileForm.age" :min="1" :max="120" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="学院"><el-input v-model="profileForm.college" disabled /></el-form-item>
            <el-form-item label="班级"><el-input v-model="profileForm.class_name" placeholder="所带班级" /></el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="职称"><el-input v-model="profileForm.title" placeholder="职称/职务" /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="所属单位"><el-input v-model="profileForm.department" placeholder="所属单位" /></el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="籍贯"><el-input v-model="profileForm.hometown" placeholder="籍贯" /></el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="联系电话"><el-input v-model="profileForm.phone" placeholder="手机号" /></el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>
      <template #footer>
        <div style="display: flex; justify-content: space-between; width: 100%">
          <el-button
            type="warning"
            @click="showChangePassword = true"
            :disabled="auth.user?.password_changed"
          >
            {{ auth.user?.password_changed ? '密码已修改过' : '修改密码' }}
          </el-button>
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

    <el-dialog v-model="showChangePassword" title="修改密码" width="400px" :close-on-click-modal="false">
      <el-form :model="passwordForm" label-width="100px">
        <el-form-item label="旧密码" required>
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="passwordForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePassword = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword" :loading="changingPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, changePassword } from '@/api/user'
import { uploadFile } from '@/api/upload'
import { getConversations, type ConversationOut } from '@/api/messages'
import { ElMessage } from 'element-plus'
import Cropper from 'cropperjs'
import {
  HomeFilled, ChatDotRound, CircleCheck, User, Message,
  SwitchButton, CameraFilled, Fold, Expand
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

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

const navItems = [
  { path: '/teacher', label: '首页', icon: HomeFilled },
  { path: '/teacher/agent', label: '智能助手', icon: ChatDotRound },
  { path: '/teacher/approval', label: '审批管理', icon: CircleCheck },
  { path: '/teacher/students', label: '学生成长', icon: User },
  { path: '/teacher/messages', label: '消息', icon: Message, badge: true },
]

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

onMounted(() => { pollUnread(); pollTimer = setInterval(pollUnread, 5000) })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

function goTo(path: string) { router.push(path) }

function logout() {
  auth.logout()
  router.push('/')
}

const showChangePassword = ref(false)
const changingPassword = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

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

async function handleChangePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    ElMessage.warning('请填写所有字段')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.error('新密码至少6位')
    return
  }

  changingPassword.value = true
  try {
    await changePassword(passwordForm.old_password, passwordForm.new_password)
    ElMessage.success('密码修改成功')
    showChangePassword.value = false
    if (auth.user) {
      auth.updateUser({ ...auth.user, password_changed: true })
    }
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '修改失败')
  } finally {
    changingPassword.value = false
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
body { overflow: hidden; margin: 0; }
</style>
<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #f5faff 0%, #f0f8ff 50%, #f8fbff 100%);
}

/* ===== Topbar ===== */
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

/* ===== Body ===== */
.body-area { display: flex; flex: 1; min-height: 0; }

/* ===== Sidebar ===== */
.sidebar {
  width: 200px; flex-shrink: 0; display: flex; flex-direction: column;
  background: var(--sidebar-bg); backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-color); box-shadow: var(--shadow-sm);
  transition: width 0.2s ease;
  overflow: hidden;
}
.sidebar.collapsed { width: 64px; }

.sidebar-nav { flex: 1; padding: 12px 8px; display: flex; flex-direction: column; gap: 4px; }

.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-radius: 8px;
  text-decoration: none; color: var(--text-secondary); font-size: 14px; font-weight: 500;
  transition: all 0.15s ease; position: relative; white-space: nowrap;
}
.sidebar.collapsed .nav-item { justify-content: center; padding: 10px; }
.nav-item:hover { background: var(--hover-bg); color: var(--accent-blue); }
.nav-item.active {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff; font-weight: 600;
}
.nav-item.active .el-icon { color: #fff; }
.nav-label { flex: 1; }
.nav-badge { position: absolute; top: 6px; right: 8px; }

/* ===== Sidebar Footer ===== */
.sidebar-footer {
  padding: 16px 12px; border-top: 1px solid var(--border-color);
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
</style>
