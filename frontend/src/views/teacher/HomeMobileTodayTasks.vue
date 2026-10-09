<template>
  <div class="sub-page task-page">
    <!-- 校园背景头部 -->
    <div class="task-hero">
      <img src="/images/campus/游仙校区博识楼.jpg" class="task-hero-bg" />
      <div class="task-hero-overlay"></div>
      <div class="task-hero-top">
        <button class="task-hero-back" @click="emit('close')">
          <el-icon><ArrowLeft /></el-icon>
        </button>
      </div>
      <!-- 日期居中 -->
      <div class="task-hero-center" @click="showDatePopup = true">
        <div class="task-hero-date">{{ taskDateDisplay.month }}月{{ taskDateDisplay.day }}日</div>
        <div class="task-hero-week">
          星期{{ taskDateDisplay.week }}
          <span v-if="taskDateDisplay.isToday" class="task-hero-today">今天</span>
        </div>
        <div class="task-hero-hint">点击查看日历</div>
      </div>
      <!-- 统计 -->
      <div class="task-hero-stats">
        <div class="hero-stat">
          <span class="hero-stat-num">{{ totalTodayCount }}</span>
          <span class="hero-stat-label">总计</span>
        </div>
        <div class="hero-stat-divider"></div>
        <div class="hero-stat">
          <span class="hero-stat-num hero-stat-green">{{ completedTodayCount }}</span>
          <span class="hero-stat-label">已完成</span>
        </div>
        <div class="hero-stat-divider"></div>
        <div class="hero-stat">
          <span class="hero-stat-num hero-stat-amber">{{ pendingTodayCount }}</span>
          <span class="hero-stat-label">待处理</span>
        </div>
      </div>
    </div>

    <!-- 日期弹窗（日历式月视图） -->
    <div v-if="showDatePopup" class="cal-overlay" @click.self="closePopup">
      <div class="cal-popup">
        <!-- 月份导航 -->
        <div class="cal-popup-nav">
          <button class="cal-nav-btn" @click="popupMonth === 1 ? (popupYear--, popupMonth=12) : popupMonth--">
            <el-icon><ArrowLeft /></el-icon>
          </button>
          <span class="cal-nav-title">{{ popupYear }}年{{ popupMonth }}月</span>
          <button class="cal-nav-btn" @click="popupMonth === 12 ? (popupYear++, popupMonth=1) : popupMonth++">
            <el-icon><DArrowRight /></el-icon>
          </button>
        </div>
        <!-- 星期头 -->
        <div class="cal-week-header">
          <span v-for="d in ['日','一','二','三','四','五','六']" :key="d" :class="{ 'cal-weekend': d === '日' || d === '六' }">{{ d }}</span>
        </div>
        <!-- 日期网格 -->
        <div class="cal-grid">
          <div
            v-for="(day, i) in popupDays"
            :key="i"
            class="cal-cell"
            :class="{
              'cal-other': day.other,
              'cal-today': day.isToday,
              'cal-selected': day.date === props.selectedDate
            }"
            @click="selectPopupDate(day)"
          >
            <span class="cal-num">{{ day.num }}</span>
            <span v-if="day.hasTask" class="cal-task-dot"></span>
          </div>
        </div>
        <!-- 选中日期的任务 -->
        <div class="cal-day-plan">
          <div class="cal-day-header">
            <span class="cal-day-title">{{ popupSelectedDisplay }}</span>
            <span v-if="popupTasks.length > 0" class="cal-day-count">{{ popupTasks.length }}项</span>
          </div>
          <div v-if="popupTasks.length > 0" class="cal-day-list">
            <div v-for="t in popupTasks" :key="t.id" class="cal-day-item">
              <span class="cal-day-dot" :style="{ background: t.color }"></span>
              <span class="cal-day-text">{{ t.text }}</span>
            </div>
          </div>
          <!-- 添加任务 -->
          <div v-if="!popupAdding" class="cal-add-btn" @click="popupAdding = true">
            <el-icon><Plus /></el-icon>
            <span>添加任务</span>
          </div>
          <div v-else class="cal-add-form">
            <input
              ref="popupInputRef"
              v-model="popupTaskContent"
              class="cal-form-input"
              placeholder="输入任务内容..."
              @keyup.enter="addTaskFromPopup"
              @keyup.escape="popupAdding = false"
            />
            <div class="cal-form-urgency">
              <button
                v-for="u in props.urgencyOptions" :key="u.value"
                class="cal-urgency-opt"
                :class="{ active: popupTaskUrgency === u.value, [u.value]: true }"
                @click="popupTaskUrgency = u.value"
              >{{ u.label }}</button>
            </div>
            <div class="cal-form-actions">
              <button class="cal-form-cancel" @click="popupAdding = false">取消</button>
              <button class="cal-form-submit" @click="addTaskFromPopup" :disabled="!popupTaskContent.trim()">添加</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速添加：加号悬浮按钮 -->
    <div class="task-quick-add-fab">
      <button class="quick-add-fab" @click="emit('open-quick-add')">
        <el-icon :size="22"><Plus /></el-icon>
      </button>
    </div>

    <!-- 任务列表 -->
    <div class="task-body">
      <!-- 待批请假（审批是其唯一完成路径，不提供本地勾选） -->
      <div v-if="props.todayLeaves.length > 0" class="task-section">
        <div class="task-section-head">
          <span class="task-section-dot" style="background:#f59e0b"></span>
          <span class="task-section-title">待批请假</span>
          <span class="task-section-badge">{{ props.todayLeaves.length }}</span>
        </div>
        <div
          v-for="l in props.todayLeaves"
          :key="'tl-'+l.id"
          class="task-card leave-card"
        >
          <div class="task-card-body">
            <div class="task-card-title">{{ l.student_name }} · {{ typeLabel(l.leave_type) }}</div>
            <div class="task-card-sub">{{ l.start_date }} ~ {{ l.end_date }}</div>
          </div>
          <button class="task-card-btn" @click="emit('navigate', '/teacher/approval')">审批</button>
        </div>
      </div>

      <!-- 逾期未完成（累积全部，不限日期） -->
      <div v-if="props.overdueSchedules.length > 0" class="task-section">
        <div class="task-section-head">
          <span class="task-section-dot" style="background:#ef4444"></span>
          <span class="task-section-title">逾期未完成</span>
          <span class="task-section-badge orange">{{ props.overdueSchedules.length }}</span>
        </div>
        <div
          v-for="s in props.overdueSchedules"
          :key="'od-'+s.id"
          class="task-card schedule-card"
          :class="['task-pending', { 'task-urgent': s.urgency === 'urgent' }]"
        >
          <div class="task-card-check" @click="emit('toggle-complete', s)">
            <div class="tc-check">
              <el-icon v-if="s.completed"><Check /></el-icon>
            </div>
          </div>
          <div class="task-card-body">
            <div class="task-card-title">{{ s.content }}</div>
            <div class="task-card-tags">
              <span class="ur-badge ur-overdue">逾期 {{ s.date }}</span>
              <span v-if="s.urgency === 'urgent'" class="ur-badge ur-urgent">紧急</span>
              <span v-else-if="s.urgency === 'important'" class="ur-badge ur-important">重要</span>
            </div>
          </div>
          <button class="task-card-del" @click="emit('delete-schedule', s.id)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
      </div>

      <!-- 日程安排（当前所选日期） -->
      <div v-if="props.todaySchedules.length > 0" class="task-section">
        <div class="task-section-head">
          <span class="task-section-dot" style="background:#3b82f6"></span>
          <span class="task-section-title">日程安排</span>
          <span class="task-section-badge">{{ props.todaySchedules.length }}</span>
        </div>
        <div
          v-for="s in props.todaySchedules"
          :key="'ts-'+s.id"
          class="task-card schedule-card"
          :class="[
            s.completed ? 'task-completed' : 'task-pending',
            { 'task-urgent': !s.completed && s.urgency === 'urgent' }
          ]"
        >
          <div class="task-card-check" @click="emit('toggle-complete', s)">
            <div class="tc-check" :class="{ checked: s.completed }">
              <el-icon v-if="s.completed"><Check /></el-icon>
            </div>
          </div>
          <div class="task-card-body">
            <div class="task-card-title">{{ s.content }}</div>
            <div class="task-card-tags">
              <span v-if="!s.completed && s.urgency === 'urgent'" class="ur-badge ur-urgent">紧急</span>
              <span v-else-if="!s.completed && s.urgency === 'important'" class="ur-badge ur-important">重要</span>
              <span v-if="!s.completed && isOverdueSchedule(s)" class="ur-badge ur-overdue">已逾期</span>
            </div>
          </div>
          <button class="task-card-del" @click="emit('delete-schedule', s.id)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="props.todayLeaves.length === 0 && props.todaySchedules.length === 0 && props.overdueSchedules.length === 0" class="task-empty">
        <img :src="siteMascot" class="task-empty-mascot" />
        <div class="task-empty-text">暂无任务安排</div>
        <div class="task-empty-sub">在上方输入框添加新任务</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowLeft, DArrowRight, Plus, Check, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { createTeacherSchedule } from '@/api/teacher'
import type { ScheduleItem, ScheduleUrgency } from '@/api/teacher'
import type { LeaveRequestOut } from '@/types'
import { useSiteConfig } from '@/composables/useSiteConfig'

// 吉祥物取自站点配置：管理端变更后教师端同步
const { siteMascot } = useSiteConfig()

const props = defineProps<{
  selectedDate: string
  todayLeaves: LeaveRequestOut[]
  todaySchedules: ScheduleItem[]
  overdueSchedules: ScheduleItem[]
  schedules: ScheduleItem[]
  pendingLeaves: LeaveRequestOut[]
  urgencyOptions: { value: ScheduleUrgency; label: string }[]
}>()

const emit = defineEmits<{
  close: []
  'select-date': [date: string]
  'open-quick-add': []
  'toggle-complete': [s: ScheduleItem]
  'delete-schedule': [id: number]
  navigate: [path: string]
  'task-added': []
}>()

// 任务统计：完成口径只计入日程（请假以审批为完成路径）
const totalTodayCount = computed(() => props.todayLeaves.length + props.todaySchedules.length)
const completedTodayCount = computed(() => props.todaySchedules.filter(s => s.completed).length)
const pendingTodayCount = computed(() => Math.max(totalTodayCount.value - completedTodayCount.value, 0))

function isOverdueSchedule(s: ScheduleItem) {
  const today = new Date().toISOString().slice(0, 10)
  return !s.completed && s.date < today
}

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

// 格式化日期显示
const taskDateDisplay = computed(() => {
  const d = new Date(props.selectedDate)
  const week = ['日', '一', '二', '三', '四', '五', '六']
  const month = d.getMonth() + 1
  const day = d.getDate()
  const today = new Date().toISOString().slice(0, 10)
  const isToday = props.selectedDate === today
  return { month, day, week: week[d.getDay()], isToday }
})

// 弹窗日历逻辑
const showDatePopup = ref(false)
const popupTaskContent = ref('')
const popupTaskUrgency = ref<ScheduleUrgency>('normal')
const popupAdding = ref(false)
const popupInputRef = ref<HTMLInputElement | null>(null)
const popupYear = ref(new Date().getFullYear())
const popupMonth = ref(new Date().getMonth() + 1)

const popupDays = computed(() => {
  const y = popupYear.value
  const m = popupMonth.value
  const first = new Date(y, m - 1, 1).getDay()
  const daysInMonth = new Date(y, m, 0).getDate()
  const daysInPrev = new Date(y, m - 1, 0).getDate()
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  // 有任务的日期集合
  const taskDates = new Set<string>()
  props.pendingLeaves.forEach(l => {
    if (l.start_date <= `${y}-${String(m).padStart(2,'0')}-31` && l.end_date >= `${y}-${String(m).padStart(2,'0')}-01`) {
      taskDates.add(l.start_date)
    }
  })
  props.schedules.forEach(s => taskDates.add(s.date))

  const days: { num: number; date: string; other: boolean; isToday: boolean; hasTask: boolean }[] = []
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
    days.push({
      num,
      date: dateStr,
      other: monthOffset !== 0,
      isToday: dateStr === todayStr,
      hasTask: taskDates.has(dateStr)
    })
  }
  return days
})

// 弹窗选中日期的任务
const popupSelectedDisplay = computed(() => {
  const d = new Date(props.selectedDate)
  return `${d.getMonth() + 1}月${d.getDate()}日 计划`
})

const popupTasks = computed(() => {
  const date = props.selectedDate
  const tasks: { id: string; text: string; color: string }[] = []
  props.pendingLeaves.forEach(l => {
    if (l.start_date <= date && l.end_date >= date) {
      tasks.push({ id: 'l-' + l.id, text: `${l.student_name} · ${typeLabel(l.leave_type)}`, color: '#f59e0b' })
    }
  })
  props.schedules.forEach(s => {
    if (s.date === date) {
      const color = s.completed ? '#10b981' : s.urgency === 'urgent' ? '#ef4444' : '#3b82f6'
      tasks.push({ id: 's-' + s.id, text: s.content, color })
    }
  })
  return tasks
})

function selectPopupDate(day: { date: string; other: boolean }) {
  // 跨月选择时同步弹窗翻月
  if (day.other) {
    const d = new Date(day.date)
    popupYear.value = d.getFullYear()
    popupMonth.value = d.getMonth() + 1
  }
  // 父级同步共享选中日期并重载对应月份数据
  emit('select-date', day.date)
}

// 关闭弹窗：保留用户选择的日期（不重置为今天），否则历史/逾期任务永远无法在列表中查看勾选
function closePopup() {
  showDatePopup.value = false
}

// 弹窗内添加任务
async function addTaskFromPopup() {
  if (!popupTaskContent.value.trim()) return
  try {
    await createTeacherSchedule(props.selectedDate, popupTaskContent.value.trim(), popupTaskUrgency.value)
    ElMessage.success('任务已添加')
    popupTaskContent.value = ''
    popupTaskUrgency.value = 'normal'
    popupAdding.value = false
    emit('task-added')
  } catch {
    ElMessage.error('添加失败')
  }
}
</script>

<style scoped>
  /* ---- 任务管理子页面（飞书风格） ---- */
  .task-page {
    padding: 0 !important;
    background: #f5f6f8;
  }
  .task-page .sub-page-body {
    padding: 0;
  }

  /* 校园背景头部 */
  .task-hero {
    position: relative;
    height: 180px;
    flex-shrink: 0;
    overflow: hidden;
  }
  .task-hero-bg {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .task-hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.55) 100%);
  }
  .task-hero-top {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
  }
  .task-hero-back {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: none;
    background: rgba(255,255,255,0.2);
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    backdrop-filter: blur(4px);
  }
  .task-hero-title {
    font-size: 15px;
    font-weight: 600;
    color: #fff;
  }
  .task-hero-center {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -60%);
    text-align: center;
    cursor: pointer;
  }
  .task-hero-date {
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    line-height: 1.2;
    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }
  .task-hero-week {
    font-size: 13px;
    color: rgba(255,255,255,0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    margin-top: 4px;
  }
  .task-hero-today {
    background: rgba(255,255,255,0.25);
    padding: 1px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
  }
  .task-hero-hint {
    font-size: 11px;
    color: rgba(255,255,255,0.6);
    margin-top: 6px;
  }

  /* 统计条 */
  .task-hero-stats {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px 16px;
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(8px);
  }
  .hero-stat {
    flex: 1;
    text-align: center;
  }
  .hero-stat-num {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    display: block;
    line-height: 1;
  }
  .hero-stat-green { color: #86efac; }
  .hero-stat-amber { color: #fcd34d; }
  .hero-stat-label {
    font-size: 10px;
    color: rgba(255,255,255,0.75);
    margin-top: 3px;
    display: block;
  }
  .hero-stat-divider {
    width: 1px;
    height: 20px;
    background: rgba(255,255,255,0.2);
  }

  /* 日期弹窗（日历式） */
  .cal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
  }
  .cal-popup {
    padding: 12px;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    width: 280px;
    animation: cal-pop-in 0.2s ease;
  }
  @keyframes cal-pop-in {
    from { transform: scale(0.95); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
}
  .cal-popup-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 8px;
  }
  .cal-nav-btn {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    border: none;
    background: #f3f4f6;
    color: #374151;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
  }
  .cal-nav-btn:active {
    background: #e5e7eb;
    transform: scale(0.95);
  }
  .cal-nav-title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    min-width: 90px;
    text-align: center;
  }
  .cal-week-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    text-align: center;
    margin-bottom: 2px;
  }
  .cal-week-header span {
    font-size: 10px;
    color: #9ca3af;
    font-weight: 500;
    padding: 2px 0;
  }
  .cal-weekend {
    color: #ef4444 !important;
  }
  .cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 1px;
  }
  .cal-cell {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 30px;
    border-radius: 6px;
    cursor: pointer;
  }
  .cal-cell:active {
    transform: scale(0.92);
  }
  .cal-num {
    font-size: 12px;
    color: #374151;
    line-height: 1;
    font-weight: 500;
  }
  .cal-other .cal-num {
    color: #d1d5db;
    font-weight: 400;
  }
  .cal-today {
    background: #eff6ff;
  }
  .cal-today .cal-num {
    color: #3b82f6;
    font-weight: 700;
  }
  .cal-selected {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3);
  }
  .cal-selected .cal-num {
    color: #fff !important;
    font-weight: 700;
  }
  .cal-task-dot {
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: #f59e0b;
    margin-top: 1px;
  }
  .cal-selected .cal-task-dot {
    background: rgba(255,255,255,0.8);
  }

  .cal-day-plan {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #f3f4f6;
  }
  .cal-day-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .cal-day-title {
    font-size: 12px;
    font-weight: 600;
    color: #1f2937;
  }
  .cal-day-count {
    font-size: 10px;
    color: #9ca3af;
    background: #f3f4f6;
    padding: 1px 6px;
    border-radius: 8px;
  }
  .cal-day-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
    max-height: 80px;
    overflow-y: auto;
  }
  .cal-day-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #374151;
    padding: 4px 6px;
    background: #f9fafb;
    border-radius: 6px;
  }
  .cal-day-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .cal-day-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* 添加任务按钮 */
  .cal-add-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    margin-top: 8px;
    padding: 6px;
    border-radius: 6px;
    border: 1px dashed #d1d5db;
    cursor: pointer;
    font-size: 11px;
    color: #6b7280;
  }
  .cal-add-btn:active {
    border-color: #3b82f6;
    color: #3b82f6;
    background: #eff6ff;
  }

  /* 添加任务表单 */
  .cal-add-form {
    margin-top: 8px;
  }
  .cal-form-input {
    width: 100%;
    height: 30px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 0 8px;
    font-size: 12px;
    outline: none;
    box-sizing: border-box;
  }
  .cal-form-input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.1);
  }
  .cal-form-input::placeholder {
    color: #c0c4cc;
  }
  .cal-form-urgency {
    display: flex;
    gap: 6px;
    margin-top: 6px;
  }
  .cal-urgency-opt {
    flex: 1;
    height: 24px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: #fff;
    color: #6b7280;
    font-size: 10px;
    cursor: pointer;
  }
  .cal-urgency-opt.active {
    border-color: #3b82f6;
    background: #eff6ff;
    color: #2563eb;
  }
  .cal-urgency-opt.active.important {
    border-color: #f59e0b;
    background: #fffbeb;
    color: #b45309;
  }
  .cal-urgency-opt.active.urgent {
    border-color: #ef4444;
    background: #fef2f2;
    color: #dc2626;
  }
  .cal-form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
    margin-top: 6px;
  }
  .cal-form-cancel {
    height: 26px;
    padding: 0 10px;
    border-radius: 6px;
    border: none;
    background: #f3f4f6;
    color: #374151;
    font-size: 11px;
    cursor: pointer;
  }
  .cal-form-cancel:active {
    background: #e5e7eb;
  }
  .cal-form-submit {
    height: 26px;
    padding: 0 12px;
    border-radius: 6px;
    border: none;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: #fff;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(59,130,246,0.3);
  }
  .cal-form-submit:active {
    transform: scale(0.97);
  }
  .cal-form-submit:disabled {
    background: #e5e7eb;
    color: #9ca3af;
    box-shadow: none;
    cursor: not-allowed;
  }

  /* 快速添加：加号悬浮按钮（固定在底部中央） */
  .task-quick-add-fab {
    position: fixed;
    bottom: 76px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 102;
  }
  .quick-add-fab {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: none;
    background: #fff;
    color: #9ca3af;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,0.14);
  }
  .quick-add-fab:active {
    transform: scale(0.95);
    box-shadow: 0 2px 8px rgba(0,0,0,0.14);
  }

  /* 任务列表区域 */
  .task-body {
    padding: 0 12px 80px;
  }
  .task-section {
    margin-bottom: 14px;
  }
  .task-section-head {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 4px 6px;
  }
  .task-section-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .task-section-title {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
  }
  .task-section-badge {
    margin-left: auto;
    font-size: 10px;
    color: #9ca3af;
    background: #f3f4f6;
    padding: 1px 8px;
    border-radius: 10px;
  }

  /* 任务卡片（飞书风格） */
  .task-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: #fff;
    border-radius: 10px;
    margin-bottom: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  /* 未完成任务：红色系 */
  .task-card.task-pending {
    background: #fff7f7;
    border-left: 3px solid #ef4444;
  }
  /* 已完成任务：绿色系 */
  .task-card.task-completed {
    background: #f0fdf4;
    border-left: 3px solid #10b981;
  }
  .task-card.task-completed .task-card-title {
    text-decoration: line-through;
    color: #6b7280;
  }
  /* 紧急未完成：红色强调置顶标记 */
  .task-card.task-urgent {
    background: #fef2f2;
    border-left: 3px solid #dc2626;
    box-shadow: 0 1px 6px rgba(239, 68, 68, 0.18);
  }
  .task-card-tags {
    display: flex;
    gap: 4px;
    margin-top: 2px;
  }
  .ur-badge {
    font-size: 10px;
    line-height: 1;
    padding: 2px 6px;
    border-radius: 8px;
    font-weight: 500;
  }
  .ur-urgent { background: #dc2626; color: #fff; }
  .ur-important { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
  .ur-overdue { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }
  .leave-card {
    background: #fffbeb !important;
    border-left: 3px solid #f59e0b !important;
  }
  .task-card-check {
    flex-shrink: 0;
    cursor: pointer;
  }
  .tc-check {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 1.5px solid #d1d5db;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
  }
  .tc-check.checked {
    background: #10b981;
    border-color: #10b981;
    color: #fff;
  }
  .tc-check .el-icon {
    font-size: 11px;
  }
  .task-card-body {
    flex: 1;
    min-width: 0;
  }
  .task-card-title {
    font-size: 13px;
    color: #1f2937;
    line-height: 1.4;
  }
  .task-done .task-card-title {
    text-decoration: line-through;
    color: #9ca3af;
  }
  .task-card-sub {
    font-size: 11px;
    color: #9ca3af;
    margin-top: 1px;
  }
  .task-card-btn {
    flex-shrink: 0;
    padding: 4px 10px;
    border-radius: 6px;
    border: none;
    background: #f0f5ff;
    color: #3b82f6;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
  }
  .task-card-del {
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: #d1d5db;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
  }
  .task-card-del:active {
    background: #fef2f2;
    color: #ef4444;
  }

  /* 空状态 */
  .task-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
  }
  .task-empty-mascot {
    width: 72px;
    height: 72px;
    object-fit: contain;
    opacity: 0.5;
    margin-bottom: 12px;
  }
  .task-empty-text {
    font-size: 14px;
    font-weight: 500;
    color: #6b7280;
    margin-bottom: 4px;
  }
  .task-empty-sub {
    font-size: 12px;
    color: #9ca3af;
  }
</style>