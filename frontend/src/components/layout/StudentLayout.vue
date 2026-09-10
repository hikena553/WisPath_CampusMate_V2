<template>
  <div class="app-shell">
    <header class="topbar">
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
          <div class="nav-item" :class="{ 'nav-active': route.path === '/student/campus' }" @click="goTo('/student/campus')">
            <el-icon :size="16"><PictureFilled /></el-icon>
            <span>校园资讯</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path === '/student/schedule' }" @click="goTo('/student/schedule')">
            <el-icon :size="16"><Calendar /></el-icon>
            <span>学业中心</span>
          </div>
          <div class="nav-item" :class="{ 'nav-active': route.path === '/student/service' }" @click="goTo('/student/service')">
            <el-icon :size="16"><Service /></el-icon>
            <span>办事服务</span>
          </div>
          <div class="nav-item nav-contact" @click="showContact = true" style="position:relative">
            <el-icon :size="16"><Message /></el-icon>
            <span>联系</span>
            <el-badge v-if="unreadCount" is-dot class="contact-badge" />
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
              <el-dropdown-item @click="openProfile">
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
      <router-view />
    </main>

    <!-- 移动端底部导航栏 -->
    <MobileTabBar v-if="isMobile" :items="mobileNavItems" :active-key="activeNavKey" @select="handleNavSelect" />

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
                <el-form-item label="学号"><el-input v-model="profileForm.username" disabled /></el-form-item>
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
            <el-form-item label="班级" required>
              <el-select v-model="profileForm.class_name" filterable allow-create default-first-option clearable placeholder="选择或输入班级" style="width:100%">
                <el-option v-for="c in classOptions" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="政治面貌">
              <el-select v-model="profileForm.political_status" placeholder="请选择政治面貌" style="width:100%">
                <el-option label="中共党员" value="dangyuan" />
                <el-option label="中共预备党员" value="yubei" />
                <el-option label="共青团员" value="tuanyuan" />
                <el-option label="群众" value="qunzhong" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="职称">
                  <el-select v-model="profileForm.title" filterable allow-create default-first-option clearable placeholder="选择或输入职称/职务" style="width:100%">
                    <el-option v-for="t in titleOptions" :key="t" :label="t" :value="t" />
                  </el-select>
                </el-form-item>
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
            <el-form-item label="辅导员">
              <div v-if="profileForm.tutor_id && tutorName" class="tutor-display">
                <el-tag type="success" size="large">{{ tutorName }}</el-tag>
                <span class="tutor-hint">辅导员已绑定，如需变更请联系管理员</span>
              </div>
              <el-select v-else v-model="profileForm.tutor_id" placeholder="搜索选择辅导员" filterable style="width:100%">
                <el-option v-for="t in teachers" :key="t.id" :label="`${t.name}（${t.username}）`" :value="t.id" />
              </el-select>
            </el-form-item>
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
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入旧密码" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="6-20位，建议包含字母和数字" />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePassword = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword" :loading="changingPassword">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="showContact" title="消息" size="min(880px, 92vw)" @open="onContactOpen">
      <StudentContactPanel :key="contactKey" @read="pollUnread" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, getTeachers, changePassword } from '@/api/user'
import { uploadFile } from '@/api/upload'
import { ElMessage } from 'element-plus'
import StudentContactPanel from '@/components/chat/StudentContactPanel.vue'
import { getConversations } from '@/api/messages'
import { getGroups } from '@/api/groups'
import Cropper from 'cropperjs'
import { ChatDotRound, PictureFilled, Calendar, Grid, Message, User, SwitchButton, CameraFilled, Service } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import MobileTabBar from '@/components/responsive/MobileTabBar.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isMobile } = useResponsive()

// 移动端底部导航
const mobileNavItems = [
  { key: 'campus', label: '校园资讯', icon: PictureFilled, route: '/student/campus' },
  { key: 'schedule', label: '学业中心', icon: Calendar, route: '/student/schedule' },
  { key: 'agent', label: '绵小城', iconImg: '/images/校徽_圆形.png', center: true, route: '/student' },
  { key: 'workbench', label: '工作台', icon: Grid, route: '/student/workbench' },
  { key: 'profile', label: '个人中心', icon: User, route: '/student/profile' },
]

const activeNavKey = computed(() => {
  const path = route.path
  if (path === '/student' || path.startsWith('/student/agent')) return 'agent'
  if (path.startsWith('/student/campus')) return 'campus'
  if (path.startsWith('/student/schedule') || path.startsWith('/student/growth') || path.startsWith('/student/grade')) return 'schedule'
  if (path.startsWith('/student/profile')) return 'profile'
  if (path.startsWith('/student/workbench') || path.startsWith('/student/service') || path.startsWith('/student/feedback')) return 'workbench'
  return 'agent'
})

function handleNavSelect(item: { route: string }) {
  router.push(item.route)
}

const showProfile = ref(false)
const saving = ref(false)
const fileInputRef = ref<HTMLInputElement>()
const showCrop = ref(false)
const cropImgRef = ref<HTMLImageElement>()
let cropper: Cropper | null = null
let pendingImageSrc = ''
const teachers = ref<any[]>([])
const showContact = ref(false)
const contactKey = ref(0)
function onContactOpen() { contactKey.value++ }
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

const tutorName = computed(() => {
  const t = teachers.value.find(t => t.id === profileForm.tutor_id)
  return t ? `${t.name}（${t.username}）` : ''
})

const showChangePassword = ref(false)
const changingPassword = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const profileForm = reactive({
  username: '', name: '', college: '', role: '',
  avatar: '', gender: '', age: 18, political_status: '',
  title: '', hometown: '', phone: '', department: '',
  class_name: '',
  tutor_id: null as number | null,
})

const titleOptions = ['班长', '团支书', '学习委员', '组织委员', '宣传委员', '生活委员', '心理委员', '体育委员', '学生会主席', '学生会副主席', '学生会干事', '无']

const classOptions = ['2023级软件工程1班', '2023级软件工程2班', '2024级软件工程1班', '2024级软件工程2班', '2024级计算机科学与技术1班', '2024级计算机科学与技术2班', '2024级数据科学与大数据技术1班', '2025级软件工程1班', '2025级计算机科学与技术1班']

onMounted(async () => {
  try {
    teachers.value = await getTeachers()
  } catch {}
  pollUnread()
  setInterval(pollUnread, 5000)
})

function goTo(path: string) { router.push(path) }

function logout() {
  auth.logout()
  router.push('/')
}

function openProfile() {
  const u = auth.user
  if (!u) return
  profileForm.username = u.username
  profileForm.name = u.name
  profileForm.college = u.college || ''
  profileForm.role = u.role
  profileForm.avatar = u.avatar || ''
  profileForm.gender = u.gender || ''
  profileForm.age = u.age ?? 18
  profileForm.political_status = u.political_status || ''
  profileForm.title = u.title || ''
  profileForm.hometown = u.hometown || ''
  profileForm.phone = u.phone || ''
  profileForm.department = u.department || ''
  profileForm.tutor_id = u.tutor_id ?? null
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
      political_status: profileForm.political_status || null,
      title: profileForm.title || null,
      hometown: profileForm.hometown || null,
      phone: profileForm.phone || null,
      department: profileForm.department || null,
      tutor_id: profileForm.tutor_id || null,
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

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #f5faff 0%, #f0f8ff 50%, #f8fbff 100%);
  overflow: hidden;
}
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px;
  background: linear-gradient(135deg, #1d4ed8, #2563eb, #3b82f6);
  flex-shrink: 0; z-index: 100;
  box-shadow: 0 2px 12px rgba(29,78,216,0.35);
}
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
.main-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; -ms-overflow-style: none; scrollbar-width: none; }
.main-area::-webkit-scrollbar { display: none; }
.main-area.has-bottom-bar { padding-bottom: 56px; }

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
.tutor-display { display: flex; align-items: center; gap: 12px; }
.tutor-hint { font-size: 12px; color: var(--text-muted); }
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
}
.el-drawer__header { margin-bottom: 0 !important; padding: 6px 16px !important; }
.el-drawer__body { padding: 0 !important; }
</style>