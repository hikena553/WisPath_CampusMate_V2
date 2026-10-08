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
        <span class="wl-mv warn">{{ leave.pending }}</span>
        <span class="wl-ml">待批请假</span>
      </div>
      <div class="wl-metric">
        <span class="wl-mv purple">{{ leave.awaiting_return }}</span>
        <span class="wl-ml">待销假</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'
import { ArrowRight, Histogram } from '@element-plus/icons-vue'
import { getWorkloadStats, type WorkloadStats } from '@/api/careRecord'
import { getTeacherTaskSummary, type TeacherTaskSummary } from '@/api/teacherTask'
import { getLeaveStats, type LeaveStats } from '@/api/leave'

const emit = defineEmits<{ 'open-records': [] }>()

const loading = ref(false)
const workload = ref<WorkloadStats>({ care: 0, talk: 0, comment: 0, total: 0 })
const summary = ref<TeacherTaskSummary>({ pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0 })
const leave = ref<LeaveStats>({
  total: 0,
  approved: 0,
  rejected: 0,
  pending: 0,
  awaiting_return: 0,
  by_type: [],
  by_class: [],
})

function pct(n: number) {
  const t = workload.value.total || 1
  return `${Math.round((n / t) * 100)}%`
}

async function load() {
  loading.value = true
  const [w, s, l] = await Promise.allSettled([
    getWorkloadStats(),
    getTeacherTaskSummary(),
    getLeaveStats(),
  ])
  if (w.status === 'fulfilled') workload.value = w.value
  if (s.status === 'fulfilled') summary.value = s.value
  if (l.status === 'fulfilled') leave.value = l.value
  loading.value = false
}

onMounted(load)
onActivated(load)
defineExpose({ reload: load })
</script>

<style scoped>
.wb-card {
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 14px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 11px;
  min-height: 172px;
}

.wb-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.wb-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: #101828;
}
.wb-ic { color: #2563eb; }
.wb-ic.green { color: #079455; }
.wb-more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: #667085;
  cursor: pointer;
  font-family: inherit;
}
.wb-more:hover { color: #2563eb; }

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
}
.wl-total-lb {
  font-size: 12px;
  color: #98a2b3;
}

.wl-bar {
  display: flex;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: #f2f4f7;
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
  color: #667085;
}
.wl-lg .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.wl-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: auto;
}
.wl-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: #f9fafb;
  border-radius: 10px;
  padding: 8px 10px;
}
.wl-mv {
  font-size: 18px;
  font-weight: 700;
  color: #101828;
  line-height: 1.15;
}
.wl-mv.ok { color: #079455; }
.wl-mv.warn { color: #b54708; }
.wl-mv.purple { color: #6941c6; }
.wl-ml {
  font-size: 11px;
  color: #98a2b3;
}
</style>