<template>
  <!--
    移动端首页看板（原 HomePage 移动端整块）：问候横幅 → 今日重点 → KPI → 常用功能 → 我的节奏。
    从 HomePage.vue 抽出的目的：教师端「首页」位置改为校园资讯后，这一块下沉到「工作台」页
    作为首屏主导内容，两处共用同一份实现，避免模板与逻辑各写一遍导致后续改版不同步。

    下拉刷新手势由父页面统一挂载（父页面可能已有自己的刷新逻辑），
    本组件只负责在吸顶横幅之后渲染指示器占位；父级未传 pullIndicatorStyle 时不渲染。
  -->
  <div class="home-board">
    <!-- 移动端头部 + 欢迎横幅（吸顶固定，不参与下拉位移） -->
    <HomeTopBanner :is-mobile="true" :user-name="authStore.userName || '教师'" :greeting="greeting"
      :today-str="todayStr" :identity="teacherIdentity">
      <template #actions>
        <span class="hm-sync-hint">
          <i class="hm-sync-dot" />每 30 秒自动同步
        </span>
      </template>
    </HomeTopBanner>

    <PullRefreshIndicator
      v-if="pullStyle"
      :indicator-style="pullStyle"
      :active="pullOn"
    />

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
      </div>
      <div class="workbench-grid">
        <WeekPlanCard @open-schedule="openSchedulePanel" />
        <WorkloadCard @open-records="emit('open-records')" />
      </div>
    </section>

    <!-- 本周计划「去安排」子页（移动端）：任务管理页，直观展示并可直接添加任务 -->
    <HomeMobileTodayTasks v-if="showTodaySubPage" :selected-date="selectedTaskDate"
      :today-leaves="todayLeaves" :today-schedules="todaySchedules" :overdue-schedules="overdueSchedules"
      :schedules="schedules" :pending-leaves="pendingLeaves" :urgency-options="urgencyOptions"
      @close="showTodaySubPage = false" @select-date="handlePopupDateSelect"
      @open-quick-add="openQuickAddDialog" @toggle-complete="toggleScheduleComplete"
      @delete-schedule="handleDeleteSchedule" @navigate="navigateTo" @task-added="handleTaskAdded" />

    <!-- 快捷添加任务弹窗 -->
    <HomeQuickAddTask v-model:visible="quickAddDialogVisible" :selected-task-date="selectedTaskDate"
      :urgency-options="urgencyOptions" @added="handleQuickTaskAdded" />

    <!-- 添加日程弹窗 -->
    <HomeAddScheduleDialog v-model:visible="scheduleDialogVisible" v-model:date="selectedDateStr"
      v-model:content="scheduleContent" v-model:urgency="scheduleUrgency" @added="loadSchedules" />

    <!-- 待批请假弹窗 -->
    <HomeLeaveDetailDialog v-model:visible="leaveDetailVisible" :leaves="selectedDayLeaves" @navigate="navigateTo('/teacher/approval')" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  UserFilled,
  WarningFilled as WarnIcon,
  Grid, Stamp, Bell, Collection, EditPen, Sunny,
  ArrowRight, TrendCharts, Notebook,
} from '@element-plus/icons-vue'
import { getAlerts } from '@/api/crisis'
import { getPendingLeaves } from '@/api/leave'
import {
  getDashboardStats, getTeacherSchedules, updateTeacherSchedule, deleteTeacherSchedule,
  getOverdueSchedules,
} from '@/api/teacher'
import type { DashboardStats, ScheduleItem, ScheduleUrgency } from '@/api/teacher'
import { getTeacherTaskSummary, type TeacherTaskSummary } from '@/api/teacherTask'
import type { CrisisAlert, LeaveRequestOut } from '@/types'
import { ElMessage } from 'element-plus'
import { getCachedData, getPrefetchPromise } from '@/utils/teacherDashboardCache'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import HomeKpiCards from './HomeKpiCards.vue'
import HomeTopBanner from './HomeTopBanner.vue'
import HomeMobileTodayTasks from './HomeMobileTodayTasks.vue'
import HomeQuickAddTask from './HomeQuickAddTask.vue'
import { useMobileSubPage } from '@/composables/useMobileSubPage'
import HomeAddScheduleDialog from './HomeAddScheduleDialog.vue'
import HomeLeaveDetailDialog from './HomeLeaveDetailDialog.vue'
import TodayFocusCard from '@/components/teacher/workbench/TodayFocusCard.vue'
import WeekPlanCard from '@/components/teacher/workbench/WeekPlanCard.vue'
import WorkloadCard from '@/components/teacher/workbench/WorkloadCard.vue'

defineOptions({ name: 'home-mobile-board' })

const props = withDefaults(defineProps<{
  /**
   * 父页面下拉刷新的指示器位移：父页面已挂手势时传入（本组件不再重复监听 touch 事件，
   * 否则同屏两套下拉手势会互相抢、也会出现两个吉祥物指示器）。
   */
  pullIndicatorStyle?: Record<string, string> | null
  pullActive?: boolean
}>(), { pullIndicatorStyle: null, pullActive: false })
// 供模板读取（下拉指示器占位）
const pullStyle = computed(() => props.pullIndicatorStyle)
const pullOn = computed(() => props.pullActive)

/** 「我的学生」KPI / 工作量卡在本页内部的落点是「学生名单」二级子页，交给父页面决定怎么开 */
const emit = defineEmits<{ 'open-records': [] }>()

const router = useRouter()
const authStore = useAuthStore()

const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
  my_open_tasks: 0, my_overdue_tasks: 0, my_due_today: 0,
  my_care_month: 0, my_visits_month: 0, my_guardian_month: 0,
  my_done_rate: 0, my_coverage_rate: 0,
  my_course_count: 0, today_course_count: 0, my_pending_submissions: 0,
  current_week: 0, semester: '',
})
const alerts = ref<CrisisAlert[]>([])
const pendingLeaves = ref<LeaveRequestOut[]>([])
const taskSummary = ref<TeacherTaskSummary>({ pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0 })

// 移动端「去安排」任务管理子页
const showTodaySubPage = ref(false)
// 移动端「今日任务」子页：打开时让出底部悬浮导航
useMobileSubPage(computed(() => showTodaySubPage.value))
// 任务子页选中日期（默认今天）
const selectedTaskDate = ref(new Date().toISOString().slice(0, 10))
// 快捷添加任务弹窗开关（表单状态在 HomeQuickAddTask 内部维护）
const quickAddDialogVisible = ref(false)
watch(showTodaySubPage, (open) => {
  if (open) selectedTaskDate.value = new Date().toISOString().slice(0, 10)
})

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

/** 教师身份（学院 · 职称 · 所带班级）：取登录态真实字段拼装，空字段自动省略 */
const teacherIdentity = computed(() => {
  const u = authStore.user
  if (!u) return ''
  const parts: string[] = []
  if (u.college) parts.push(u.college)
  if (u.title) parts.push(u.title)
  if (u.class_name) parts.push(`所带 ${u.class_name}`)
  return parts.join(' · ')
})

// 概览 KPI（移动端）：只保留班级维度的只读统计；个人待办统一收敛到「今日重点」
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

/** 常用功能宫格：图标底色取自设计令牌同源色值；审批 / 预警挂实时角标 */
const featureEntries = computed(() => [
  { path: '/teacher/approval', label: '审批', icon: Stamp, color: '#b54708', tint: '#fffaeb', count: stats.value.pending_leave_count || 0, tone: 'warn' },
  { path: '/teacher/crisis', label: '预警', icon: WarnIcon, color: '#d92d20', tint: '#fef3f2', count: stats.value.severe_alert_count || 0, tone: 'danger' },
  { path: '/teacher/announcement', label: '公告', icon: Bell, color: '#2563eb', tint: '#eff4ff', count: 0, tone: 'brand' },
  { path: '/teacher/portfolio', label: '成长档案', icon: Collection, color: '#6941c6', tint: '#f4f3ff', count: 0, tone: 'violet' },
  { path: '/teacher/survey', label: '问卷互评', icon: EditPen, color: '#2563eb', tint: '#eff4ff', count: 0, tone: 'brand' },
  { path: '/teacher/care-center', label: '关怀与家校', icon: Sunny, color: '#f79009', tint: '#fffaeb', count: 0, tone: 'warn' },
  { path: '/teacher/growth', label: '我的成长', icon: TrendCharts, color: '#6941c6', tint: '#f4f3ff', count: 0, tone: 'violet' },
  // 仅保留只读课表入口，课堂点名/作业/成绩已下线
  { path: '/teacher/schedule', label: '我的课表', icon: Notebook, color: '#0891b2', tint: '#ecfeff', count: 0, tone: 'cyan' },
])

/** 本页内的「我的学生」落点 = 学生名单二级子页；其余路径照常路由跳转 */
function navigateTo(path: string) {
  if (path === '/teacher/students') {
    emit('open-records')
    return
  }
  router.push(path)
}

// ===== 日程 / 任务 =====
const urgencyOptions: { value: ScheduleUrgency; label: string }[] = [
  { value: 'normal', label: '普通' },
  { value: 'important', label: '重要' },
  { value: 'urgent', label: '紧急' },
]

const now = new Date()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth() + 1)
const schedules = ref<ScheduleItem[]>([])
const overdueSchedules = ref<ScheduleItem[]>([])
const scheduleDialogVisible = ref(false)
const scheduleContent = ref('')
const scheduleUrgency = ref<ScheduleUrgency>('normal')
const selectedDateStr = ref('')
const leaveDetailVisible = ref(false)
const selectedDayLeaves = ref<LeaveRequestOut[]>([])

// 逾期列表请求序号：仅写入最新请求的响应，避免轮询旧数据覆盖刚勾选完成的状态
let overdueReqSeq = 0

const todayLeaves = computed(() =>
  pendingLeaves.value.filter(l => l.start_date <= selectedTaskDate.value && l.end_date >= selectedTaskDate.value)
)
const todaySchedules = computed(() =>
  schedules.value.filter(s => s.date === selectedTaskDate.value)
)

/** 我的节奏：周计划「去安排」——移动端进任务管理子页 */
function openSchedulePanel() {
  showTodaySubPage.value = true
}

/** 勾选/取消完成：持久化到后端；原地更新状态不重排列表 */
async function toggleScheduleComplete(s: ScheduleItem) {
  const target = !s.completed
  try {
    await updateTeacherSchedule(s.id, target)
    overdueReqSeq++
    s.completed = target
    s.completed_at = target ? new Date().toISOString() : null
    const today = new Date().toISOString().slice(0, 10)
    if (target) {
      overdueSchedules.value = overdueSchedules.value.filter(o => o.id !== s.id)
    } else if (s.date < today) {
      overdueSchedules.value = [s, ...overdueSchedules.value.filter(o => o.id !== s.id)]
    }
    await loadOverdueSchedules()
  } catch {
    ElMessage.error('操作失败')
  }
}

function openQuickAddDialog() {
  quickAddDialogVisible.value = true
}

function handlePopupDateSelect(date: string) {
  selectedTaskDate.value = date
  const d = new Date(date)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

function handleTaskAdded() {
  const d = new Date(selectedTaskDate.value)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

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
    if (seq === overdueReqSeq) overdueSchedules.value = data
  } catch { /* ignore */ }
}

async function loadData() {
  const prefetch = getPrefetchPromise()
  if (prefetch) await prefetch
  const cached = {
    s: getCachedData<DashboardStats>('dashboard-stats'),
    a: getCachedData<CrisisAlert[]>('alerts'),
    pl: getCachedData<LeaveRequestOut[]>('pending-leaves'),
    ts: getCachedData<TeacherTaskSummary>('teacher-task-summary'),
  }
  if (cached.s) stats.value = cached.s
  if (cached.a) alerts.value = cached.a
  if (cached.pl) pendingLeaves.value = cached.pl
  if (cached.ts) taskSummary.value = cached.ts

  const [s, a, pl, ts] = await Promise.all([
    getDashboardStats().catch(() => stats.value),
    getAlerts(undefined).catch(() => alerts.value),
    getPendingLeaves().catch(() => pendingLeaves.value),
    getTeacherTaskSummary().catch(() => taskSummary.value),
  ])
  stats.value = s
  alerts.value = a
  pendingLeaves.value = pl
  taskSummary.value = ts
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let lastRefreshAt = 0

/** 静默后台刷新：并行加载全部数据，不触发任何加载状态 */
async function silentRefresh() {
  await Promise.all([
    loadData(),
    loadSchedules(),
    loadOverdueSchedules(),
  ]).catch(() => {})
  lastRefreshAt = Date.now()
}

onMounted(() => {
  silentRefresh()
  pollTimer = setInterval(silentRefresh, 30000)
})

onActivated(() => {
  selectedTaskDate.value = new Date().toISOString().slice(0, 10)
  if (Date.now() - lastRefreshAt >= 60_000) silentRefresh()
  if (pollTimer === null) pollTimer = setInterval(silentRefresh, 30000)
})

onDeactivated(() => {
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

/** 供父页面的下拉刷新一并带上本块数据 */
defineExpose({ refresh: silentRefresh })
</script>

<style>
/* 与首页同口径：本块内禁用所有 CSS 动效（下拉刷新指示器除外，它靠过渡做回弹） */
.home-board *:not(.ptr-ind):not(.ptr-mascot),
.home-board *:not(.ptr-ind):not(.ptr-mascot)::before,
.home-board *:not(.ptr-ind):not(.ptr-mascot)::after {
  transition: none !important;
  animation: none !important;
}
</style>

<style scoped>
/* 问候卡需要在「整页」范围内吸顶：本块不产生盒子，
   使 sticky 的包含块直接落到外层滚动容器（.students-page），
   否则滚过本块末尾（班级数据分析等后续内容）时，问候卡会随本块一起上移 */
.home-board { display: contents; }

/* ===== 今日重点：与上方吸顶问候卡之间的呼吸间距（问候卡自身无下边距） ===== */
.home-board :deep(.tf-card) {
  margin-top: 12px;
}

/* ===== 常用功能（移动端）：模块宫格（一行平铺，可左右滑动） ===== */
.home-features {
  margin: 4px 0 14px;
}
.home-features .tui-card-head { padding: 13px 16px 9px; font-size: 13px; }
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

/* ===== 页头操作（插进 HomeTopBanner 的 actions 插槽） ===== */
.hm-sync-hint {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(37, 99, 235, 0.14);
  font-size: 11.5px;
  color: #667085;
  white-space: nowrap;
}
.hm-sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #12b76a;
  box-shadow: 0 0 0 2px rgba(18, 183, 106, 0.18);
  flex-shrink: 0;
}

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
.workbench-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
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
