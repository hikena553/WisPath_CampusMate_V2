<template>
  <div v-loading="loading" class="tf-card">
    <div class="tf-head">
      <div class="tf-title">
        <el-icon class="tf-ic"><Sunrise /></el-icon>
        <span>今日重点</span>
        <span class="tf-title-sub">我的待办与待批事项</span>
      </div>
      <button class="tf-more" @click="emit('navigate', '/teacher/tasks')">
        全部任务<el-icon :size="12"><ArrowRight /></el-icon>
      </button>
    </div>

    <div class="tf-metrics">
      <button class="tf-metric" @click="emit('navigate', '/teacher/tasks?filter=overdue')">
        <span class="tf-num" :class="{ danger: summary.overdue > 0 }">{{ summary.overdue }}</span>
        <span class="tf-lb">逾期未办</span>
      </button>
      <button class="tf-metric" @click="emit('navigate', '/teacher/tasks?filter=today')">
        <span class="tf-num">{{ summary.today }}</span>
        <span class="tf-lb">今日到期</span>
      </button>
      <button class="tf-metric" @click="emit('navigate', '/teacher/approval')">
        <span class="tf-num" :class="{ warn: pendingLeaves.length > 0 }">{{ pendingLeaves.length }}</span>
        <span class="tf-lb">待批请假</span>
      </button>
    </div>

    <div class="tf-list">
      <div v-if="!loading && !rows.length" class="tf-empty">今天没有需要处理的事项</div>
      <button v-for="row in rows" :key="row.key" class="tf-item" @click="emit('navigate', row.link)">
        <span class="tf-tag" :class="`is-${row.kind}`">{{ row.tagText }}</span>
        <span class="tf-item-title">{{ row.title }}</span>
        <span v-if="row.sub" class="tf-item-sub">{{ row.sub }}</span>
        <el-icon :size="13" class="tf-arrow"><ArrowRight /></el-icon>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { ArrowRight, Sunrise } from '@element-plus/icons-vue'
import {
  getTeacherTaskSummary,
  getTeacherTasks,
  type TeacherTask,
  type TeacherTaskSummary,
} from '@/api/teacherTask'
import { getPendingLeaves } from '@/api/leave'
import type { LeaveRequestOut } from '@/types'

const emit = defineEmits<{ navigate: [path: string] }>()

const loading = ref(false)
const summary = ref<TeacherTaskSummary>({
  pending: 0,
  overdue: 0,
  today: 0,
  done_this_week: 0,
  total: 0,
})
const overdueTasks = ref<TeacherTask[]>([])
const todayTasks = ref<TeacherTask[]>([])
const pendingLeaves = ref<LeaveRequestOut[]>([])

interface FocusRow {
  kind: 'overdue' | 'today' | 'leave'
  key: string
  title: string
  sub: string
  link: string
  tagText: string
}

/** 逾期任务 → 今日任务 → 待批请假，按 id 去重后取前 5 条 */
const rows = computed<FocusRow[]>(() => {
  const out: FocusRow[] = []
  const seenTask = new Set<number>()
  for (const t of overdueTasks.value) {
    if (seenTask.has(t.id)) continue
    seenTask.add(t.id)
    out.push({
      kind: 'overdue',
      key: `t-${t.id}`,
      title: t.title,
      sub: t.student_name,
      link: `/teacher/tasks?filter=overdue&task=${t.id}`,
      tagText: '逾期',
    })
  }
  for (const t of todayTasks.value) {
    if (seenTask.has(t.id)) continue
    seenTask.add(t.id)
    out.push({
      kind: 'today',
      key: `t-${t.id}`,
      title: t.title,
      sub: t.student_name,
      link: `/teacher/tasks?filter=today&task=${t.id}`,
      tagText: '今日',
    })
  }
  const seenLeave = new Set<number>()
  for (const l of pendingLeaves.value.slice(0, 3)) {
    if (seenLeave.has(l.id)) continue
    seenLeave.add(l.id)
    out.push({
      kind: 'leave',
      key: `l-${l.id}`,
      title: `${l.student_name} 提交请假申请`,
      sub: `${l.start_date} ~ ${l.end_date}`,
      link: '/teacher/approval',
      tagText: '请假',
    })
  }
  return out.slice(0, 5)
})

async function load() {
  loading.value = true
  try {
    const [s, od, td, lv] = await Promise.allSettled([
      getTeacherTaskSummary(),
      getTeacherTasks({ due: 'overdue', limit: 5 }),
      getTeacherTasks({ due: 'today', limit: 5 }),
      getPendingLeaves(),
    ])
    if (s.status === 'fulfilled') summary.value = s.value
    if (od.status === 'fulfilled') overdueTasks.value = od.value
    if (td.status === 'fulfilled') todayTasks.value = td.value
    if (lv.status === 'fulfilled') pendingLeaves.value = lv.value
  } catch {
    // 首页卡片各自容错，单块失败不影响其它
  } finally {
    loading.value = false
  }
}

onMounted(load)
onActivated(load)
defineExpose({ reload: load })
</script>

<style scoped>
.tf-card {
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.tf-title {
  display: flex;
  align-items: baseline;
  gap: 7px;
  min-width: 0;
}
.tf-title > span:nth-child(2) {
  font-size: 14px;
  font-weight: 600;
  color: #101828;
}
.tf-ic {
  color: #2563eb;
  align-self: center;
}
.tf-title-sub {
  font-size: 12px;
  color: #98a2b3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tf-more {
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
  flex-shrink: 0;
}
.tf-more:hover { color: #2563eb; }

.tf-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.tf-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-start;
  background: #f9fafb;
  border: none;
  border-radius: 10px;
  padding: 9px 12px;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.tf-metric:hover { background: #f2f4f7; }
.tf-num {
  font-size: 20px;
  font-weight: 700;
  color: #101828;
  line-height: 1.15;
}
.tf-num.danger { color: #d92d20; }
.tf-num.warn { color: #b54708; }
.tf-lb {
  font-size: 11.5px;
  color: #98a2b3;
}

.tf-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.tf-empty {
  font-size: 12.5px;
  color: #98a2b3;
  padding: 6px 0;
}
.tf-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 9px;
  border-radius: 9px;
  background: #fcfcfd;
  border: 1px solid #f2f4f7;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.tf-item:hover { border-color: #d0d5dd; }
.tf-tag {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
  padding: 1px 7px;
  border-radius: 999px;
}
.tf-tag.is-overdue { background: #fef3f2; color: #d92d20; }
.tf-tag.is-today { background: #eff4ff; color: #1d4ed8; }
.tf-tag.is-leave { background: #fffaeb; color: #b54708; }
.tf-item-title {
  font-size: 12.5px;
  color: #344054;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tf-item-sub {
  font-size: 11.5px;
  color: #98a2b3;
  flex-shrink: 0;
}
.tf-arrow {
  margin-left: auto;
  color: #98a2b3;
  flex-shrink: 0;
}
</style>