<template>
  <ResponsivePopup
    :model-value="modelValue"
    title="新增关怀事项"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    destroy-on-close
    class="tui-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="ce-form">
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>将自动进入本月关怀日历；关联学生后可在其成长档案中看到这条关怀记录。</span>
      </div>

      <!-- 上下文信息条 -->
      <div class="ce-ctx">
        <el-icon><User /></el-icon>
        <span v-if="selectedStudent">
          关联对象：<b>{{ selectedStudent.name }}</b>
          <template v-if="selectedStudent.college"> · {{ selectedStudent.college }}</template>
          <template v-if="selectedStudent.crisis_level"> · 预警等级 {{ selectedStudent.crisis_level }}</template>
        </span>
        <span v-else>尚未关联学生：仅进入本月关怀日历，不写入任何学生档案。</span>
      </div>

      <div class="ce-grid2">
        <div class="ce-field">
          <label class="ce-label">事项类型</label>
          <el-select v-model="form.event_type" placeholder="请选择事项类型" style="width:100%">
            <el-option
              v-for="t in typeOptions"
              :key="t"
              :label="CARE_EVENT_LABEL[t]"
              :value="t"
            />
          </el-select>
        </div>
        <div class="ce-field">
          <label class="ce-label">日期</label>
          <el-date-picker
            v-model="form.event_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width:100%"
          />
        </div>
      </div>

      <div class="ce-field">
        <label class="ce-label">关联学生</label>
        <el-select v-model="form.student_id" clearable filterable placeholder="可不选" style="width:100%">
          <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </div>

      <div class="ce-field">
        <label class="ce-label">标题</label>
        <el-input v-model="form.title" maxlength="200" placeholder="例如：给小王过生日 / 学业预警跟进" />
      </div>

      <AiDraftField
        v-model="form.note"
        label="事项备注"
        :rows="3"
        :maxlength="300"
        placeholder="准备事项、注意事项、后续安排……"
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

/** 已选学生（用于上下文信息条与 AI 草稿） */
const selectedStudent = computed(
  () => students.value.find((s) => s.id === form.student_id) || null
)
const who = computed(() => selectedStudent.value?.name || '相关学生')

/** AI 草稿：结合所选类型 + 学生姓名 + 日期 */
const aiDraft = computed(() => {
  const d = form.event_date
  const n = who.value
  switch (form.event_type) {
    case 'birthday':
      return `${d}，为${n}准备生日关怀：提前订好小蛋糕与祝福卡片，利用课余时间在班级小范围为${n}送上祝福，让${n}感受到集体的温暖。注意尊重其意愿、把握分寸，避免过度关注带来压力。`
    case 'difficulty':
      return `${d}，关注${n}的实际困难：了解到其在生活/家庭方面存在具体困难，已协助对接资助与心理支持渠道。后续将持续跟进帮扶落实情况，确保关心落到实处。`
    case 'academic':
      return `${d}，${n}出现学业预警，需重点跟进：已与其沟通近期学习状况，共同梳理薄弱环节并制定学习计划。后续每周跟踪其学习状态，及时与任课老师联动，防止问题累积。`
    default:
      return `${d}，围绕${n}的关怀事项：记录本次事项的背景与目的、需要提前准备的材料或安排，以及需要注意的事项。后续按计划推进并及时回访，确保关怀闭环。`
  }
})

/** AI 建议要点 */
const aiPoints = computed<string[]>(() => {
  switch (form.event_type) {
    case 'birthday':
      return ['生日日期确认', '准备事项（蛋糕/贺卡）', '参与范围与尺度', '注意事项']
    case 'difficulty':
      return ['困难具体情况', '已对接的支持渠道', '学生本人意愿', '后续跟进安排']
    case 'academic':
      return ['预警科目与表现', '沟通情况', '制定的学习计划', '跟踪与联动安排']
    default:
      return ['事项背景', '准备事项', '注意事项', '后续安排']
  }
})

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
.ce-form { display: flex; flex-direction: column; gap: 12px; }
.ce-form .tui-section-hint { margin-bottom: 0; }

.ce-ctx {
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
.ce-ctx .el-icon { flex-shrink: 0; color: var(--tui-text-tertiary); }
.ce-ctx b { color: var(--tui-text); font-weight: 600; }

.ce-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 8px;
}
.ce-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 767px) {
  .ce-grid2 { grid-template-columns: 1fr; }
}
</style>