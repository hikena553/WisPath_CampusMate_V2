<template>
  <section class="tui-section tt-list">
    <div class="tui-section-head">
      <h3><el-icon><List /></el-icon>任务清单</h3>
      <div class="tui-section-extra">
        <span class="tt-count">{{ tasks.length }} 条</span>
      </div>
    </div>
    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>按优先级分组：逾期为高优先、今日到期为中优先、其余为常规；勾选左侧方框即可办结任务。</span>
    </div>

    <!-- 筛选 chips -->
    <div class="tui-section-tools">
      <div class="tt-filters">
        <button
          v-for="f in filters"
          :key="f.value"
          class="tt-chip"
          :class="{ active: activeFilter === f.value }"
          @click="switchFilter(f.value)"
        >
          {{ f.label }}
          <span v-if="f.count > 0" class="tt-chip-count">{{ f.count }}</span>
        </button>
      </div>
    </div>

    <!-- 加载骨架 -->
    <div v-if="loading && !tasks.length" class="tt-skeleton">
      <div v-for="i in 3" :key="i" class="tt-skeleton-card">
        <div class="sk-line sk-w40"></div>
        <div class="sk-line sk-w80"></div>
        <div class="sk-line sk-w60"></div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!tasks.length" class="tui-empty">
      <span class="tui-empty-icon"><el-icon :size="24"><CircleCheck /></el-icon></span>
      <span class="tui-empty-title">{{ emptyTitle }}</span>
      <span class="tui-empty-desc">{{ emptyDesc }}</span>
    </div>

    <!-- 分组清单 -->
    <template v-else>
      <div v-for="g in groups" :key="g.key" class="tt-group">
        <div class="tt-group-head">
          <span class="tt-group-bar" :class="`is-${g.tone}`"></span>
          <span class="tt-group-title">{{ g.label }}</span>
          <span class="tt-group-count">{{ g.items.length }}</span>
        </div>
        <div class="tt-group-items">
          <TeacherTaskCard
            v-for="t in g.items"
            :key="t.id"
            :task="t"
            @toggle-done="handleToggleDone"
            @update-status="handleUpdateStatus"
            @record-care="emit('record-care', $event)"
          />
        </div>
      </div>
    </template>

    <!-- 底部加载更多 -->
    <div v-if="hasMore" class="tt-more">
      <button class="tt-more-btn" :disabled="loading" @click="loadMore">
        {{ loading ? '加载中…' : '加载更多' }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CircleCheck, InfoFilled, List } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getTeacherTasks,
  getTeacherTaskSummary,
  updateTeacherTask,
  type TaskStatus,
  type TeacherTask,
  type TeacherTaskSummary,
} from '@/api/teacherTask'
import TeacherTaskCard from './TeacherTaskCard.vue'

const props = defineProps<{
  /** 初始筛选：all / overdue / today */
  initialFilter?: string
}>()

const emit = defineEmits<{
  'record-care': [task: TeacherTask]
  changed: []
}>()

type FilterValue = 'all' | 'pending' | 'today' | 'contacted' | 'cared' | 'done' | 'overdue'
type PriorityTier = 'high' | 'mid' | 'low'

const PAGE_SIZE = 20
const tasks = ref<TeacherTask[]>([])
const loading = ref(false)
const activeFilter = ref<FilterValue>((props.initialFilter as FilterValue) || 'all')
const offset = ref(0)
const lastPageFull = ref(false)
const summary = ref<TeacherTaskSummary>({
  pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0,
})

const hasMore = computed(() => lastPageFull.value)

const filters = computed(() => [
  { value: 'all' as const, label: '全部', count: summary.value.total },
  { value: 'pending' as const, label: '待处理', count: summary.value.pending },
  { value: 'today' as const, label: '今日到期', count: summary.value.today },
  { value: 'overdue' as const, label: '已逾期', count: summary.value.overdue },
  { value: 'contacted' as const, label: '已联系', count: 0 },
  { value: 'cared' as const, label: '已关怀', count: 0 },
  { value: 'done' as const, label: '已办结', count: 0 },
])

const emptyTitle = computed(() => {
  if (activeFilter.value === 'overdue') return '没有逾期任务'
  if (activeFilter.value === 'today') return '今天没有到期的任务'
  if (activeFilter.value === 'done') return '还没有办结的任务'
  return '暂无待办任务'
})

const emptyDesc = computed(() => {
  if (activeFilter.value === 'overdue') return '保持得很好，暂无需要紧急处理的任务'
  if (activeFilter.value === 'today') return '可提前处理待办，避免任务堆积到明天'
  if (activeFilter.value === 'done') return '完成任务后会在这里留痕，便于回看本周推进'
  return '新的跟进任务会由 AI 建议、预警等自动汇入'
})

/** 优先级分层：逾期 → 高，今日到期 → 中，其余 → 低 */
function tierOf(t: TeacherTask): PriorityTier {
  if (t.overdue) return 'high'
  if (t.due_at) {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const due = new Date(t.due_at)
    due.setHours(0, 0, 0, 0)
    if (due.getTime() === today.getTime()) return 'mid'
  }
  return 'low'
}

const groups = computed(() => {
  const buckets: Record<PriorityTier, TeacherTask[]> = { high: [], mid: [], low: [] }
  for (const t of tasks.value) buckets[tierOf(t)].push(t)
  return [
    { key: 'high', label: '高优先级 · 逾期', tone: 'high' as const, items: buckets.high },
    { key: 'mid', label: '中优先级 · 今日到期', tone: 'mid' as const, items: buckets.mid },
    { key: 'low', label: '常规任务', tone: 'low' as const, items: buckets.low },
  ].filter((g) => g.items.length > 0)
})

function buildQuery(pageOffset: number) {
  const q: Record<string, unknown> = { limit: PAGE_SIZE, offset: pageOffset }
  if (activeFilter.value === 'overdue') q.due = 'overdue'
  else if (activeFilter.value === 'today') q.due = 'today'
  else if (activeFilter.value !== 'all') q.status = activeFilter.value
  return q
}

async function loadSummary() {
  try {
    summary.value = await getTeacherTaskSummary()
  } catch {
    /* KPI 拉取失败不影响列表 */
  }
}

async function fetchPage(reset: boolean) {
  loading.value = true
  try {
    const pageOffset = reset ? 0 : offset.value
    const data = await getTeacherTasks(buildQuery(pageOffset) as never)
    tasks.value = reset ? data : [...tasks.value, ...data]
    offset.value = pageOffset + data.length
    lastPageFull.value = data.length === PAGE_SIZE
  } catch {
    ElMessage.error('任务加载失败')
  } finally {
    loading.value = false
  }
}

async function reload() {
  await Promise.all([fetchPage(true), loadSummary()])
}

function switchFilter(value: FilterValue) {
  if (activeFilter.value === value) return
  activeFilter.value = value
  reload()
}

function loadMore() {
  fetchPage(false)
}

async function handleUpdateStatus(task: TeacherTask, status: TaskStatus) {
  try {
    const updated = await updateTeacherTask(task.id, { status })
    const idx = tasks.value.findIndex((t) => t.id === task.id)
    if (idx >= 0) {
      // 当前筛选下状态不再匹配时移除该卡片，保持列表语义一致
      const stillMatch =
        activeFilter.value === 'all' ||
        (activeFilter.value === 'overdue' && updated.overdue) ||
        activeFilter.value === updated.status
      if (stillMatch) tasks.value[idx] = updated
      else tasks.value.splice(idx, 1)
    }
    await loadSummary()
    emit('changed')
    ElMessage.success(status === 'done' ? '任务已办结' : '任务已更新')
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '操作失败')
  }
}

/** 勾选清单：勾选即办结，取消勾选则重新打开 */
function handleToggleDone(task: TeacherTask, done: boolean) {
  handleUpdateStatus(task, done ? 'done' : 'pending')
}

defineExpose({ reload })

onMounted(reload)
</script>

<style scoped>
.tt-list { gap: 0; }
.tt-count { font-size: 11.5px; color: var(--tui-text-quiet); }

/* 筛选 chips */
.tt-filters {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  width: 100%;
  padding-bottom: 2px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.tt-filters::-webkit-scrollbar { display: none; }

.tt-chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--tui-border-strong);
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  border-radius: 999px;
  padding: 5px 11px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
}
.tt-chip.active {
  background: var(--tui-brand);
  border-color: var(--tui-brand);
  color: var(--tui-surface);
  font-weight: 600;
}
.tt-chip-count {
  font-size: 11px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-tertiary);
}
.tt-chip.active .tt-chip-count {
  background: rgba(255, 255, 255, 0.24);
  color: var(--tui-surface);
}

/* 分组 */
.tt-group { margin-bottom: 12px; }
.tt-group:last-child { margin-bottom: 0; }
.tt-group-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
}
.tt-group-bar { width: 3px; height: 13px; border-radius: 999px; background: var(--tui-border-strong); }
.tt-group-bar.is-high { background: var(--tui-danger); }
.tt-group-bar.is-mid { background: var(--tui-warn); }
.tt-group-bar.is-low { background: var(--tui-brand); }
.tt-group-title { font-size: 12.5px; font-weight: 600; color: var(--tui-text); }
.tt-group-count {
  font-size: 11px;
  font-weight: 600;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-tertiary);
}
.tt-group-items { display: flex; flex-direction: column; gap: 8px; }

/* 骨架 */
.tt-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tt-skeleton-card {
  background: var(--tui-surface);
  border-radius: var(--tui-radius-sm);
  border: 1px solid var(--tui-border);
  padding: 12px;
}
.sk-line {
  height: 10px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--tui-surface-muted) 25%, var(--tui-surface-sunken) 37%, var(--tui-surface-muted) 63%);
  background-size: 400% 100%;
  animation: sk 1.4s ease infinite;
  margin-bottom: 9px;
}
.sk-line:last-child { margin-bottom: 0; }
.sk-w40 { width: 40%; }
.sk-w80 { width: 80%; }
.sk-w60 { width: 60%; }
@keyframes sk {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

/* 加载更多 */
.tt-more {
  display: flex;
  justify-content: center;
  padding: 12px 0 2px;
}
.tt-more-btn {
  border: 1px solid var(--tui-border-strong);
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  border-radius: 999px;
  padding: 6px 20px;
  font-size: 12.5px;
  cursor: pointer;
  font-family: inherit;
}
.tt-more-btn:hover:not(:disabled) { background: var(--tui-surface-muted); }
.tt-more-btn:disabled { opacity: 0.6; cursor: default; }
</style>