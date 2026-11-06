<template>
  <!-- 添加待办（3 字段：移动端=底部动作面板） -->
  <ActionSheet
    v-model="visibleModel"
    title="添加待办"
    width="460px"
    class="schedule-dialog"
  >
    <div class="sd-sub" style="margin:-4px 0 10px">保存后会进入「我的待办」，到期当天出现在今日重点</div>

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
        保存待办
      </el-button>
    </template>
  </ActionSheet>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
// v6.1 弹窗减负：小表单走底部动作面板
import ActionSheet from '@/components/common/ActionSheet.vue'
import { createTeacherTask } from '@/api/teacherTask'
import type { ScheduleUrgency } from '@/api/teacher'
import { urgencyToPriority } from '@/utils/teacherPlan'
import { ElMessage } from 'element-plus'
import ScheduleFormFields from '@/components/teacher/schedule/ScheduleFormFields.vue'

// 添加待办弹窗（桌面日历点击日期、或周计划「去安排」触发）：
// 表单内容与父级共享（移动端添加待办子页使用同一状态）
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
    await createTeacherTask({
      title: props.content.trim(),
      due_at: props.date,
      priority: urgencyToPriority(props.urgency),
      source_type: 'manual',
    })
    ElMessage.success('待办已添加')
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