<template>
  <el-dialog
    :model-value="modelValue"
    title="新增关怀事项"
    :width="isMobile ? '94%' : '520px'"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="ce-form">
      <div class="ce-field">
        <label class="ce-label">事项类型</label>
        <el-radio-group v-model="form.event_type">
          <el-radio-button v-for="t in typeOptions" :key="t" :value="t">
            {{ CARE_EVENT_LABEL[t] }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="ce-grid2">
        <div class="ce-field">
          <label class="ce-label">日期</label>
          <el-date-picker v-model="form.event_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </div>
        <div class="ce-field">
          <label class="ce-label">关联学生</label>
          <el-select v-model="form.student_id" clearable filterable placeholder="可不选" style="width:100%">
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
      </div>

      <div class="ce-field">
        <label class="ce-label">标题</label>
        <el-input v-model="form.title" maxlength="200" placeholder="例如：给小王过生日" />
      </div>

      <div class="ce-field">
        <label class="ce-label">备注</label>
        <el-input v-model="form.note" type="textarea" :rows="3" maxlength="300" show-word-limit placeholder="准备事项、注意事项……" />
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
import { createCareEvent, CARE_EVENT_LABEL, type CareEventType } from '@/api/careCenter'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const typeOptions: CareEventType[] = ['birthday', 'difficulty', 'academic', 'other']

const students = ref<StudentSummary[]>([])
const saving = ref(false)

const form = reactive<{
  event_type: CareEventType
  event_date: string
  title: string
  note: string
  student_id: number | undefined
}>({
  event_type: 'other',
  event_date: new Date().toISOString().slice(0, 10),
  title: '',
  note: '',
  student_id: undefined,
})

const valid = computed(() => !!form.event_date && form.title.trim().length > 0)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    form.event_type = 'other'
    form.event_date = new Date().toISOString().slice(0, 10)
    form.title = ''
    form.note = ''
    form.student_id = undefined
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
  if (!valid.value) return
  saving.value = true
  try {
    await createCareEvent({
      event_type: form.event_type,
      event_date: form.event_date,
      title: form.title.trim(),
      note: form.note.trim() || null,
      student_id: form.student_id ?? null,
    })
    ElMessage.success('已添加关怀事项')
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
.ce-form { display: flex; flex-direction: column; gap: 16px; }
.ce-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}
.ce-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 767px) {
  .ce-grid2 { grid-template-columns: 1fr; }
}
</style>