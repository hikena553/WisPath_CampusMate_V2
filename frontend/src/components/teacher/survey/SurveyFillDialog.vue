<template>
  <el-dialog
    :model-value="modelValue"
    :title="survey?.title || '参与评价'"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    class="tui-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="survey" class="sf-form">
      <div class="tui-section-hint success">
        <el-icon><Lock /></el-icon>
        <span>本问卷完全匿名：系统不记录填写人，也不保存任何可回溯身份的信息；评分需逐项填写后才能提交。</span>
      </div>

      <div class="sf-ctx">
        <el-icon><Tickets /></el-icon>
        <span>{{ SURVEY_TARGET_LABEL[survey.target_type] }} · {{ survey.questions.length }} 个维度 · {{ survey.period || '未标注周期' }}</span>
      </div>

      <div class="sf-field">
        <label class="sf-label">评价对象</label>
        <el-select v-model="targetId" placeholder="选择被评价的辅导员" style="width: 100%">
          <el-option
            v-for="t in candidates"
            :key="t.id"
            :label="`${t.name}${t.college ? ' · ' + t.college : ''}`"
            :value="t.id"
          />
        </el-select>
      </div>

      <div class="sf-field">
        <label class="sf-label">评分<small>1–5 分，逐项必填</small></label>
        <div v-for="q in survey.questions" :key="q.key" class="sf-q">
          <span class="sf-q-label">{{ q.label }}</span>
          <el-rate v-model="scores[q.key]" :max="q.max || 5" />
        </div>
      </div>

      <AiDraftField
        v-model="suggestion"
        label="建议"
        :rows="3"
        :maxlength="300"
        placeholder="给这位老师一条建设性建议……"
        :draft="aiDraft"
        :points="aiPoints"
      />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!canSubmit" @click="submit">
        匿名提交
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Lock, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import { getTeachers } from '@/api/user'
import { submitSurvey, SURVEY_TARGET_LABEL, type PeerSurvey } from '@/api/peerSurvey'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'

const props = defineProps<{ modelValue: boolean; survey: PeerSurvey | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const auth = useAuthStore()

const teachers = ref<{ id: number; name: string; college?: string | null }[]>([])
const targetId = ref<number | undefined>(undefined)
const scores = reactive<Record<string, number>>({})
const suggestion = ref('')
const saving = ref(false)

/** 排除自己：不自评 */
const candidates = computed(() => teachers.value.filter((t) => t.id !== auth.user?.id))

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** AI 草稿：结合问卷评价类型 + 被评老师 + 日期，写成真实教师口吻的匿名建议 */
const aiDraft = computed(() => {
  const t = teachers.value.find((x) => x.id === targetId.value)
  const name = t?.name || '这位老师'
  const target = SURVEY_TARGET_LABEL[props.survey?.target_type ?? 'peer']
  return `${today()} 匿名反馈（${target}）：${name}老师日常对学生的情绪与诉求回应比较及时，沟通也较坦诚。建议继续保持陪伴投入，遇到突发情况及时留下书面记录、主动同步进展，便于家校与同事协同跟进。`
})
const aiPoints = ['课堂与陪伴投入', '沟通的及时性', '处事是否公正', '一条可改进的具体建议']

const canSubmit = computed(() => {
  if (!props.survey || !targetId.value) return false
  return props.survey.questions.every((q) => (scores[q.key] || 0) > 0)
})

async function loadTeachers() {
  try {
    teachers.value = await getTeachers()
  } catch {
    teachers.value = []
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    targetId.value = undefined
    suggestion.value = ''
    Object.keys(scores).forEach((k) => delete scores[k])
    if (!teachers.value.length) await loadTeachers()
  }
)

async function submit() {
  if (!props.survey || !targetId.value) return
  saving.value = true
  try {
    await submitSurvey(props.survey.id, {
      target_teacher_id: targetId.value,
      scores: { ...scores },
      suggestion: suggestion.value.trim() || null,
    })
    ElMessage.success('已匿名提交，感谢反馈')
    emit('update:modelValue', false)
    emit('saved')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '提交失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.sf-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sf-ctx {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 11px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
}
.sf-ctx .el-icon {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.sf-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 6px;
}
.sf-label small {
  font-size: 11px;
  font-weight: 400;
  color: var(--tui-text-quiet);
}
.sf-q {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 0;
  border-bottom: 1px solid var(--tui-border);
}
.sf-q:last-child {
  border-bottom: none;
}
.sf-q-label {
  font-size: 12.5px;
  color: var(--tui-text);
}
</style>