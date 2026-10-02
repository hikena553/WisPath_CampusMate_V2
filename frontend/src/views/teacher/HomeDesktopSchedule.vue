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
      <div class="upcoming-section">
        <div class="reminder-title">📌 近期提醒</div>
        <div v-if="upcomingReminders.length === 0" class="empty-tip-small">暂无提醒</div>
        <div v-for="r in upcomingReminders.slice(0, 3)" :key="r.id" class="reminder-item">
          <span class="reminder-date">{{ r.date.slice(5) }}</span>
          <span class="reminder-content">{{ r.content }}</span>
          <el-button text type="danger" size="small" @click="emit('delete-schedule', r.id)">删除</el-button>
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
import type { LeaveRequestOut, Announcement } from '@/types'

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
  campusAnnouncements: Announcement[]
  myAnnouncements: AnnouncementItem[]
  upcomingReminders: ScheduleItem[]
}>()

const emit = defineEmits<{
  'select-day': [day: CalDay]
  'prev-month': []
  'next-month': []
  'today-month': []
  'delete-schedule': [id: number]
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
.empty-tip-small {
  text-align: center;
  color: #bbb;
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