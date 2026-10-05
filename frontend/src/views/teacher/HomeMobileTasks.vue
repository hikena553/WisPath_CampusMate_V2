<template>
  <div class="sub-page task-layer-page">
    <!-- 校园背景头部 -->
    <div class="tl-hero">
      <img src="/images/campus/游仙校区博识楼.jpg" class="tl-hero-bg" alt="" />
      <div class="tl-hero-overlay"></div>
      <div class="tl-hero-top">
        <button class="tl-hero-back" @click="emit('close')">
          <el-icon :size="18"><ArrowLeft /></el-icon>
        </button>
        <span class="tl-hero-title">待办任务</span>
      </div>
      <div class="tl-hero-stats">
        <div class="tl-stat">
          <span class="tl-stat-num">{{ summary.pending }}</span>
          <span class="tl-stat-label">待处理</span>
        </div>
        <div class="tl-stat-divider"></div>
        <div class="tl-stat">
          <span class="tl-stat-num tl-danger">{{ summary.overdue }}</span>
          <span class="tl-stat-label">已逾期</span>
        </div>
        <div class="tl-stat-divider"></div>
        <div class="tl-stat">
          <span class="tl-stat-num tl-success">{{ summary.done_this_week }}</span>
          <span class="tl-stat-label">本周办结</span>
        </div>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="tl-body">
      <TeacherTaskList ref="listRef" @record-care="openCare" />
    </div>

    <!-- 记录关怀 -->
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
import { ArrowLeft } from '@element-plus/icons-vue'
import { getTeacherTaskSummary, type TeacherTask, type TeacherTaskSummary } from '@/api/teacherTask'
import TeacherTaskList from '@/components/teacher/task/TeacherTaskList.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'

const emit = defineEmits<{ close: [] }>()

const listRef = ref<InstanceType<typeof TeacherTaskList> | null>(null)
const summary = ref<TeacherTaskSummary>({
  pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0,
})

const careVisible = ref(false)
const careTask = ref<TeacherTask | null>(null)

async function loadSummary() {
  try {
    summary.value = await getTeacherTaskSummary()
  } catch {
    /* 概览失败不阻塞列表 */
  }
}

function openCare(task: TeacherTask) {
  if (!task.student_id) return
  careTask.value = task
  careVisible.value = true
}

function onCareSaved() {
  listRef.value?.reload()
  loadSummary()
}

onMounted(loadSummary)
</script>

<style scoped>
.task-layer-page {
  position: fixed;
  inset: 0;
  background: #f5f7fa;
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.tl-hero {
  position: relative;
  flex-shrink: 0;
  padding: 14px 16px 20px;
  color: #fff;
  overflow: hidden;
}
.tl-hero-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.tl-hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(16, 24, 40, 0.86), rgba(37, 99, 235, 0.78));
}
.tl-hero-top {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
}
.tl-hero-back {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.tl-hero-title {
  font-size: 16px;
  font-weight: 600;
}
.tl-hero-stats {
  position: relative;
  display: flex;
  align-items: center;
  margin-top: 18px;
}
.tl-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}
.tl-stat-num {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}
.tl-stat-num.tl-danger { color: #fda29b; }
.tl-stat-num.tl-success { color: #75e0a7; }
.tl-stat-label {
  font-size: 11.5px;
  color: rgba(255, 255, 255, 0.82);
}
.tl-stat-divider {
  width: 1px;
  height: 26px;
  background: rgba(255, 255, 255, 0.24);
}

.tl-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 12px 24px;
  -webkit-overflow-scrolling: touch;
}
</style>
