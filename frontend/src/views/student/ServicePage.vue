<template>
  <div class="service-page">
    <!-- left: form area -->
    <div class="form-area">
      <div class="page-header">
        <h2>办事服务</h2>
        <p class="subtitle">一站式在线申请，提交后等待辅导员审批</p>
      </div>

      <div class="tabs-row">
        <div v-for="tab in formTabs" :key="tab.key" :class="['tab-card', { active: activeForm === tab.key }]" @click="activeForm = tab.key">
          <span class="tab-icon">{{ tab.icon }}</span>
          <div>
            <div class="tab-title">{{ tab.label }}</div>
            <div class="tab-desc">{{ tab.desc }}</div>
          </div>
        </div>
      </div>

      <div class="form-section">
        <div class="section-title">{{ currentTab.label }}表单</div>
        
        <!-- 普通表单 (请假/证明/项目) -->
        <el-form v-if="activeForm !== 'feedback'" :model="form" :rules="formRules" ref="formRef" label-width="100px" class="apply-form">
          <el-row :gutter="20">
            <el-col :span="8"><el-form-item label="姓名"><el-input v-model="form.applicant_name" disabled /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="学号"><el-input v-model="form.applicant_no" disabled /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="学院"><el-input v-model="form.applicant_college" disabled /></el-form-item></el-col>
          </el-row>

          <template v-if="activeForm === 'leave'">
            <el-form-item label="请假类型" prop="form_data.leave_type">
              <el-select v-model="form.form_data.leave_type" placeholder="请选择请假类型" style="width:100%">
                <el-option label="课假" value="课假" /><el-option label="公假" value="公假" /><el-option label="宿假" value="宿假" />
                <el-option label="事假" value="事假" /><el-option label="病假" value="病假" /><el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-row :gutter="20">
              <el-col :span="12"><el-form-item label="开始日期" prop="form_data.start_date"><el-date-picker v-model="form.form_data.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="结束日期" prop="form_data.end_date"><el-date-picker v-model="form.form_data.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            </el-row>
            <el-form-item label="请假理由" prop="content"><el-input v-model="form.content" type="textarea" :rows="3" placeholder="请详细描述请假原因" /></el-form-item>
            <template v-if="form.form_data.leave_type === '课假' || form.form_data.leave_type === '公假'">
              <el-form-item label="证明材料">
                <UploadBtn @uploaded="addAttachment" />
                <div v-for="(f, i) in form.attachments" :key="i" class="file-tag"><el-tag closable @close="removeAttachment(i)">{{ fileName(f) }}</el-tag></div>
              </el-form-item>
            </template>
            <template v-if="form.form_data.leave_type === '宿假'">
              <el-row :gutter="20">
                <el-col :span="12"><el-form-item label="宿舍楼"><el-input v-model="form.form_data.dormitory_building" placeholder="如：A栋" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="宿舍号"><el-input v-model="form.form_data.dormitory_room" placeholder="如：301" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="家长证明">
                <UploadBtn @uploaded="(u:string) => { form.form_data.parent_proof = u }" />
                <div v-if="form.form_data.parent_proof" class="file-tag"><el-tag closable @close="form.form_data.parent_proof = ''">{{ fileName(form.form_data.parent_proof) }}</el-tag></div>
              </el-form-item>
              <el-form-item label="其他证明">
                <UploadBtn @uploaded="addAttachment" />
                <div v-for="(f, i) in form.attachments" :key="i" class="file-tag"><el-tag closable @close="removeAttachment(i)">{{ fileName(f) }}</el-tag></div>
              </el-form-item>
            </template>
          </template>

          <template v-if="activeForm === 'certificate'">
            <el-form-item label="证明类型" prop="form_data.certificate_type">
              <el-select v-model="form.form_data.certificate_type" placeholder="请选择证明类型" style="width:100%">
                <el-option label="在校证明" value="在校证明" /><el-option label="成绩单" value="成绩单" />
                <el-option label="在读证明" value="在读证明" /><el-option label="学籍证明" value="学籍证明" /><el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-form-item label="用途说明" prop="content"><el-input v-model="form.content" type="textarea" :rows="3" placeholder="请说明开具证明的用途" /></el-form-item>
            <el-form-item label="所需份数"><el-input-number v-model="form.form_data.quantity" :min="1" :max="20" /></el-form-item>
            <el-form-item label="附件材料">
              <UploadBtn @uploaded="addAttachment" />
              <div v-for="(f, i) in form.attachments" :key="i" class="file-tag"><el-tag closable @close="removeAttachment(i)">{{ fileName(f) }}</el-tag></div>
            </el-form-item>
          </template>

          <template v-if="activeForm === 'project'">
            <el-form-item label="项目类型" prop="form_data.project_type">
              <el-select v-model="form.form_data.project_type" placeholder="请选择项目类型" style="width:100%">
                <el-option label="竞赛项目" value="竞赛项目" /><el-option label="科研项目" value="科研项目" /><el-option label="社会实践" value="社会实践" />
                <el-option label="创业项目" value="创业项目" /><el-option label="学生工作" value="学生工作" /><el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-form-item label="项目名称" prop="title"><el-input v-model="form.title" placeholder="请输入项目名称" /></el-form-item>
            <el-form-item label="指导老师"><el-input v-model="form.form_data.advisor" placeholder="指导老师姓名" /></el-form-item>
            <el-form-item label="团队成员"><el-input v-model="form.form_data.team_members" placeholder="成员姓名（多个用逗号隔开）" /></el-form-item>
            <el-row :gutter="20">
              <el-col :span="12"><el-form-item label="开始日期" prop="form_data.start_date"><el-date-picker v-model="form.form_data.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="结束日期" prop="form_data.end_date"><el-date-picker v-model="form.form_data.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            </el-row>
            <el-form-item label="预算（元）"><el-input-number v-model="form.form_data.budget" :min="0" :step="100" style="width:200px" /></el-form-item>
            <el-form-item label="项目简介" prop="content"><el-input v-model="form.content" type="textarea" :rows="4" placeholder="请描述项目背景、目标、预期成果" /></el-form-item>
            <el-form-item label="附件材料">
              <UploadBtn @uploaded="addAttachment" />
              <div v-for="(f, i) in form.attachments" :key="i" class="file-tag"><el-tag closable @close="removeAttachment(i)">{{ fileName(f) }}</el-tag></div>
            </el-form-item>
          </template>

          <el-form-item>
            <el-button type="primary" @click="handleSubmit" :loading="submitting">提交申请</el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>
        
        <!-- 反馈表单 -->
        <el-form v-if="activeForm === 'feedback'" :model="feedbackForm" :rules="feedbackRules" ref="feedbackFormRef" label-width="100px" class="apply-form">
          <el-form-item label="反馈类型" prop="type">
            <el-select v-model="feedbackForm.type" placeholder="请选择反馈类型" style="width:100%">
              <el-option label="问题反馈" value="bug" />
              <el-option label="功能建议" value="feature" />
              <el-option label="投诉" value="complaint" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="标题" prop="title">
            <el-input v-model="feedbackForm.title" placeholder="请简要描述您的反馈" maxlength="100" show-word-limit />
          </el-form-item>
          <el-form-item label="详细内容" prop="content">
            <el-input v-model="feedbackForm.content" type="textarea" :rows="4" placeholder="请详细描述您的问题或建议" maxlength="1000" show-word-limit />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="feedbackForm.contact" placeholder="手机号/邮箱（选填，方便我们联系您）" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSubmit" :loading="submitting">提交反馈</el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- toggle button -->
    <div class="sidebar-toggle" :class="{ collapsed: !sidebarOpen }" @click="sidebarOpen = !sidebarOpen">
      <span class="toggle-icon">{{ sidebarOpen ? '\u25B6' : '\u25C0' }}</span>
      <span v-if="!sidebarOpen" class="toggle-label">记录</span>
    </div>

    <!-- right: records sidebar -->
    <div v-show="sidebarOpen" class="records-sidebar">
      <div class="sidebar-header">
        <h3>申请记录</h3>
        <span class="sidebar-count">近3个月 {{ totalCount }} 条</span>
      </div>
      <div v-if="!groupedMonths.length" class="empty-msg">暂无申请记录</div>
      <div v-for="group in groupedMonths" :key="group.month" class="month-group">
        <div class="month-label">{{ group.label }}</div>
        <div v-for="r in group.records" :key="r._source + '-' + r.id" :class="['record-item', { active: detail && detail.id === r.id && detail._source === r._source }]" @click="viewDetail(r)">
          <div class="record-top">
            <span class="record-type">{{ typeLabel(r.type) }}</span>
            <el-tag :type="statusTagType(r.status)" size="small" effect="plain">{{ statusLabel(r.status) }}</el-tag>
          </div>
          <div class="record-title">{{ r.title }}</div>
          <div class="record-date">{{ formatDate(r.created_at) }}</div>
          <div v-if="r.status === 'pending'" class="record-actions">
            <el-button link type="danger" size="small" @click.stop="handleCancel(r)">撤销</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="detailVisible" :title="detail?.title || '申请详情'" width="620px">
      <div v-if="detail" class="detail-panel">
        <div class="detail-status-bar">
          <el-tag :type="statusTagType(detail.status)" size="large" effect="dark">{{ statusLabel(detail.status) }}</el-tag>
        </div>
        <!-- Leave record detail -->
        <template v-if="detail._source === 'leave'">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="类型">请假（{{ leaveTypeLabel(detail.leave_type) }}）</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="开始日期">{{ detail.start_date }}</el-descriptions-item>
            <el-descriptions-item label="结束日期">{{ detail.end_date }}</el-descriptions-item>
            <el-descriptions-item label="请假原因" :span="2"><div style="white-space:pre-wrap">{{ detail.reason }}</div></el-descriptions-item>
            <el-descriptions-item label="提交时间" :span="2">{{ detail.created_at }}</el-descriptions-item>
            <el-descriptions-item v-if="detail.reject_reason" label="驳回原因" :span="2" style="color:#f56c6c">{{ detail.reject_reason }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <!-- Service ticket detail -->
        <template v-else>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="类型">{{ typeLabel(detail.type) }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="姓名">{{ detail.applicant_name }}</el-descriptions-item>
            <el-descriptions-item label="学号">{{ detail.applicant_no }}</el-descriptions-item>
            <el-descriptions-item label="学院" :span="2">{{ detail.applicant_college }}</el-descriptions-item>
            <el-descriptions-item label="标题" :span="2">{{ detail.title }}</el-descriptions-item>
            <el-descriptions-item label="内容" :span="2"><div style="white-space:pre-wrap">{{ detail.content }}</div></el-descriptions-item>
            <el-descriptions-item label="提交时间" :span="2">{{ detail.created_at }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="detail.form_data && Object.keys(detail.form_data).length" style="margin-top:16px">
            <h4 style="margin-bottom:8px">表单数据</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item v-for="(val, key) in (detail.form_data as Record<string, any>)" :key="key" :label="formFieldLabel(key as string)">
                {{ typeof val === 'object' ? JSON.stringify(val) : val || '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
          <div v-if="detail.attachments?.length" style="margin-top:16px">
            <h4 style="margin-bottom:8px">附件</h4>
            <div v-for="(url, i) in detail.attachments" :key="i" style="margin-bottom:4px">
              <a :href="url" target="_blank" class="attachment-link">{{ fileName(url) }}</a>
            </div>
          </div>
        </template>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTickets, createTicket, cancelTicket } from '@/api/service'
import { getMyLeaves, createLeave, deleteLeave } from '@/api/leave'
import { createFeedback, type FeedbackCreate } from '@/api/feedback'
import { useAuthStore } from '@/stores/auth'
import UploadBtn from '@/components/upload/UploadBtn.vue'
import type { ServiceTicket, LeaveRequestOut } from '@/types'

const auth = useAuthStore()
const route = useRoute()
const activeForm = ref((route.query.type as string) || 'leave')
const tickets = ref<ServiceTicket[]>([])
const leaveRecords = ref<LeaveRequestOut[]>([])
const submitting = ref(false)
const detailVisible = ref(false)
const detail = ref<any | null>(null)
const sidebarOpen = ref(true)
const formRef = ref<any>(null)
const feedbackFormRef = ref<any>(null)

const form = reactive({
  applicant_name: '', applicant_no: '', applicant_college: '',
  title: '', content: '', attachments: [] as string[],
  form_data: {} as Record<string, any>,
})

// 表单验证规则（仅用于普通表单）
const formRules = computed(() => {
  if (activeForm.value === 'leave') {
    return {
      'form_data.leave_type': [{ required: true, message: '请选择请假类型', trigger: 'change' }],
      'form_data.start_date': [{ required: true, message: '请选择开始日期', trigger: 'change' }],
      'form_data.end_date': [{ required: true, message: '请选择结束日期', trigger: 'change' }],
      'content': [{ required: true, message: '请填写请假理由', trigger: 'blur' }],
    }
  }
  if (activeForm.value === 'certificate') {
    return {
      'form_data.certificate_type': [{ required: true, message: '请选择证明类型', trigger: 'change' }],
      'content': [{ required: true, message: '请填写用途说明', trigger: 'blur' }],
    }
  }
  if (activeForm.value === 'project') {
    return {
      'form_data.project_type': [{ required: true, message: '请选择项目类型', trigger: 'change' }],
      'title': [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
      'form_data.start_date': [{ required: true, message: '请选择开始日期', trigger: 'change' }],
      'form_data.end_date': [{ required: true, message: '请选择结束日期', trigger: 'change' }],
      'content': [{ required: true, message: '请填写项目简介', trigger: 'blur' }],
    }
  }
  return {}
})

// 反馈表单验证规则
const feedbackRules = {
  type: [{ required: true, message: '请选择反馈类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入反馈标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入详细内容', trigger: 'blur' }],
}

// 反馈表单
const feedbackForm = reactive<FeedbackCreate>({
  type: 'other',
  title: '',
  content: '',
  contact: ''
})
const formTabs = [
  { key: 'leave', label: '请假申请', icon: '📅', desc: '课假/公假/宿假/事假/病假' },
  { key: 'certificate', label: '证明申请', icon: '📄', desc: '在校证明/成绩单/在读证明' },
  { key: 'project', label: '项目申请', icon: '🚀', desc: '竞赛/科研/社会实践/创业' },
  { key: 'feedback', label: '意见反馈', icon: '💬', desc: '问题反馈/功能建议/投诉' },
]

const currentTab = computed(() => formTabs.find(t => t.key === activeForm.value)!)

let pollTimer: ReturnType<typeof setInterval> | null = null

async function loadTickets() {
  try {
    tickets.value = await getTickets() as any
  } catch {}
}

async function loadLeaveRecords() {
  try {
    leaveRecords.value = await getMyLeaves() as any
  } catch {}
}

async function loadAll() {
  await Promise.all([loadTickets(), loadLeaveRecords()])
}

onMounted(async () => {
  resetForm()
  await loadAll()
  pollTimer = setInterval(loadAll, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 监听路由 query 变化
watch(() => route.query.type, (val) => {
  if (val && typeof val === 'string') activeForm.value = val
})

// 监听表单类型切换，重置表单验证状态
watch(activeForm, () => {
  nextTick(() => {
    if (formRef.value) {
      formRef.value.clearValidate()
      formRef.value.resetFields()
    }
    if (feedbackFormRef.value) {
      feedbackFormRef.value.clearValidate()
      feedbackFormRef.value.resetFields()
    }
  })
})

function resetForm() {
  Object.assign(form, { applicant_name: auth.user?.name || '', applicant_no: auth.user?.username || '', applicant_college: auth.user?.college || '', title: '', content: '', attachments: [], form_data: {} })
  feedbackForm.type = 'other'
  feedbackForm.title = ''
  feedbackForm.content = ''
  feedbackForm.contact = ''
  if (formRef.value) formRef.value.resetFields()
  if (feedbackFormRef.value) feedbackFormRef.value.resetFields()
}

function addAttachment(url: string) { form.attachments.push(url) }
function removeAttachment(i: number) { form.attachments.splice(i, 1) }
function fileName(url: string) { return url.split('/').pop() || url }

function typeLabel(t: string) {
  const m: Record<string, string> = { leave: '请假', certificate: '证明', project: '项目' }
  return m[t] || t
}

function leaveTypeLabel(t: string) {
  const m: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return m[t] || t
}

// 将表单请假类型标签映射为API枚举值
function mapLeaveType(label: string): string {
  const m: Record<string, string> = { '课假': 'other', '公假': 'competition', '宿假': 'personal', '事假': 'personal', '病假': 'sick', '其他': 'other' }
  return m[label] || 'other'
}

function statusLabel(s: string) {
  const m: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已拒绝' }
  return m[s] || s
}

function statusTagType(s: string) {
  const m: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return m[s] || 'info'
}

function formFieldLabel(k: string) {
  const m: Record<string, string> = { leave_type: '请假类型', start_date: '开始日期', end_date: '结束日期', dormitory_building: '宿舍楼', dormitory_room: '宿舍号', parent_proof: '家长证明', certificate_type: '证明类型', quantity: '份数', project_type: '项目类型', advisor: '指导老师', team_members: '团队成员', budget: '预算', project_name: '项目名称' }
  return m[k] || k
}

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const groupedMonths = computed(() => {
  const now = new Date()
  const threeMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 3, 1)
  // 合并请假记录和服务工单（排除工单中的请假类型，因为它们现在是分开的）
  const allRecords: any[] = [
    ...leaveRecords.value.map(r => ({ ...r, _source: 'leave', created_at: r.created_at, type: 'leave', title: `${leaveTypeLabel(r.leave_type)} ${r.start_date} ~ ${r.end_date}` })),
    ...tickets.value.filter(r => r.type !== 'leave').map(r => ({ ...r, _source: 'ticket' })),
  ].filter(r => new Date(r.created_at) >= threeMonthsAgo)
  const groups: { month: string; label: string; records: any[] }[] = []
  const map = new Map<string, any[]>()
  for (const r of allRecords) {
    const d = new Date(r.created_at)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(r)
  }
  const keys = Array.from(map.keys()).sort().reverse()
  for (const k of keys) {
    const [y, m] = k.split('-')
    const d = new Date(+y, +m - 1)
    const label = d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
    groups.push({ month: k, label, records: map.get(k)!.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) })
  }
  return groups
})

const totalCount = computed(() => leaveRecords.value.length + tickets.value.filter(r => r.type !== 'leave').length)

async function handleSubmit() {
  // 处理反馈表单
  if (activeForm.value === 'feedback') {
    // 先验证反馈表单
    if (feedbackFormRef.value) {
      try {
        await feedbackFormRef.value.validate()
      } catch (e) {
        return
      }
    }
    
    submitting.value = true
    try {
      await createFeedback(feedbackForm)
      ElMessage.success('反馈已提交，感谢您的意见！')
      // 重置反馈表单
      feedbackForm.type = 'other'
      feedbackForm.title = ''
      feedbackForm.content = ''
      feedbackForm.contact = ''
      if (feedbackFormRef.value) feedbackFormRef.value.resetFields()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '提交失败')
    } finally {
      submitting.value = false
    }
    return
  }

  // 先验证普通表单
  if (formRef.value) {
    try {
      await formRef.value.validate()
    } catch (e) {
      return
    }
  }

  // 处理其他表单
  submitting.value = true
  try {
    if (activeForm.value === 'leave') {
      // 请假申请提交到leave_requests表（教师审批页面可见）
      const reason = form.form_data.leave_type ? `[${form.form_data.leave_type}] ${form.content}` : form.content
      await createLeave({
        start_date: form.form_data.start_date,
        end_date: form.form_data.end_date,
        reason,
        leave_type: mapLeaveType(form.form_data.leave_type),
      })
      ElMessage.success('请假申请已提交，等待辅导员审批')
      resetForm()
      await loadLeaveRecords()
    } else {
      // 证明和项目申请提交到service_tickets表
      const title = form.title || `${currentTab.value.label}`
      await createTicket({
        type: activeForm.value, title, content: form.content,
        applicant_name: form.applicant_name, applicant_no: form.applicant_no, applicant_college: form.applicant_college,
        form_data: form.form_data, attachments: form.attachments.length ? form.attachments : undefined,
      })
      ElMessage.success('提交成功，等待审批')
      resetForm()
      await loadTickets()
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

function viewDetail(row: any) {
  detail.value = row
  detailVisible.value = true
}

async function handleCancel(row: any) {
  try {
    await ElMessageBox.confirm('确定要撤销这条申请吗？撤销后将直接删除该记录。', '确认撤销', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  try {
    if (row._source === 'leave') {
      await deleteLeave(row.id)
      leaveRecords.value = leaveRecords.value.filter(r => r.id !== row.id)
    } else {
      await cancelTicket(row.id)
      tickets.value = tickets.value.filter(t => t.id !== row.id)
    }
    ElMessage.success('已撤销')
    detailVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '撤销失败')
  }
}
</script>

<style scoped>
.service-page {
  display: flex;
  gap: 20px;
  padding: 20px 24px;
  height: 100%;
  align-items: flex-start;
  max-width: 1200px;
  margin: 0 auto;
  box-sizing: border-box;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.service-page::-webkit-scrollbar { display: none; }
.form-area {
  flex: 1;
  min-width: 0;
}
.page-header h2 { margin: 0 0 4px; font-size: 22px; }
.subtitle { margin: 0 0 20px; color: var(--text-muted); font-size: 14px; }

.tabs-row { display: flex; gap: 12px; margin-bottom: 20px; }
.tab-card {
  flex: 1; display: flex; align-items: center; gap: 10px; padding: 14px 16px;
  border-radius: 10px; border: 1px solid var(--border-color); cursor: pointer;
  transition: all 0.2s; background: var(--bg-primary);
}
.tab-card:hover { border-color: #409eff; background: #ecf5ff; }
.tab-card.active { border-color: #409eff; background: #ecf5ff; box-shadow: 0 2px 8px rgba(64,158,255,0.15); }
.tab-icon { font-size: 24px; }
.tab-title { font-size: 15px; font-weight: 600; margin-bottom: 2px; }
.tab-desc { font-size: 12px; color: var(--text-muted); }

.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #409eff; }
.form-section { background: var(--bg-card); border-radius: 10px; padding: 24px; box-shadow: var(--shadow-md); }
.file-tag { display: inline-block; margin: 4px 4px 0 0; }

.records-sidebar {
  width: 320px; flex-shrink: 0; position: sticky; top: 20px;
  background: var(--bg-card); border-radius: 10px; padding: 16px;
  box-shadow: var(--shadow-md); max-height: calc(100vh - 110px); overflow-y: auto;
  scrollbar-width: none; -ms-overflow-style: none;
}
.records-sidebar::-webkit-scrollbar { display: none; }
.sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.sidebar-header h3 { margin: 0; font-size: 16px; }
.sidebar-count { font-size: 12px; color: var(--text-muted); }
.empty-msg { text-align: center; color: var(--text-placeholder); padding: 40px 0; font-size: 14px; }

.month-group { margin-bottom: 16px; }
.month-label { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; padding: 0 4px; }

.record-item {
  padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.15s;
  border: 1px solid transparent; margin-bottom: 6px;
}
.record-item:hover { background: #f5f7fa; }
.record-item.active { background: #ecf5ff; border-color: #409eff; }
.record-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.record-type { font-size: 12px; color: #409eff; font-weight: 500; }
.record-title { font-size: 13px; color: var(--text-primary); margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.record-date { font-size: 11px; color: var(--text-placeholder); }
.record-actions { margin-top: 4px; }

.detail-panel { max-height: 65vh; overflow-y: auto; scrollbar-width: none; -ms-overflow-style: none; }
.detail-panel::-webkit-scrollbar { display: none; }
.detail-status-bar { margin-bottom: 16px; }
.attachment-link { color: #409eff; text-decoration: none; }
.attachment-link:hover { text-decoration: underline; }

.sidebar-toggle {
  width: 28px; height: 48px; flex-shrink: 0; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 6px 0 0 6px;
  margin-top: 60px; transition: all 0.2s; position: relative;
  box-shadow: -2px 0 6px rgba(0,0,0,0.04);
}
.sidebar-toggle:hover { background: #ecf5ff; border-color: #409eff; color: #409eff; }
.sidebar-toggle.collapsed { border-radius: 0 6px 6px 0; box-shadow: 2px 0 6px rgba(0,0,0,0.04); }
.toggle-icon { font-size: 10px; }
.toggle-label { position: absolute; bottom: -18px; font-size: 11px; color: var(--text-muted); white-space: nowrap; }

/* ===== Mobile ===== */
@media (max-width: 767px) {
  .service-page { flex-direction: column; padding: 12px; gap: 12px; }
  .tabs-row { flex-wrap: wrap; gap: 8px; }
  .tab-card { min-width: calc(50% - 4px); flex: unset; padding: 10px 12px; }
  .tab-desc { display: none; }
  .form-section { padding: 16px; }
  .records-sidebar { width: 100%; position: static; max-height: 300px; }
  .sidebar-toggle { display: none; }
  .el-col { max-width: 100% !important; flex: 0 0 100% !important; }
}
</style>