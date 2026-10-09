<template>
  <div class="home-dashboard">
    <!-- 移动端头部 + 欢迎横幅 -->
    <HomeTopBanner :is-mobile="isMobile" :user-name="authStore.userName || '教师'" :greeting="greeting"
      :pending-count="pendingCount" :severe-alert-count="stats.severe_alert_count" :today-str="todayStr" />

    <!-- ===== 第一层：KPI统计卡片 ===== -->
    <HomeKpiCards :cards="statCards" @navigate="navigateTo" />

    <!-- ===== 我的工作台（模块 7）：今日待办 / 本周计划 / 工作量 ===== -->
    <section class="workbench-section">
      <div class="workbench-head">
        <span class="workbench-title">我的工作台</span>
        <span class="workbench-sub">以「我」为主语，一眼看清今天该做什么</span>
      </div>
      <div class="workbench-grid">
        <TodayTasksCard @open-tasks="openTasksPanel" />
        <WeekPlanCard @open-schedule="openSchedulePanel" />
        <WorkloadCard @open-records="router.push('/teacher/students')" />
      </div>
    </section>

    <!-- ===== AI 悬浮按钮 + 决策支持层 ===== -->
    <HomeAiPanel :proactive-actions="proactiveActions" :contact-suggestions="contactSuggestions"
      :ai-loading="aiLoading" @refresh="loadAiDecisions" />

    <!-- 班级数据分析：归属「学生」页（与学生相关的数据维度），首页不再内嵌（功能不交叉） -->

    <!-- 移动端：逾期提醒 + 今日任务 + 公告 -->
    <HomeMobileToday v-if="isMobile" :today-leaves="todayLeaves" :today-schedules="todaySchedules"
      :campus-announcements="campusAnnouncements" :overdue-count="overdueSchedules.length"
      @open-today="showTodaySubPage = true" />

    <!-- 移动端：待办任务子页（统一任务层） -->
    <HomeMobileTasks v-if="isMobile && showTasksSubPage" @close="showTasksSubPage = false" />

    <!-- 添加日程子页面 -->
    <!-- transition removed -->
    <HomeMobileSchedule v-if="isMobile && showScheduleSubPage" :content="scheduleContent"
      :urgency="scheduleUrgency" :urgency-options="urgencyOptions" :upcoming-reminders="upcomingReminders"
      @close="showScheduleSubPage = false" @update:content="scheduleContent = $event"
      @update:urgency="scheduleUrgency = $event" @add="handleAddScheduleFromSubPage"
      @delete="handleDeleteSchedule" />
    <!-- /transition removed -->

    <!-- 危机预警：归属「预警工作台」模块页，首页不再内嵌（功能不交叉） -->

    <!-- 待办任务子页面 -->
    <!-- transition removed -->
    <!-- ===== 移动端：今日任务子页 ===== -->
    <HomeMobileTodayTasks v-if="isMobile && showTodaySubPage" :selected-date="selectedTaskDate"
      :today-leaves="todayLeaves" :today-schedules="todaySchedules" :overdue-schedules="overdueSchedules"
      :schedules="schedules" :pending-leaves="pendingLeaves" :urgency-options="urgencyOptions"
      @close="showTodaySubPage = false" @select-date="handlePopupDateSelect"
      @open-quick-add="openQuickAddDialog" @toggle-complete="toggleScheduleComplete"
      @delete-schedule="handleDeleteSchedule" @navigate="navigateTo" @task-added="handleTaskAdded" />
    <!-- /transition removed -->

    <!-- ===== 第三层：日程 + 公告（桌面端） ===== -->
    <HomeDesktopSchedule
      v-if="!isMobile"
      :schedules="schedules"
      :pending-leaves="pendingLeaves"
      :campus-announcements="campusAnnouncements"
      :my-announcements="myAnnouncements"
      :upcoming-reminders="upcomingReminders"
      :cal-year="calYear"
      :cal-month="calMonth"
      @select-day="onDayClick"
      @prev-month="prevMonth"
      @next-month="nextMonth"
      @today-month="todayMonth"
      @delete-schedule="handleDeleteSchedule"
      @create="openCreateDialog"
      @delete="handleDelete"
    />

    <!-- 审批管理：归属「审批管理」模块页，首页不再内嵌（功能不交叉） -->

    <!-- 发布公告 Dialog -->
    <HomeAnnouncementDialog v-model:visible="createDialogVisible" @created="loadMyAnnouncements" />

    <!-- 待批请假弹窗 -->
    <HomeLeaveDetailDialog v-model:visible="leaveDetailVisible" :leaves="selectedDayLeaves" @navigate="navigateTo('/teacher/approval')" />

    <!-- 快捷添加任务弹窗 -->
    <HomeQuickAddTask v-model:visible="quickAddDialogVisible" :selected-task-date="selectedTaskDate"
      :urgency-options="urgencyOptions" @added="handleQuickTaskAdded" />
    <!-- 添加日程弹窗 -->
    <HomeAddScheduleDialog v-model:visible="scheduleDialogVisible" :date="selectedDateStr"
      v-model:content="scheduleContent" v-model:urgency="scheduleUrgency" @added="loadSchedules" />
    <!-- 桌面端：全部待办任务弹窗（模块 7 工作台入口） -->
    <el-dialog v-model="showTasksDialog" title="我的待办任务"
      :width="isMobile ? '92%' : '640px'" align-center destroy-on-close class="wb-task-dialog">
      <TeacherTaskList initial-filter="all" @record-care="openQuickCare" />
    </el-dialog>

    <!-- 记录关怀（来自任务卡） -->
    <CareRecordDialog v-model="showCareDialog" :student-id="careStudentId"
      :student-name="careStudentName" :task-id="careTaskId" :task-title="careTaskTitle" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  UserFilled,
  WarningFilled as WarnIcon, EditPen,
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
const { isMobile } = useResponsive()
import { getAlerts } from '@/api/crisis'
import { fetchProactiveActions, type ProactiveAction } from '@/api/agent'
import { getPendingLeaves } from '@/api/leave'
import { getDashboardStats, getTeacherSchedules, createTeacherSchedule, deleteTeacherSchedule, getOverdueSchedules, updateTeacherSchedule, suggestContacts } from '@/api/teacher'
import type { TeacherTask } from '@/api/teacherTask'
import type { DashboardStats, ScheduleItem, ScheduleUrgency, ContactSuggestion } from '@/api/teacher'
import { getAnnouncements } from '@/api/campus'
import { getTeacherAnnouncements, deleteAnnouncement, type AnnouncementItem } from '@/api/announcement'
import type { CrisisAlert, LeaveRequestOut, Announcement } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCachedData, getPrefetchPromise } from '@/utils/teacherDashboardCache'
import HomeKpiCards from './HomeKpiCards.vue'
import HomeTopBanner from './HomeTopBanner.vue'
import HomeAiPanel from './HomeAiPanel.vue'
import HomeMobileToday from './HomeMobileToday.vue'
import HomeDesktopSchedule from './HomeDesktopSchedule.vue'
import HomeMobileTodayTasks from './HomeMobileTodayTasks.vue'
import HomeMobileTasks from './HomeMobileTasks.vue'
import HomeMobileSchedule from './HomeMobileSchedule.vue'
import HomeAnnouncementDialog from './HomeAnnouncementDialog.vue'
import HomeLeaveDetailDialog from './HomeLeaveDetailDialog.vue'
import HomeQuickAddTask from './HomeQuickAddTask.vue'
import HomeAddScheduleDialog from './HomeAddScheduleDialog.vue'
import TodayTasksCard from '@/components/teacher/workbench/TodayTasksCard.vue'
import WeekPlanCard from '@/components/teacher/workbench/WeekPlanCard.vue'
import WorkloadCard from '@/components/teacher/workbench/WorkloadCard.vue'
import TeacherTaskList from '@/components/teacher/task/TeacherTaskList.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'

// keep-alive include 按组件名匹配，必须与 TeacherLayout 的 cachedNames 一致，否则切换时组件被销毁重建导致数据闪变
defineOptions({ name: 'teacher-home' })

const router = useRouter()
const authStore = useAuthStore()

const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
})
const alerts = ref<CrisisAlert[]>([])
const proactiveActions = ref<ProactiveAction[]>([])
const contactSuggestions = ref<ContactSuggestion[]>([])
const aiLoading = ref(false)

/** 拉取 AI 决策支持数据（主动发现 + 推荐联系），低频调用不参与 30s 轮询 */
async function loadAiDecisions() {
  aiLoading.value = true
  try {
    const [acts, contacts] = await Promise.all([
      fetchProactiveActions().catch(() => [] as ProactiveAction[]),
      suggestContacts().catch(() => [] as ContactSuggestion[]),
    ])
    proactiveActions.value = acts
    contactSuggestions.value = contacts
  } finally {
    aiLoading.value = false
  }
}
const pendingLeaves = ref<LeaveRequestOut[]>([])
const announcements = ref<Announcement[]>([])
const myAnnouncements = ref<AnnouncementItem[]>([])
const createDialogVisible = ref(false)
const campusAnnouncements = ref<Announcement[]>([])
const showScheduleSubPage = ref(false)
const dataReady = ref(false) // 标记数据是否已加载完成，防止空状态闪烁

// 同步读取预加载缓存：setup 阶段直接填充数据，避免首次渲染时空状态闪现
function initFromCache() {
  const cachedStats = getCachedData<DashboardStats>('dashboard-stats')
  const cachedAlerts = getCachedData<CrisisAlert[]>('alerts')
  const cachedPendingLeaves = getCachedData<LeaveRequestOut[]>('pending-leaves')
  const cachedAnnouncements = getCachedData<Announcement[]>('announcements')
  const cachedCampusAnn = getCachedData<Announcement[]>('announcements')
  const cachedSchedules = getCachedData<ScheduleItem[]>('teacher-schedules')
  const cachedMyAnn = getCachedData<AnnouncementItem[]>('teacher-announcements')
  const cachedOverdue = getCachedData<ScheduleItem[]>('overdue-schedules')
  if (cachedStats) stats.value = cachedStats
  if (cachedAlerts) alerts.value = cachedAlerts
  if (cachedPendingLeaves) pendingLeaves.value = cachedPendingLeaves
  if (cachedAnnouncements) announcements.value = cachedAnnouncements
  if (cachedCampusAnn) campusAnnouncements.value = cachedCampusAnn
  if (cachedSchedules) schedules.value = cachedSchedules
  if (cachedMyAnn) myAnnouncements.value = cachedMyAnn
  if (cachedOverdue) overdueSchedules.value = cachedOverdue
  // 只要任意缓存有数据，就标记为 ready，避免显示加载占位符
  if (cachedStats || cachedAlerts || cachedPendingLeaves || cachedAnnouncements || cachedCampusAnn || cachedSchedules || cachedMyAnn) {
    dataReady.value = true
  }
}
initFromCache()

// 今日任务
const todayLeaves = computed(() => {
  const date = selectedTaskDate.value
  return pendingLeaves.value.filter(l => l.start_date <= date && l.end_date >= date)
})
const todaySchedules = computed(() => {
  const date = selectedTaskDate.value
  return schedules.value.filter(s => s.date === date)
})

// 标记任务完成/取消完成：持久化到后端；原地更新状态不重排列表（勾选后卡片不跳位置）；刷新后不丢失
async function toggleScheduleComplete(s: ScheduleItem) {
  const target = !s.completed
  try {
    await updateTeacherSchedule(s.id, target)
    // PATCH 已提交，作废在途的逾期列表请求，防止其旧响应覆盖即将更新的本地状态
    overdueReqSeq++
    s.completed = target
    s.completed_at = target ? new Date().toISOString() : null
    // 逾期提醒条本地即时同步（不等网络往返）
    const todayStr = new Date().toISOString().slice(0, 10)
    if (target) {
      overdueSchedules.value = overdueSchedules.value.filter(o => o.id !== s.id)
    } else if (s.date < todayStr) {
      overdueSchedules.value = [s, ...overdueSchedules.value.filter(o => o.id !== s.id)]
    }
    await loadOverdueSchedules() // 本地同步后与服务器对齐（内部有 guard，失败不抛）
  } catch {
    ElMessage.error('操作失败')
  }
}

const pendingCount = computed(() =>
  stats.value.pending_leave_count + stats.value.severe_alert_count
)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayStr = computed(() => {
  const d = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 星期${week[d.getDay()]}`
})

// 概览 KPI：只保留班级维度的只读统计；个人待办统一收敛到「我的工作台」，避免同页重复
const statCards = computed(() => [
  {
    label: '我的学生', value: stats.value.total_students,
    color: '#5b8def', icon: UserFilled, link: '/teacher/students',
  },
  {
    label: '危机预警', value: stats.value.alert_count,
    color: '#f56c6c', icon: WarnIcon, link: '/teacher/crisis',
  },
  {
    label: '待批请假', value: stats.value.pending_leave_count,
    color: '#e6a23c', icon: EditPen, link: '/teacher/approval',
  },
])

// ===== Class Evaluation Radar =====
const showTodaySubPage = ref(false)
const showTasksSubPage = ref(false)
// 桌面端全部待办弹窗（工作台入口）
const showTasksDialog = ref(false)
// 工作台：来自任务卡的记录关怀
const showCareDialog = ref(false)
const careStudentId = ref(0)
const careStudentName = ref('')
const careTaskId = ref<number>()
const careTaskTitle = ref('')
watch(showTodaySubPage, (open) => {
  if (open) selectedTaskDate.value = new Date().toISOString().slice(0, 10)
})

// 任务日期选择
const selectedTaskDate = ref(new Date().toISOString().slice(0, 10))

// 快捷添加任务弹窗开关（表单状态在 HomeQuickAddTask 内部维护）
const quickAddDialogVisible = ref(false)

// 任务等级选项（普通/重要/紧急）
const urgencyOptions: { value: ScheduleUrgency; label: string }[] = [
  { value: 'normal', label: '普通' },
  { value: 'important', label: '重要' },
  { value: 'urgent', label: '紧急' },
]

// 逾期未完成任务提醒（已过期且未完成，跨月份）
const overdueSchedules = ref<ScheduleItem[]>([])
// 逾期列表请求序号：仅写入最新请求的响应，避免轮询旧数据覆盖刚勾选完成的状态
let overdueReqSeq = 0

// 打开快捷添加弹窗（表单重置与聚焦由子组件负责）
function openQuickAddDialog() {
  quickAddDialogVisible.value = true
}

// 快捷添加任务成功回调：同步日历年月并重载当月数据
function handleQuickTaskAdded(date: string) {
  const d = new Date(date)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

// 任务子页弹窗选择日期：同步共享状态并重载对应月份数据
function handlePopupDateSelect(date: string) {
  selectedTaskDate.value = date
  const d = new Date(date)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

// 任务子页弹窗内添加任务成功后：同步日历年月以加载对应月份数据
function handleTaskAdded() {
  const d = new Date(selectedTaskDate.value)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

function navigateTo(path: string) {
  router.push(path)
}

/** 工作台：全部待办——移动端进子页，桌面端开弹窗 */
function openTasksPanel() {
  if (isMobile.value) showTasksSubPage.value = true
  else showTasksDialog.value = true
}

/** 工作台：周计划去安排——移动端进日程子页，桌面端开新增日程 */
function openSchedulePanel() {
  if (isMobile.value) showScheduleSubPage.value = true
  else openCreateDialog()
}

/** 工作台：任务卡一键记录关怀 */
function openQuickCare(task: TeacherTask) {
  if (!task.student_id) {
    navigateTo('/teacher/students')
    return
  }
  careStudentId.value = task.student_id
  careStudentName.value = task.student_name
  careTaskId.value = task.id
  careTaskTitle.value = task.title
  showCareDialog.value = true
}

// ===== Calendar State =====
interface CalDay {
  num: number
  month: number
  isToday: boolean
  isPast: boolean
  hasLeave: boolean
  hasSchedule: boolean
  dateStr: string
  leaves: LeaveRequestOut[]
}
const now = new Date()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth() + 1)
const schedules = ref<ScheduleItem[]>([])
const scheduleDialogVisible = ref(false)
const scheduleContent = ref('')
const scheduleUrgency = ref<ScheduleUrgency>('normal')

const selectedDateStr = ref('')
const leaveDetailVisible = ref(false)
const selectedDayLeaves = ref<LeaveRequestOut[]>([])

const upcomingReminders = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const threeDaysLater = new Date(today)
  threeDaysLater.setDate(threeDaysLater.getDate() + 3)
  return schedules.value.filter(s => {
    const d = new Date(s.date)
    return !s.completed && d >= today && d <= threeDaysLater
  }).sort((a, b) => a.date.localeCompare(b.date))
})

function prevMonth() {
  if (calMonth.value === 1) { calYear.value--; calMonth.value = 12 }
  else calMonth.value--
  loadSchedules()
}
function nextMonth() {
  if (calMonth.value === 12) { calYear.value++; calMonth.value = 1 }
  else calMonth.value++
  loadSchedules()
}
function todayMonth() {
  const n = new Date()
  calYear.value = n.getFullYear()
  calMonth.value = n.getMonth() + 1
  loadSchedules()
}

function onDayClick(day: CalDay) {
  if (day.month !== 0 || day.isPast) return
  if (day.hasLeave) {
    selectedDayLeaves.value = day.leaves
    leaveDetailVisible.value = true
  } else {
    selectedDateStr.value = day.dateStr
    scheduleContent.value = ''
    scheduleUrgency.value = 'normal'
    scheduleDialogVisible.value = true
  }
}

async function handleAddScheduleFromSubPage(date: string) {
  if (!date || !scheduleContent.value.trim()) return
  try {
    await createTeacherSchedule(date, scheduleContent.value.trim(), scheduleUrgency.value)
    ElMessage.success('日程已添加')
    scheduleContent.value = ''
    scheduleUrgency.value = 'normal'
    showScheduleSubPage.value = false
    loadSchedules()
  } catch { ElMessage.error('添加失败') }
}

async function handleDeleteSchedule(id: number) {
  try {
    await deleteTeacherSchedule(id)
    ElMessage.success('已删除')
    loadSchedules()
  } catch { ElMessage.error('删除失败') }
}

async function loadSchedules() {
  const prefetch = getPrefetchPromise()
  if (prefetch) await prefetch
  // 仅在本地无数据时用缓存兜底：已有数据时跳过缓存，避免轮询期间旧缓存覆盖刚勾选的完成状态
  const cached = getCachedData<ScheduleItem[]>('teacher-schedules')
  if (cached && schedules.value.length === 0) schedules.value = cached
  try {
    schedules.value = await getTeacherSchedules(calYear.value, calMonth.value)
  } catch { /* ignore */ }
}

async function loadOverdueSchedules() {
  const seq = ++overdueReqSeq
  try {
    const data = await getOverdueSchedules()
    // 仅当前最新请求的响应才写入，防止过期响应覆盖本地刚同步的勾选状态
    if (seq === overdueReqSeq) overdueSchedules.value = data
  } catch { /* ignore */ }
}

async function loadMyAnnouncements() {
  const prefetch = getPrefetchPromise()
  if (prefetch) await prefetch
  const cached = getCachedData<AnnouncementItem[]>('teacher-announcements')
  if (cached) myAnnouncements.value = cached
  try { myAnnouncements.value = await getTeacherAnnouncements() }
  catch { /* ignore */ }
}

function openCreateDialog() {
  createDialogVisible.value = true
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此公告？', '提示')
    await deleteAnnouncement(id)
    ElMessage.success('已删除')
    loadMyAnnouncements()
  } catch { /* canceled or error */ }
}

// 数据预加载缓存：优先读取布局预加载的缓存数据（即时显示），然后并行刷新
async function loadData() {
  // 如果预加载仍在进行，先等待其完成（避免从空缓存读取导致数字跳变）
  const prefetch = getPrefetchPromise()
  if (prefetch) await prefetch

  // 从预加载缓存读取
  const cached = {
    s: getCachedData<DashboardStats>('dashboard-stats'),
    a: getCachedData<CrisisAlert[]>('alerts'),
    pl: getCachedData<LeaveRequestOut[]>('pending-leaves'),
    ann: getCachedData<Announcement[]>('announcements'),
    ca: getCachedData<Announcement[]>('announcements'),
  }
  // 立即使用缓存数据（如果有的话），消除加载等待
  if (cached.s) stats.value = cached.s
  if (cached.a) alerts.value = cached.a
  if (cached.pl) pendingLeaves.value = cached.pl
  if (cached.ann) announcements.value = cached.ann
  if (cached.ca) campusAnnouncements.value = cached.ca

  // 并行刷新最新数据（静默更新，不触发加载状态）
  const [s, a, pl, ann, ca] = await Promise.all([
    getDashboardStats().catch(() => stats.value),
    getAlerts(undefined).catch(() => alerts.value),
    getPendingLeaves().catch(() => pendingLeaves.value),
    getAnnouncements().catch(() => announcements.value),
    getAnnouncements().catch(() => campusAnnouncements.value),
  ])
  stats.value = s
  alerts.value = a
  pendingLeaves.value = pl
  announcements.value = ann
  campusAnnouncements.value = ca
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let lastRefreshAt = 0

// 静默后台刷新：并行加载所有数据，不触发任何加载状态
async function silentRefresh() {
  await Promise.all([
    loadData(),
    loadSchedules(),
    loadMyAnnouncements(),
    loadOverdueSchedules(),
  ]).catch(() => {})
  lastRefreshAt = Date.now()
  dataReady.value = true // 数据加载完成，允许显示空状态
}

onMounted(() => {
  silentRefresh()
  loadAiDecisions()
  pollTimer = setInterval(silentRefresh, 30000)
})

onActivated(() => {
  // 返回首页时重置日期到今天
  selectedTaskDate.value = new Date().toISOString().slice(0, 10)
  // 距上次刷新超过60秒才触发静默刷新（后台更新数据，不触发加载动画）
  if (Date.now() - lastRefreshAt >= 60_000) {
    silentRefresh()
  }
  // 恢复轮询（若被 onDeactivated 暂停）
  if (pollTimer === null) {
    pollTimer = setInterval(silentRefresh, 30000)
  }
})

onDeactivated(() => {
  // 暂停轮询，但保留组件状态
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

onUnmounted(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style>
/* 全局禁用教师首页所有 CSS 动效（非 scoped：覆盖 Element Plus 内部元素与伪元素；ECharts 动画已在各图表选项中单独关闭） */
.home-dashboard,
.home-dashboard *,
.home-dashboard *::before,
.home-dashboard *::after {
  transition: none !important;
  animation: none !important;
}
</style>

<style scoped>
/* ===== Global ===== */
.home-dashboard {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.section-title:hover {
  opacity: 0.7;
}


/* ===== Common ===== */
.empty-tip {
  text-align: center;
  color: #bbb;
  padding: 24px 0;
  font-size: 13px;
}

.empty-tip-small {
  text-align: center;
  color: #bbb;
  padding: 14px 0;
  font-size: 12px;
}

/* ===== Schedule Items ===== */
.schedule-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.schedule-item:hover {
  background: rgba(91,141,239,0.05);
}

.schedule-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-warning { background: #e6a23c; }

.schedule-content {
  flex: 1;
  min-width: 0;
}

.schedule-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.schedule-meta {
  font-size: 11px;
  color: #999;
  margin-top: 1px;
}

.dot-leave { background: #e6a23c; }
.dot-schedule { background: #409eff; }

.schedule-add-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

/* ===== Responsive ===== */
@media (max-width: 767px) {
  .home-dashboard {
    padding: 0 8px 12px;
  }

  .section-title {
    font-size: 13px;
  }

  /* 快捷添加任务弹窗 */
  .quick-add-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 2100;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
  }
  .quick-add-popup {
    width: 280px;
    padding: 20px 16px 16px;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  }
  .quick-add-title {
    text-align: center;
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
  }
  .quick-add-date {
    text-align: center;
    font-size: 12px;
    color: #9ca3af;
    margin: 6px 0 14px;
  }
  .quick-add-input {
    width: 100%;
    box-sizing: border-box;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #f9fafb;
    padding: 10px 12px;
    font-size: 14px;
    color: #1f2937;
    outline: none;
  }
  .quick-add-input:focus {
    border-color: #3b82f6;
    background: #fff;
  }
  .quick-add-input::placeholder {
    color: #c0c4cc;
  }
  .quick-add-actions {
    display: flex;
    gap: 10px;
    margin-top: 16px;
  }
  .quick-add-cancel {
    flex: 1;
    padding: 9px 0;
    border: none;
    border-radius: 8px;
    background: #f3f4f6;
    color: #6b7280;
    font-size: 14px;
    cursor: pointer;
  }
  .quick-add-submit {
    flex: 1;
    padding: 9px 0;
    border: none;
    border-radius: 8px;
    background: #3b82f6;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
  }
  .quick-add-submit:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .quick-add-urgency {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  .urgency-opt {
    flex: 1;
    padding: 7px 0;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fff;
    color: #6b7280;
    font-size: 12px;
    cursor: pointer;
  }
  .urgency-opt.active {
    border-color: #3b82f6;
    background: #eff6ff;
    color: #2563eb;
    font-weight: 600;
  }
  .urgency-opt.active.important {
    border-color: #f59e0b;
    background: #fffbeb;
    color: #b45309;
  }
  .urgency-opt.active.urgent {
    border-color: #ef4444;
    background: #fef2f2;
    color: #dc2626;
  }
}

/* ===== 我的工作台（模块 7）：今日待办 / 本周计划 / 工作量 ===== */
.workbench-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 4px 0 14px;
}
.workbench-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 0 4px;
}
.workbench-title {
  font-size: 15px;
  font-weight: 700;
  color: #101828;
}
.workbench-sub {
  font-size: 12px;
  color: #98a2b3;
}
.workbench-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
}

@media (max-width: 767px) {
  .workbench-head {
    flex-direction: column;
    gap: 2px;
  }
  .workbench-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}

</style>
