<template>
  <el-dialog
    :model-value="modelValue"
    title="发起问卷"
    :width="isMobile ? '94%' : '600px'"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="sc-form">
      <div class="sc-field">
        <label class="sc-label">问卷标题</label>
        <el-input v-model="form.title" maxlength="200" placeholder="例如：2026 春季辅导员互评" />
      </div>

      <div class="sc-grid2">
        <div class="sc-field">
          <label class="sc-label">评价类型</label>
          <el-radio-group v-model="form.target_type">
            <el-radio-button value="peer">辅导员互评</el-radio-button>
            <el-radio-button value="student">学生评辅导员</el-radio-button>
          </el-radio-group>
        </div>
        <div class="sc-field">
          <label class="sc-label">周期</label>
          <el-input v-model="form.period" placeholder="如 2026-spring，可留空" />
        </div>
      </div>

      <div class="sc-field">
        <label class="sc-label">
          评价维度
          <small>建议 3–6 项，评分 1–5 分</small>
        </label>
        <div v-for="(q, i) in form.questions" :key="i" class="sc-q">
          <el-input v-model="q.label" placeholder="维度名称，如：关心学生" class="sc-q-label" />
          <el-input v-model="q.key" placeholder="键名，如 care" class="sc-q-key" />
          <el-button text circle type="danger" :disabled="form.questions.length <= 1" @click="removeQ(i)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button size="small" round :icon="Plus" @click="addQ">添加维度</el-button>
      </div>

      <div class="sc-field">
        <label class="sc-label">发布状态</label>
        <el-radio-group v-model="form.status">
          <el-radio-button value="draft">存为草稿</el-radio-button>
          <el-radio-button value="open">立即开放</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!valid" @click="submit">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createSurvey,
  DEFAULT_SURVEY_QUESTIONS,
  type SurveyQuestion,
  type SurveyStatus,
  type SurveyTargetType,
} from '@/api/peerSurvey'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; created: [] }>()

const { isMobile } = useResponsive()

const form = reactive<{
  title: string
  target_type: SurveyTargetType
  period: string
  status: SurveyStatus
  questions: SurveyQuestion[]
}>({
  title: '',
  target_type: 'peer',
  period: '',
  status: 'open',
  questions: [],
})

const saving = ref(false)

const valid = computed(
  () =>
    form.title.trim().length > 0 &&
    form.questions.length > 0 &&
    form.questions.every((q) => q.label.trim() && q.key.trim())
)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.title = ''
    form.target_type = 'peer'
    form.period = ''
    form.status = 'open'
    form.questions = DEFAULT_SURVEY_QUESTIONS.map((q) => ({ ...q }))
  }
)

function addQ() {
  form.questions.push({ key: '', label: '', max: 5 })
}
function removeQ(i: number) {
  form.questions.splice(i, 1)
}

async function submit() {
  if (!valid.value) return
  saving.value = true
  try {
    await createSurvey({
      title: form.title.trim(),
      target_type: form.target_type,
      period: form.period.trim() || null,
      questions: form.questions.map((q) => ({ key: q.key.trim(), label: q.label.trim(), max: q.max || 5 })),
      status: form.status,
    })
    ElMessage.success(form.status === 'open' ? '问卷已开放' : '草稿已保存')
    emit('update:modelValue', false)
    emit('created')
  } catch {
    ElMessage.error('创建失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.sc-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.sc-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}
.sc-label small {
  font-size: 11px;
  font-weight: 400;
  color: #98a2b3;
}
.sc-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.sc-q {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.sc-q-label { flex: 1; }
.sc-q-key { flex: 0 0 30%; }
@media (max-width: 767px) {
  .sc-grid2 { grid-template-columns: 1fr; }
  .sc-q-key { flex: 0 0 34%; }
}
</style>