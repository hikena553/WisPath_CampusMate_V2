<template>
  <div class="tt-card" :class="[`tt-${task.status}`, { 'tt-overdue': task.overdue }]">
    <!-- 左侧状态指示条 -->
    <div class="tt-rail" :class="`rail-${task.status}`"></div>

    <div class="tt-main">
      <!-- 头部：来源标签 + 逾期标记 -->
      <div class="tt-head">
        <span class="tt-source" :class="`src-${task.source_type}`">
          {{ TASK_SOURCE_LABEL[task.source_type] }}
        </span>
        <span v-if="task.overdue" class="tt-overdue-tag">
          <el-icon :size="11"><WarningFilled /></el-icon>已逾期
        </span>
        <span class="tt-spacer"></span>
        <span class="tt-status" :class="`st-${task.status}`">{{ TASK_STATUS_LABEL[task.status] }}</span>
      </div>

      <!-- 标题 -->
      <div class="tt-title" :class="{ 'tt-done-text': task.status === 'done' }">{{ task.title }}</div>

      <!-- 详情 -->
      <div v-if="task.detail" class="tt-detail">{{ task.detail }}</div>

      <!-- 元信息 -->
      <div class="tt-meta">
        <span v-if="task.student_name" class="tt-meta-item">
          <el-icon :size="12"><User /></el-icon>{{ task.student_name }}
        </span>
        <span v-if="task.due_at" class="tt-meta-item" :class="{ 'tt-due-overdue': task.overdue }">
          <el-icon :size="12"><Calendar /></el-icon>{{ dueText }}
        </span>
      </div>

      <!-- 操作区 -->
      <div class="tt-actions">
        <template v-if="task.status !== 'done'">
          <button
            v-if="task.status === 'pending'"
            class="tt-btn tt-btn-plain"
            @click="emit('update-status', task, 'contacted')"
          >标记已联系</button>
          <button
            v-if="task.status === 'pending' || task.status === 'contacted'"
            class="tt-btn tt-btn-care"
            @click="emit('record-care', task)"
          >记录关怀</button>
          <button class="tt-btn tt-btn-done" @click="emit('update-status', task, 'done')">办结</button>
        </template>
        <template v-else>
          <span class="tt-done-hint">
            <el-icon :size="12"><CircleCheckFilled /></el-icon>{{ doneText }}
          </span>
          <button class="tt-btn tt-btn-plain" @click="emit('update-status', task, 'pending')">重新打开</button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Calendar, CircleCheckFilled, User, WarningFilled } from '@element-plus/icons-vue'
import {
  TASK_SOURCE_LABEL,
  TASK_STATUS_LABEL,
  type TaskStatus,
  type TeacherTask,
} from '@/api/teacherTask'

const props = defineProps<{ task: TeacherTask }>()

const emit = defineEmits<{
  'update-status': [task: TeacherTask, status: TaskStatus]
  'record-care': [task: TeacherTask]
}>()

const dueText = computed(() => {
  if (!props.task.due_at) return ''
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(props.task.due_at)
  due.setHours(0, 0, 0, 0)
  const diff = Math.round((due.getTime() - today.getTime()) / 86400000)
  const md = `${due.getMonth() + 1}月${due.getDate()}日`
  if (diff === 0) return `今天 · ${md}`
  if (diff === 1) return `明天 · ${md}`
  if (diff < 0) return `已逾期 ${-diff} 天 · ${md}`
  return md
})

const doneText = computed(() => {
  if (!props.task.done_at) return '已办结'
  const d = new Date(props.task.done_at)
  return `${d.getMonth() + 1}月${d.getDate()}日办结`
})
</script>

<style scoped>
.tt-card {
  position: relative;
  display: flex;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.035);
  overflow: hidden;
}

.tt-card.tt-overdue {
  border-color: rgba(239, 68, 68, 0.28);
  box-shadow: 0 2px 12px rgba(239, 68, 68, 0.1);
}

.tt-rail {
  width: 4px;
  flex-shrink: 0;
  background: #cbd5e1;
}
.rail-pending { background: #3b82f6; }
.rail-contacted { background: #8b5cf6; }
.rail-cared { background: #10b981; }
.rail-done { background: #cbd5e1; }
.rail-expired { background: #94a3b8; }

.tt-main {
  flex: 1;
  min-width: 0;
  padding: 12px 14px 12px 12px;
}

.tt-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 7px;
}

.tt-source {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eff4ff;
  color: #2563eb;
  white-space: nowrap;
}
.src-ai_suggest { background: #f4f3ff; color: #6941c6; }
.src-follow_up { background: #ecfdf3; color: #067647; }
.src-approval { background: #fffaeb; color: #b54708; }
.src-alert { background: #fef3f2; color: #d92d20; }
.src-care_plan { background: #fdf2fa; color: #c11574; }
.src-manual { background: #f2f4f7; color: #475467; }

.tt-overdue-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 600;
  color: #dc2626;
}

.tt-spacer { flex: 1; }

.tt-status {
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.st-pending { color: #2563eb; }
.st-contacted { color: #7c3aed; }
.st-cared { color: #059669; }
.st-done { color: #98a2b3; }
.st-expired { color: #98a2b3; }

.tt-title {
  font-size: 14.5px;
  font-weight: 600;
  color: #101828;
  line-height: 1.45;
  word-break: break-word;
}
.tt-done-text {
  color: #98a2b3;
  text-decoration: line-through;
}

.tt-detail {
  margin-top: 4px;
  font-size: 12.5px;
  color: #667085;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tt-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
}
.tt-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: #98a2b3;
}
.tt-due-overdue { color: #dc2626; font-weight: 600; }

.tt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 11px;
}

.tt-btn {
  border: none;
  border-radius: 8px;
  padding: 6px 13px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
}
.tt-btn-plain { background: #f2f4f7; color: #475467; }
.tt-btn-care { background: #ecfdf3; color: #067647; }
.tt-btn-done { background: #2563eb; color: #fff; }
.tt-btn:active { opacity: 0.75; }

.tt-done-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  color: #98a2b3;
  margin-right: auto;
}
</style>
