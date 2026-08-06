<template>
  <div class="home-dashboard">
    <!-- ===== Welcome Header ===== -->
    <div class="welcome-header animate-fade-in-up">
      <div class="welcome-left">
        <div class="welcome-greeting">
          <h1 class="text-gradient">{{ greeting }}, {{ authStore.userName || '教师' }}  <span class="wave">👋</span></h1>
          <p class="welcome-sub">今天有 <strong class="animate-pulse">{{ pendingCount }}</strong> 件待办事项 · {{ todayStr }}</p>
        </div>
        <div class="header-tags">
          <el-tag v-if="stats.pending_leave_count > 0" type="warning" effect="plain" class="animate-scale-in delay-200">
            <el-icon><WarningFilled /></el-icon> 待批请假 {{ stats.pending_leave_count }} 条
          </el-tag>
          <el-tag v-if="stats.severe_alert_count > 0" type="danger" effect="plain" class="animate-scale-in delay-300">
            <el-icon><WarningFilled /></el-icon> 高危预警 {{ stats.severe_alert_count }} 条
          </el-tag>
        </div>
      </div>
    </div>

    <!-- ===== AI 绵小城悬浮按钮 ===== -->
    <div class="ai-float" @click="goAgent">
      <img src="/images/mascot.png" alt="绵小城" class="ai-mascot" />
      <span class="ai-label">绵小城</span>
    </div>

    <!-- ===== 统计卡片行 ===== -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="6" v-for="(card, index) in statCards" :key="card.label">
        <div class="stat-card hover-lift animate-fade-in-up" :style="{ '--card-color': card.color, animationDelay: `${index * 0.05 + 0.1}s` }" @click="navigateTo(card.link)">
          <div class="stat-icon-wrapper">
            <el-icon :size="28"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
          <div class="stat-trend" v-if="card.trend !== undefined">
            <span :class="card.trend >= 0 ? 'trend-up' : 'trend-down'">
              {{ card.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(card.trend) }}%
            </span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ===== 综合评价行 ===== -->
    <el-row :gutter="20" class="charts-row">
      <!-- 班级综合评价雷达 -->
      <el-col :xs="24" :md="12">
        <div class="section-card animate-fade-in-left delay-300">
          <div class="section-header" @click="navigateTo('/teacher/students')">
            <h3><el-icon><DataAnalysis /></el-icon> 班级综合评估</h3>
            <el-link type="primary" :underline="false">
              学生档案 <el-icon><DArrowRight /></el-icon>
            </el-link>
          </div>
          <div class="chart-container">
            <VChart v-if="evaluationRadarOptions" :option="evaluationRadarOptions" autoresize />
            <el-empty v-else description="暂无评估数据" :image-size="80" />
          </div>
        </div>
      </el-col>

      <!-- 班级指标卡片 -->
      <el-col :xs="24" :md="12">
        <div class="section-card animate-fade-in-right delay-300">
          <div class="section-header" style="cursor:default">
            <h3><el-icon><DataBoard /></el-icon> 班级指标</h3>
            <el-link type="primary" :underline="false" @click="navigateTo('/teacher/students')">
              学生档案 <el-icon><DArrowRight /></el-icon>
            </el-link>
          </div>
          <div class="metrics-grid">
            <div class="metric-item animate-scale-in delay-400">
              <div class="metric-value" style="color:#5b8def">{{ evalData.total_students }}</div>
              <div class="metric-label">学生总数</div>
            </div>
            <div class="metric-item animate-scale-in delay-450">
              <div class="metric-value" style="color:#67c23a">{{ evalData.avg_gpa?.toFixed(2) || '-' }}</div>
              <div class="metric-label">平均绩点</div>
            </div>
            <div class="metric-item animate-scale-in delay-500">
              <div class="metric-value" style="color:#e6a23c">{{ evalData.avg_score?.toFixed(1) || '-' }}</div>
              <div class="metric-label">平均成绩</div>
            </div>
            <div class="metric-item animate-scale-in delay-600">
              <div class="metric-value" style="color:#f56c6c">{{ evalData.crisis?.total || 0 }}</div>
              <div class="metric-label">预警总数</div>
            </div>
            <div class="metric-item animate-scale-in delay-700">
              <div class="metric-value" style="color:#909399">{{ evalData.pending_leaves || 0 }}</div>
              <div class="metric-label">待处理请假</div>
            </div>
            <div class="metric-item animate-scale-in delay-800">
              <div class="metric-value" style="color:#909399">{{ evalData.crisis?.resolved || 0 }}</div>
              <div class="metric-label">已处理预警</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ===== 底部行：日程计划 + 班级公告 ===== -->
    <el-row :gutter="20" class="bottom-row">
      <!-- 日程计划 - 日历 -->
      <el-col :xs="24" :md="12">
        <div class="section-card animate-fade-in-up delay-400">
          <div class="section-header" style="cursor:default">
            <h3><el-icon><Calendar /></el-icon> 日程计划</h3>
            <div class="cal-nav">
              <el-button text @click="prevMonth">&lt;</el-button>
              <span class="cal-title">{{ calYear }}年{{ calMonth }}月</span>
              <el-button text @click="nextMonth">&gt;</el-button>
              <el-button text @click="todayMonth" size="small" style="margin-left:4px">今天</el-button>
            </div>
          </div>

          <!-- 日历表格 -->
          <table class="cal-table">
            <thead><tr>
              <th v-for="d in ['日','一','二','三','四','五','六']" :key="d">{{ d }}</th>
            </tr></thead>
            <tbody>
              <tr v-for="(week, wi) in calWeeks" :key="wi">
                <td v-for="(day, di) in week" :key="di"
                  :class="{
                    'cal-other': day.month !== 0,
                    'cal-today': day.isToday,
                    'cal-past': day.isPast,
                    'cal-has-leave': day.hasLeave,
                    'cal-has-schedule': day.hasSchedule,
                  }"
                  @click="onDayClick(day)"
                >
                  <span class="cal-day-num">{{ day.num }}</span>
                  <div class="cal-dots">
                    <span v-if="day.hasLeave" class="dot-leave" title="有待批请假"></span>
                    <span v-if="day.hasSchedule" class="dot-schedule" title="有日程"></span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 红点图例说明 -->
          <div class="cal-legend">
            <span><span class="dot-leave" style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px"></span>待批请假</span>
            <span style="margin-left:12px"><span class="dot-schedule" style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px"></span>日程安排</span>
          </div>

          <!-- 待批请假弹窗 -->
          <el-dialog v-model="leaveDetailVisible" title="待处理事项" width="420px">
            <div v-if="selectedDayLeaves.length === 0" class="empty-tip">今日无待处理事项</div>
            <div v-for="l in selectedDayLeaves" :key="l.id" class="schedule-item" @click="navigateTo('/teacher/approval')">
              <div class="schedule-dot dot-warning"></div>
              <div class="schedule-content">
                <div class="schedule-title">{{ l.student_name }} 的请假申请</div>
                <div class="schedule-meta">{{ l.start_date }} ~ {{ l.end_date }} · {{ typeLabel(l.leave_type) }}</div>
              </div>
              <el-button text size="small" type="primary" @click.stop="navigateTo('/teacher/approval')">详情</el-button>
            </div>
          </el-dialog>

          <!-- 添加日程弹窗 -->
          <el-dialog v-model="scheduleDialogVisible" title="添加日程" width="400px">
            <p style="margin-bottom:12px;color:#666">日期：<strong>{{ selectedDateStr }}</strong></p>
            <el-input v-model="scheduleContent" type="textarea" :rows="3" placeholder="请输入日程内容" />
            <template #footer>
              <el-button @click="scheduleDialogVisible = false">取消</el-button>
              <el-button type="primary" @click="handleAddSchedule">保存</el-button>
            </template>
          </el-dialog>

          <!-- 近3日提醒 -->
          <div class="reminder-section">
            <h4 class="reminder-title">📌 未来3日提醒</h4>
            <div v-if="upcomingReminders.length === 0" class="empty-tip">未来3天暂无日程安排</div>
            <div v-for="r in upcomingReminders" :key="r.id" class="reminder-item">
              <div class="reminder-date">{{ r.date.slice(5) }}</div>
              <div class="reminder-content">{{ r.content }}</div>
              <el-button text type="danger" size="small" @click="handleDeleteSchedule(r.id)">删除</el-button>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 班级公告 · 我发布的 -->
      <el-col :xs="24" :md="12">
        <div class="section-card animate-fade-in-up delay-500">
          <div class="section-header" style="cursor:default">
            <h3><el-icon><Notification /></el-icon> 班级公告 · 我发布的</h3>
            <el-button type="primary" size="small" @click="openCreateDialog">发布公告</el-button>
          </div>
          <div class="announce-list" style="min-height:60px">
            <div v-if="myAnnouncements.length === 0" class="empty-tip">暂无公告</div>
            <div v-for="a in myAnnouncements" :key="a.id" class="announce-item">
              <el-tag :type="urgencyTagType(a.urgency)" size="small" effect="plain" style="flex-shrink:0">
                {{ urgencyLabel(a.urgency) }}
              </el-tag>
              <div class="announce-content">
                <div class="announce-title">{{ a.title }}</div>
                <div class="announce-date">{{ new Date(a.created_at).toLocaleString('zh-CN') }}</div>
              </div>
              <a v-if="a.attachment_url" :href="a.attachment_url" target="_blank" class="attach-link" @click.stop>📎</a>
              <el-button text type="danger" size="small" @click="handleDelete(a.id)">删除</el-button>
            </div>
          </div>
        </div>

        <!-- 发布公告 Dialog -->
        <el-dialog v-model="createDialogVisible" title="发布公告" width="520px">
          <el-form label-position="top">
            <el-form-item label="标题">
              <el-input v-model="createForm.title" placeholder="公告标题" maxlength="200" />
            </el-form-item>
            <el-form-item label="内容">
              <el-input v-model="createForm.content" type="textarea" :rows="4" placeholder="公告内容" />
            </el-form-item>
            <el-form-item label="紧急程度">
              <el-radio-group v-model="createForm.urgency">
                <el-radio value="normal">普通</el-radio>
                <el-radio value="important">重要</el-radio>
                <el-radio value="urgent">紧急</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="附件（可选）">
              <input type="file" @change="(e: any) => { if (e.target?.files?.[0]) createFile = e.target.files[0] }" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="createDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleCreate">发布</el-button>
          </template>
        </el-dialog>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  WarningFilled, DataAnalysis, DataBoard,
  Calendar, Notification, UserFilled,
  WarningFilled as WarnIcon,
  EditPen, DArrowRight
} from '@element-plus/icons-vue'
import { getAlerts } from '@/api/crisis'
import { getPendingLeaves } from '@/api/leave'
import { getDashboardStats, getClassEvaluation, getTeacherSchedules, createTeacherSchedule, deleteTeacherSchedule } from '@/api/teacher'
import type { DashboardStats, ClassEvaluation } from '@/api/teacher'
import { getAnnouncements } from '@/api/campus'
import { getTeacherAnnouncements, createAnnouncement, deleteAnnouncement, type AnnouncementItem } from '@/api/announcement'
import type { CrisisAlert, LeaveRequestOut, Announcement } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import {
  TooltipComponent, LegendComponent,
  RadarComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, RadarChart, TooltipComponent, LegendComponent, RadarComponent])

const router = useRouter()
const authStore = useAuthStore()

const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
})
const alerts = ref<CrisisAlert[]>([])
const pendingLeaves = ref<LeaveRequestOut[]>([])
const announcements = ref<Announcement[]>([])
const myAnnouncements = ref<AnnouncementItem[]>([])
const createDialogVisible = ref(false)
const createForm = reactive({ title: '', content: '', urgency: 'normal' })
const createFile = ref<File | null>(null)

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

const statCards = computed(() => [
  {
    label: '我的学生', value: stats.value.total_students,
    color: '#5b8def', icon: UserFilled, link: '/teacher/students',
    trend: undefined,
  },
  {
    label: '危机预警', value: stats.value.alert_count,
    color: '#f56c6c', icon: WarnIcon, link: '/teacher',
    trend: stats.value.alert_count > 0 ? undefined : undefined,
  },
  {
    label: '高危预警', value: stats.value.severe_alert_count,
    color: '#e63946', icon: WarnIcon, link: '/teacher',
    trend: undefined,
  },
  {
    label: '待批请假', value: stats.value.pending_leave_count,
    color: '#e6a23c', icon: EditPen, link: '/teacher/approval',
    trend: undefined,
  },
])

// ===== Class Evaluation Radar =====
const evalData = ref<ClassEvaluation>({
  total_students: 0, avg_gpa: 0, avg_score: 0,
  growth: {}, crisis: {}, pending_leaves: 0,
})

const evaluationRadarOptions = computed(() => {
  const g = evalData.value.growth
  if (!g || Object.keys(g).length === 0) return null
  const vals = [g.honor || 0, g.competition || 0, g.practice || 0, g.paper || 0, g.achievement || 0]
  const max = Math.max(...vals, 1)
  return {
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '荣誉', max: Math.max(max, 1) },
        { name: '竞赛', max: Math.max(max, 1) },
        { name: '实践', max: Math.max(max, 1) },
        { name: '论文', max: Math.max(max, 1) },
        { name: '成果', max: Math.max(max, 1) },
      ],
      axisName: { color: '#666', fontSize: 12 },
      splitArea: {
        areaStyle: {
          color: ['rgba(91,141,239,0.02)', 'rgba(91,141,239,0.06)'],
        },
      },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: vals,
        name: '班级综合',
        areaStyle: { color: 'rgba(91,141,239,0.25)' },
        lineStyle: { color: '#5b8def', width: 2 },
        itemStyle: { color: '#5b8def' },
      }],
      animationDuration: 2000,
      animationEasing: 'cubicOut' as const,
      animationDelay: function(idx: number) {
        return idx * 100;
      }
    }],
    animationDuration: 2000,
    animationEasing: 'cubicOut' as const,
  }
})

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

function navigateTo(path: string) {
  router.push(path)
}

function goAgent() {
  router.push('/teacher/agent')
}

// ===== Calendar State =====
interface CalDay {
  num: number
  month: number  // 0=current, -1=prev, 1=next
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
const schedules = ref<{ id: number; date: string; content: string }[]>([])
const scheduleDialogVisible = ref(false)
const scheduleContent = ref('')
const selectedDateStr = ref('')
const leaveDetailVisible = ref(false)
const selectedDayLeaves = ref<LeaveRequestOut[]>([])

const calWeeks = computed(() => {
  const y = calYear.value
  const m = calMonth.value
  const first = new Date(y, m - 1, 1).getDay()
  const daysInMonth = new Date(y, m, 0).getDate()
  const daysInPrev = new Date(y, m - 1, 0).getDate()
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

  // 构建请假映射
  const leaveMap = new Map<string, LeaveRequestOut[]>()
  pendingLeaves.value.forEach(l => {
    const d = l.start_date
    if (!leaveMap.has(d)) leaveMap.set(d, [])
    leaveMap.get(d)!.push(l)
  })

  // 构建课程表映射
  const scheduleMap = new Map<string, boolean>()
  schedules.value.forEach(s => { scheduleMap.set(s.date, true) })

  const weeks: CalDay[][] = []
  let week: CalDay[] = []
  const totalCells = Math.ceil((first + daysInMonth) / 7) * 7
  for (let i = 0; i < totalCells; i++) {
    let num: number, monthOffset: number
    if (i < first) {
      num = daysInPrev - first + i + 1
      monthOffset = -1
    } else if (i >= first + daysInMonth) {
      num = i - first - daysInMonth + 1
      monthOffset = 1
    } else {
      num = i - first + 1
      monthOffset = 0
    }
    let dateStr = ''
    if (monthOffset === 0) {
      dateStr = `${y}-${String(m).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    } else if (monthOffset === -1) {
      const pm = m === 1 ? 12 : m - 1
      const py = m === 1 ? y - 1 : y
      dateStr = `${py}-${String(pm).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    } else {
      const nm = m === 12 ? 1 : m + 1
      const ny = m === 12 ? y + 1 : y
      dateStr = `${ny}-${String(nm).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    }
    week.push({
      num, month: monthOffset, isToday: dateStr === todayStr,
      isPast: monthOffset === 0 && dateStr < todayStr,
      hasLeave: leaveMap.has(dateStr), hasSchedule: scheduleMap.has(dateStr),
      dateStr, leaves: leaveMap.get(dateStr) || [],
    })
    if (week.length === 7) {
      weeks.push(week)
      week = []
    }
  }
  return weeks
})

const upcomingReminders = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const threeDaysLater = new Date(today)
  threeDaysLater.setDate(threeDaysLater.getDate() + 3)
  return schedules.value.filter(s => {
    const d = new Date(s.date)
    return d >= today && d <= threeDaysLater
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
    scheduleDialogVisible.value = true
  }
}

async function handleAddSchedule() {
  if (!scheduleContent.value.trim()) {
    ElMessage.warning('请输入日程内容')
    return
  }
  try {
    await createTeacherSchedule(selectedDateStr.value, scheduleContent.value)
    ElMessage.success('日程已添加')
    scheduleDialogVisible.value = false
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
  try {
    schedules.value = await getTeacherSchedules(calYear.value, calMonth.value)
  } catch { /* ignore */ }
}

const urgencyMap: Record<string, { type: string; label: string }> = {
  normal: { type: '', label: '普通' },
  important: { type: 'warning', label: '重要' },
  urgent: { type: 'danger', label: '紧急' },
}

function urgencyTagType(u: string) { return urgencyMap[u]?.type || '' }
function urgencyLabel(u: string) { return urgencyMap[u]?.label || u }

async function loadMyAnnouncements() {
  try { myAnnouncements.value = await getTeacherAnnouncements() }
  catch { /* ignore */ }
}

function openCreateDialog() {
  createForm.title = ''
  createForm.content = ''
  createForm.urgency = 'normal'
  createFile.value = null
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.title.trim() || !createForm.content.trim()) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  const fd = new FormData()
  fd.append('title', createForm.title)
  fd.append('content', createForm.content)
  fd.append('urgency', createForm.urgency)
  if (createFile.value) fd.append('file', createFile.value)
  try {
    await createAnnouncement(fd)
    ElMessage.success('发布成功')
    createDialogVisible.value = false
    loadMyAnnouncements()
  } catch { ElMessage.error('发布失败') }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此公告？', '提示')
    await deleteAnnouncement(id)
    ElMessage.success('已删除')
    loadMyAnnouncements()
  } catch { /* canceled or error */ }
}

async function loadData() {
  try {
    stats.value = await getDashboardStats()
  } catch { /* ignore */ }
  try {
    alerts.value = await getAlerts(undefined)
  } catch { /* ignore */ }
  try {
    pendingLeaves.value = await getPendingLeaves()
  } catch { /* ignore */ }
  try {
    announcements.value = await getAnnouncements()
  } catch { /* ignore */ }
  try {
    evalData.value = await getClassEvaluation()
  } catch { /* ignore */ }
}

onMounted(() => {
  loadData()
  loadMyAnnouncements()
  loadSchedules()
})
</script>

<style scoped>
/* ===== Global ===== */
.home-dashboard {
  height: 100%; overflow-y: auto; overflow-x: hidden;
  padding: 8px 4px 120px;
  position: relative;
  animation: fadeInUp 0.35s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes slideInDown {
  from { opacity: 0; transform: translateY(-30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes countUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in-up { animation: fadeInUp 0.35s ease-out; }
.animate-fade-in-left { animation: fadeInLeft 0.35s ease-out; }
.animate-fade-in-right { animation: fadeInRight 0.35s ease-out; }
.animate-scale-in { animation: scaleIn 0.3s ease-out; }
.animate-slide-in-down { animation: slideInDown 0.3s ease-out; }
.animate-pulse { animation: pulse 2s ease-in-out infinite; }
.animate-shimmer {
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}

.delay-100 { animation-delay: 0.03s; }
.delay-200 { animation-delay: 0.06s; }
.delay-300 { animation-delay: 0.09s; }
.delay-400 { animation-delay: 0.12s; }
.delay-500 { animation-delay: 0.15s; }
.delay-600 { animation-delay: 0.18s; }
.delay-700 { animation-delay: 0.21s; }
.delay-800 { animation-delay: 0.24s; }

.text-gradient {
  background: linear-gradient(135deg, #5b8def 0%, #8fb8ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.text-glow {
  text-shadow: 0 0 10px rgba(91, 141, 239, 0.3);
}

.hover-lift {
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease;
}
.hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.12);
}

/* ===== Welcome Header ===== */
.welcome-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28px;
  padding: 24px 28px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
  border-radius: 16px;
  border: 1px solid rgba(91, 141, 239, 0.12);
  position: relative;
  overflow: hidden;
}
.welcome-header::before {
  content: '';
  position: absolute;
  top: -40%;
  right: -10%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(91,141,239,0.06) 0%, transparent 70%);
  border-radius: 50%;
}
.welcome-greeting h1 {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 6px;
}
.wave { display: inline-block; animation: wave 2s infinite; }
@keyframes wave {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(15deg); }
  75% { transform: rotate(-10deg); }
}
.welcome-sub {
  font-size: 14px;
  color: #888;
  margin: 0;
}
.welcome-sub strong { color: #e6a23c; }
.header-tags {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

/* ===== AI Floating Button ===== */
.ai-float {
  position: fixed;
  bottom: 32px;
  right: 32px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.ai-float:hover { transform: scale(1.1); }
.ai-mascot {
  width: 56px;
  height: 56px;
  object-fit: contain;
  transition: transform 0.15s ease;
  animation: mascot-float 2s ease-in-out infinite;
}
.ai-float:hover .ai-mascot { transform: scale(1.15) translateY(-4px); }
@keyframes mascot-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.ai-label {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #5b8def;
  background: rgba(255,255,255,0.9);
  padding: 2px 10px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

/* ===== Stat Cards ===== */
.stats-row { margin-bottom: 24px !important; }
.stat-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
  position: relative;
  overflow: hidden;
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.35s ease-out forwards;
}
.stat-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: var(--card-color);
  border-radius: 0 2px 2px 0;
}
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.08);
}
.stat-card:active {
  transform: translateY(-2px);
}
.stat-icon-wrapper {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--card-color) 12%, white);
  color: var(--card-color);
  flex-shrink: 0;
}
.stat-info { flex: 1; }
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  color: #888;
  margin-top: 2px;
}
.stat-trend { text-align: right; }
.trend-up { color: #67c23a; font-size: 13px; font-weight: 600; }
.trend-down { color: #f56c6c; font-size: 13px; font-weight: 600; }

/* ===== Section Cards ===== */
.section-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px 22px;
  margin-bottom: 20px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.section-header:hover { opacity: 0.7; }
.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ===== Charts ===== */
.charts-row { margin-bottom: 0 !important; }
.chart-container {
  width: 100%;
  height: 260px;
  animation: scaleIn 0.8s ease-out;
  animation-delay: 0.4s;
  animation-fill-mode: both;
}

/* ===== Schedule List ===== */
.schedule-list { min-height: 120px; }
.empty-tip {
  text-align: center;
  color: #bbb;
  padding: 32px 0;
  font-size: 14px;
}
.schedule-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 6px;
}
.schedule-item:hover {
  background: rgba(91,141,239,0.05);
}
.schedule-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-warning { background: #e6a23c; }
.dot-danger { background: #f56c6c; }
.dot-info { background: #909399; }
.dot-success { background: #67c23a; }
.schedule-content { flex: 1; min-width: 0; }
.schedule-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.schedule-meta {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

/* ===== Announcement List ===== */
.announce-list { min-height: 120px; }
.announce-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  transition: all 0.2s ease;
  margin-bottom: 2px;
  opacity: 0;
  transform: translateY(10px);
  animation: fadeInUp 0.4s ease-out forwards;
}
.announce-item:nth-child(2) { animation-delay: 0.05s; }
.announce-item:nth-child(3) { animation-delay: 0.1s; }
.announce-item:nth-child(4) { animation-delay: 0.15s; }
.announce-item:hover { 
  background: rgba(91,141,239,0.04); 
  transform: translateY(-2px);
}
.announce-badge {
  width: 6px;
  height: 24px;
  border-radius: 3px;
  flex-shrink: 0;
}
.badge-blue { background: #5b8def; }
.badge-green { background: #67c23a; }
.badge-orange { background: #e6a23c; }
.badge-purple { background: #9b59b6; }
.announce-content { flex: 1; min-width: 0; }
.announce-title {
  font-size: 13.5px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.announce-date {
  font-size: 12px;
  color: #bbb;
  margin-top: 2px;
}
.announce-list .empty-tip { text-align: center; color: #bbb; padding: 16px 0; font-size: 13px; }
.announce-list .announce-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 0; border-bottom: 1px solid #f5f5f5;
}
.announce-list .announce-item:last-child { border-bottom: none; }

/* ===== Metrics Grid ===== */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 4px 0;
}
.metric-item {
  text-align: center;
  padding: 16px 8px;
  border-radius: 10px;
  background: #f8faff;
  border: 1px solid rgba(91,141,239,0.06);
  transition: all 0.3s ease;
  opacity: 0;
  transform: scale(0.9);
  animation: scaleIn 0.3s ease-out forwards;
}
.metric-item:hover {
  background: #f0f7ff;
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(91,141,239,0.1);
}
.metric-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
  transition: all 0.3s ease;
}
.metric-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  transition: color 0.3s ease;
}
.metric-item:hover .metric-value {
  transform: scale(1.1);
}
.metric-item:hover .metric-label {
  color: #5b8def;
}

/* ===== Calendar ===== */
.cal-nav { display: flex; align-items: center; gap: 2px; }
.cal-title { font-size: 14px; font-weight: 600; color: #333; min-width: 100px; text-align: center; }
.cal-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
.cal-table th {
  font-size: 12px; color: #999; font-weight: 500;
  padding: 6px 0; text-align: center;
}
.cal-table td {
  text-align: center; padding: 6px 0;
  cursor: pointer; border-radius: 6px;
  transition: all 0.2s ease;
  vertical-align: top;
  position: relative;
  height: 48px;
}
.cal-table td:hover { 
  background: rgba(91,141,239,0.06); 
  transform: scale(1.1);
}
.cal-other { opacity: 0.25; pointer-events: none; }
.cal-past { opacity: 0.4; cursor: default; }
.cal-past:hover { background: transparent !important; transform: none !important; }
.cal-past .cal-day-num { color: #ccc; }
.cal-today .cal-day-num {
  background: #5b8def; color: #fff;
  display: inline-block; width: 26px; height: 26px;
  line-height: 26px; border-radius: 50%;
  font-weight: 600;
  animation: pulse 2s ease-in-out infinite;
}
.cal-day-num { font-size: 13px; font-weight: 500; }
.cal-dots { display: flex; justify-content: center; gap: 3px; min-height: 8px; margin-top: 2px; }
.dot-leave { width: 6px; height: 6px; border-radius: 50%; background: #f56c6c; display: inline-block; }
.dot-schedule { width: 6px; height: 6px; border-radius: 50%; background: #67c23a; display: inline-block; }
.cal-has-leave .cal-day-num { position: relative; }
.cal-legend { font-size: 11px; color: #999; margin-bottom: 12px; padding: 4px 0; }

/* ===== Reminder Section ===== */
.reminder-section {
  border-top: 1px solid #f0f0f0;
  padding-top: 14px;
  margin-top: 4px;
}
.reminder-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin: 0 0 10px;
}
.reminder-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 4px;
  transition: all 0.2s ease;
  opacity: 0;
  transform: translateX(-20px);
  animation: fadeInLeft 0.3s ease-out forwards;
}
.reminder-item:nth-child(2) { animation-delay: 0.05s; }
.reminder-item:nth-child(3) { animation-delay: 0.1s; }
.reminder-item:nth-child(4) { animation-delay: 0.15s; }
.reminder-item:hover { 
  background: rgba(91,141,239,0.04); 
  transform: translateX(4px);
}
.reminder-date {
  font-size: 12px;
  font-weight: 600;
  color: #5b8def;
  background: #f0f7ff;
  padding: 2px 10px;
  border-radius: 10px;
  flex-shrink: 0;
}
.reminder-content { flex: 1; font-size: 13px; color: #555; }
.announce-list .announce-content { flex: 1; min-width: 0; }
.announce-list .announce-title { font-size: 13.5px; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.announce-list .announce-date { font-size: 11px; color: #bbb; margin-top: 1px; }
.attach-link { text-decoration: none; font-size: 16px; cursor: pointer; }
</style>
