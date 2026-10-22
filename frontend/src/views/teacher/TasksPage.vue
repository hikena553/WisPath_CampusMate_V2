<template>
  <div class="tui-page">
    <SubPageHeader title="任务日程" sub="智能生成 · 按日期推进" fallback="/teacher" />

    <div class="tui-content">
      <!-- 桌面端头部：本页以「日期」为主轴，头部承担身份与刷新入口 -->
      <TuiPageHero
        v-if="!isMobile"
        title="任务日程"
        sub="智能评估自动排期 · 也可手动新增或从聊天一键加入"
        :icon="List"
        tone="brand"
      >
        <el-button text circle aria-label="刷新" @click="refreshAll">
          <el-icon :size="18"><Refresh /></el-icon>
        </el-button>
      </TuiPageHero>

      <!-- 工具条：视图切换（日程 / 清单）+ 智能生成 + 新增 -->
      <div class="tp-toolbar">
        <TuiSegmented v-model="viewMode" :options="viewOptions" />
        <div class="tp-toolbar-actions">
          <el-button size="small" :loading="generating" @click="smartGenerate">
            <el-icon><MagicStick /></el-icon><span>智能生成</span>
          </el-button>
          <el-button size="small" type="primary" @click="openCreate(null)">
            <el-icon><Plus /></el-icon><span>新增任务</span>
          </el-button>
        </div>
      </div>

      <!-- 智能生成结果提示（一次性，不打扰） -->
      <div v-if="genHint" class="tp-genhint tui-notice">
        <el-icon><MagicStick /></el-icon>
        <span>{{ genHint }}</span>
        <button class="tp-genhint-close" type="button" aria-label="关闭" @click="genHint = ''">×</button>
      </div>

      <!-- ===================== 日程视图 ===================== -->
      <template v-if="viewMode === 'schedule'">
        <!-- 桌面端：左月历 + 右选中日任务 -->
        <div v-if="!isMobile" class="tp-sched">
          <section class="tui-section tp-cal-card">
            <div class="tui-section-head">
              <h3><el-icon><Calendar /></el-icon>任务日历</h3>
              <div class="tui-section-extra tp-cal-nav">
                <button class="tp-cal-btn" type="button" @click="shiftMonth(-1)">上月</button>
                <button class="tp-cal-btn is-strong" type="button" @click="gotoToday">今天</button>
                <button class="tp-cal-btn" type="button" @click="shiftMonth(1)">下月</button>
              </div>
            </div>
            <div class="tp-cal-title">{{ cursorTitle }}</div>
            <div class="tp-cal-week">
              <span v-for="w in WEEK_LABELS" :key="w">{{ w }}</span>
            </div>
            <div class="tp-cal-grid">
              <button
                v-for="cell in calendarCells"
                :key="cell.key"
                type="button"
                class="tp-cal-cell"
                :class="{
                  'is-out': !cell.inMonth,
                  'is-today': cell.isToday,
                  'is-active': cell.dateStr === selectedDate,
                }"
                @click="selectDate(cell.dateStr)"
              >
                <span class="tp-cal-day">{{ cell.day }}</span>
                <span v-if="cell.openCount" class="tp-cal-count" :class="`tone-${cell.topTone}`">
                  {{ cell.openCount }}
                </span>
                <span class="tp-cal-dots">
                  <i v-for="(tone, i) in cell.dots" :key="i" :class="`tone-${tone}`"></i>
                </span>
              </button>
            </div>
            <div class="tp-cal-legend">
              <span><i class="tone-high"></i>高优先级</span>
              <span><i class="tone-mid"></i>中优先级</span>
              <span><i class="tone-low"></i>低优先级</span>
            </div>

            <!-- 未排期：既无提醒日也无截止日 -->
            <div class="tp-unscheduled">
              <div class="tp-unscheduled-head">
                <span>未排期任务</span>
                <span class="tp-unscheduled-count">{{ unscheduledTasks.length }}</span>
              </div>
              <div v-if="!unscheduledTasks.length" class="tp-unscheduled-empty">暂无未排期任务</div>
              <div v-else class="tp-unscheduled-list">
                <button
                  v-for="t in unscheduledTasks.slice(0, 5)"
                  :key="t.id"
                  type="button"
                  class="tp-unscheduled-item"
                  @click="openEdit(t)"
                >
                  <span class="tp-unscheduled-title">{{ t.title }}</span>
                  <span class="tp-unscheduled-action">定日期</span>
                </button>
              </div>
            </div>
          </section>

          <section class="tui-section tp-day">
            <div class="tui-section-head">
              <h3><el-icon><List /></el-icon>{{ selectedDateLabel }}</h3>
              <div class="tui-section-extra">
                <span class="tp-day-count">{{ dayTasks.length }} 条</span>
                <el-button size="small" @click="openCreate(selectedDate)">
                  <el-icon><Plus /></el-icon><span>当日新增</span>
                </el-button>
              </div>
            </div>

            <!-- 未来 7 天负荷概览：一眼看出哪天最忙 -->
            <div class="tp-load">
              <button
                v-for="d in weekLoad"
                :key="d.dateStr"
                type="button"
                class="tp-load-item"
                :class="{ 'is-active': d.dateStr === selectedDate, 'is-today': d.isToday }"
                @click="selectDate(d.dateStr)"
              >
                <span class="tp-load-day">{{ d.label }}</span>
                <span class="tp-load-bar">
                  <i :style="{ height: `${Math.min(100, d.openCount * 22 + (d.openCount ? 10 : 0))}%` }"></i>
                </span>
                <span class="tp-load-num">{{ d.openCount }}</span>
              </button>
            </div>

            <div v-if="!dayTasks.length" class="tui-empty tp-day-empty">
              <span class="tui-empty-icon"><el-icon :size="24"><Calendar /></el-icon></span>
              <span class="tui-empty-title">这一天没有任务</span>
              <span class="tui-empty-desc">可以点「当日新增」把任务安排到 {{ selectedDateLabel }}</span>
            </div>
            <div v-else class="tp-day-list">
              <TeacherTaskCard
                v-for="t in dayTasks"
                :key="t.id"
                :task="t"
                @toggle-done="handleToggleDone"
                @update-status="handleUpdateStatus"
                @record-care="openCare"
                @edit="openEdit"
                @delete="handleDelete"
              />
            </div>
          </section>
        </div>

        <!-- 移动端：按日期分组纵向列表 -->
        <template v-else>
          <section v-for="g in mobileDateGroups" :key="g.key" class="tui-section">
            <div class="tui-section-head">
              <h3>
                <el-icon><Calendar /></el-icon>{{ g.label }}
                <span v-if="g.sub" class="tp-group-sub">{{ g.sub }}</span>
              </h3>
              <div class="tui-section-extra"><span class="tp-day-count">{{ g.items.length }} 条</span></div>
            </div>
            <div v-if="!g.items.length" class="tp-group-empty">暂无任务</div>
            <div v-else class="tp-day-list">
              <TeacherTaskCard
                v-for="t in g.items"
                :key="t.id"
                :task="t"
                @toggle-done="handleToggleDone"
                @update-status="handleUpdateStatus"
                @record-care="openCare"
                @edit="openEdit"
                @delete="handleDelete"
              />
            </div>
          </section>
        </template>
      </template>

      <!-- ===================== 清单视图 ===================== -->
      <div v-else class="tp-workbench">
        <aside class="tp-side">
          <div class="tp-side-card">
            <div class="tp-side-block">
              <div class="tp-side-label">分组筛选</div>
              <div class="tp-filters">
                <button
                  v-for="f in filterOptions"
                  :key="f.value"
                  type="button"
                  class="tp-filter"
                  :class="{ 'is-active': activeFilter === f.value }"
                  @click="switchFilter(f.value)"
                >
                  <span class="tp-filter-label">{{ f.label }}</span>
                  <span class="tp-filter-count">{{ f.count }}</span>
                </button>
              </div>
            </div>

            <div class="tp-side-block">
              <div class="tp-side-label">本周完成度</div>
              <div class="tp-rate-row">
                <span class="tui-ring" :style="{ '--pct': doneRate / 100, '--ring-color': ringColor }">
                  <span class="tui-ring-num">{{ doneRate }}%</span>
                </span>
                <div class="tui-progress">
                  <div class="tui-progress-track">
                    <span class="tui-progress-fill" :style="{ '--pct': doneRate / 100, '--bar-color': ringColor }" />
                  </div>
                </div>
              </div>
              <p class="tp-rate-note">完成度 = 本周办结 ÷（本周办结 + 待处理），仅统计你名下尚未关闭的跟进任务。</p>
            </div>

            <div class="tp-metrics">
              <div class="tui-stat">
                <span class="tui-stat-num">{{ summary.pending }}</span>
                <span class="tui-stat-label">待处理</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num is-high">{{ summary.high ?? 0 }}</span>
                <span class="tui-stat-label">高优先级</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num is-remind">{{ summary.remind_today ?? 0 }}</span>
                <span class="tui-stat-label">今日提醒</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num">{{ summary.today }}</span>
                <span class="tui-stat-label">今日到期</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num is-overdue">{{ summary.overdue }}</span>
                <span class="tui-stat-label">已逾期</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num is-done">{{ summary.done_this_week }}</span>
                <span class="tui-stat-label">本周办结</span>
              </div>
            </div>
          </div>
        </aside>

        <section class="tp-main">
          <div class="tp-main-head">
            <h3><el-icon><List /></el-icon>任务清单</h3>
            <span class="tp-main-count">{{ summary.total }} 条</span>
          </div>
          <TeacherTaskList
            ref="listRef"
            :key="activeFilter"
            :initial-filter="activeFilter"
            @record-care="openCare"
            @changed="loadSummary"
          />
        </section>
      </div>
    </div>

    <!-- 新增/编辑任务：日程视图按选中日期预填截止日，方便「排期」；
         外部（消息页「加入任务」）通过 query 传入学生与标题时一并预填 -->
    <TeacherTaskDialog
      v-model="createVisible"
      :task="editingTask"
      :preset-due-at="presetDueAt"
      :preset-title="presetTitle"
      :preset-student-id="presetStudent?.id ?? null"
      :preset-student-name="presetStudent?.name"
      @saved="refreshAll"
    />

    <CareRecordDialog
      v-model="careVisible"
      :student-id="careTask?.student_id || 0"
      :student-name="careTask?.student_name"
      :task-id="careTask?.id"
      :task-title="careTask?.title"
      @saved="refreshAll"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Calendar, List, MagicStick, Plus, Refresh } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import TeacherTaskList from '@/components/teacher/task/TeacherTaskList.vue'
import TeacherTaskCard from '@/components/teacher/task/TeacherTaskCard.vue'
import TeacherTaskDialog from '@/components/teacher/task/TeacherTaskDialog.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'
import { useResponsive } from '@/composables/useResponsive'
import {
  autoGenerateTeacherTasks,
  deleteTeacherTask,
  getTeacherTaskSummary,
  getTeacherTasks,
  updateTeacherTask,
  type TaskPriority,
  type TaskStatus,
  type TeacherTask,
  type TeacherTaskSummary,
} from '@/api/teacherTask'

defineOptions({ name: 'teacher-tasks' })

const { isMobile } = useResponsive()
const route = useRoute()

const WEEK_LABELS = ['一', '二', '三', '四', '五', '六', '日']

const filterMap: Record<string, string> = { overdue: 'overdue', today: 'today', pending: 'pending', high: 'high', remind: 'remind' }
const rawFilter = Array.isArray(route.query.filter) ? route.query.filter[0] : route.query.filter
const initialFilter = rawFilter ? (filterMap[rawFilter] ?? 'all') : 'all'

/** 视图：日程（默认，按日期排期）/ 清单（按优先级推进）。带筛选深链进入时默认落到清单视图 */
const viewMode = ref<'schedule' | 'list'>(rawFilter ? 'list' : 'schedule')
const viewOptions = computed(() => [
  { value: 'schedule', label: '日程' },
  { value: 'list', label: '清单', count: summary.value.total || undefined },
])

const listRef = ref<InstanceType<typeof TeacherTaskList> | null>(null)
const summary = ref<TeacherTaskSummary>({
  pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0, high: 0, remind_today: 0,
})

const activeFilter = ref(initialFilter)
const filterOptions = computed(() => [
  { value: 'all', label: '全部', count: summary.value.total },
  { value: 'high', label: '高优先级', count: summary.value.high ?? 0 },
  { value: 'remind', label: '今日提醒', count: summary.value.remind_today ?? 0 },
  { value: 'today', label: '今日到期', count: summary.value.today },
  { value: 'overdue', label: '已逾期', count: summary.value.overdue },
  { value: 'pending', label: '待处理', count: summary.value.pending },
])

function switchFilter(value: string) {
  activeFilter.value = value
}

// ===== 日程数据：一次性取回任务，按「提醒日优先、否则截止日」落到日期 =====
const SCHEDULE_LIMIT = 200
const scheduleTasks = ref<TeacherTask[]>([])
const selectedDate = ref(toDateStr(new Date()))
const cursorMonth = ref(startOfMonth(new Date()))

const generating = ref(false)
const genHint = ref('')

const createVisible = ref(false)
const editingTask = ref<TeacherTask | null>(null)
const presetDueAt = ref<string | null>(null)
/** 外部预填（消息页「加入任务」跳转过来时由 query 提供） */
const presetTitle = ref('')
const presetStudent = ref<{ id: number; name: string } | null>(null)

const careVisible = ref(false)
const careTask = ref<TeacherTask | null>(null)

function pad(n: number) {
  return String(n).padStart(2, '0')
}
function toDateStr(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

/** 任务落在哪一天：优先提醒日，其次截止日；都没有则视为未排期 */
function taskDateKey(t: TeacherTask): string {
  const raw = t.remind_at || t.due_at
  return raw ? String(raw).slice(0, 10) : ''
}

const isOpenTask = (t: TeacherTask) => t.status !== 'done'

const byDate = computed(() => {
  const map: Record<string, TeacherTask[]> = {}
  for (const t of scheduleTasks.value) {
    const key = taskDateKey(t)
    if (!key) continue
    ;(map[key] ||= []).push(t)
  }
  return map
})

const unscheduledTasks = computed(() => scheduleTasks.value.filter((t) => !taskDateKey(t) && isOpenTask(t)))

const cursorTitle = computed(() => `${cursorMonth.value.getFullYear()} 年 ${cursorMonth.value.getMonth() + 1} 月`)

interface CalCell {
  key: string
  dateStr: string
  day: number
  inMonth: boolean
  isToday: boolean
  openCount: number
  dots: TaskPriority[]
  topTone: TaskPriority
}

/** 月历网格：以周一为首列，补齐首尾使其为整周 */
const calendarCells = computed<CalCell[]>(() => {
  const first = startOfMonth(cursorMonth.value)
  const offset = (first.getDay() + 6) % 7 // 周一=0
  const start = new Date(first)
  start.setDate(first.getDate() - offset)
  const todayStr = toDateStr(new Date())
  const cells: CalCell[] = []
  for (let i = 0; i < 42; i++) {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    const dateStr = toDateStr(d)
    const items = byDate.value[dateStr] || []
    const open = items.filter(isOpenTask)
    const dots = open.slice(0, 3).map((t) => (t.priority || 'mid') as TaskPriority)
    cells.push({
      key: dateStr,
      dateStr,
      day: d.getDate(),
      inMonth: d.getMonth() === cursorMonth.value.getMonth(),
      isToday: dateStr === todayStr,
      openCount: open.length,
      dots,
      topTone: dots.includes('high') ? 'high' : dots.includes('mid') ? 'mid' : 'low',
    })
  }
  return cells
})

const selectedDateLabel = computed(() => {
  const [y, m, d] = selectedDate.value.split('-')
  const todayStr = toDateStr(new Date())
  if (selectedDate.value === todayStr) return `今天 · ${m}月${d}日`
  return `${y}年${Number(m)}月${Number(d)}日`
})

const dayTasks = computed(() => {
  const items = byDate.value[selectedDate.value] || []
  // 未办结在前，其次高优先级
  const rank: Record<TaskPriority, number> = { high: 0, mid: 1, low: 2 }
  return [...items].sort((a, b) => {
    if (isOpenTask(a) !== isOpenTask(b)) return isOpenTask(a) ? -1 : 1
    return (rank[(a.priority || 'mid') as TaskPriority] ?? 1) - (rank[(b.priority || 'mid') as TaskPriority] ?? 1)
  })
})

/** 未来 7 天负荷：用于右侧柱状概览 */
const weekLoad = computed(() => {
  const out: { dateStr: string; label: string; openCount: number; isToday: boolean }[] = []
  const todayStr = toDateStr(new Date())
  for (let i = 0; i < 7; i++) {
    const d = new Date()
    d.setDate(d.getDate() + i)
    const dateStr = toDateStr(d)
    out.push({
      dateStr,
      label: i === 0 ? '今天' : i === 1 ? '明天' : `${d.getMonth() + 1}/${d.getDate()}`,
      openCount: (byDate.value[dateStr] || []).filter(isOpenTask).length,
      isToday: dateStr === todayStr,
    })
  }
  return out
})

/** 移动端：按日期分组（今天 / 明天 / 本周内 / 更晚 / 未排期） */
const mobileDateGroups = computed(() => {
  const todayStr = toDateStr(new Date())
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  const tomorrowStr = toDateStr(tomorrow)
  const weekEnd = new Date()
  weekEnd.setDate(weekEnd.getDate() + 7)
  const weekEndStr = toDateStr(weekEnd)

  const buckets: Record<string, TeacherTask[]> = { today: [], tomorrow: [], week: [], later: [], none: [] }
  for (const t of scheduleTasks.value) {
    if (!isOpenTask(t)) continue
    const key = taskDateKey(t)
    if (!key) buckets.none.push(t)
    else if (key === todayStr) buckets.today.push(t)
    else if (key === tomorrowStr) buckets.tomorrow.push(t)
    else if (key < todayStr) buckets.today.push(t) // 逾期归入今天，提醒优先处理
    else if (key <= weekEndStr) buckets.week.push(t)
    else buckets.later.push(t)
  }
  const sortByPriority = (a: TeacherTask, b: TeacherTask) =>
    (a.priority === 'high' ? 0 : a.priority === 'mid' ? 1 : 2) - (b.priority === 'high' ? 0 : b.priority === 'mid' ? 1 : 2)
  return [
    { key: 'today', label: '今天', sub: '含逾期', items: buckets.today.sort(sortByPriority) },
    { key: 'tomorrow', label: '明天', sub: '', items: buckets.tomorrow.sort(sortByPriority) },
    { key: 'week', label: '本周内', sub: '', items: buckets.week.sort(sortByPriority) },
    { key: 'later', label: '更晚', sub: '', items: buckets.later.sort(sortByPriority) },
    { key: 'none', label: '未排期', sub: '建议定个日期', items: buckets.none.sort(sortByPriority) },
  ].filter((g) => g.items.length > 0)
})

function selectDate(dateStr: string) {
  selectedDate.value = dateStr
  const d = new Date(dateStr)
  cursorMonth.value = startOfMonth(d)
}
function shiftMonth(step: number) {
  cursorMonth.value = new Date(cursorMonth.value.getFullYear(), cursorMonth.value.getMonth() + step, 1)
}
function gotoToday() {
  const today = new Date()
  cursorMonth.value = startOfMonth(today)
  selectedDate.value = toDateStr(today)
}

/** 本周完成度 */
const doneRate = computed(() => {
  const denom = summary.value.done_this_week + summary.value.pending
  if (!denom) return 0
  return Math.min(100, Math.round((summary.value.done_this_week / denom) * 100))
})
const rateTone = computed(() => {
  const r = doneRate.value
  if (r >= 80) return 'is-success'
  if (r >= 50) return 'is-brand'
  if (r >= 25) return 'is-warn'
  return 'is-danger'
})
const ringColor = computed(() => {
  switch (rateTone.value) {
    case 'is-success': return 'var(--tui-success)'
    case 'is-warn': return 'var(--tui-warn)'
    case 'is-danger': return 'var(--tui-danger)'
    default: return 'var(--tui-brand)'
  }
})

async function loadSummary() {
  try {
    summary.value = await getTeacherTaskSummary()
  } catch {
    /* 指标拉取失败不影响列表 */
  }
}

async function loadSchedule() {
  try {
    scheduleTasks.value = await getTeacherTasks({ limit: SCHEDULE_LIMIT })
  } catch {
    scheduleTasks.value = []
  }
}

async function refreshAll() {
  await Promise.all([loadSummary(), loadSchedule()])
  listRef.value?.reload()
}

/** 智能生成：评估 → 自动排期，并把结果以一句话提示回显 */
async function smartGenerate() {
  generating.value = true
  try {
    const r = await autoGenerateTeacherTasks()
    const b = r.breakdown || {}
    if (r.created > 0) {
      genHint.value = `已智能生成 ${r.created} 条任务并排入日程（学情规则 ${b.rule ?? 0} 条 · 心理预警 ${b.crisis ?? 0} 条）`
    } else {
      genHint.value = '智能评估完成：当前没有新的待干预信号，日程保持现状'
    }
    await refreshAll()
    // 生成后自动跳到最早有任务的日期，方便立即看到结果
    const next = Object.keys(byDate.value).filter((d) => d >= toDateStr(new Date())).sort()[0]
    if (r.created > 0 && next) selectDate(next)
  } catch {
    ElMessage.error('智能生成失败，请稍后重试')
  } finally {
    generating.value = false
  }
}

function openCreate(dateStr: string | null) {
  editingTask.value = null
  presetDueAt.value = dateStr
  createVisible.value = true
}
function openEdit(task: TeacherTask) {
  editingTask.value = task
  presetDueAt.value = null
  createVisible.value = true
}
function openCare(task: TeacherTask) {
  careTask.value = task
  careVisible.value = true
}

async function handleUpdateStatus(task: TeacherTask, status: TaskStatus) {
  try {
    await updateTeacherTask(task.id, { status })
    await refreshAll()
    ElMessage.success(status === 'done' ? '任务已办结' : '任务已更新')
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '操作失败')
  }
}
function handleToggleDone(task: TeacherTask, done: boolean) {
  handleUpdateStatus(task, done ? 'done' : 'pending')
}

async function handleDelete(task: TeacherTask) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${task.title}」吗？该操作不可撤销。`, '删除任务', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteTeacherTask(task.id)
    ElMessage.success('任务已删除')
    await refreshAll()
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

/** 同步外部（消息页「加入任务」）跳转进来时的 query：?student_id=&student_name=&title= */
onMounted(() => {
  refreshAll()
  const sid = route.query.student_id
  const title = route.query.title
  if (!sid && !title) return
  editingTask.value = null
  presetDueAt.value = toDateStr(new Date())
  if (typeof title === 'string') presetTitle.value = title
  if (sid) presetStudent.value = { id: Number(sid), name: String(route.query.student_name || '') }
  createVisible.value = true
})
</script>

<style scoped>
/* ================= 工具条 ================= */
.tp-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tp-toolbar .tui-seg { margin-bottom: 0; }
.tp-toolbar-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }

.tp-genhint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.tp-genhint-close {
  margin-left: auto;
  border: none;
  background: transparent;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  color: var(--tui-text-tertiary);
}

/* ================= 日程视图（桌面） ================= */
.tp-sched {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 14px;
  align-items: start;
}
@media (max-width: 1199px) {
  .tp-sched { grid-template-columns: minmax(0, 1fr); }
}

.tp-cal-nav { display: flex; align-items: center; gap: 6px; }
.tp-cal-btn {
  border: 1px solid var(--tui-border-strong);
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 11.5px;
  font-family: inherit;
  cursor: pointer;
}
.tp-cal-btn:hover { background: var(--tui-surface-muted); }
.tp-cal-btn.is-strong { color: var(--tui-brand-strong); border-color: var(--tui-brand-soft); background: var(--tui-brand-soft); }

.tp-cal-title { font-size: 13.5px; font-weight: 600; color: var(--tui-text); margin: 2px 0 8px; }

.tp-cal-week,
.tp-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
}
.tp-cal-week span {
  text-align: center;
  font-size: 11px;
  color: var(--tui-text-quiet);
  padding-bottom: 4px;
}

.tp-cal-cell {
  position: relative;
  min-height: 54px;
  border: 1px solid transparent;
  border-radius: var(--tui-radius-xs);
  background: var(--tui-surface-muted);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 5px 6px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s var(--tui-ease), border-color 0.15s var(--tui-ease);
}
.tp-cal-cell:hover { background: var(--tui-surface-sunken); }
.tp-cal-cell.is-out { opacity: 0.45; }
.tp-cal-cell.is-today { border-color: var(--tui-brand); }
.tp-cal-cell.is-active {
  background: var(--tui-brand-soft);
  border-color: var(--tui-brand);
  box-shadow: 0 0 0 1px var(--tui-brand);
}
.tp-cal-day { font-size: 12px; color: var(--tui-text-secondary); font-variant-numeric: tabular-nums; }
.tp-cal-cell.is-today .tp-cal-day { color: var(--tui-brand-strong); font-weight: 700; }
.tp-cal-count {
  position: absolute;
  top: 4px;
  right: 5px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
  color: #fff;
  background: var(--tui-brand);
}
.tp-cal-count.tone-high { background: var(--tui-danger); }
.tp-cal-count.tone-mid { background: var(--tui-warn); }
.tp-cal-dots { display: flex; gap: 3px; margin-top: auto; }
.tp-cal-dots i { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.tone-high { background: var(--tui-danger); }
.tone-mid { background: var(--tui-warn); }
.tone-low { background: var(--tui-brand); }

.tp-cal-legend {
  display: flex;
  gap: 14px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.tp-cal-legend span { display: inline-flex; align-items: center; gap: 4px; }
.tp-cal-legend i { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }

/* 未排期 */
.tp-unscheduled {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--tui-border);
}
.tp-unscheduled-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--tui-text-tertiary);
}
.tp-unscheduled-count {
  padding: 0 6px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  font-size: 10.5px;
}
.tp-unscheduled-empty { margin-top: 6px; font-size: 11.5px; color: var(--tui-text-quiet); }
.tp-unscheduled-list { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
.tp-unscheduled-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: none;
  border-radius: var(--tui-radius-xs);
  background: var(--tui-surface-muted);
  padding: 6px 8px;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.tp-unscheduled-item:hover { background: var(--tui-surface-sunken); }
.tp-unscheduled-title {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: var(--tui-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tp-unscheduled-action { font-size: 11px; color: var(--tui-brand-strong); flex-shrink: 0; }

/* 右侧：选中日期任务 */
.tp-day-count { font-size: 11.5px; color: var(--tui-text-quiet); margin-right: 8px; }
.tp-load {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 5px;
  margin-bottom: 10px;
}
.tp-load-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  border: 1px solid transparent;
  border-radius: var(--tui-radius-xs);
  background: var(--tui-surface-muted);
  padding: 6px 2px;
  cursor: pointer;
  font-family: inherit;
}
.tp-load-item.is-today { border-color: var(--tui-brand-soft); }
.tp-load-item.is-active { background: var(--tui-brand-soft); border-color: var(--tui-brand); }
.tp-load-day { font-size: 10.5px; color: var(--tui-text-quiet); }
.tp-load-bar {
  width: 6px;
  height: 26px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.tp-load-bar i { display: block; width: 100%; background: var(--tui-brand); border-radius: 999px; }
.tp-load-num { font-size: 10.5px; color: var(--tui-text-tertiary); font-variant-numeric: tabular-nums; }

.tp-day-list { display: flex; flex-direction: column; gap: 8px; }
.tp-day-empty { padding: 26px 12px; }
.tp-group-sub { margin-left: 4px; font-size: 10.5px; font-weight: 400; color: var(--tui-text-quiet); }
.tp-group-empty { font-size: 12px; color: var(--tui-text-quiet); padding: 4px 2px; }

/* ================= 清单视图（沿用原双栏） ================= */
.tp-workbench {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}
.tp-side { position: sticky; top: 12px; }
.tp-side-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 13px 12px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
}
.tp-side-block { display: flex; flex-direction: column; gap: 8px; }
.tp-side-label { font-size: 11.5px; font-weight: 600; color: var(--tui-text-quiet); }
.tp-filters { display: flex; flex-direction: column; gap: 3px; }
.tp-filter {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  padding: 7px 9px 7px 12px;
  border: none;
  border-radius: var(--tui-radius-xs);
  background: transparent;
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), color 0.15s var(--tui-ease);
}
.tp-filter::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  bottom: 7px;
  width: 2px;
  border-radius: 999px;
  background: transparent;
}
.tp-filter:hover { background: var(--tui-surface-muted); color: var(--tui-text); }
.tp-filter.is-active { background: var(--tui-brand-soft); color: var(--tui-brand-strong); font-weight: 600; }
.tp-filter.is-active::before { background: var(--tui-brand); }
.tp-filter-count { font-size: 11px; font-variant-numeric: tabular-nums; color: var(--tui-text-tertiary); }
.tp-filter.is-active .tp-filter-count { color: var(--tui-brand-strong); }

.tp-rate-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.tp-side-card .tp-rate-row { margin-bottom: 0; }
.tp-rate-note { margin: 0; font-size: 11px; line-height: 1.5; color: var(--tui-text-quiet); }
.tp-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.tui-stat-num.is-overdue { color: var(--tui-danger); }
.tui-stat-num.is-done { color: var(--tui-success); }
.tui-stat-num.is-high { color: #7f56d9; }
.tui-stat-num.is-remind { color: var(--tui-warn); }

.tp-main { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.tp-main-head { display: flex; align-items: center; gap: 7px; padding: 0 2px; }
.tp-main-head h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
}
.tp-main-head h3 :deep(.el-icon) { font-size: 15px; color: var(--tui-text-tertiary); }
.tp-main-count {
  margin-left: auto;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text-quiet);
}

/* 移动端：清单视图不再双栏 */
@media (max-width: 767px) {
  .tp-workbench { grid-template-columns: minmax(0, 1fr); }
  .tp-side { position: static; }
}
</style>