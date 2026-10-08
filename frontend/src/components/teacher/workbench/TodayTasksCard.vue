<template>
  <div v-loading="loading" class="wb-card">
    <div class="wb-head">
      <div class="wb-title">
        <el-icon class="wb-ic"><List /></el-icon>
        <span>今日待办</span>
      </div>
      <button class="wb-more" @click="emit('open-tasks')">
        查看全部<el-icon :size="12"><ArrowRight /></el-icon>
      </button>
    </div>

    <div class="wb-stats">
      <div class="wb-stat">
        <span class="wb-num">{{ summary.today }}</span>
        <span class="wb-lb">今日到期</span>
      </div>
      <div class="wb-stat">
        <span class="wb-num danger">{{ summary.overdue }}</span>
        <span class="wb-lb">逾期未办</span>
      </div>
      <div class="wb-stat">
        <span class="wb-num ok">{{ summary.done_this_week }}</span>
        <span class="wb-lb">本周完成</span>
      </div>
    </div>

    <div class="wb-list">
      <div v-if="!loading && !tasks.length" class="wb-empty">今天没有到期的跟进任务</div>
      <div
        v-for="t in tasks"
        :key="t.id"
        class="wb-item"
        :class="{ 'is-overdue': t.overdue }"
        @click="emit('open-tasks')"
      >
        <span class="wb-dot" :class="t.status"></span>
        <span class="wb-item-title">{{ t.title }}</span>
        <span v-if="t.student_name" class="wb-item-sub">{{ t.student_name }}</span>
        <el-tag v-if="t.overdue" size="small" type="danger" effect="plain" round>逾期</el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'
import { ArrowRight, List } from '@element-plus/icons-vue'
import {
  getTeacherTaskSummary,
  getTeacherTasks,
  type TeacherTask,
  type TeacherTaskSummary,
} from '@/api/teacherTask'

const emit = defineEmits<{ 'open-tasks': [] }>()

const loading = ref(false)
const tasks = ref<TeacherTask[]>([])
const summary = ref<TeacherTaskSummary>({
  pending: 0,
  overdue: 0,
  today: 0,
  done_this_week: 0,
  total: 0,
})

async function load() {
  loading.value = true
  try {
    const [s, today, overdue] = await Promise.all([
      getTeacherTaskSummary(),
      getTeacherTasks({ due: 'today', limit: 20 }),
      getTeacherTasks({ due: 'overdue', limit: 20 }),
    ])
    summary.value = s
    // 今日到期在前、逾期在后，最多展示 4 条
    tasks.value = [...today, ...overdue.filter((o) => !today.some((t) => t.id === o.id))].slice(0, 4)
  } catch {
    // 首页组件各自容错，单块失败不影响其它卡片
  } finally {
    loading.value = false
  }
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
  gap: 14px;
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

.wb-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.wb-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: #f9fafb;
  border-radius: 10px;
  padding: 9px 10px;
}
.wb-num {
  font-size: 20px;
  font-weight: 700;
  color: #101828;
  line-height: 1.15;
}
.wb-num.danger { color: #d92d20; }
.wb-num.ok { color: #079455; }
.wb-lb {
  font-size: 11.5px;
  color: #98a2b3;
}

.wb-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.wb-empty {
  font-size: 12.5px;
  color: #98a2b3;
  padding: 6px 0;
}
.wb-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 9px;
  border-radius: 9px;
  background: #fcfcfd;
  border: 1px solid #f2f4f7;
  cursor: pointer;
}
.wb-item:hover { border-color: #d0d5dd; }
.wb-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #98a2b3;
  flex-shrink: 0;
}
.wb-dot.pending { background: #f79009; }
.wb-dot.contacted { background: #2563eb; }
.wb-dot.cared { background: #7c3aed; }
.wb-dot.done { background: #079455; }
.wb-dot.expired { background: #d0d5dd; }

.wb-item-title {
  font-size: 12.5px;
  color: #344054;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wb-item-sub {
  font-size: 11.5px;
  color: #98a2b3;
  flex-shrink: 0;
}
.wb-item .el-tag { margin-left: auto; flex-shrink: 0; }
</style>