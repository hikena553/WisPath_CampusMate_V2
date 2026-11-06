<template>
  <div v-loading="loading" class="wb-card">
    <div class="wb-head">
      <div class="wb-title">
        <el-icon class="wb-ic green"><Histogram /></el-icon>
        <span>我的工作量</span>
      </div>
      <button class="wb-more" @click="emit('open-records')">
        档案<el-icon :size="12"><ArrowRight /></el-icon>
      </button>
    </div>

    <div class="wl-hero">
      <span class="wl-total">{{ workload.total }}</span>
      <span class="wl-total-lb">条工作记录</span>
    </div>

    <div class="wl-bar" v-if="workload.total">
      <span class="wl-seg seg-care" :style="{ width: pct(workload.care) }"></span>
      <span class="wl-seg seg-talk" :style="{ width: pct(workload.talk) }"></span>
      <span class="wl-seg seg-comment" :style="{ width: pct(workload.comment) }"></span>
    </div>

    <div class="wl-legend">
      <span class="wl-lg"><i class="dot seg-care"></i>关怀 {{ workload.care }}</span>
      <span class="wl-lg"><i class="dot seg-talk"></i>谈心 {{ workload.talk }}</span>
      <span class="wl-lg"><i class="dot seg-comment"></i>评语 {{ workload.comment }}</span>
    </div>

    <div class="wl-metrics">
      <div class="wl-metric">
        <span class="wl-mv ok">{{ summary.done_this_week }}</span>
        <span class="wl-ml">本周办结</span>
      </div>
      <div class="wl-metric">
        <span class="wl-mv purple">{{ leave.pending }}</span>
        <span class="wl-ml">待请假</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowRight, Histogram } from '@element-plus/icons-vue'
import { getWorkloadStats, type WorkloadStats } from '@/api/careRecord'
import { getTeacherTaskSummary, type TeacherTaskSummary } from '@/api/teacherTask'
import { getLeaveStats, type LeaveStats } from '@/api/leave'
import { getCachedData } from '@/utils/teacherDashboardCache'
import { onRealtimeData } from '@/utils/realtime'

const emit = defineEmits<{ 'open-records': [] }>()

const loading = ref(false)
const workload = ref<WorkloadStats>({ care: 0, talk: 0, comment: 0, total: 0 })
const summary = ref<TeacherTaskSummary>({ pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0 })
const leave = ref<LeaveStats>({
  total: 0,
  approved: 0,
  rejected: 0,
  pending: 0,
  by_type: [],
  by_class: [],
})

function pct(n: number) {
  const t = workload.value.total || 1
  return `${Math.round((n / t) * 100)}%`
}

/**
 * 拉取三块数据。
 *
 * 要点：
 * - 首帧用预加载缓存直出（有缓存就不亮 loading），避免切页时数字先归零再跳回来；
 * - 始终 silent：本卡片数据只由 SSE 事件驱动刷新，不显示 loading，做到「无闪烁」；
 * - Promise.allSettled：三者互不阻塞，任一失败保留旧值，不会因一个接口抖动导致整卡清空。
 */
let inflight: Promise<void> | null = null

async function load(silent = true) {
  // 并发去重：一次操作可能连发多个域事件，合并成一轮请求
  if (inflight) return inflight
  if (!silent) loading.value = true

  inflight = (async () => {
    const [w, s, l] = await Promise.allSettled([
      getWorkloadStats(),
      getTeacherTaskSummary(),
      getLeaveStats(),
    ])
    if (w.status === 'fulfilled') workload.value = w.value
    if (s.status === 'fulfilled') summary.value = s.value
    if (l.status === 'fulfilled') leave.value = l.value
    loading.value = false
  })()

  try {
    await inflight
  } finally {
    inflight = null
  }
}

/** 首屏：优先吃布局预加载缓存（同一批接口，避免重复请求） */
function hydrateFromCache() {
  const cachedLeave = getCachedData<LeaveStats>('leave-stats')
  if (cachedLeave) leave.value = cachedLeave
  const cachedSummary = getCachedData<TeacherTaskSummary>('teacher-task-summary')
  if (cachedSummary) summary.value = cachedSummary
}

hydrateFromCache()

// 实时更新：关怀/谈心/评语、任务办结、请假审批 —— 任一变化都静默重拉本卡片。
// 这是取代「30 秒轮询 + 切页重挂载」的主更新路径，无整页刷新、无闪烁。
const offRealtime = onRealtimeData(
  ['teacher-care', 'teacher-tasks', 'teacher-approval', 'teacher-dashboard'],
  () => { void load(true) },
)

onMounted(() => { void load(true) })
onBeforeUnmount(offRealtime)

defineExpose({ reload: load })
</script>

<style scoped>
.wb-card {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  padding: 16px;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  gap: 11px;
  min-height: 172px;
}

.wb-head {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: space-between;
}
.wb-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: #2b3245;
}
.wb-ic {
  color: #2563eb;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  flex-shrink: 0;
  font-size: 13px;
}
.wb-ic.green {
  background: color-mix(in srgb, #079455 12%, #fff);
  color: #079455;
}
.wb-more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: none;
  background: none;
  padding: 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  cursor: pointer;
  font-family: inherit;
}
.wb-more:hover { color: var(--tui-brand); }

.wl-hero {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.wl-total {
  font-size: 26px;
  font-weight: 700;
  color: #101828;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.wl-total-lb {
  font-size: 12px;
  color: var(--tui-text-quiet);
}

.wl-bar {
  display: flex;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--tui-surface-muted);
}
.wl-seg { display: block; height: 100%; }
.seg-care { background: #f04438; }
.seg-talk { background: #7c3aed; }
.seg-comment { background: #2563eb; }

.wl-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.wl-lg {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--tui-text-secondary);
}
.wl-lg .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.wl-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: auto;
}
.wl-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: var(--tui-surface-muted);
  border-radius: 10px;
  padding: 8px 10px;
}
.wl-mv {
  font-size: 18px;
  font-weight: 700;
  color: #101828;
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
}
.wl-mv.ok { color: #079455; }
.wl-mv.warn { color: #b54708; }
.wl-mv.purple { color: #6941c6; }
.wl-ml {
  font-size: 11px;
  color: var(--tui-text-quiet);
}
</style>