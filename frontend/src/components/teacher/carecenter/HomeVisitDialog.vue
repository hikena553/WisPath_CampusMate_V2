<template>
  <el-dialog
    :model-value="modelValue"
    title="新增家访记录"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    destroy-on-close
    class="tui-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="hv-form">
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>记录后进入「家访时间轴」；填写「后续计划」的事项会自动进入关怀中心的待回访提醒。</span>
      </div>

      <!-- 上下文信息条 -->
      <div class="hv-ctx">
        <el-icon><User /></el-icon>
        <span v-if="selectedStudent">
          家访对象：<b>{{ selectedStudent.name }}</b>
          <template v-if="selectedStudent.college"> · {{ selectedStudent.college }}</template>
          <template v-if="selectedStudent.crisis_level"> · 预警等级 {{ selectedStudent.crisis_level }}</template>
        </span>
        <span v-else>请先选择学生：家访记录会归入该生成长档案并计入家访台账。</span>
      </div>

      <div class="hv-grid2">
        <div class="hv-field">
          <label class="hv-label">学生</label>
          <el-select v-model="form.student_id" filterable placeholder="选择学生" style="width:100%">
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
        <div class="hv-field">
          <label class="hv-label">日期</label>
          <el-date-picker
            v-model="form.visit_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width:100%"
          />
        </div>
      </div>

      <div class="hv-field">
        <label class="hv-label">沟通方式</label>
        <el-select v-model="form.method" placeholder="请选择沟通方式" style="width:100%">
          <el-option v-for="m in methodOptions" :key="m" :label="VISIT_METHOD_LABEL[m]" :value="m" />
        </el-select>
      </div>

      <AiDraftField
        v-model="form.content"
        label="沟通内容"
        required
        :rows="4"
        :maxlength="600"
        placeholder="家长反馈、学生在校表现、达成的共识……"
        :draft="aiDraft"
        :points="aiPoints"
      />

      <div class="hv-field">
        <label class="hv-label">后续计划</label>
        <el-input v-model="form.follow_up" type="textarea" :rows="2" maxlength="300" show-word-limit
          placeholder="下一步要跟进什么（选填），例如：两周后电话回访家长" />
      </div>

      <div class="hv-sync">
        <div class="hv-sync-text">
          <span class="hv-sync-title">同步到家校沟通台账</span>
          <span class="hv-sync-desc">开启后，本次家访会以「日常关怀」场景写入家校沟通台账，便于统一留痕。</span>
        </div>
        <el-switch v-model="form.sync_to_guardian" />
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
import { InfoFilled, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
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
  sync_to_guardian: boolean
}>({
  student_id: undefined,
  visit_date: new Date().toISOString().slice(0, 10),
  method: 'phone',
  content: '',
  follow_up: '',
  sync_to_guardian: true,
})

const valid = computed(() => !!form.student_id && !!form.visit_date && form.content.trim().length > 0)

/** 已选学生（上下文信息条与 AI 草稿共用） */
const selectedStudent = computed(
  () => students.value.find((s) => s.id === form.student_id) || null
)

/** AI 草稿：结合沟通方式 + 学生姓名 + 日期 */
const aiDraft = computed(() => {
  const d = form.visit_date
  const n = selectedStudent.value?.name || '该生'
  const m = VISIT_METHOD_LABEL[form.method]
  return `${d}，通过${m}与${n}的家长进行了沟通。向家长反馈了${n}近期在校的学习与情绪状态，说明其表现与需要关注的地方；家长也介绍了孩子在家的情况与顾虑。双方就共同配合的方向达成共识，家长表示会继续支持与督促。`
})

/** AI 建议要点 */
const aiPoints = computed<string[]>(() => [
  '沟通方式与对象',
  '学生在校表现',
  '家长反馈与顾虑',
  '达成的共识',
  '后续跟进计划',
])

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    form.student_id = props.presetStudentId ?? undefined
    form.visit_date = new Date().toISOString().slice(0, 10)
    form.method = 'phone'
    form.content = ''
    form.follow_up = ''
    form.sync_to_guardian = true
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
      sync_to_guardian: form.sync_to_guardian,
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
.hv-form { display: flex; flex-direction: column; gap: 12px; }
.hv-form .tui-section-hint { margin-bottom: 0; }

.hv-ctx {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 9px;
  background: var(--tui-surface-muted);
  color: var(--tui-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.hv-ctx .el-icon { flex-shrink: 0; color: var(--tui-text-tertiary); }
.hv-ctx b { color: var(--tui-text); font-weight: 600; }

.hv-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 8px;
}
.hv-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.hv-sync {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 11px;
  border-radius: 9px;
  background: var(--tui-surface-muted);
  border: 1px solid var(--tui-border);
}
.hv-sync-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.hv-sync-title { font-size: 12.5px; font-weight: 600; color: var(--tui-text-secondary); }
.hv-sync-desc { font-size: 11px; line-height: 1.5; color: var(--tui-text-quiet); }
.hv-sync :deep(.el-switch) { flex-shrink: 0; }
@media (max-width: 767px) {
  .hv-grid2 { grid-template-columns: 1fr; }
}
</style>