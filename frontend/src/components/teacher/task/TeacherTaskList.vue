<template>
  <div class="tt-list">
    <!-- 筛选条 -->
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

    <!-- 加载骨架 -->
    <div v-if="loading && !tasks.length" class="tt-skeleton">
      <div v-for="i in 3" :key="i" class="tt-skeleton-card">
        <div class="sk-line sk-w40"></div>
        <div class="sk-line sk-w80"></div>
        <div class="sk-line sk-w60"></div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!tasks.length" class="tt-empty">
      <el-icon :size="40" color="#d0d5dd"><CircleCheck /></el-icon>
      <p>{{ emptyText }}</p>
    </div>

    <!-- 任务列表 -->
    <div v-else class="tt-items">
      <TeacherTaskCard
        v-for="t in tasks"
        :key="t.id"
        :task="t"
        @update-status="handleUpdateStatus"
        @record-care="emit('record-care', $event)"
      />
    </div>

    <!-- 底部加载更多 -->
    <div v-if="hasMore" class="tt-more">
      <button class="tt-more-btn" :disabled="loading" @click="loadMore">
        {{ loading ? '加载中…' : '加载更多' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CircleCheck } from '@element-plus/icons-vue'
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

type FilterValue = 'all' | 'pending' | 'contacted' | 'cared' | 'done' | 'overdue'

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
  { value: 'overdue' as const, label: '已逾期', count: summary.value.overdue },
  { value: 'contacted' as const, label: '已联系', count: 0 },
  { value: 'cared' as const, label: '已关怀', count: 0 },
  { value: 'done' as const, label: '已办结', count: 0 },
])

const emptyText = computed(() => {
  if (activeFilter.value === 'overdue') return '没有逾期任务，保持得很好'
  if (activeFilter.value === 'done') return '还没有办结的任务'
  return '暂无待办任务'
})

function buildQuery(pageOffset: number) {
  const q: Record<string, unknown> = { limit: PAGE_SIZE, offset: pageOffset }
  if (activeFilter.value === 'overdue') q.due = 'overdue'
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

defineExpose({ reload })

onMounted(reload)
</script>

<style scoped>
.tt-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 筛选 chips */
.tt-filters {
  display: flex;
  gap: 8px;
  overflow-x: auto;
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
  border: 1px solid #e4e7ec;
  background: #fff;
  color: #475467;
  border-radius: 999px;
  padding: 6px 13px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
}
.tt-chip.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
  font-weight: 600;
}
.tt-chip-count {
  font-size: 11px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
}
.tt-chip.active .tt-chip-count {
  background: rgba(255, 255, 255, 0.24);
}

.tt-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 骨架 */
.tt-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tt-skeleton-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  padding: 14px;
}
.sk-line {
  height: 10px;
  border-radius: 6px;
  background: linear-gradient(90deg, #f2f4f7 25%, #e9edf2 37%, #f2f4f7 63%);
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

.tt-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 42px 0;
  color: #98a2b3;
  font-size: 13px;
}
.tt-empty p { margin: 0; }

.tt-more {
  display: flex;
  justify-content: center;
  padding: 4px 0 8px;
}
.tt-more-btn {
  border: 1px solid #e4e7ec;
  background: #fff;
  color: #475467;
  border-radius: 999px;
  padding: 7px 22px;
  font-size: 12.5px;
  cursor: pointer;
  font-family: inherit;
}
.tt-more-btn:disabled { opacity: 0.6; cursor: default; }
</style>
