<template>
  <ResponsivePopup
    :model-value="modelValue"
    title="记录正向激励"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    destroy-on-close
    class="tui-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="pr-form">
      <div class="tui-section-hint success">
        <el-icon><InfoFilled /></el-icon>
        <span>激励会展示给学生，成为正向反馈；理由写得越具体，激励越有力量。</span>
      </div>

      <!-- 上下文信息条 -->
      <div class="pr-ctx">
        <el-icon><User /></el-icon>
        <span v-if="selectedStudent">
          激励对象：<b>{{ selectedStudent.name }}</b>
          <template v-if="selectedStudent.college"> · {{ selectedStudent.college }}</template>
          <template v-if="selectedStudent.crisis_level"> · 预警等级 {{ selectedStudent.crisis_level }}</template>
        </span>
        <span v-else>请先选择学生：激励会写入该生的正向反馈记录并展示给学生。</span>
      </div>

      <div class="pr-grid2">
        <div class="pr-field">
          <label class="pr-label">学生</label>
          <el-select v-model="form.student_id" filterable placeholder="选择学生" style="width:100%">
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
        <div class="pr-field">
          <label class="pr-label">日期</label>
          <el-date-picker
            v-model="form.occurred_on"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width:100%"
          />
        </div>
      </div>

      <div class="pr-field">
        <label class="pr-label">激励方式</label>
        <el-select v-model="form.praise_type" placeholder="请选择激励方式" style="width:100%">
          <el-option
            v-for="t in praiseTypeOptions"
            :key="t"
            :label="PRAISE_TYPE_LABEL[t]"
            :value="t"
          />
        </el-select>
      </div>

      <div v-if="form.praise_type === 'badge'" class="pr-field">
        <label class="pr-label">徽章名称</label>
        <el-input v-model="form.badge_name" maxlength="50" placeholder="例如：进步之星 / 服务标兵" />
      </div>

      <AiDraftField
        v-model="form.reason"
        label="激励理由"
        required
        :rows="3"
        :maxlength="400"
        placeholder="具体做了什么值得肯定，越具体越有力量……"
        :draft="aiDraft"
        :points="aiPoints"
      />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!valid" @click="submit">保存</el-button>
    </template>
  </ResponsivePopup>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
// v6.1 弹窗减负：移动端弹窗改用全屏子页承接（桌面端仍为 el-dialog）
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { InfoFilled, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
import { getStudents, type StudentSummary } from '@/api/teacher'
import { createPraise, PRAISE_TYPE_LABEL, type PraiseType } from '@/api/careCenter'

const props = defineProps<{ modelValue: boolean; presetStudentId?: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const praiseTypeOptions: PraiseType[] = ['praise', 'badge']
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

/** 已选学生（上下文信息条与 AI 草稿共用） */
const selectedStudent = computed(
  () => students.value.find((s) => s.id === form.student_id) || null
)

/** AI 草稿：结合激励方式（含徽章名）+ 学生姓名 + 日期 */
const aiDraft = computed(() => {
  const d = form.occurred_on
  const n = selectedStudent.value?.name || '该生'
  if (form.praise_type === 'badge') {
    const badge = form.badge_name.trim() || '进步之星'
    return `${d}，为${n}颁发「${badge}」徽章。今天${n}主动帮助同学并认真完成了任务，展现出责任心与互助精神，值得全班同学学习。希望这份肯定能让${n}更有信心，也带动更多同学一起进步。`
  }
  return `${d}，特别表扬${n}。今天${n}在课堂/活动中表现突出，主动承担、认真投入，让大家看到了其努力与闪光点。希望这份肯定能让${n}继续保持，把这份认真带到更多的事情上。`
})

/** AI 建议要点 */
const aiPoints = computed<string[]>(() => [
  '值得肯定的具体行为',
  '对集体/他人的正向影响',
  '对学生的鼓励话语',
  '期望与后续关注',
])

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
.pr-form { display: flex; flex-direction: column; gap: 12px; }
.pr-form .tui-section-hint { margin-bottom: 0; }

.pr-ctx {
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
.pr-ctx .el-icon { flex-shrink: 0; color: var(--tui-text-tertiary); }
.pr-ctx b { color: var(--tui-text); font-weight: 600; }

.pr-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 8px;
}
.pr-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 767px) {
  .pr-grid2 { grid-template-columns: 1fr; }
}
</style>