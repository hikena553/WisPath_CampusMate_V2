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
        <el-tab-pane label="班级公告" name="class">
          <div class="tab-header">
            <el-button type="primary" size="small" @click="emit('create')">发布公告</el-button>
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
import { ref, computed } from 'vue'
import { Calendar, DArrowRight } from '@element-plus/icons-vue'
import type { ScheduleItem } from '@/api/teacher'
import type { AnnouncementItem } from '@/api/announcement'
import type { LeaveRequestOut } from '@/types'

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

const activeAnnouncementTab = ref('class')

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
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.schedule-section, .announcements-section {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  box-shadow: none;
  padding: 16px;
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
  border-bottom: 1px solid var(--tui-border);
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