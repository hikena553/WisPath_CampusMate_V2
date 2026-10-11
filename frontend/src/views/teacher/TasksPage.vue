<template>
  <div class="tui-page">
    <SubPageHeader title="我的任务" sub="按状态筛选跟进任务" fallback="/teacher" />

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">我的任务</h2>
          <p class="tui-header-sub">按状态筛选跟进任务，点击卡片可更新状态或记录关怀</p>
        </div>
      </header>

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
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
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
.tui-stat-num.is-overdue { color: #d92d20; }
.tui-stat-num.is-done { color: #079455; }
</style>