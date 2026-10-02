<template>
  <el-dialog v-model="visibleModel" title="添加日程" width="400px">
    <p style="margin-bottom:12px;color:#666">日期：<strong>{{ date }}</strong></p>
    <el-form ref="scheduleFormRef" :model="{ content: contentModel }" :rules="scheduleRules">
      <el-form-item prop="content">
        <el-input v-model="contentModel" type="textarea" :rows="3" placeholder="请输入日程内容，如：期中考试监考" />
      </el-form-item>
      <el-form-item label="等级">
        <el-radio-group v-model="urgencyModel">
          <el-radio value="normal">普通</el-radio>
          <el-radio value="important">重要</el-radio>
          <el-radio value="urgent">紧急</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visibleModel = false">取消</el-button>
      <el-button type="primary" @click="handleAddSchedule">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { createTeacherSchedule } from '@/api/teacher'
import type { ScheduleUrgency } from '@/api/teacher'
import { ElMessage } from 'element-plus'

// 添加日程弹窗（桌面日历点击日期触发）：表单内容与父级共享（移动端添加日程子页使用同一状态）
const props = defineProps<{
  visible: boolean
  date: string
  content: string
  urgency: ScheduleUrgency
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:content': [value: string]
  'update:urgency': [value: ScheduleUrgency]
  added: []
}>()

const scheduleFormRef = ref<any>()
const scheduleRules = {
  content: [{ required: true, message: '请输入日程内容', trigger: 'blur' }],
}

const visibleModel = computed({
  get: () => props.visible,
  set: (v: boolean) => emit('update:visible', v),
})
const contentModel = computed({
  get: () => props.content,
  set: (v: string) => emit('update:content', v),
})
const urgencyModel = computed({
  get: () => props.urgency,
  set: (v: ScheduleUrgency) => emit('update:urgency', v),
})

async function handleAddSchedule() {
  if (scheduleFormRef.value) {
    try { await scheduleFormRef.value.validate() } catch { return }
  }
  try {
    await createTeacherSchedule(props.date, props.content, props.urgency)
    ElMessage.success('日程已添加')
    visibleModel.value = false
    emit('update:urgency', 'normal')
    emit('added')
  } catch { ElMessage.error('添加失败') }
}
</script>