<template>
  <div class="home-dashboard">
    <!-- ===== 第一层：欢迎横幅（精简版） ===== -->
    <div class="welcome-banner">
      <div class="welcome-content">
        <h2 class="welcome-title">{{ greeting }}，{{ authStore.userName || '教师' }}</h2>
        <span class="today-text">{{ todayStr }}</span>
      </div>
      <div class="welcome-tags">
        <el-tag v-if="pendingCount > 0" type="warning" size="small" effect="plain">
          <el-icon><WarningFilled /></el-icon> {{ pendingCount }} 件待办
        </el-tag>
        <el-tag v-if="stats.severe_alert_count > 0" type="danger" size="small" effect="plain">
          <el-icon><WarningFilled /></el-icon> {{ stats.severe_alert_count }} 条高危预警
        </el-tag>
      </div>
    </div>

    <!-- ===== AI 绵小城悬浮按钮 ===== -->
    <div class="ai-float" @click="goAgent">
      <img src="/images/mascot.png" alt="绵小城" class="ai-mascot" />
      <span class="ai-label">绵小城</span>
    </div>

    <!-- ===== 第一层：KPI统计卡片 ===== -->
    <div class="kpi-cards">
      <div class="kpi-card" v-for="card in statCards" :key="card.label"
        :style="{ '--kpi-color': card.color }" @click="navigateTo(card.link)">
        <div class="kpi-icon">
          <el-icon :size="24"><component :is="card.icon" /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ card.value }}</div>
          <div class="kpi-label">{{ card.label }}</div>
        </div>
        <div class="kpi-trend" v-if="card.trend !== undefined" :class="card.trend >= 0 ? 'trend-up' : 'trend-down'">
          {{ card.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(card.trend) }}%
        </div>
      </div>
    </div>

    <!-- ===== 第二层：数据分析区（左2:右1） ===== -->
    <div class="analytics-row">
      <!-- 左侧：雷达图 + 成绩分布 + 政治面貌 + 预警趋势 + 生源地 -->
      <div class="analytics-left">
        <!-- 第一行：雷达图 + 成绩分布 -->
        <div class="chart-row">
          <div class="chart-half">
            <div class="section-title" @click="navigateTo('/teacher/students')">
              <el-icon><DataAnalysis /></el-icon>
              <span>班级综合评估</span>
              <el-link type="primary" :underline="false" class="section-link">
                学生档案 <el-icon><DArrowRight /></el-icon>
              </el-link>
            </div>
            <div class="chart-container">
              <VChart v-if="evaluationRadarOptions" :option="evaluationRadarOptions" autoresize />
              <el-empty v-else description="暂无评估数据" :image-size="60" />
            </div>
          </div>
          <div class="chart-half">
            <div class="section-title">
              <el-icon><Histogram /></el-icon>
              <span>成绩分布</span>
            </div>
            <div class="chart-container">
              <VChart v-if="gradeBarOptions" :option="gradeBarOptions" autoresize />
              <el-empty v-else description="暂无数据" :image-size="60" />
            </div>
          </div>
        </div>

        <!-- 第二行：政治面貌 + 预警趋势 -->
        <div class="chart-row">
          <div class="chart-half">
            <div class="section-title">
              <el-icon><UserFilled /></el-icon>
              <span>政治面貌分布</span>
            </div>
            <div class="chart-container">
              <VChart v-if="politicalPieOptions" :option="politicalPieOptions" autoresize />
              <el-empty v-else description="暂无数据" :image-size="60" />
            </div>
          </div>
          <div class="chart-half">
            <div class="section-title">
              <el-icon><WarningFilled /></el-icon>
              <span>预警趋势</span>
            </div>
            <div class="chart-container">
              <VChart v-if="crisisTrendOptions" :option="crisisTrendOptions" autoresize />
              <el-empty v-else description="暂无数据" :image-size="60" />
            </div>
          </div>
        </div>

        <!-- 第三行：生源地分布（全宽） -->
        <div class="chart-full">
          <div class="section-title">
            <el-icon><Location /></el-icon>
            <span>生源地分布</span>
          </div>
          <div class="chart-container">
            <VChart v-if="hometownBarOptions" :option="hometownBarOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
      </div>

      <!-- 右侧：两个饼图 -->
      <div class="analytics-right">
        <div class="chart-section half">
          <div class="section-title">
            <el-icon><UserFilled /></el-icon>
            <span>性别比例</span>
          </div>
          <div class="chart-container pie-chart">
            <VChart v-if="genderPieOptions" :option="genderPieOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
        <div class="chart-divider"></div>
        <div class="chart-section half">
          <div class="section-title">
            <el-icon><WarningFilled /></el-icon>
            <span>心理危机分布</span>
          </div>
          <div class="chart-container pie-chart">
            <VChart v-if="crisisPieOptions" :option="crisisPieOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
        <div class="chart-divider"></div>
        <div class="ai-analysis-section">
          <div class="section-title">
            <el-icon><DataAnalysis /></el-icon>
            <span>AI 班级分析</span>
          </div>
          <div v-if="!analysisResult && !analysisLoading" class="analysis-placeholder">
            <p>点击按钮，AI 将为您分析班级数据</p>
            <el-button type="primary" @click="handleClassAnalysis" :loading="analysisLoading" size="small">
              开始分析
            </el-button>
          </div>
          <div v-else-if="analysisLoading" class="analysis-loading">
            <el-icon class="loading-icon"><DataAnalysis /></el-icon>
            <p>AI 正在分析班级数据...</p>
          </div>
          <div v-else class="analysis-content">
            <div class="analysis-text">{{ analysisResult }}</div>
            <el-button text type="primary" size="small" @click="handleClassAnalysis">
              重新分析
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 第三层：日程 + 公告（1:1） ===== -->
    <div class="schedule-row">
      <!-- 左侧：日历 + 提醒 -->
      <div class="schedule-section">
        <div class="section-title">
          <el-icon><Calendar /></el-icon>
          <span>日程安排</span>
        </div>
        <div class="calendar-wrapper">
          <div class="cal-nav">
            <el-button text size="small" @click="prevMonth">&lt;</el-button>
            <span class="cal-title">{{ calYear }}年{{ calMonth }}月</span>
            <el-button text size="small" @click="nextMonth">&gt;</el-button>
            <el-button text size="small" @click="todayMonth" style="margin-left:4px">今天</el-button>
          </div>
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
          <div class="cal-legend">
            <span><span class="dot-leave"></span> 待批请假</span>
            <span><span class="dot-schedule"></span> 日程安排</span>
          </div>
        </div>
        <div class="upcoming-section">
          <div class="reminder-title">📌 近期提醒</div>
          <div v-if="upcomingReminders.length === 0" class="empty-tip-small">暂无提醒</div>
          <div v-for="r in upcomingReminders.slice(0, 3)" :key="r.id" class="reminder-item">
            <span class="reminder-date">{{ r.date.slice(5) }}</span>
            <span class="reminder-content">{{ r.content }}</span>
            <el-button text type="danger" size="small" @click="handleDeleteSchedule(r.id)">删除</el-button>
          </div>
        </div>
      </div>

      <!-- 右侧：公告（Tab切换） -->
      <div class="announcements-section">
        <el-tabs v-model="activeAnnouncementTab" class="announcement-tabs">
          <el-tab-pane label="校园公告" name="campus">
            <div class="announcement-list">
              <div v-if="campusAnnouncements.length === 0" class="empty-tip-small">暂无校园公告</div>
              <a v-for="(item, index) in campusAnnouncements.slice(0, 5)" :key="index"
                :href="item.url || '#'" target="_blank" class="campus-item">
                <span class="campus-title">{{ item.title }}</span>
                <span class="campus-date">{{ item.date }}</span>
              </a>
            </div>
            <el-button text type="primary" size="small" class="view-all-btn"
              href="https://jwc.mycc.edu.cn/jwgl/tzgg.htm" target="_blank">
              查看更多 <el-icon><DArrowRight /></el-icon>
            </el-button>
          </el-tab-pane>
          <el-tab-pane label="班级公告" name="class">
            <div class="tab-header">
              <el-button type="primary" size="small" @click="openCreateDialog">发布公告</el-button>
            </div>
            <div class="announcement-list">
              <div v-if="myAnnouncements.length === 0" class="empty-tip-small">暂无公告</div>
              <div v-for="a in myAnnouncements.slice(0, 5)" :key="a.id" class="announcement-item">
                <el-tag :type="urgencyTagType(a.urgency)" size="small" effect="plain">
                  {{ urgencyLabel(a.urgency) }}
                </el-tag>
                <div class="announcement-content">
                  <div class="announcement-title">{{ a.title }}</div>
                  <div class="announcement-date">{{ formatDate(a.created_at) }}</div>
                </div>
                <a v-if="a.attachment_url" :href="a.attachment_url" target="_blank" class="attach-link" @click.stop>📎</a>
                <el-button text type="danger" size="small" @click="handleDelete(a.id)">删除</el-button>
              </div>
            </div>
            <el-button v-if="myAnnouncements.length > 5" text type="primary" size="small" class="view-all-btn">
              查看全部 <el-icon><DArrowRight /></el-icon>
            </el-button>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 发布公告 Dialog -->
    <el-dialog v-model="createDialogVisible" title="发布公告" width="520px">
      <el-form ref="announcementFormRef" :model="createForm" label-position="top" :rules="announcementRules">
        <el-form-item label="标题" prop="title">
          <el-input v-model="createForm.title" placeholder="请输入公告标题，如：关于五一放假安排的通知" maxlength="200" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="createForm.content" type="textarea" :rows="4" placeholder="请输入公告内容，建议包含时间、地点、注意事项等" />
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
      <el-form ref="scheduleFormRef" :model="{ content: scheduleContent }" :rules="scheduleRules">
        <el-form-item prop="content">
          <el-input v-model="scheduleContent" type="textarea" :rows="3" placeholder="请输入日程内容，如：期中考试监考" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddSchedule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  WarningFilled, DataAnalysis, Calendar, UserFilled,
  WarningFilled as WarnIcon, EditPen, DArrowRight, Histogram, Location
} from '@element-plus/icons-vue'
import { getAlerts } from '@/api/crisis'
import { getPendingLeaves } from '@/api/leave'
import { getDashboardStats, getClassEvaluation, getTeacherSchedules, createTeacherSchedule, deleteTeacherSchedule, getClassStats } from '@/api/teacher'
import type { DashboardStats, ClassEvaluation, ClassStats } from '@/api/teacher'
import { getAnnouncements } from '@/api/campus'
import { getTeacherAnnouncements, createAnnouncement, deleteAnnouncement, type AnnouncementItem } from '@/api/announcement'
import type { CrisisAlert, LeaveRequestOut, Announcement } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAiAnalysis } from '@/composables/useAiAnalysis'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, PieChart, BarChart, LineChart } from 'echarts/charts'
import {
  TooltipComponent, LegendComponent,
  RadarComponent, GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, RadarChart, PieChart, BarChart, LineChart, TooltipComponent, LegendComponent, RadarComponent, GridComponent])

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
const announcementFormRef = ref<any>()
const announcementRules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }],
}
const classStats = ref<ClassStats>({
  total_students: 0,
  gender_stats: {},
  crisis_stats: {},
  grade_stats: {},
  political_stats: {},
  hometown_stats: {},
  crisis_trend: [],
})
const campusAnnouncements = ref<Announcement[]>([])
const activeAnnouncementTab = ref('campus')

// ===== AI 班级分析 =====
const { loading: analysisLoading, renderedResult: analysisResult, analyze: runAnalysis } = useAiAnalysis('teacher-class-analysis')

function buildAnalysisPrompt() {
  const stats = classStats.value
  return `作为辅导员老师，请分析以下班级数据并给出指导建议：

班级数据：
- 学生总数：${stats.total_students}
- 性别比例：${JSON.stringify(stats.gender_stats)}
- 政治面貌：${JSON.stringify(stats.political_stats)}
- 心理危机分布：高危${stats.crisis_stats?.severe || 0}人、中危${stats.crisis_stats?.moderate || 0}人、低危${stats.crisis_stats?.mild || 0}人、已解决${stats.crisis_stats?.resolved || 0}人
- 成绩分布：优秀${stats.grade_stats?.excellent || 0}人、良好${stats.grade_stats?.good || 0}人、中等${stats.grade_stats?.medium || 0}人、及格${stats.grade_stats?.pass || 0}人、不及格${stats.grade_stats?.fail || 0}人

请从以下方面进行分析：
1. 班级整体概况
2. 心理健康状况分析
3. 学业成绩分析
4. 辅导员工作建议

请用简洁专业的语言，控制在500字以内。`
}

async function handleClassAnalysis() {
  await runAnalysis(buildAnalysisPrompt(), { skipCache: true })
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

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

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
      animationDuration: 1500,
      animationEasing: 'cubicOut' as const,
    }],
  }
})

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

// ===== 性别比例饼图 =====
const genderPieOptions = computed(() => {
  const data = classStats.value.gender_stats
  if (!data || Object.keys(data).length === 0) return null
  
  const colors = ['#5b8def', '#f56c6c', '#67c23a', '#e6a23c', '#909399']
  const pieData = Object.entries(data).map(([name, value], index) => ({
    name,
    value,
    itemStyle: { color: colors[index % colors.length] }
  }))
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 5,
      textStyle: { color: '#666', fontSize: 11 }
    },
    series: [{
      name: '性别分布',
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 'bold' }
      },
      data: pieData,
    }]
  }
})

// ===== 心理危机比例饼图 =====
const crisisPieOptions = computed(() => {
  const data = classStats.value.crisis_stats
  if (!data) return null
  
  const colors = ['#f56c6c', '#e6a23c', '#67c23a', '#909399']
  const names = ['高危', '中危', '低危', '已解决']
  const values = [data.severe || 0, data.moderate || 0, data.mild || 0, data.resolved || 0]
  
  const total = values.reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  const pieData = names.map((name, index) => ({
    name,
    value: values[index],
    itemStyle: { color: colors[index] }
  }))
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 5,
      textStyle: { color: '#666', fontSize: 11 }
    },
    series: [{
      name: '危机分布',
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 'bold' }
      },
      data: pieData,
    }]
  }
})

// ===== 成绩分布柱状图 =====
const gradeBarOptions = computed(() => {
  const data = classStats.value.grade_stats
  if (!data) return null
  
  const categories = ['优秀', '良好', '中等', '及格', '不及格']
  const values = [data.excellent || 0, data.good || 0, data.medium || 0, data.pass || 0, data.fail || 0]
  
  const total = values.reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  const colors = ['#67c23a', '#5b8def', '#e6a23c', '#f56c6c', '#909399']
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#666', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#666' }
    },
    series: [{
      name: '人数',
      type: 'bar',
      barWidth: '50%',
      data: values.map((value, index) => ({
        value,
        itemStyle: { color: colors[index], borderRadius: [3, 3, 0, 0] }
      })),
    }],
  }
})

// ===== 政治面貌饼图 =====
const politicalPieOptions = computed(() => {
  const data = classStats.value.political_stats
  if (!data || Object.keys(data).length === 0) return null
  
  const total = Object.values(data).reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  const colors = ['#5b8def', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
  const pieData = Object.entries(data).map(([name, value], index) => ({
    name,
    value,
    itemStyle: { color: colors[index % colors.length] }
  }))
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 5,
      textStyle: { color: '#666', fontSize: 11 }
    },
    series: [{
      name: '政治面貌',
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 'bold' }
      },
      data: pieData,
    }]
  }
})

// ===== 预警趋势折线图 =====
const crisisTrendOptions = computed(() => {
  const data = classStats.value.crisis_trend
  if (!data || data.length === 0) return null
  
  return {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>预警数量: {c}'
    },
    grid: {
      left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.map(d => d.month),
      axisLabel: { color: '#666', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#666' }
    },
    series: [{
      name: '预警数量',
      type: 'line',
      data: data.map(d => d.count),
      smooth: true,
      lineStyle: { color: '#f56c6c', width: 2 },
      itemStyle: { color: '#f56c6c' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(245,108,108,0.3)' },
            { offset: 1, color: 'rgba(245,108,108,0.05)' }
          ]
        }
      }
    }]
  }
})

// ===== 生源地柱状图 =====
const hometownBarOptions = computed(() => {
  const data = classStats.value.hometown_stats
  if (!data || Object.keys(data).length === 0) return null
  
  const categories = Object.keys(data)
  const values = Object.values(data)
  
  const total = values.reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%', right: '4%', bottom: '10%', top: '8%', containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#666', fontSize: 11, rotate: categories.length > 5 ? 30 : 0 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#666' }
    },
    series: [{
      name: '人数',
      type: 'bar',
      data: values,
      itemStyle: {
        color: '#5b8def',
        borderRadius: [3, 3, 0, 0]
      }
    }]
  }
})

function navigateTo(path: string) {
  router.push(path)
}

function goAgent() {
  router.push('/teacher/agent')
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
const schedules = ref<{ id: number; date: string; content: string }[]>([])
const scheduleDialogVisible = ref(false)
const scheduleContent = ref('')
const scheduleFormRef = ref<any>()
const scheduleRules = {
  content: [{ required: true, message: '请输入日程内容', trigger: 'blur' }],
}
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

  const leaveMap = new Map<string, LeaveRequestOut[]>()
  pendingLeaves.value.forEach(l => {
    const d = l.start_date
    if (!leaveMap.has(d)) leaveMap.set(d, [])
    leaveMap.get(d)!.push(l)
  })

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
  if (scheduleFormRef.value) {
    try { await scheduleFormRef.value.validate() } catch { return }
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
  if (announcementFormRef.value) {
    try { await announcementFormRef.value.validate() } catch { return }
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
  try {
    classStats.value = await getClassStats()
  } catch { /* ignore */ }
  try {
    campusAnnouncements.value = await getAnnouncements()
  } catch { /* ignore */ }
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let lastRefreshAt = 0

onMounted(() => {
  loadData()
  loadMyAnnouncements()
  loadSchedules()
  pollTimer = setInterval(() => {
    loadData()
    loadSchedules()
    loadMyAnnouncements()
  }, 30000)
  lastRefreshAt = Date.now()
})

onActivated(() => {
  // 距上次刷新超过 60 秒才触发轻量刷新
  if (Date.now() - lastRefreshAt >= 60_000) {
    loadData()
    loadSchedules()
    loadMyAnnouncements()
    lastRefreshAt = Date.now()
  }
  // 恢复轮询（若被 onDeactivated 暂停）
  if (pollTimer === null) {
    pollTimer = setInterval(() => {
      loadData()
      loadSchedules()
      loadMyAnnouncements()
    }, 30000)
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

<style scoped>
/* ===== Global ===== */
.home-dashboard {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px;
}

/* ===== Welcome Banner ===== */
.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
  border-radius: 10px;
  margin-bottom: 14px;
  border: 1px solid rgba(91, 141, 239, 0.1);
}

.welcome-content {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.welcome-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.today-text {
  font-size: 12px;
  color: #888;
}

.welcome-tags {
  display: flex;
  gap: 6px;
}

/* ===== KPI Cards ===== */
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.kpi-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--kpi-color) 12%, white);
  color: var(--kpi-color);
  flex-shrink: 0;
}

.kpi-info {
  flex: 1;
}

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.kpi-label {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}

.kpi-trend {
  font-size: 12px;
  font-weight: 600;
}

.trend-up { color: #67c23a; }
.trend-down { color: #f56c6c; }

/* ===== Analytics Row ===== */
.analytics-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.analytics-left, .analytics-right {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.analytics-left {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.chart-half {
  min-width: 0;
}

.chart-full {
  width: 100%;
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
  transition: opacity 0.2s;
}

.section-title:hover {
  opacity: 0.7;
}

.section-link {
  margin-left: auto;
  font-size: 11px;
}

.chart-container {
  width: 100%;
  height: 160px;
}

.chart-divider {
  height: 1px;
  background: #f0f0f0;
  margin: 6px 0;
}

/* ===== AI Analysis ===== */
.ai-analysis-section {
  margin-top: 6px;
  padding-top: 6px;
}

.analysis-placeholder {
  text-align: center;
  padding: 12px 8px;
  color: #888;
}

.analysis-placeholder p {
  margin: 0 0 8px 0;
  font-size: 12px;
}

.analysis-loading {
  text-align: center;
  padding: 12px 8px;
}

.loading-icon {
  font-size: 20px;
  color: #5b8def;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.analysis-content {
  font-size: 12px;
  line-height: 1.5;
  color: #555;
}

.analysis-text {
  white-space: pre-wrap;
  margin-bottom: 10px;
  max-height: 160px;
  overflow-y: auto;
}

/* ===== Schedule Row ===== */
.schedule-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.schedule-section, .announcements-section {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

/* ===== Calendar ===== */
.calendar-wrapper {
  margin-bottom: 10px;
}

.cal-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 10px;
}

.cal-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  min-width: 80px;
  text-align: center;
}

.cal-table {
  width: 100%;
  border-collapse: collapse;
}

.cal-table th {
  font-size: 11px;
  color: #999;
  font-weight: 500;
  padding: 4px 0;
  text-align: center;
}

.cal-table td {
  text-align: center;
  padding: 3px 0;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
  height: 32px;
}

.cal-table td:hover {
  background: rgba(91,141,239,0.06);
}

.cal-other { opacity: 0.25; pointer-events: none; }
.cal-past { opacity: 0.4; cursor: default; }
.cal-past:hover { background: transparent !important; }
.cal-past .cal-day-num { color: #ccc; }

.cal-today .cal-day-num {
  background: #5b8def;
  color: #fff;
  display: inline-block;
  width: 22px;
  height: 22px;
  line-height: 22px;
  border-radius: 50%;
  font-weight: 600;
}

.cal-day-num { font-size: 12px; font-weight: 500; }

.cal-dots {
  display: flex;
  justify-content: center;
  gap: 2px;
  min-height: 5px;
  margin-top: 1px;
}

.dot-leave {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #f56c6c;
  display: inline-block;
}

.dot-schedule {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #67c23a;
  display: inline-block;
}

.cal-legend {
  font-size: 10px;
  color: #999;
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.cal-legend span {
  display: flex;
  align-items: center;
  gap: 3px;
}

/* ===== Upcoming Section ===== */
.upcoming-section {
  border-top: 1px solid #f0f0f0;
  padding-top: 10px;
}

.reminder-title {
  font-size: 12px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}

.reminder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.reminder-date {
  font-size: 11px;
  font-weight: 600;
  color: #5b8def;
  background: #f0f7ff;
  padding: 1px 6px;
  border-radius: 6px;
  flex-shrink: 0;
}

.reminder-content {
  flex: 1;
  font-size: 12px;
  color: #555;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== Announcements ===== */
.announcement-tabs {
  height: 100%;
}

.tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}

.announcement-list {
  min-height: 140px;
}

.announcement-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-content {
  flex: 1;
  min-width: 0;
}

.announcement-title {
  font-size: 13px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.announcement-date {
  font-size: 11px;
  color: #999;
  margin-top: 1px;
}

.attach-link {
  text-decoration: none;
  font-size: 13px;
}

.campus-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
  text-decoration: none;
  transition: background 0.2s;
}

.campus-item:last-child {
  border-bottom: none;
}

.campus-item:hover {
  background: #f8f9ff;
}

.campus-title {
  font-size: 13px;
  color: #333;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 10px;
}

.campus-date {
  font-size: 11px;
  color: #999;
  flex-shrink: 0;
}

.view-all-btn {
  margin-top: 6px;
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
  transition: all 0.2s;
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

/* ===== AI Floating Button ===== */
.ai-float {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.ai-float:hover { transform: scale(1.1); }

.ai-mascot {
  width: 48px;
  height: 48px;
  object-fit: contain;
  animation: mascot-float 2s ease-in-out infinite;
}

@keyframes mascot-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.ai-label {
  margin-top: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #5b8def;
  background: rgba(255,255,255,0.9);
  padding: 1px 8px;
  border-radius: 8px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.08);
}

/* ===== Responsive ===== */
@media (max-width: 1200px) {
  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 1024px) {
  .analytics-row {
    grid-template-columns: 1fr;
  }
  
  .schedule-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .kpi-cards {
    grid-template-columns: 1fr;
  }
  
  .welcome-banner {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .welcome-content {
    flex-direction: column;
    gap: 3px;
  }
}
</style>
