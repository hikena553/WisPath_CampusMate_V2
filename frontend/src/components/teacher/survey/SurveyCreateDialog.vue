<template>
  <el-dialog
    :model-value="modelValue"
    title="发起问卷"
    :width="isMobile ? '90%' : '400px'"
    align-center
    :close-on-click-modal="false"
    class="tui-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>问卷匿名收集，只出聚合结果；建议设置 3–6 个维度，评分 1–5 分。</span>
    </div>
    <div class="sc-ctx">
      <el-icon><InfoFilled /></el-icon>
      <span>本次将发起「{{ SURVEY_TARGET_LABEL[form.target_type] }}」，周期 {{ form.period.trim() || '未填（可不填）' }}，匿名收集、不回溯个人。</span>
    </div>
    <div class="sc-form">
      <AiDraftField
        v-model="form.title"
        label="问卷标题"
        required
        :rows="2"
        :maxlength="200"
        placeholder="例如：2026 春季辅导员互评"
        :draft="aiDraft"
        :points="aiPoints"
      />

      <div class="sc-grid2">
        <div class="sc-field">
          <label class="sc-label">评价类型</label>
          <el-select v-model="form.target_type" style="width:100%">
            <el-option v-for="t in targetOptions" :key="t" :label="SURVEY_TARGET_LABEL[t]" :value="t" />
          </el-select>
        </div>
        <div class="sc-field">
          <label class="sc-label">周期</label>
          <el-select
            v-model="form.period"
            filterable
            allow-create
            default-first-option
            clearable
            placeholder="选择或输入周期"
            style="width:100%"
          >
            <el-option v-for="p in periodOptions" :key="p" :label="p" :value="p" />
          </el-select>
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
        <el-select v-model="form.status" style="width:100%">
          <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
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
import { Delete, InfoFilled, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createSurvey,
  DEFAULT_SURVEY_QUESTIONS,
  SURVEY_TARGET_LABEL,
  type SurveyQuestion,
  type SurveyStatus,
  type SurveyTargetType,
} from '@/api/peerSurvey'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; created: [] }>()

const { isMobile } = useResponsive()

const targetOptions: SurveyTargetType[] = ['peer', 'student']
const statusOptions: { value: SurveyStatus; label: string }[] = [
  { value: 'open', label: '立即开放' },
  { value: 'draft', label: '存为草稿' },
]

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

/** 周期候选：当前学年与上一学年，可再手动输入 */
const periodOptions = computed(() => {
  const y = new Date().getFullYear()
  return [`${y}-spring`, `${y}-fall`, `${y - 1}-fall`, `${y - 1}-spring`]
})

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** AI 草稿：结合所选评价类型 + 周期 + 日期，写成真实教师口吻的问卷主题 */
const aiDraft = computed(() => {
  const target = SURVEY_TARGET_LABEL[form.target_type]
  const period = form.period.trim() || '本学期'
  return `${period}${target}（${today()} 发起）：围绕关心学生、处事公正、沟通及时、工作负责四个维度匿名收集意见，评分 1–5 分，仅汇总聚合结果、不回溯个人，用于本周期工作改进参考。`
})
const aiPoints = computed(() => {
  const y = new Date().getFullYear()
  return [`${y} 春季学期`, `${SURVEY_TARGET_LABEL[form.target_type]}`, '匿名收集·仅出聚合结果']
})

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
  gap: 12px;
  margin-top: 10px;
}
.sc-ctx {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 11px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-brand-soft);
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--tui-brand-strong);
}
.sc-ctx .el-icon {
  flex-shrink: 0;
  margin-top: 1px;
  font-size: 12px;
}
.sc-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 6px;
}
.sc-label small {
  font-size: 11px;
  font-weight: 400;
  color: var(--tui-text-quiet);
}
.sc-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.sc-q {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.sc-q-label { flex: 1; }
.sc-q-key { flex: 0 0 30%; }
@media (max-width: 767px) {
  .sc-grid2 { grid-template-columns: 1fr; }
  .sc-q-key { flex: 0 0 34%; }
}
</style>