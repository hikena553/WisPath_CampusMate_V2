<template>
  <div class="tt-card" :class="[`is-${priority}`, { 'tt-overdue': task.overdue, 'tt-done': task.status === 'done' }]">
    <!-- 左侧优先级色条：由任务 priority 驱动（高=红 / 中=橙 / 低=蓝） -->
    <span class="tt-rail" :class="`is-${priority}`"></span>

    <div class="tt-main">
      <!-- 头部：勾选框 + 来源标签 + 优先级 + 逾期/提醒标记 + 状态 -->
      <div class="tt-head">
        <button
          class="tt-check"
          type="button"
          :class="{ checked: task.status === 'done' }"
          :aria-pressed="task.status === 'done'"
          :aria-label="task.status === 'done' ? '取消办结' : '勾选办结'"
          @click="toggleDone"
        >
          <el-icon v-if="task.status === 'done'"><Check /></el-icon>
        </button>
        <span class="tt-priority" :class="`pri-${priority}`">{{ TASK_PRIORITY_LABEL[priority] }}</span>
        <span class="tt-source" :class="`src-${task.source_type}`">
          {{ TASK_SOURCE_LABEL[task.source_type] }}
        </span>
        <span v-if="task.rule_code" class="tt-rule">
          <el-icon :size="11"><MagicStick /></el-icon>{{ taskRuleLabel(task.rule_code) }}
        </span>
        <span v-if="task.overdue" class="tt-overdue-tag">
          <el-icon :size="11"><WarningFilled /></el-icon>已逾期
        </span>
        <span v-else-if="task.remind_due && task.status !== 'done'" class="tt-remind-tag">
          <el-icon :size="11"><Bell /></el-icon>今日提醒
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
        <span v-if="task.remind_at" class="tt-meta-item" :class="{ 'tt-due-overdue': task.remind_due && task.status !== 'done' }">
          <el-icon :size="12"><Bell /></el-icon>{{ remindText }}
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
        <button class="tt-btn tt-btn-ghost" @click="emit('edit', task)">编辑</button>
        <button class="tt-btn tt-btn-ghost is-danger" @click="emit('delete', task)">删除</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Bell, Calendar, Check, CircleCheckFilled, MagicStick, User, WarningFilled } from '@element-plus/icons-vue'
import {
  TASK_PRIORITY_LABEL,
  TASK_SOURCE_LABEL,
  TASK_STATUS_LABEL,
  taskRuleLabel,
  type TaskPriority,
  type TaskStatus,
  type TeacherTask,
} from '@/api/teacherTask'

const props = defineProps<{ task: TeacherTask }>()

const emit = defineEmits<{
  'update-status': [task: TeacherTask, status: TaskStatus]
  'record-care': [task: TeacherTask]
  'toggle-done': [task: TeacherTask, done: boolean]
  edit: [task: TeacherTask]
  delete: [task: TeacherTask]
}>()

/** 优先级：由后端字段驱动（缺省按中优先级兜底） */
const priority = computed<TaskPriority>(() => props.task.priority || 'mid')

function toggleDone() {
  emit('toggle-done', props.task, props.task.status !== 'done')
}

/** 提醒日文案：今天/明天/已到提醒日/具体日期 */
const remindText = computed(() => {
  if (!props.task.remind_at) return ''
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(props.task.remind_at)
  target.setHours(0, 0, 0, 0)
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000)
  const md = `${target.getMonth() + 1}月${target.getDate()}日`
  if (diff === 0) return `提醒 · 今天`
  if (diff === 1) return `提醒 · 明天`
  if (diff < 0) return `提醒已到 · ${md}`
  return `提醒 · ${md}`
})

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
  background: var(--tui-surface);
  border-radius: var(--tui-radius-sm);
  border: 1px solid var(--tui-border);
  box-shadow: var(--tui-shadow-1);
  overflow: hidden;
}

.tt-card.tt-overdue {
  border-color: var(--tui-danger-soft);
}

.tt-rail {
  width: 4px;
  flex-shrink: 0;
  background: var(--tui-border-strong);
}
.tt-rail.is-high { background: var(--tui-danger); }
.tt-rail.is-mid { background: var(--tui-warn); }
.tt-rail.is-low { background: var(--tui-brand); }
.tt-card.tt-done .tt-rail { background: var(--tui-border-strong); }

.tt-main {
  flex: 1;
  min-width: 0;
  padding: 10px 12px 10px 10px;
}

.tt-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

/* 勾选框：勾选即办结 */
.tt-check {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 6px;
  border: 1.5px solid var(--tui-border-strong);
  background: var(--tui-surface);
  color: var(--tui-surface);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}
.tt-check .el-icon { font-size: 12px; }
.tt-check.checked {
  background: var(--tui-success);
  border-color: var(--tui-success);
}

.tt-source {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  white-space: nowrap;
}
.src-ai_suggest { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.src-follow_up { background: var(--tui-success-soft); color: var(--tui-success); }
.src-approval { background: var(--tui-warn-soft); color: var(--tui-warn); }
.src-alert { background: var(--tui-danger-soft); color: var(--tui-danger); }
.src-care_plan { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.src-manual { background: var(--tui-surface-muted); color: var(--tui-text-tertiary); }

/* 优先级标签：与左侧色条同源配色 */
.tt-priority {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}
.pri-high { background: var(--tui-danger-soft); color: var(--tui-danger); }
.pri-mid { background: var(--tui-warn-soft); color: var(--tui-warn); }
.pri-low { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.tt-done .tt-priority { background: var(--tui-surface-muted); color: var(--tui-text-tertiary); }

/* 今日提醒标签 */
.tt-remind-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--tui-warn);
}

/* 预警规则标签（learning_alert pipeline 生成的任务） */
.tt-rule {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--tui-warn-soft);
  color: var(--tui-warn);
  white-space: nowrap;
}

.tt-overdue-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--tui-danger);
}

.tt-spacer { flex: 1; }

.tt-status {
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.st-pending { color: var(--tui-brand-strong); }
.st-contacted { color: var(--tui-brand-strong); }
.st-cared { color: var(--tui-success); }
.st-done { color: var(--tui-text-quiet); }
.st-expired { color: var(--tui-text-quiet); }

.tt-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tui-text);
  line-height: 1.45;
  word-break: break-word;
}
.tt-done-text {
  color: var(--tui-text-quiet);
  text-decoration: line-through;
}

.tt-detail {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--tui-text-secondary);
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
  margin-top: 7px;
}
.tt-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.tt-due-overdue { color: var(--tui-danger); font-weight: 600; }

.tt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 9px;
}

.tt-btn {
  border: none;
  border-radius: 8px;
  padding: 5px 12px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
}
.tt-btn-plain { background: var(--tui-surface-sunken); color: var(--tui-text-secondary); }
.tt-btn-care { background: var(--tui-success-soft); color: var(--tui-success); }
.tt-btn-done { background: var(--tui-brand); color: var(--tui-surface); }
/* 编辑/删除：无底色文字按钮，与主操作区分，避免操作区视觉噪音 */
.tt-btn-ghost { background: transparent; color: var(--tui-text-tertiary); padding: 5px 6px; }
.tt-btn-ghost:hover { background: var(--tui-surface-muted); color: var(--tui-text); }
.tt-btn-ghost.is-danger:hover { background: var(--tui-danger-soft); color: var(--tui-danger); }
.tt-btn:active { opacity: 0.75; }

.tt-done-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  color: var(--tui-text-quiet);
  margin-right: auto;
}
</style>