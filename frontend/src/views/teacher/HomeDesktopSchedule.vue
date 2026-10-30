<template>
  <div class="schedule-row">
    <!-- 左侧：日历 + 提醒 -->
    <div class="schedule-section">
      <div class="section-title">
        <el-icon><Calendar /></el-icon>
        <span>日程安排</span>
      </div>
      <div class="calendar-wrapper">
        <div class="cal-nav">
          <el-button text size="small" @click="emit('prev-month')">&lt;</el-button>
          <span class="cal-title">{{ calYear }}年{{ calMonth }}月</span>
          <el-button text size="small" @click="emit('next-month')">&gt;</el-button>
          <el-button text size="small" @click="emit('today-month')" style="margin-left:4px">今天</el-button>
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
                @click="emit('select-day', day)"
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
    </div>

    <!-- 右侧：公告（Tab切换） -->
    <div class="announcements-section">
      <el-tabs v-model="activeAnnouncementTab" class="announcement-tabs">
        <el-tab-pane label="校园公告" name="campus">
          <div class="announcement-list">
            <div v-if="campusLoading && campusAnnouncements.length === 0" class="empty-tip-small">加载中…</div>
            <div v-else-if="campusAnnouncements.length === 0" class="empty-tip-small">暂无校园公告</div>
            <a
              v-for="(n, idx) in campusAnnouncements"
              :key="idx"
              :href="n.url || '#'"
              target="_blank"
              rel="noopener"
              class="announcement-item campus-item"
            >
              <div class="announcement-content">
                <div class="announcement-title">{{ n.title }}</div>
                <div class="announcement-date">{{ n.date || '—' }}</div>
              </div>
              <el-icon class="campus-link-icon"><TopRight /></el-icon>
            </a>
          </div>
        </el-tab-pane>
        <el-tab-pane label="班级公告" name="class">
          <div class="tab-header">
            <el-button size="small" @click="emit('create')">发布公告</el-button>
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
              <el-button text type="danger" size="small" @click="emit('delete', a.id)">删除</el-button>
            </div>
          </div>
          <el-button v-if="myAnnouncements.length > 5" text type="primary" size="small" class="view-all-btn">
            查看全部 <el-icon><DArrowRight /></el-icon>
          </el-button>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Calendar, DArrowRight, TopRight } from '@element-plus/icons-vue'
import { getAnnouncements } from '@/api/campus'
import type { ScheduleItem } from '@/api/teacher'
import type { AnnouncementItem } from '@/api/announcement'
import type { Announcement, LeaveRequestOut } from '@/types'

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

const props = defineProps<{
  calYear: number
  calMonth: number
  schedules: ScheduleItem[]
  pendingLeaves: LeaveRequestOut[]
  myAnnouncements: AnnouncementItem[]
}>()

const emit = defineEmits<{
  'select-day': [day: CalDay]
  'prev-month': []
  'next-month': []
  'today-month': []
  'create': []
  'delete': [id: number]
}>()

const now = new Date()

const calWeeks = computed(() => {
  const y = props.calYear
  const m = props.calMonth
  const first = new Date(y, m - 1, 1).getDay()
  const daysInMonth = new Date(y, m, 0).getDate()
  const daysInPrev = new Date(y, m - 1, 0).getDate()
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

  const leaveMap = new Map<string, LeaveRequestOut[]>()
  props.pendingLeaves.forEach(l => {
    const d = l.start_date
    if (!leaveMap.has(d)) leaveMap.set(d, [])
    leaveMap.get(d)!.push(l)
  })

  const scheduleMap = new Map<string, boolean>()
  props.schedules.forEach(s => { scheduleMap.set(s.date, true) })

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

const activeAnnouncementTab = ref('campus')

// ── 校园公告：教务处通知公告（后端爬取 + 5 分钟缓存，前端定时拉取做动态更新）──
const CAMPUS_REFRESH_MS = 5 * 60 * 1000

const campusAnnouncements = ref<Announcement[]>([])
const campusLoading = ref(false)
let campusTimer: ReturnType<typeof setInterval> | null = null

async function loadCampusAnnouncements() {
  campusLoading.value = true
  try {
    const list = await getAnnouncements()
    // 按时间降序，无日期的排在末尾；列表区固定高度，靠内滚动查看其余条目
    campusAnnouncements.value = [...list].sort((a, b) => (b.date || '').localeCompare(a.date || ''))
  } catch {
    // 抓取失败时保留上一次结果，不打断首页其它卡片
  } finally {
    campusLoading.value = false
  }
}

onMounted(() => {
  loadCampusAnnouncements()
  campusTimer = setInterval(loadCampusAnnouncements, CAMPUS_REFRESH_MS)
})

onUnmounted(() => {
  if (campusTimer) clearInterval(campusTimer)
  campusTimer = null
})

const urgencyMap: Record<string, { type: string; label: string }> = {
  normal: { type: '', label: '普通' },
  important: { type: 'warning', label: '重要' },
  urgent: { type: 'danger', label: '紧急' },
}

function urgencyTagType(u: string) { return urgencyMap[u]?.type || '' }
function urgencyLabel(u: string) { return urgencyMap[u]?.label || u }

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
/* 卡头：与首页其它卡片同一套语言（22px 图标块 + 14px/600 标题） */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #2b3245;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title .el-icon {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: color-mix(in srgb, #2563eb 12%, #fff);
  color: #2563eb;
  font-size: 13px;
  flex-shrink: 0;
}
.schedule-row {
  display: grid;
  /* minmax(0,1fr)：栅格轨道不取子项的最小内容宽度，长标题不会把某一列撑宽压到邻列 */
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}
.schedule-section, .announcements-section {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  box-shadow: none;
  padding: 16px;
}
/* 公告卡片高度由左侧日历（同行更高的卡片）撑定，卡片本身不随条目多少增高，
   内部列表区固定分配剩余高度并自行滚动 —— 切 Tab / 条目刷新都不改变卡片大小。 */
.announcements-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
  /* 网格子项默认 min-width:auto：长公告标题（nowrap）的最小内容宽度会把本列撑宽、
     越过栅格压到右侧卡片上（表现为 UI 交叉 + 切 Tab 变宽）。置 0 后宽度只由栅格决定。 */
  min-width: 0;
}
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
  color: var(--tui-text-quiet);
  font-weight: 500;
  padding: 4px 0;
  text-align: center;
}
.cal-table td {
  text-align: center;
  padding: 3px 0;
  cursor: pointer;
  border-radius: 6px;
  height: 32px;
}
.cal-table td:hover {
  background: var(--tui-surface-muted);
}
.cal-other { opacity: 0.25; pointer-events: none; }
.cal-past { opacity: 0.4; cursor: default; }
.cal-past:hover { background: transparent !important; }
.cal-past .cal-day-num { color: var(--tui-text-quiet); }
.cal-today .cal-day-num {
  background: var(--tui-brand);
  color: #fff;
  display: inline-block;
  width: 22px;
  height: 22px;
  line-height: 22px;
  border-radius: 50%;
  font-weight: 600;
}
.cal-day-num {
  font-size: 12px;
  font-weight: 500;
  color: var(--tui-text-secondary);
  font-variant-numeric: tabular-nums;
}
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
  background: #d92d20;
  display: inline-block;
}
.dot-schedule {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #12b76a;
  display: inline-block;
}
.cal-legend {
  font-size: 11px;
  color: var(--tui-text-quiet);
  display: flex;
  gap: 10px;
  margin-top: 8px;
}
.cal-legend span {
  display: flex;
  align-items: center;
  gap: 3px;
}
.announcement-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  /* 沿 flex 链一路放开最小宽度，避免长标题把卡片撑宽 */
  min-width: 0;
}
.announcement-tabs :deep(.el-tabs__content) {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}
.announcement-tabs :deep(.el-tab-pane) {
  display: flex;
  flex-direction: column;
  flex: 1;
  /* 内容区高度下限（两个 Tab 一致）：卡片尺寸不随切换 Tab、条目多少而变化 */
  min-height: 200px;
  min-width: 0;
}
.tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}
.announcement-list {
  /* height:0 + flex-grow：列表自身不给卡片贡献高度（卡片高度仍由同行日历撑定），
     只在内容区剩余空间里伸展；超出部分在卡片内滚动。 */
  flex: 1 1 auto;
  height: 0;
  min-height: 0;
  min-width: 0;
  /* 只纵向滚动：overflow-y 非 visible 会把 overflow-x 也算成 auto，
     必须显式 hidden，否则长标题会横向滚出卡片、压到右侧卡片上 */
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  /* 隐藏侧边滚动条（仍可滚动/触控滑动） */
  scrollbar-width: none;
}
.announcement-list::-webkit-scrollbar {
  display: none;
}
.announcement-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--tui-border);
}
.announcement-item:last-child {
  border-bottom: none;
}
.campus-item {
  text-decoration: none;
  color: inherit;
}
.campus-item:hover .announcement-title {
  color: var(--tui-brand);
}
.campus-link-icon {
  font-size: 12px;
  color: var(--tui-text-quiet);
  flex-shrink: 0;
}
.announcement-content {
  flex: 1;
  min-width: 0;
}
.announcement-title {
  font-size: 13px;
  color: var(--tui-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.announcement-date {
  font-size: 11px;
  color: var(--tui-text-quiet);
  margin-top: 1px;
  font-variant-numeric: tabular-nums;
}
.attach-link {
  text-decoration: none;
  font-size: 13px;
}
.view-all-btn {
  margin-top: 6px;
}
.empty-tip-small {
  text-align: center;
  color: var(--tui-text-quiet);
  padding: 14px 0;
  font-size: 12px;
}
@media (max-width: 1024px) {
  .schedule-row {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 767px) {
  .schedule-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}
</style>