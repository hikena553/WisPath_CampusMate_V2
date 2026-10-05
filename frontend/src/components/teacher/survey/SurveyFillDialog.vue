<template>
  <el-dialog
    :model-value="modelValue"
    :title="survey?.title || '参与评价'"
    :width="isMobile ? '94%' : '560px'"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="survey" class="sf-form">
      <div class="sf-note">
        <el-icon><Lock /></el-icon>
        <span>本问卷完全匿名：系统不记录填写人，也不保存任何可回溯身份的信息</span>
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
        <label class="sf-label">评分</label>
        <div v-for="q in survey.questions" :key="q.key" class="sf-q">
          <span class="sf-q-label">{{ q.label }}</span>
          <el-rate v-model="scores[q.key]" :max="q.max || 5" />
        </div>
      </div>

      <div class="sf-field">
        <label class="sf-label">
          建议
          <small>选填，匿名展示</small>
        </label>
        <el-input
          v-model="suggestion"
          type="textarea"
          :rows="3"
          maxlength="300"
          show-word-limit
          placeholder="给这位老师一条建设性建议……"
        />
      </div>
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
import { Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import { getTeachers } from '@/api/user'
import { submitSurvey, type PeerSurvey } from '@/api/peerSurvey'

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
  gap: 16px;
}
.sf-note {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  color: #079455;
  background: #ecfdf3;
  border-radius: 10px;
  padding: 9px 12px;
}
.sf-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}
.sf-label small {
  font-size: 11px;
  font-weight: 400;
  color: #98a2b3;
}
.sf-q {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid #f2f4f7;
}
.sf-q:last-child {
  border-bottom: none;
}
.sf-q-label {
  font-size: 13px;
  color: #344054;
}
</style>