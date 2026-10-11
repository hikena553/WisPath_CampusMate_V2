<template>
  <el-dialog
    v-model="visibleModel"
    width="460px"
    align-center
    :close-on-click-modal="false"
    class="schedule-dialog"
  >
    <template #header>
      <div class="sd-header">
        <span class="sd-title">添加日程</span>
        <span class="sd-sub">写下要安排的事，到期后会出现在今日重点</span>
      </div>
    </template>

    <ScheduleFormFields
      :date="date"
      :content="content"
      :urgency="urgency"
      @update:date="emit('update:date', $event)"
      @update:content="emit('update:content', $event)"
      @update:urgency="emit('update:urgency', $event)"
    />

    <template #footer>
      <el-button @click="visibleModel = false">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!content.trim()" @click="handleAddSchedule">
        保存日程
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { createTeacherSchedule } from '@/api/teacher'
import type { ScheduleUrgency } from '@/api/teacher'
import { ElMessage } from 'element-plus'
import ScheduleFormFields from '@/components/teacher/schedule/ScheduleFormFields.vue'

// 添加日程弹窗（桌面日历点击日期、或周计划「去安排」触发）：
// 表单内容与父级共享（移动端添加日程子页使用同一状态）
const props = defineProps<{
  visible: boolean
  date: string
  content: string
  urgency: ScheduleUrgency
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:date': [value: string]
  'update:content': [value: string]
  'update:urgency': [value: ScheduleUrgency]
  added: []
}>()

const saving = ref(false)

const visibleModel = computed({
  get: () => props.visible,
  set: (v: boolean) => emit('update:visible', v),
})

async function handleAddSchedule() {
  if (!props.content.trim() || !props.date) return
  saving.value = true
  try {
    await createTeacherSchedule(props.date, props.content.trim(), props.urgency)
    ElMessage.success('日程已添加')
    visibleModel.value = false
    emit('update:urgency', 'normal')
    emit('added')
  } catch {
    ElMessage.error('添加失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
:deep(.schedule-dialog .el-dialog) {
  border-radius: 16px;
  overflow: hidden;
}
:deep(.schedule-dialog .el-dialog__header) {
  margin-right: 0;
  padding: 18px 20px 4px;
}
:deep(.schedule-dialog .el-dialog__body) {
  padding: 12px 20px 4px;
}
:deep(.schedule-dialog .el-dialog__footer) {
  padding: 12px 20px 18px;
}
:deep(.schedule-dialog .el-dialog__footer .el-button) {
  border-radius: 999px;
  padding: 8px 20px;
}
</style>

<style scoped>
.sd-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sd-title {
  font-size: 16px;
  font-weight: 600;
  color: #101828;
}
.sd-sub {
  font-size: 12px;
  color: #98a2b3;
}
</style>