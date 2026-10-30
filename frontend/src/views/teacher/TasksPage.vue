<template>
  <div
    class="tui-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader title="任务清单" fallback="/teacher" />
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <div class="tui-content">
      <!-- 桌面端头部 -->
      <TuiPageHero
        v-if="!isMobile"
        title="任务清单"
        sub="手动新增或从聊天一键加入"
        :icon="List"
        tone="brand"
      />

      <!-- 工具条：新增任务 -->
      <div class="tp-toolbar">
        <div class="tp-toolbar-actions">
          <el-button size="small" @click="openCreate()">
            <el-icon><Plus /></el-icon><span>新增任务</span>
          </el-button>
        </div>
      </div>

      <!-- ===================== 移动端：时间轴式任务日程（方案C） ===================== -->
      <div v-if="isMobile" class="tp-timeline">
        <!-- 日期条：以今天为中心的前后 7 天 -->
        <div class="tp-date-strip tui-scroll-hidden">
          <button
            v-for="d in dayStrip"
            :key="d.date"
            type="button"
            class="tp-day"
            :class="{ 'is-on': selectedDate === d.date }"
            @click="selectedDate = d.date"
          >
            {{ d.weekday }}<b>{{ d.dayNum }}</b>
            <i v-if="d.count > 0" class="tp-day-dot" />
          </button>
        </div>

        <!-- 已逾期分组（红色节点，置顶） -->
        <template v-if="overdueGroup.items.length">
          <div class="tp-tlg">已逾期<span class="tp-tlg-n is-danger">{{ overdueGroup.items.length }}</span></div>
          <div class="tp-tl">
            <div v-for="t in overdueGroup.items" :key="'od' + t.id" class="tp-tlt is-urgent">
              <div class="tp-tl-time">{{ timeLabel(t) }}<span class="tp-tl-overdue-tag">逾期</span></div>
              <button type="button" class="tp-tcard" @click="openEditTask(t)">
                <span class="tp-tcard-title">{{ t.title }}</span>
                <span class="tp-tcard-meta">
                  <span class="tp-ttag" :class="'is-' + (t.priority || 'mid')">{{ TASK_PRIORITY_LABEL[t.priority || 'mid'] }}</span>
                  <span v-if="t.student_name" class="tp-tmeta">{{ t.student_name }}</span>
                  <span class="tp-tmeta">{{ TASK_SOURCE_LABEL[t.source_type] }}</span>
                </span>
              </button>
            </div>
          </div>
        </template>

        <!-- 所选日期：按上午 / 下午 / 晚上 / 未安排 分组 -->
        <template v-for="g in timelineGroups" :key="g.key">
          <div class="tp-tlg">{{ g.title }}<span class="tp-tlg-n" :class="g.tone">{{ g.items.length }}</span></div>
          <div class="tp-tl">
            <div v-for="t in g.items" :key="g.key + t.id" class="tp-tlt" :class="{ 'is-urgent': t.overdue, 'is-now': !t.overdue && t.status !== 'done' }">
              <div class="tp-tl-time">{{ timeLabel(t) }}</div>
              <button type="button" class="tp-tcard" :class="{ 'is-done': t.status === 'done' }" @click="openEditTask(t)">
                <span class="tp-tcard-title">{{ t.title }}</span>
                <span class="tp-tcard-meta">
                  <span class="tp-ttag" :class="'is-' + (t.priority || 'mid')">{{ TASK_PRIORITY_LABEL[t.priority || 'mid'] }}</span>
                  <span v-if="t.student_name" class="tp-tmeta">{{ t.student_name }}</span>
                  <span class="tp-tmeta">{{ TASK_SOURCE_LABEL[t.source_type] }}</span>
                </span>
              </button>
            </div>
          </div>
        </template>

        <div v-if="!timelineGroups.length && !overdueGroup.items.length" class="tp-tl-empty">
          <el-icon :size="22"><Calendar /></el-icon>
          <p>当前日期没有安排任务</p>
        </div>

        <!-- 本周完成度 -->
        <div class="tp-prog-line">
          <span>本周完成 {{ summary.done_this_week }} 项</span>
          <span class="tp-prog-bar"><i :style="{ width: doneRate + '%', background: ringColor }" /></span>
          <em>{{ doneRate }}%</em>
        </div>
      </div>

      <!-- ===================== 桌面端：清单视图（沿用原双栏） ===================== -->
      <div v-else class="tp-workbench">
        <aside class="tp-side">
          <div class="tp-side-card">
            <div class="tp-side-block">
              <div class="tp-side-label">分组筛选</div>
              <div class="tp-filters">
                <div
                  v-for="f in filterOptions"
                  :key="f.value"
                  class="tp-filter-wrap"
                  :class="{ 'is-expanded': expandedFilters.has(f.value) }"
                >
                  <div class="tp-filter-row">
                    <button
                      type="button"
                      class="tp-filter"
                      :class="{ 'is-active': activeFilter === f.value }"
                      @click="switchFilter(f.value)"
                    >
                      <span class="tp-filter-label">{{ f.label }}</span>
                      <span class="tp-filter-count">{{ f.count }}</span>
                    </button>
                    <button
                      v-if="f.count > 0"
                      type="button"
                      class="tp-filter-toggle"
                      :aria-label="expandedFilters.has(f.value) ? '收起' : '展开'"
                      @click="toggleExpand(f.value)"
                    >
                      <el-icon :size="12" :class="{ 'is-open': expandedFilters.has(f.value) }"><ArrowRight /></el-icon>
                    </button>
                  </div>
                  <!-- 展开后展示该分组下的具体任务 -->
                  <div v-if="expandedFilters.has(f.value)" class="tp-filter-tasks">
                    <div v-if="filterLoading.has(f.value)" class="tp-filter-loading">加载中…</div>
                    <template v-else>
                      <div v-if="!filterTasks[f.value]?.length" class="tp-filter-empty">暂无任务</div>
                      <button
                        v-for="t in filterTasks[f.value]"
                        :key="t.id"
                        type="button"
                        class="tp-filter-task"
                        @click="openEditTask(t)"
                      >
                        <span class="tp-filter-task-title" :class="{ 'is-done': t.status === 'done' }">{{ t.title }}</span>
                        <span v-if="t.student_name" class="tp-filter-task-meta">{{ t.student_name }}</span>
                      </button>
                    </template>
                  </div>
                </div>
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

    <!-- 新增/编辑任务：外部（消息页「加入任务」）通过 query 传入学生与标题时预填 -->
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
import { ArrowRight, Calendar, List, Plus } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TeacherTaskList from '@/components/teacher/task/TeacherTaskList.vue'
import TeacherTaskDialog from '@/components/teacher/task/TeacherTaskDialog.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'
import { useResponsive } from '@/composables/useResponsive'
import {
  getTeacherTaskSummary,
  getTeacherTasks,
  TASK_PRIORITY_LABEL,
  TASK_SOURCE_LABEL,
  type TeacherTask,
  type TeacherTaskSummary,
} from '@/api/teacherTask'

defineOptions({ name: 'teacher-tasks' })

const { isMobile } = useResponsive()
const route = useRoute()

/** 移动端下拉刷新：手动刷新按钮已移除，统一由下拉手势触发 */
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

const filterMap: Record<string, string> = { overdue: 'overdue', today: 'today', pending: 'pending', high: 'high', remind: 'remind' }
const rawFilter = Array.isArray(route.query.filter) ? route.query.filter[0] : route.query.filter
const initialFilter = rawFilter ? (filterMap[rawFilter] ?? 'all') : 'all'

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

/** 分组筛选展开状态：展开后直接在侧栏展示该分组下的具体任务 */
const expandedFilters = ref<Set<string>>(new Set())
const filterTasks = ref<Record<string, TeacherTask[]>>({})
const filterLoading = ref<Set<string>>(new Set())

/** 将筛选值映射为 getTeacherTasks 的查询参数 */
function buildFilterQuery(value: string): Record<string, unknown> {
  const q: Record<string, unknown> = { limit: 50, offset: 0 }
  if (value === 'overdue') q.due = 'overdue'
  else if (value === 'today') q.due = 'today'
  else if (value === 'remind') q.due = 'remind'
  else if (value === 'high') q.priority = 'high'
  else if (value === 'pending') q.status = 'pending'
  return q
}

/** 切换某筛选分组的展开/收起；展开时按需拉取该分组任务 */
async function toggleExpand(value: string) {
  const isExpanded = expandedFilters.value.has(value)
  if (isExpanded) {
    expandedFilters.value.delete(value)
    return
  }
  expandedFilters.value.add(value)
  if (!filterTasks.value[value]) {
    filterLoading.value.add(value)
    try {
      filterTasks.value[value] = await getTeacherTasks(buildFilterQuery(value) as never)
    } catch {
      filterTasks.value[value] = []
    } finally {
      filterLoading.value.delete(value)
    }
  }
}

/** 点击筛选标签本身：切换主视图筛选；不影响展开状态 */
function switchFilter(value: string) {
  activeFilter.value = value
}

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

/** 本周完成度 */
const doneRate = computed(() => {
  const denom = summary.value.done_this_week + summary.value.pending
  if (!denom) return 0
  return Math.min(100, Math.round((summary.value.done_this_week / denom) * 100))
})

/* ================= 移动端：时间轴式任务日程 ================= */
/** 移动端全量任务（近若干条，用于日期条与时间轴） */
const mobileTasks = ref<TeacherTask[]>([])
const selectedDate = ref(toDateStr(new Date()))

/** 取任务的截止时间 Date（无截止返回 null） */
function taskDue(t: TeacherTask): Date | null {
  if (!t.due_at) return null
  const d = new Date(t.due_at)
  return Number.isNaN(d.getTime()) ? null : d
}
/** 取日期部分 YYYY-MM-DD */
function taskDueDate(t: TeacherTask): string | null {
  const d = taskDue(t)
  return d ? toDateStr(d) : null
}
/** 时间轴上的时刻标签：HH:MM 或「全天」 */
function timeLabel(t: TeacherTask): string {
  const d = taskDue(t)
  return d ? `${pad(d.getHours())}:${pad(d.getMinutes())}` : '全天'
}
const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/** 以今天为中心的前后 7 天日期条 */
const dayStrip = computed(() => {
  const today = new Date()
  const days: { date: string; weekday: string; dayNum: string; count: number }[] = []
  for (let i = -3; i <= 3; i++) {
    const d = new Date(today)
    d.setDate(d.getDate() + i)
    const ds = toDateStr(d)
    days.push({
      date: ds,
      weekday: i === 0 ? '今天' : WEEKDAYS[d.getDay()],
      dayNum: `${d.getMonth() + 1}/${d.getDate()}`,
      count: mobileTasks.value.filter((t) => t.status !== 'done' && taskDueDate(t) === ds).length,
    })
  }
  return days
})

/** 已逾期任务（未办结且已过期） */
const overdueGroup = computed(() => ({
  items: mobileTasks.value.filter((t) => t.overdue && t.status !== 'done'),
}))

/** 所选日期的任务按时间段分组 */
const timelineGroups = computed(() => {
  const items = mobileTasks.value.filter((t) => taskDueDate(t) === selectedDate.value)
  if (!items.length) return []
  const buckets: { key: string; title: string; tone: string; items: TeacherTask[] }[] = [
    { key: 'am', title: '上午', tone: '', items: [] },
    { key: 'pm', title: '下午', tone: '', items: [] },
    { key: 'eve', title: '晚上', tone: '', items: [] },
    { key: 'na', title: '未安排', tone: 'is-quiet', items: [] },
  ]
  for (const t of items) {
    const d = taskDue(t)
    if (!d) buckets[3].items.push(t)
    else if (d.getHours() < 12) buckets[0].items.push(t)
    else if (d.getHours() < 18) buckets[1].items.push(t)
    else buckets[2].items.push(t)
  }
  // 各桶内按时刻升序，已办结沉底
  for (const b of buckets) {
    b.items.sort((a, c) => {
      if ((a.status === 'done') !== (c.status === 'done')) return a.status === 'done' ? 1 : -1
      return timeLabel(a).localeCompare(timeLabel(c))
    })
  }
  return buckets.filter((b) => b.items.length)
})

async function loadMobileTasks() {
  try {
    mobileTasks.value = await getTeacherTasks({ limit: 100, offset: 0 } as never)
  } catch {
    /* 时间轴拉取失败保持空态 */
  }
}
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

async function refreshAll() {
  await Promise.all([loadSummary(), loadMobileTasks()])
  // 任务数据变化后清空已缓存的分组任务，下次展开时重新拉取
  filterTasks.value = {}
  listRef.value?.reload()
}

function openCreate() {
  editingTask.value = null
  presetDueAt.value = null
  createVisible.value = true
}
function openCare(task: TeacherTask) {
  careTask.value = task
  careVisible.value = true
}
/** 从侧栏展开的任务列表直接打开编辑弹窗 */
function openEditTask(task: TeacherTask) {
  editingTask.value = task
  presetDueAt.value = null
  createVisible.value = true
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
.tui-page.pull-enabled { overscroll-behavior-y: contain; }
/* ================= 工具条 ================= */
.tp-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tp-toolbar-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }

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
.tp-filter-wrap { display: flex; flex-direction: column; }
.tp-filter-row {
  display: flex;
  align-items: center;
  gap: 2px;
}
.tp-filter {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex: 1;
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

/* 展开/收起按钮 */
.tp-filter-toggle {
  flex-shrink: 0;
  width: 22px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--tui-radius-xs);
  background: transparent;
  color: var(--tui-text-quiet);
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), color 0.15s var(--tui-ease);
}
.tp-filter-toggle:hover { background: var(--tui-surface-muted); color: var(--tui-text-secondary); }
.tp-filter-toggle .el-icon { transition: transform 0.2s var(--tui-ease); }
.tp-filter-toggle .el-icon.is-open { transform: rotate(90deg); }

/* 展开后的任务列表 */
.tp-filter-tasks {
  margin: 2px 0 4px 22px;
  padding: 4px 0;
  border-left: 1px dashed var(--tui-border);
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.tp-filter-loading,
.tp-filter-empty {
  padding: 5px 10px;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.tp-filter-task {
  display: flex;
  flex-direction: column;
  gap: 1px;
  width: 100%;
  padding: 5px 10px;
  border: none;
  border-radius: var(--tui-radius-xs);
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: background 0.12s var(--tui-ease);
}
.tp-filter-task:hover { background: var(--tui-surface-muted); }
.tp-filter-task-title {
  font-size: 12px;
  color: var(--tui-text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tp-filter-task-title.is-done { text-decoration: line-through; color: var(--tui-text-quiet); }
.tp-filter-task-meta { font-size: 10.5px; color: var(--tui-text-quiet); }

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

/* ================= 移动端时间轴式任务日程（方案C） ================= */
.tp-date-strip {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  margin-bottom: 14px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.tp-date-strip::-webkit-scrollbar { display: none; width: 0; height: 0; }
.tp-day {
  position: relative;
  flex: 1;
  min-width: 48px;
  border: 1px solid var(--tui-border);
  border-radius: 12px;
  background: var(--tui-surface);
  text-align: center;
  padding: 7px 0 6px;
  font-size: 11px;
  color: var(--tui-text-tertiary);
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), border-color 0.15s var(--tui-ease);
}
.tp-day b { display: block; font-size: 13.5px; font-weight: 700; color: var(--tui-text); margin-top: 1px; font-variant-numeric: tabular-nums; }
.tp-day.is-on { background: var(--tui-brand); border-color: var(--tui-brand); color: rgba(255, 255, 255, 0.85); }
.tp-day.is-on b { color: #fff; }
.tp-day-dot {
  position: absolute;
  top: 5px;
  right: 7px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--tui-warn);
}
.tp-day.is-on .tp-day-dot { background: #fff; }

.tp-tlg {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 14px 2px 8px;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--tui-text-tertiary);
}
.tp-tlg-n {
  font-size: 10.5px;
  line-height: 1.6;
  color: #fff;
  border-radius: 999px;
  padding: 0 7px;
  font-weight: 600;
  background: var(--tui-brand);
}
.tp-tlg-n.is-danger { background: var(--tui-danger); }
.tp-tlg-n.is-quiet { background: var(--tui-text-quiet); }

.tp-tl { position: relative; padding-left: 20px; }
.tp-tl::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 4px;
  bottom: 4px;
  width: 2px;
  border-radius: 999px;
  background: var(--tui-border-strong);
}
.tp-tlt { position: relative; margin-bottom: 10px; }
.tp-tlt::before {
  content: '';
  position: absolute;
  left: -19px;
  top: 15px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--tui-surface);
  border: 2.5px solid var(--tui-text-quiet);
}
.tp-tlt.is-urgent::before { border-color: var(--tui-danger); }
.tp-tlt.is-now::before { border-color: var(--tui-success); background: var(--tui-success); }
.tp-tl-time {
  font-size: 11px;
  color: var(--tui-text-quiet);
  font-weight: 600;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-variant-numeric: tabular-nums;
}
.tp-tl-overdue-tag {
  font-size: 10px;
  color: var(--tui-danger);
  background: var(--tui-danger-soft);
  border-radius: 999px;
  padding: 0 6px;
}
.tp-tcard {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  padding: 10px 12px;
  box-shadow: var(--tui-shadow-1);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: background 0.15s var(--tui-ease);
}
.tp-tcard:active { background: var(--tui-surface-muted); }
.tp-tcard.is-done .tp-tcard-title { text-decoration: line-through; color: var(--tui-text-quiet); }
.tp-tcard-title { font-size: 13px; font-weight: 600; color: var(--tui-text); line-height: 1.45; }
.tp-tcard-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tp-ttag {
  font-size: 10.5px;
  font-weight: 600;
  border-radius: 999px;
  padding: 1px 8px;
}
.tp-ttag.is-high { color: var(--tui-danger); background: var(--tui-danger-soft); }
.tp-ttag.is-mid { color: var(--tui-brand-strong); background: var(--tui-brand-soft); }
.tp-ttag.is-low { color: var(--tui-text-tertiary); background: var(--tui-surface-sunken); }
.tp-tmeta { font-size: 11px; color: var(--tui-text-tertiary); }
.tp-tl-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 36px 0 24px;
  color: var(--tui-text-quiet);
  font-size: 12.5px;
}
.tp-tl-empty p { margin: 0; }
.tp-prog-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 18px 2px 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.tp-prog-bar {
  flex: 1;
  height: 5px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
}
.tp-prog-bar i { display: block; height: 100%; border-radius: 999px; transition: width 0.4s var(--tui-ease); }
.tp-prog-line em { font-style: normal; font-size: 11px; font-weight: 400; color: var(--tui-text-quiet); }
</style>