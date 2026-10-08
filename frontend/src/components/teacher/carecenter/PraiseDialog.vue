<template>
  <el-dialog
    :model-value="modelValue"
    title="记录正向激励"
    :width="isMobile ? '94%' : '520px'"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="pr-form">
      <div class="pr-grid2">
        <div class="pr-field">
          <label class="pr-label">学生</label>
          <el-select v-model="form.student_id" filterable placeholder="选择学生" style="width:100%">
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
        <div class="pr-field">
          <label class="pr-label">日期</label>
          <el-date-picker v-model="form.occurred_on" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </div>
      </div>

      <div class="pr-field">
        <label class="pr-label">激励方式</label>
        <el-radio-group v-model="form.praise_type">
          <el-radio-button value="praise">表扬</el-radio-button>
          <el-radio-button value="badge">徽章</el-radio-button>
        </el-radio-group>
      </div>

      <div v-if="form.praise_type === 'badge'" class="pr-field">
        <label class="pr-label">徽章名称</label>
        <el-input v-model="form.badge_name" maxlength="50" placeholder="例如：进步之星 / 服务标兵" />
      </div>

      <div class="pr-field">
        <label class="pr-label">激励理由</label>
        <el-input v-model="form.reason" type="textarea" :rows="3" maxlength="400" show-word-limit
          placeholder="具体做了什么值得肯定，越具体越有力量……" />
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
import { createPraise, type PraiseType } from '@/api/careCenter'

const props = defineProps<{ modelValue: boolean; presetStudentId?: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const students = ref<StudentSummary[]>([])
const saving = ref(false)

const form = reactive<{
  student_id: number | undefined
  praise_type: PraiseType
  badge_name: string
  reason: string
  occurred_on: string
}>({
  student_id: undefined,
  praise_type: 'praise',
  badge_name: '',
  reason: '',
  occurred_on: new Date().toISOString().slice(0, 10),
})

const valid = computed(() => !!form.student_id && form.reason.trim().length > 0)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    form.student_id = props.presetStudentId ?? undefined
    form.praise_type = 'praise'
    form.badge_name = ''
    form.reason = ''
    form.occurred_on = new Date().toISOString().slice(0, 10)
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
    await createPraise({
      student_id: form.student_id,
      praise_type: form.praise_type,
      badge_name: form.praise_type === 'badge' ? form.badge_name.trim() || null : null,
      reason: form.reason.trim(),
      occurred_on: form.occurred_on || null,
    })
    ElMessage.success('已记录激励')
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
.pr-form { display: flex; flex-direction: column; gap: 16px; }
.pr-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}
.pr-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 767px) {
  .pr-grid2 { grid-template-columns: 1fr; }
}
</style>