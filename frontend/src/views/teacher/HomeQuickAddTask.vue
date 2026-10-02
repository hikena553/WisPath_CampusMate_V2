<template>
  <div v-if="visible" class="quick-add-overlay" @click.self="emit('update:visible', false)">
    <div class="quick-add-popup">
      <div class="quick-add-title">添加任务</div>
      <div class="quick-add-date">{{ selectedTaskDate }}</div>
      <input
        ref="quickAddInputRef"
        v-model="quickTaskContent"
        class="quick-add-input"
        placeholder="输入任务内容..."
        maxlength="100"
        @keyup.enter="handleQuickAddTask"
      />
      <div class="quick-add-urgency">
        <button
          v-for="u in urgencyOptions" :key="u.value"
          class="urgency-opt"
          :class="{ active: quickTaskUrgency === u.value, [u.value]: true }"
          @click="quickTaskUrgency = u.value"
        >{{ u.label }}</button>
      </div>
      <div class="quick-add-actions">
        <button class="quick-add-cancel" @click="emit('update:visible', false)">取消</button>
        <button class="quick-add-submit" :disabled="!quickTaskContent.trim()" @click="handleQuickAddTask">添加</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { createTeacherSchedule } from '@/api/teacher'
import type { ScheduleUrgency } from '@/api/teacher'
import { ElMessage } from 'element-plus'

// 快捷添加任务弹窗：由 HomeMobileTodayTasks 的 @open-quick-add 触发，成功后通知父级刷新当月数据
const props = defineProps<{
  visible: boolean
  selectedTaskDate: string
  urgencyOptions: { value: ScheduleUrgency; label: string }[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  added: [date: string]
}>()

const quickTaskContent = ref('')
const quickTaskUrgency = ref<ScheduleUrgency>('normal')
const quickAddInputRef = ref<HTMLInputElement>()

// 每次打开时重置表单并聚焦输入框
watch(() => props.visible, (open) => {
  if (open) {
    quickTaskContent.value = ''
    quickTaskUrgency.value = 'normal'
    nextTick(() => {
      quickAddInputRef.value?.focus()
    })
  }
})

// 快速添加任务（弹窗）
async function handleQuickAddTask() {
  if (!quickTaskContent.value.trim()) return
  try {
    await createTeacherSchedule(props.selectedTaskDate, quickTaskContent.value.trim(), quickTaskUrgency.value)
    ElMessage.success('任务已添加')
    quickTaskContent.value = ''
    quickTaskUrgency.value = 'normal'
    emit('update:visible', false)
    emit('added', props.selectedTaskDate)
  } catch {
    ElMessage.error('添加失败')
  }
}
</script>

<style scoped>
/* 快捷添加任务弹窗 */
.quick-add-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 2100;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
}
.quick-add-popup {
  width: 280px;
  padding: 20px 16px 16px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}
.quick-add-title {
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}
.quick-add-date {
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  margin: 6px 0 14px;
}
.quick-add-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f9fafb;
  padding: 10px 12px;
  font-size: 14px;
  color: #1f2937;
  outline: none;
}
.quick-add-input:focus {
  border-color: #3b82f6;
  background: #fff;
}
.quick-add-input::placeholder {
  color: #c0c4cc;
}
.quick-add-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}
.quick-add-cancel {
  flex: 1;
  padding: 9px 0;
  border: none;
  border-radius: 8px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
}
.quick-add-submit {
  flex: 1;
  padding: 9px 0;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
.quick-add-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.quick-add-urgency {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.urgency-opt {
  flex: 1;
  padding: 7px 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
}
.urgency-opt.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}
.urgency-opt.active.important {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #b45309;
}
.urgency-opt.active.urgent {
  border-color: #ef4444;
  background: #fef2f2;
  color: #dc2626;
}
</style>