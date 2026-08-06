<template>
  <div class="profile-page">
    <!-- Personal Info Card -->
    <div class="info-card">
      <div class="info-header">
        <el-avatar :size="64" :src="auth.user?.avatar || ''" shape="square" class="user-avatar">
          {{ auth.userName?.[0] }}
        </el-avatar>
        <div class="info-text">
          <div class="user-name">{{ auth.userName }}</div>
          <div class="user-id">{{ auth.user?.username }}</div>
        </div>
        <el-button text circle class="edit-btn" @click="openProfileDialog">
          <el-icon :size="16"><Edit /></el-icon>
        </el-button>
      </div>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">学院</span>
          <span class="info-value">{{ auth.user?.college || '--' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">班级</span>
          <span class="info-value">{{ auth.user?.department || '--' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">性别</span>
          <span class="info-value">{{ auth.user?.gender || '--' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">联系电话</span>
          <span class="info-value">{{ auth.user?.phone || '--' }}</span>
        </div>
      </div>
    </div>

    <!-- Service Applications -->
    <div class="section-card">
      <div class="section-title">办事服务</div>
      <div class="service-grid">
        <div v-for="s in serviceTypes" :key="s.key" class="service-item" @click="openServiceForm(s.key)">
          <div class="service-icon" :style="{ background: s.color + '12', color: s.color }">{{ s.icon }}</div>
          <div class="service-label">{{ s.label }}</div>
        </div>
        <div class="service-item" @click="showRecords = true; loadRecords()">
          <div class="service-icon" style="background:rgba(99,102,241,.1);color:#6366f1">📋</div>
          <div class="service-label">查看申请</div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="section-card">
      <div class="section-title">快捷入口</div>
      <div class="quick-list">
        <div class="quick-item" @click="showChangePassword = true">
          <el-icon :size="18"><Lock /></el-icon>
          <span>修改密码</span>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </div>
        <div class="quick-item" @click="logout">
          <el-icon :size="18"><SwitchButton /></el-icon>
          <span>退出登录</span>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- ===== Service Form Dialogs ===== -->
    <!-- 请假申请 -->
    <el-dialog v-model="serviceDialogs.leave" title="请假申请" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="leaveForm" label-width="90px" ref="leaveFormRef" :rules="leaveRules">
        <el-form-item label="姓名"><el-input :model-value="auth.userName" disabled /></el-form-item>
        <el-form-item label="学号"><el-input :model-value="auth.user?.username" disabled /></el-form-item>
        <el-form-item label="请假类型" prop="leave_type">
          <el-select v-model="leaveForm.leave_type" placeholder="请选择" style="width:100%">
            <el-option label="课假" value="课假" /><el-option label="公假" value="公假" /><el-option label="宿假" value="宿假" />
            <el-option label="事假" value="事假" /><el-option label="病假" value="病假" /><el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="开始日期" prop="start_date"><el-date-picker v-model="leaveForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="结束日期" prop="end_date"><el-date-picker v-model="leaveForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="请假理由" prop="reason"><el-input v-model="leaveForm.reason" type="textarea" :rows="3" placeholder="请详细描述请假原因" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="serviceDialogs.leave = false">取消</el-button>
        <el-button type="primary" @click="submitLeave" :loading="submitting">提交申请</el-button>
      </template>
    </el-dialog>

    <!-- 证明申请 -->
    <el-dialog v-model="serviceDialogs.certificate" title="证明申请" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="certForm" label-width="90px" ref="certFormRef" :rules="certRules">
        <el-form-item label="姓名"><el-input :model-value="auth.userName" disabled /></el-form-item>
        <el-form-item label="学号"><el-input :model-value="auth.user?.username" disabled /></el-form-item>
        <el-form-item label="证明类型" prop="certificate_type">
          <el-select v-model="certForm.certificate_type" placeholder="请选择" style="width:100%">
            <el-option label="在校证明" value="在校证明" /><el-option label="成绩单" value="成绩单" />
            <el-option label="在读证明" value="在读证明" /><el-option label="学籍证明" value="学籍证明" /><el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="用途说明" prop="content"><el-input v-model="certForm.content" type="textarea" :rows="3" placeholder="请说明开具证明的用途" /></el-form-item>
        <el-form-item label="所需份数"><el-input-number v-model="certForm.quantity" :min="1" :max="20" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="serviceDialogs.certificate = false">取消</el-button>
        <el-button type="primary" @click="submitCert" :loading="submitting">提交申请</el-button>
      </template>
    </el-dialog>

    <!-- 项目申请 -->
    <el-dialog v-model="serviceDialogs.project" title="项目申请" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="projectForm" label-width="90px" ref="projectFormRef" :rules="projectRules">
        <el-form-item label="姓名"><el-input :model-value="auth.userName" disabled /></el-form-item>
        <el-form-item label="学号"><el-input :model-value="auth.user?.username" disabled /></el-form-item>
        <el-form-item label="项目类型" prop="project_type">
          <el-select v-model="projectForm.project_type" placeholder="请选择" style="width:100%">
            <el-option label="竞赛项目" value="竞赛项目" /><el-option label="科研项目" value="科研项目" /><el-option label="社会实践" value="社会实践" />
            <el-option label="创业项目" value="创业项目" /><el-option label="学生工作" value="学生工作" /><el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称" prop="title"><el-input v-model="projectForm.title" placeholder="请输入项目名称" /></el-form-item>
        <el-form-item label="指导老师"><el-input v-model="projectForm.advisor" placeholder="指导老师姓名" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="开始日期" prop="start_date"><el-date-picker v-model="projectForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="结束日期" prop="end_date"><el-date-picker v-model="projectForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="项目简介" prop="content"><el-input v-model="projectForm.content" type="textarea" :rows="3" placeholder="请描述项目背景、目标" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="serviceDialogs.project = false">取消</el-button>
        <el-button type="primary" @click="submitProject" :loading="submitting">提交申请</el-button>
      </template>
    </el-dialog>

    <!-- 意见反馈 -->
    <el-dialog v-model="serviceDialogs.feedback" title="意见反馈" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form :model="feedbackForm" label-width="90px" ref="feedbackFormRef" :rules="feedbackRules">
        <el-form-item label="反馈类型" prop="type">
          <el-select v-model="feedbackForm.type" placeholder="请选择" style="width:100%">
            <el-option label="问题反馈" value="bug" /><el-option label="功能建议" value="feature" />
            <el-option label="投诉" value="complaint" /><el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" prop="title"><el-input v-model="feedbackForm.title" placeholder="请简要描述" maxlength="100" show-word-limit /></el-form-item>
        <el-form-item label="详细内容" prop="content"><el-input v-model="feedbackForm.content" type="textarea" :rows="4" placeholder="请详细描述" maxlength="1000" show-word-limit /></el-form-item>
        <el-form-item label="联系方式"><el-input v-model="feedbackForm.contact" placeholder="手机号/邮箱（选填）" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="serviceDialogs.feedback = false">取消</el-button>
        <el-button type="primary" @click="submitFeedback" :loading="submitting">提交反馈</el-button>
      </template>
    </el-dialog>

    <!-- ===== Records Dialog ===== -->
    <el-drawer v-model="showRecords" title="申请记录" size="420px" direction="rtl">
      <div v-loading="recordsLoading" class="records-list">
        <div v-if="!records.length" class="empty-records">暂无申请记录</div>
        <div v-for="r in records" :key="r.id" class="record-item">
          <div class="record-top">
            <span class="record-type">{{ r._typeLabel }}</span>
            <el-tag :type="r.status === 'approved' ? 'success' : r.status === 'rejected' ? 'danger' : 'warning'" size="small" effect="plain">
              {{ r.status === 'approved' ? '已通过' : r.status === 'rejected' ? '已拒绝' : '待审批' }}
            </el-tag>
          </div>
          <div class="record-title">{{ r.title }}</div>
          <div class="record-date">{{ r.created_at?.slice(0, 10) }}</div>
        </div>
      </div>
    </el-drawer>

    <!-- Change Password Dialog -->
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

    <!-- Profile Edit Dialog -->
    <el-dialog v-model="showProfileDialog" title="个人资料" width="640px" :close-on-click-modal="false" class="profile-dialog">
      <el-form :model="profileForm" label-width="80px" label-position="left" size="large">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学号"><el-input v-model="profileForm.username" disabled placeholder="请输入学号" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名"><el-input v-model="profileForm.name" disabled placeholder="请输入姓名" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
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
        <el-form-item label="学院"><el-input v-model="profileForm.college" disabled placeholder="请输入学院" /></el-form-item>
        <el-form-item label="班级"><el-input v-model="profileForm.className" placeholder="请输入班级" /></el-form-item>
        <el-form-item label="政治面貌">
          <el-select v-model="profileForm.political_status" placeholder="请选择" style="width:100%">
            <el-option label="群众" value="群众" />
            <el-option label="共青团员" value="共青团员" />
            <el-option label="中共预备党员" value="中共预备党员" />
            <el-option label="中共党员" value="中共党员" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="籍贯"><el-input v-model="profileForm.hometown" placeholder="请输入籍贯" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话"><el-input v-model="profileForm.phone" placeholder="请输入手机号" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="辅导员">
          <el-select
            v-if="!profileSaved || !profileForm.tutor_id"
            v-model="profileForm.tutor_id"
            placeholder="搜索选择辅导员"
            filterable
            style="width:100%"
          >
            <el-option v-for="t in teachers" :key="t.id" :label="`${t.name}（${t.username}）`" :value="t.id" />
          </el-select>
          <template v-else>
            <el-tag type="success" size="large">{{ tutorName }}</el-tag>
            <span class="tutor-hint">已绑定，如需变更请联系管理员</span>
          </template>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProfileDialog = false" size="large">取消</el-button>
        <el-button type="primary" @click="handleSaveProfile" :loading="saving" size="large">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, getTeachers, changePassword } from '@/api/user'
import { createTicket, getTickets } from '@/api/service'
import { createLeave, getMyLeaves } from '@/api/leave'
import { createFeedback } from '@/api/feedback'
import { Edit, ArrowRight, Lock, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const showChangePassword = ref(false)
const showProfileDialog = ref(false)
const showRecords = ref(false)
const saving = ref(false)
const submitting = ref(false)
const changingPassword = ref(false)
const recordsLoading = ref(false)
const teachers = ref<any[]>([])
const records = ref<any[]>([])

const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const profileForm = reactive({ username: '', name: '', college: '', gender: '', age: 18, hometown: '', phone: '', tutor_id: null as number | null, className: '', political_status: '' })
const profileSaved = ref(false)

const serviceDialogs = reactive({ leave: false, certificate: false, project: false, feedback: false })

const serviceTypes = [
  { key: 'leave', label: '请假申请', icon: '📅', color: '#409eff' },
  { key: 'certificate', label: '证明申请', icon: '📄', color: '#67c23a' },
  { key: 'project', label: '项目申请', icon: '🚀', color: '#e6a23c' },
  { key: 'feedback', label: '意见反馈', icon: '💬', color: '#f56c6c' },
]

// --- Leave Form ---
const leaveFormRef = ref<any>()
const leaveForm = reactive({ leave_type: '', start_date: '', end_date: '', reason: '' })
const leaveRules = {
  leave_type: [{ required: true, message: '请选择请假类型', trigger: 'change' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  reason: [{ required: true, message: '请填写请假理由', trigger: 'blur' }],
}

// --- Certificate Form ---
const certFormRef = ref<any>()
const certForm = reactive({ certificate_type: '', content: '', quantity: 1 })
const certRules = {
  certificate_type: [{ required: true, message: '请选择证明类型', trigger: 'change' }],
  content: [{ required: true, message: '请填写用途说明', trigger: 'blur' }],
}

// --- Project Form ---
const projectFormRef = ref<any>()
const projectForm = reactive({ project_type: '', title: '', advisor: '', start_date: '', end_date: '', content: '' })
const projectRules = {
  project_type: [{ required: true, message: '请选择项目类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  content: [{ required: true, message: '请填写项目简介', trigger: 'blur' }],
}

// --- Feedback Form ---
const feedbackFormRef = ref<any>()
const feedbackForm = reactive({ type: 'other', title: '', content: '', contact: '' })
const feedbackRules = {
  type: [{ required: true, message: '请选择反馈类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入详细内容', trigger: 'blur' }],
}

const tutorName = computed(() => {
  const t = teachers.value.find(t => t.id === profileForm.tutor_id)
  return t ? `${t.name}（${t.username}）` : ''
})

function mapLeaveType(label: string): string {
  const m: Record<string, string> = { '课假': 'other', '公假': 'competition', '宿假': 'personal', '事假': 'personal', '病假': 'sick', '其他': 'other' }
  return m[label] || 'other'
}

function openServiceForm(type: string) {
  ;(serviceDialogs as any)[type] = true
}

function logout() { auth.logout(); router.push('/') }

async function submitLeave() {
  if (!leaveFormRef.value) return
  try { await leaveFormRef.value.validate() } catch { return }
  submitting.value = true
  try {
    await createLeave({
      start_date: leaveForm.start_date, end_date: leaveForm.end_date,
      reason: `[${leaveForm.leave_type}] ${leaveForm.reason}`,
      leave_type: mapLeaveType(leaveForm.leave_type),
    })
    ElMessage.success('请假申请已提交')
    serviceDialogs.leave = false
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') }
  finally { submitting.value = false }
}

async function submitCert() {
  if (!certFormRef.value) return
  try { await certFormRef.value.validate() } catch { return }
  submitting.value = true
  try {
    await createTicket({
      type: 'certificate', title: certForm.certificate_type, content: certForm.content,
      applicant_name: auth.userName || '', applicant_no: auth.user?.username || '', applicant_college: auth.user?.college || '',
      form_data: { certificate_type: certForm.certificate_type, quantity: certForm.quantity },
    })
    ElMessage.success('证明申请已提交')
    serviceDialogs.certificate = false
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') }
  finally { submitting.value = false }
}

async function submitProject() {
  if (!projectFormRef.value) return
  try { await projectFormRef.value.validate() } catch { return }
  submitting.value = true
  try {
    await createTicket({
      type: 'project', title: projectForm.title, content: projectForm.content,
      applicant_name: auth.userName || '', applicant_no: auth.user?.username || '', applicant_college: auth.user?.college || '',
      form_data: { project_type: projectForm.project_type, advisor: projectForm.advisor, start_date: projectForm.start_date, end_date: projectForm.end_date },
    })
    ElMessage.success('项目申请已提交')
    serviceDialogs.project = false
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') }
  finally { submitting.value = false }
}

async function submitFeedback() {
  if (!feedbackFormRef.value) return
  try { await feedbackFormRef.value.validate() } catch { return }
  submitting.value = true
  try {
    await createFeedback(feedbackForm)
    ElMessage.success('反馈已提交')
    serviceDialogs.feedback = false
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') }
  finally { submitting.value = false }
}

async function loadRecords() {
  recordsLoading.value = true
  try {
    const [leaves, tickets] = await Promise.all([getMyLeaves(), getTickets()])
    const leaveRecords = (leaves as any[]).map(r => ({
      id: r.id, title: `${r.leave_type} ${r.start_date} ~ ${r.end_date}`, status: r.status,
      created_at: r.created_at, _typeLabel: '请假',
    }))
    const ticketRecords = (tickets as any[]).map(r => ({
      id: r.id, title: r.title, status: r.status, created_at: r.created_at,
      _typeLabel: r.type === 'certificate' ? '证明' : r.type === 'project' ? '项目' : r.type,
    }))
    records.value = [...leaveRecords, ...ticketRecords].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  } catch { records.value = [] }
  finally { recordsLoading.value = false }
}

async function handleChangePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) { ElMessage.warning('请填写所有字段'); return }
  if (passwordForm.new_password !== passwordForm.confirm_password) { ElMessage.error('两次输入的新密码不一致'); return }
  if (passwordForm.new_password.length < 6) { ElMessage.error('新密码至少6位'); return }
  changingPassword.value = true
  try {
    await changePassword(passwordForm.old_password, passwordForm.new_password)
    ElMessage.success('密码修改成功')
    showChangePassword.value = false
    if (auth.user) auth.updateUser({ ...auth.user, password_changed: true })
    passwordForm.old_password = ''; passwordForm.new_password = ''; passwordForm.confirm_password = ''
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '修改失败') }
  finally { changingPassword.value = false }
}

async function handleSaveProfile() {
  saving.value = true
  try {
    const updated = await updateProfile({
      gender: profileForm.gender || null, age: profileForm.age || null,
      hometown: profileForm.hometown || null, phone: profileForm.phone || null,
      tutor_id: profileForm.tutor_id || null,
      class_name: profileForm.className || null,
      political_status: profileForm.political_status || null,
    })
    auth.updateUser(updated as any)
    profileSaved.value = true
    ElMessage.success('保存成功')
    showProfileDialog.value = false
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { saving.value = false }
}

function openProfileDialog() {
  const u = auth.user; if (!u) return
  profileForm.username = u.username; profileForm.name = u.name
  profileForm.college = u.college || ''; profileForm.gender = u.gender || ''
  profileForm.age = u.age ?? 18; profileForm.hometown = u.hometown || ''
  profileForm.phone = u.phone || ''; profileForm.tutor_id = u.tutor_id ?? null
  profileForm.className = (u as any).class_name || ''; profileForm.political_status = (u as any).political_status || ''
  profileSaved.value = !!u.tutor_id
  showProfileDialog.value = true
}

onMounted(async () => { try { teachers.value = await getTeachers() } catch {} })
</script>

<style scoped>
.profile-page { padding: 16px; height: 100%; overflow-y: auto; }

.info-card { background: linear-gradient(135deg, #409eff, #337ecc); border-radius: 16px; padding: 20px; color: #fff; margin-bottom: 16px; }
.info-header { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
.user-avatar { width: 64px !important; height: 64px !important; font-size: 24px; border: 2px solid rgba(255,255,255,0.3); }
.info-text { flex: 1; }
.user-name { font-size: 20px; font-weight: 700; }
.user-id { font-size: 13px; opacity: 0.8; margin-top: 2px; }
.edit-btn { color: rgba(255,255,255,0.8); }
.edit-btn:hover { color: #fff; background: rgba(255,255,255,0.15); }
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.info-item { display: flex; flex-direction: column; gap: 2px; }
.info-label { font-size: 11px; opacity: 0.7; }
.info-value { font-size: 14px; font-weight: 500; }

.section-card { background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.section-title { font-size: 15px; font-weight: 600; color: #1a1a1a; margin-bottom: 14px; }

.service-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.service-item { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 14px 0; border-radius: 10px; cursor: pointer; transition: background 0.2s; }
.service-item:active { background: #f5f7fa; }
.service-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.service-label { font-size: 12px; color: #333; font-weight: 500; }

.quick-list { display: flex; flex-direction: column; }
.quick-item { display: flex; align-items: center; gap: 10px; padding: 14px 0; border-bottom: 1px solid #f5f5f5; cursor: pointer; color: #333; }
.quick-item:last-child { border-bottom: none; }
.quick-item:active { background: #f5f7fa; margin: 0 -16px; padding-left: 16px; padding-right: 16px; }
.quick-item span { flex: 1; font-size: 14px; }
.arrow { color: #ccc; font-size: 14px; }

.records-list { padding: 0 16px; }
.empty-records { text-align: center; color: #999; padding: 40px 0; font-size: 14px; }
.record-item { padding: 12px 0; border-bottom: 1px solid #f5f5f5; }
.record-item:last-child { border-bottom: none; }
.record-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.record-type { font-size: 12px; color: #409eff; font-weight: 500; }
.record-title { font-size: 14px; color: #333; margin-bottom: 4px; }
.record-date { font-size: 12px; color: #999; }

.tutor-hint { font-size: 12px; color: #999; margin-left: 8px; }

.profile-dialog :deep(.el-dialog__body) {
  padding: 28px 36px 12px;
}
.profile-dialog :deep(.el-form-item__label) {
  text-align-last: justify;
  text-align: justify;
}

@media (max-width: 767px) {
  .profile-page { padding: 12px; }
  .info-card { padding: 16px; }
  .user-avatar { width: 56px !important; height: 56px !important; }
  .user-name { font-size: 18px; }
  .service-grid { grid-template-columns: repeat(3, 1fr); gap: 6px; }
  .service-icon { width: 40px; height: 40px; font-size: 20px; }
  .service-label { font-size: 11px; }
}
</style>
