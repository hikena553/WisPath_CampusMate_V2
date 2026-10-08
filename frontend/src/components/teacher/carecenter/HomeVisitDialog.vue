<template>
  <el-dialog
    :model-value="modelValue"
    title="新增家访记录"
    :width="isMobile ? '94%' : '540px'"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="hv-form">
      <div class="hv-grid2">
        <div class="hv-field">
          <label class="hv-label">学生</label>
          <el-select v-model="form.student_id" filterable placeholder="选择学生" style="width:100%">
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
        <div class="hv-field">
          <label class="hv-label">日期</label>
          <el-date-picker v-model="form.visit_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </div>
      </div>

      <div class="hv-field">
        <label class="hv-label">沟通方式</label>
        <el-radio-group v-model="form.method">
          <el-radio-button v-for="m in methodOptions" :key="m" :value="m">
            {{ VISIT_METHOD_LABEL[m] }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="hv-field">
        <label class="hv-label">沟通内容</label>
        <el-input v-model="form.content" type="textarea" :rows="4" maxlength="600" show-word-limit
          placeholder="家长反馈、学生在校表现、达成的共识……" />
      </div>

      <div class="hv-field">
        <label class="hv-label">后续计划</label>
        <el-input v-model="form.follow_up" type="textarea" :rows="2" maxlength="300" show-word-limit
          placeholder="下一步要跟进什么（选填）" />
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!valid" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { getStudents, type StudentSummary } from '@/api/teacher'
import { createHomeVisit, VISIT_METHOD_LABEL, type HomeVisitMethod } from '@/api/careCenter'

const props = defineProps<{ modelValue: boolean; presetStudentId?: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const methodOptions: HomeVisitMethod[] = ['home', 'phone', 'video', 'school', 'other']
const students = ref<StudentSummary[]>([])
const saving = ref(false)

const form = reactive<{
  student_id: number | undefined
  visit_date: string
  method: HomeVisitMethod
  content: string
  follow_up: string
}>({
  student_id: undefined,
  visit_date: new Date().toISOString().slice(0, 10),
  method: 'phone',
  content: '',
  follow_up: '',
})

const valid = computed(() => !!form.student_id && !!form.visit_date && form.content.trim().length > 0)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    form.student_id = props.presetStudentId ?? undefined
    form.visit_date = new Date().toISOString().slice(0, 10)
    form.method = 'phone'
    form.content = ''
    form.follow_up = ''
    if (!students.value.length) {
      try {
        students.value = await getStudents()
      } catch {
        students.value = []
      }
    }
  }
)

async function submit() {
  if (!valid.value || !form.student_id) return
  saving.value = true
  try {
    await createHomeVisit({
      student_id: form.student_id,
      visit_date: form.visit_date,
      method: form.method,
      content: form.content.trim(),
      follow_up: form.follow_up.trim() || null,
    })
    ElMessage.success('已保存家访记录')
    emit('update:modelValue', false)
    emit('saved')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.hv-form { display: flex; flex-direction: column; gap: 16px; }
.hv-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}
.hv-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 767px) {
  .hv-grid2 { grid-template-columns: 1fr; }
}
</style>