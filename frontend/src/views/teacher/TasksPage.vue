<template>
  <div class="tui-page">
    <SubPageHeader title="今日任务清单" sub="按完成度推进 · 勾选即办结" fallback="/teacher" />

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">今日任务清单</h2>
          <p class="tui-header-sub">按优先级分组推进，勾选任务即办结；点击卡片可更新状态或记录关怀</p>
        </div>
      </header>

      <!-- 完成度进度：本周推进节奏一目了然 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Odometer /></el-icon>本周完成度</h3>
          <div class="tui-section-extra">
            <span class="tp-rate" :class="rateTone">{{ doneRate }}%</span>
          </div>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>完成度 = 本周办结 ÷（本周办结 + 待处理），仅统计你名下尚未关闭的跟进任务，用来衡量本周推进节奏。</span>
        </div>
        <div class="tp-progress">
          <span class="tp-progress-fill" :class="rateTone" :style="{ width: doneRate + '%' }" />
        </div>
        <div class="tui-stat-row cols-4">
          <div class="tui-stat">
            <span class="tui-stat-num">{{ summary.pending }}</span>
            <span class="tui-stat-label">待处理</span>
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
      </section>

      <TeacherTaskList ref="listRef" :initial-filter="initialFilter" @record-care="openCare" />
    </div>

    <CareRecordDialog
      v-model="careVisible"
      :student-id="careTask?.student_id || 0"
      :student-name="careTask?.student_name"
      :task-id="careTask?.id"
      :task-title="careTask?.title"
      @saved="onCareSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { InfoFilled, Odometer } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TeacherTaskList from '@/components/teacher/task/TeacherTaskList.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'
import { useResponsive } from '@/composables/useResponsive'
import { getTeacherTaskSummary, type TeacherTask, type TeacherTaskSummary } from '@/api/teacherTask'

defineOptions({ name: 'teacher-tasks' })

const { isMobile } = useResponsive()
const route = useRoute()

const filterMap: Record<string, string> = { overdue: 'overdue', today: 'today', pending: 'pending' }
const rawFilter = Array.isArray(route.query.filter) ? route.query.filter[0] : route.query.filter
const initialFilter = rawFilter ? (filterMap[rawFilter] ?? 'all') : 'all'

const listRef = ref<InstanceType<typeof TeacherTaskList> | null>(null)
const summary = ref<TeacherTaskSummary>({ pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0 })

const careVisible = ref(false)
const careTask = ref<TeacherTask | null>(null)

/** 本周完成度：完全基于现有 summary 字段派生，不新增接口 */
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

async function loadSummary() {
  try {
    summary.value = await getTeacherTaskSummary()
  } catch {
    /* 指标拉取失败不影响列表 */
  }
}

function openCare(task: TeacherTask) {
  careTask.value = task
  careVisible.value = true
}

function onCareSaved() {
  listRef.value?.reload()
}

onMounted(loadSummary)
</script>

<style scoped>
.tp-rate {
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  padding: 2px 9px;
  border-radius: 999px;
}
.tp-rate.is-success { background: var(--tui-success-soft); color: var(--tui-success); }
.tp-rate.is-brand { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.tp-rate.is-warn { background: var(--tui-warn-soft); color: var(--tui-warn); }
.tp-rate.is-danger { background: var(--tui-danger-soft); color: var(--tui-danger); }

.tp-progress {
  height: 10px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
  margin-bottom: 12px;
}
.tp-progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s var(--tui-ease);
}
.tp-progress-fill.is-success { background: var(--tui-success); }
.tp-progress-fill.is-brand { background: var(--tui-brand); }
.tp-progress-fill.is-warn { background: var(--tui-warn); }
.tp-progress-fill.is-danger { background: var(--tui-danger); }

.tui-stat-num.is-overdue { color: var(--tui-danger); }
.tui-stat-num.is-done { color: var(--tui-success); }
</style>