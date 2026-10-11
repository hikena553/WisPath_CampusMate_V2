<template>
  <div class="home-dashboard">
    <!-- 移动端头部 + 欢迎横幅 -->
    <HomeTopBanner :is-mobile="isMobile" :user-name="authStore.userName || '教师'" :greeting="greeting"
      :today-str="todayStr" />

    <!-- ===== 今日重点（置顶，突出教师个人事务） ===== -->
    <TodayFocusCard @navigate="navigateTo" />

    <!-- ===== 第一层：KPI统计卡片 ===== -->
    <HomeKpiCards :cards="statCards" @navigate="navigateTo" />

    <!-- ===== 常用功能：原「更多」页签内的模块入口，统一收敛为首页彩色圆角宫格 ===== -->
    <section class="home-features">
      <div class="tui-card">
        <div class="tui-card-head">
          <span class="tui-card-head-icon feat-head-icon">
            <el-icon :size="13"><Grid /></el-icon>
          </span>
          常用功能
          <button class="feat-all" type="button" @click="navigateTo('/teacher/features')">
            全部功能
            <el-icon :size="12"><ArrowRight /></el-icon>
          </button>
        </div>
        <div class="tui-grid-nav">
          <button
            v-for="f in featureEntries"
            :key="f.path"
            type="button"
            class="tui-nav-cell"
            @click="navigateTo(f.path)"
          >
            <span class="tui-nav-icon" :style="{ background: f.tint, color: f.color }">
              <el-icon :size="21"><component :is="f.icon" /></el-icon>
            </span>
            <span class="tui-nav-label">{{ f.label }}</span>
            <span
              v-if="f.count > 0"
              class="tui-count"
              :class="{ 'tui-count-warn': f.tone === 'warn' }"
            >{{ f.count > 99 ? '99+' : f.count }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- ===== 我的节奏：本周计划 / 工作量 ===== -->
    <section class="workbench-section">
      <div class="workbench-head">
        <span class="workbench-title">我的节奏</span>
        <span class="workbench-sub">本周安排与工作沉淀</span>
      </div>
      <div class="workbench-grid">
        <WeekPlanCard @open-schedule="openSchedulePanel" />
        <WorkloadCard @open-records="router.push('/teacher/students')" />
      </div>
    </section>

    <!-- ===== AI 悬浮按钮 + 决策支持层 ===== -->
    <HomeAiPanel :proactive-actions="proactiveActions" :contact-suggestions="contactSuggestions"
      :ai-loading="aiLoading" @refresh="loadAiDecisions" />

    <!-- ===== 第三层：日程 + 班级公告（桌面端） ===== -->
    <HomeDesktopSchedule
      v-if="!isMobile"
      :schedules="schedules"
      :pending-leaves="pendingLeaves"
      :my-announcements="myAnnouncements"
      :cal-year="calYear"
      :cal-month="calMonth"
      @select-day="onDayClick"
      @prev-month="prevMonth"
      @next-month="nextMonth"
      @today-month="todayMonth"
      @create="openCreateDialog"
      @delete="handleDelete"
    />

    <!-- 发布公告 Dialog -->
    <HomeAnnouncementDialog v-model:visible="createDialogVisible" @created="loadMyAnnouncements" />

    <!-- 待批请假弹窗 -->
    <HomeLeaveDetailDialog v-model:visible="leaveDetailVisible" :leaves="selectedDayLeaves" @navigate="navigateTo('/teacher/approval')" />

    <!-- 添加日程弹窗（桌面端「去安排」/ 桌面日历点击日期） -->
    <HomeAddScheduleDialog v-model:visible="scheduleDialogVisible" v-model:date="selectedDateStr"
      v-model:content="scheduleContent" v-model:urgency="scheduleUrgency" @added="loadSchedules" />

    <!-- 本周计划「去安排」子页（移动端）：任务管理页，直观展示并可直接添加任务 -->
    <HomeMobileTodayTasks v-if="isMobile && showTodaySubPage" :selected-date="selectedTaskDate"
      :today-leaves="todayLeaves" :today-schedules="todaySchedules" :overdue-schedules="overdueSchedules"
      :schedules="schedules" :pending-leaves="pendingLeaves" :urgency-options="urgencyOptions"
      @close="showTodaySubPage = false" @select-date="handlePopupDateSelect"
      @open-quick-add="openQuickAddDialog" @toggle-complete="toggleScheduleComplete"
      @delete-schedule="handleDeleteSchedule" @navigate="navigateTo" @task-added="handleTaskAdded" />

    <!-- 快捷添加任务弹窗 -->
    <HomeQuickAddTask v-model:visible="quickAddDialogVisible" :selected-task-date="selectedTaskDate"
      :urgency-options="urgencyOptions" @added="handleQuickTaskAdded" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  UserFilled,
  WarningFilled as WarnIcon,
  Grid, Stamp, Bell, Collection, EditPen, Sunny, Connection, ArrowRight,
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
const { isMobile } = useResponsive()
import { getAlerts } from '@/api/crisis'
import { fetchProactiveActions, type ProactiveAction } from '@/api/agent'
import { getPendingLeaves } from '@/api/leave'
import { getDashboardStats, getTeacherSchedules, updateTeacherSchedule, deleteTeacherSchedule, getOverdueSchedules, suggestContacts } from '@/api/teacher'
import type { DashboardStats, ScheduleItem, ScheduleUrgency, ContactSuggestion } from '@/api/teacher'
import { getTeacherAnnouncements, deleteAnnouncement, type AnnouncementItem } from '@/api/announcement'
import type { CrisisAlert, LeaveRequestOut } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCachedData, getPrefetchPromise } from '@/utils/teacherDashboardCache'
import HomeKpiCards from './HomeKpiCards.vue'
import HomeTopBanner from './HomeTopBanner.vue'
import HomeAiPanel from './HomeAiPanel.vue'
import HomeDesktopSchedule from './HomeDesktopSchedule.vue'
import HomeMobileTodayTasks from './HomeMobileTodayTasks.vue'
import HomeQuickAddTask from './HomeQuickAddTask.vue'
import HomeAnnouncementDialog from './HomeAnnouncementDialog.vue'
import HomeLeaveDetailDialog from './HomeLeaveDetailDialog.vue'
import HomeAddScheduleDialog from './HomeAddScheduleDialog.vue'
import TodayFocusCard from '@/components/teacher/workbench/TodayFocusCard.vue'
import WeekPlanCard from '@/components/teacher/workbench/WeekPlanCard.vue'
import WorkloadCard from '@/components/teacher/workbench/WorkloadCard.vue'

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
const myAnnouncements = ref<AnnouncementItem[]>([])
const createDialogVisible = ref(false)
// 移动端「去安排」任务管理子页
const showTodaySubPage = ref(false)
// 任务子页选中日期（默认今天）
const selectedTaskDate = ref(new Date().toISOString().slice(0, 10))
// 快捷添加任务弹窗开关（表单状态在 HomeQuickAddTask 内部维护）
const quickAddDialogVisible = ref(false)
// 打开任务子页时把选中日期重置为今天
watch(showTodaySubPage, (open) => {
  if (open) selectedTaskDate.value = new Date().toISOString().slice(0, 10)
})
const dataReady = ref(false) // 标记数据是否已加载完成，防止空状态闪烁

// 同步读取预加载缓存：setup 阶段直接填充数据，避免首次渲染时空状态闪现
function initFromCache() {
  const cachedStats = getCachedData<DashboardStats>('dashboard-stats')
  const cachedAlerts = getCachedData<CrisisAlert[]>('alerts')
  const cachedPendingLeaves = getCachedData<LeaveRequestOut[]>('pending-leaves')
  const cachedSchedules = getCachedData<ScheduleItem[]>('teacher-schedules')
  const cachedMyAnn = getCachedData<AnnouncementItem[]>('teacher-announcements')
  const cachedOverdue = getCachedData<ScheduleItem[]>('overdue-schedules')
  if (cachedStats) stats.value = cachedStats
  if (cachedAlerts) alerts.value = cachedAlerts
  if (cachedPendingLeaves) pendingLeaves.value = cachedPendingLeaves
  if (cachedSchedules) schedules.value = cachedSchedules
  if (cachedMyAnn) myAnnouncements.value = cachedMyAnn
  if (cachedOverdue) overdueSchedules.value = cachedOverdue
  // 只要任意缓存有数据，就标记为 ready，避免显示加载占位符
  if (cachedStats || cachedAlerts || cachedPendingLeaves || cachedSchedules || cachedMyAnn) {
    dataReady.value = true
  }
}
initFromCache()

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

// 概览 KPI：只保留班级维度的只读统计；个人待办统一收敛到「今日重点」，避免同页重复
const statCards = computed(() => [
  {
    label: '我的学生', value: stats.value.total_students,
    color: '#2563eb', icon: UserFilled, link: '/teacher/students',
  },
  {
    label: '高危预警', value: stats.value.severe_alert_count,
    color: '#d92d20', icon: WarnIcon, link: '/teacher/crisis',
  },
])

/**
 * 常用功能宫格：原「更多」页签内的模块入口，全部迁入首页，点击下钻到对应子页面。
 * 图标底色取自设计令牌（teacher-ui.css）的同源色值，避免各处硬编码散色；
 * 审批 / 预警挂实时角标，来源为首页已预取的 dashboard 统计数据。
 */
const featureEntries = computed(() => [
  { path: '/teacher/approval', label: '审批', icon: Stamp, color: '#b54708', tint: '#fffaeb', count: stats.value.pending_leave_count || 0, tone: 'warn' },
  { path: '/teacher/crisis', label: '预警', icon: WarnIcon, color: '#d92d20', tint: '#fef3f2', count: stats.value.severe_alert_count || 0, tone: 'danger' },
  { path: '/teacher/announcement', label: '公告', icon: Bell, color: '#2563eb', tint: '#eff4ff', count: 0, tone: 'brand' },
  { path: '/teacher/portfolio', label: '成长档案', icon: Collection, color: '#6941c6', tint: '#f4f3ff', count: 0, tone: 'violet' },
  { path: '/teacher/survey', label: '问卷互评', icon: EditPen, color: '#2563eb', tint: '#eff4ff', count: 0, tone: 'brand' },
  { path: '/teacher/care-center', label: '关怀中心', icon: Sunny, color: '#f79009', tint: '#fffaeb', count: 0, tone: 'warn' },
  { path: '/teacher/guardian', label: '家校沟通', icon: Connection, color: '#0891b2', tint: '#ecfeff', count: 0, tone: 'cyan' },
])

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

function navigateTo(path: string) {
  router.push(path)
}

/** 我的节奏：周计划「去安排」——移动端进任务管理子页，桌面端打开添加日程弹窗 */
function openSchedulePanel() {
  if (isMobile.value) {
    showTodaySubPage.value = true
    return
  }
  selectedDateStr.value = new Date().toISOString().slice(0, 10)
  scheduleContent.value = ''
  scheduleUrgency.value = 'normal'
  scheduleDialogVisible.value = true
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

// 任务子页：所选日期的请假与日程（请假以审批为完成路径，日程可勾选完成）
const todayLeaves = computed(() =>
  pendingLeaves.value.filter(l => l.start_date <= selectedTaskDate.value && l.end_date >= selectedTaskDate.value)
)
const todaySchedules = computed(() =>
  schedules.value.filter(s => s.date === selectedTaskDate.value)
)

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

/** 勾选/取消完成：持久化到后端；原地更新状态不重排列表（勾选后卡片不跳位置）；刷新后不丢失 */
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

/** 打开快捷添加任务弹窗（表单重置与聚焦由子组件负责） */
function openQuickAddDialog() {
  quickAddDialogVisible.value = true
}

/** 任务子页弹窗选择日期：同步共享状态并重载对应月份数据 */
function handlePopupDateSelect(date: string) {
  selectedTaskDate.value = date
  const d = new Date(date)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

/** 任务子页内添加任务成功后：同步日历年月以加载对应月份数据 */
function handleTaskAdded() {
  const d = new Date(selectedTaskDate.value)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

/** 快捷添加任务成功回调：同步日历年月并重载当月数据 */
function handleQuickTaskAdded(date: string) {
  const d = new Date(date)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
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
  }
  // 立即使用缓存数据（如果有的话），消除加载等待
  if (cached.s) stats.value = cached.s
  if (cached.a) alerts.value = cached.a
  if (cached.pl) pendingLeaves.value = cached.pl

  // 并行刷新最新数据（静默更新，不触发加载状态）
  const [s, a, pl] = await Promise.all([
    getDashboardStats().catch(() => stats.value),
    getAlerts(undefined).catch(() => alerts.value),
    getPendingLeaves().catch(() => pendingLeaves.value),
  ])
  stats.value = s
  alerts.value = a
  pendingLeaves.value = pl
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
  // 返回首页时重置任务子页日期到今天
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
  /* 顶部留白交由吸顶问候卡（HomeTopBanner）自身内边距提供，便于其铺满整行遮挡滚动内容 */
  padding: 0 16px 12px;
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
}

/* ===== 常用功能：原「更多」迁入的模块宫格（一行平铺，可左右滑动） ===== */
.home-features {
  margin: 4px 0 14px;
}
.home-features .tui-card-head { padding: 13px 16px 9px; font-size: 13px; }
/* 固定宽度 + 横向滚动：不压缩图标与文字，超出部分滑动查看 */
.home-features .tui-grid-nav {
  display: flex;
  gap: 2px;
  padding: 10px 10px 12px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
  scroll-snap-type: x proximity;
}
.home-features .tui-grid-nav::-webkit-scrollbar { display: none; }
.home-features .tui-nav-cell {
  flex: 0 0 auto;
  width: 72px;
  gap: 7px;
  padding: 8px 2px 6px;
  scroll-snap-align: start;
}
.home-features .tui-nav-icon { width: 46px; height: 46px; border-radius: 14px; }
.home-features .tui-nav-label { font-size: 12px; }
.home-features .tui-nav-cell .tui-count {
  top: 4px;
  right: calc(50% - 30px);
}
.feat-head-icon {
  background: #eff4ff;
  color: #2563eb;
}
/* 卡片头部右侧「全部功能」入口：轻量文字按钮，不抢主内容 */
.feat-all {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 0;
  border: none;
  background: transparent;
  color: var(--tui-text-quiet);
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 500;
  cursor: pointer;
}
.feat-all:active { color: var(--tui-text-secondary); }

/* ===== 我的节奏：本周计划 / 工作量 ===== */
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
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