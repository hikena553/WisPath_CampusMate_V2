<template>
  <el-dialog
    :model-value="modelValue"
    title="记录沟通"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    destroy-on-close
    class="tui-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="cl-form">
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>这条记录会留痕到沟通台账，家长零账号也能通过只读链接查看；选择「短信提示」将尝试发送短信。</span>
      </div>

      <div v-if="student" class="cl-ctx">
        <el-icon><User /></el-icon>
        <div class="cl-ctx-text">
          <span class="cl-ctx-name">{{ student.name }}<em v-if="student.college"> · {{ student.college }}</em></span>
          <small v-if="student.crisis_level">近期预警：{{ student.crisis_level }}{{ student.latest_crisis_summary ? ' · ' + student.latest_crisis_summary : '' }}</small>
          <small v-else>该生暂无危机预警记录，可按常规关怀跟进</small>
        </div>
      </div>

      <div class="cl-grid2">
        <div class="cl-field">
          <label class="cl-label">场景</label>
          <el-select v-model="form.scene" style="width:100%">
            <el-option v-for="s in sceneOptions" :key="s" :label="GUARDIAN_SCENE_LABEL[s]" :value="s" />
          </el-select>
        </div>
        <div class="cl-field">
          <label class="cl-label">家长联系人</label>
          <el-select v-model="form.guardian_id" clearable placeholder="可不选" style="width:100%">
            <el-option
              v-for="g in guardians"
              :key="g.id"
              :label="`${g.name}（${g.relation}）`"
              :value="g.id"
            />
          </el-select>
        </div>
      </div>

      <div class="cl-field">
        <label class="cl-label">沟通方式</label>
        <el-select v-model="form.channel" style="width:100%">
          <el-option v-for="c in channelOptions" :key="c" :label="GUARDIAN_CHANNEL_LABEL[c]" :value="c" />
        </el-select>
      </div>

      <div v-if="form.channel === 'sms'" class="cl-sms">
        <div class="cl-sms-text">
          <span>同时发送短信提示</span>
          <small>未配置短信服务商时将记为「待发送」，不阻塞业务</small>
        </div>
        <el-switch v-model="form.send_sms" />
      </div>

      <div v-if="form.scene === 'crisis'" class="cl-warn">
        <el-icon><WarningFilled /></el-icon>
        <span>危机类记录涉及隐私，将不会生成家长分享链接</span>
      </div>

      <AiDraftField
        v-model="form.content_summary"
        label="沟通内容摘要"
        required
        :rows="4"
        :maxlength="600"
        placeholder="沟通对象、主要事项、达成的共识……"
        :draft="aiDraft"
        :points="aiPoints"
      />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!form.content_summary.trim()" @click="submit">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { InfoFilled, User, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createContactLog, GUARDIAN_CHANNEL_LABEL, GUARDIAN_SCENE_LABEL,
  type Guardian, type GuardianChannel, type GuardianScene,
} from '@/api/guardian'
import type { StudentSummary } from '@/api/teacher'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'

const props = defineProps<{
  modelValue: boolean
  studentId: number
  guardians: Guardian[]
  /** 当前已选学生：用于展示操作对象与近期预警 */
  student?: StudentSummary | null
  /** 闭环：从学生成长档案带过来的反馈事由，打开即预填 */
  initialContent?: string
  initialScene?: GuardianScene
  /** 家长联系人卡快捷入口：预填沟通方式 */
  initialChannel?: GuardianChannel
  /** 家长联系人卡快捷入口：预填沟通对象 */
  initialGuardianId?: number
}>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const sceneOptions: GuardianScene[] = ['leave', 'crisis', 'academic', 'care', 'other']
const channelOptions: GuardianChannel[] = ['sms', 'report', 'link', 'note']

const saving = ref(false)
const form = reactive<{
  scene: GuardianScene
  guardian_id: number | undefined
  channel: GuardianChannel
  send_sms: boolean
  content_summary: string
}>({
  scene: 'care',
  guardian_id: undefined,
  channel: 'note',
  send_sms: false,
  content_summary: '',
})

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** AI 草稿：结合所选场景 + 沟通方式 + 家长 + 学生 + 当天日期，写成真实教师口吻 */
const aiDraft = computed(() => {
  const name = props.student?.name || '该生'
  const guardian = props.guardians.find((g) => g.id === form.guardian_id)
  const who = guardian ? `${guardian.name}（${guardian.relation}）` : '家长'
  const scene = GUARDIAN_SCENE_LABEL[form.scene]
  const channel = GUARDIAN_CHANNEL_LABEL[form.channel]
  return `【${scene}】${today()} 以「${channel}」方式与${who}沟通：反馈${name}近期在校的课堂表现与情绪状态，说明学校已采取的关心帮扶措施，就家校配合的具体分工达成一致，家长表示理解与支持，约定一周后再回访跟进。`
})
const aiPoints = ['沟通对象与时间', '学生近期表现', '已采取的帮扶措施', '家校配合安排', '后续回访计划']

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.scene = props.initialScene || 'care'
    form.guardian_id = props.initialGuardianId ?? props.guardians.find((g) => g.is_primary)?.id
    form.channel = props.initialChannel || 'note'
    form.send_sms = false
    form.content_summary = props.initialContent || ''
  }
)

async function submit() {
  if (!form.content_summary.trim()) return
  saving.value = true
  try {
    await createContactLog({
      student_id: props.studentId,
      guardian_id: form.guardian_id ?? null,
      scene: form.scene,
      channel: form.channel,
      content_summary: form.content_summary.trim(),
      send_sms: form.channel === 'sms' && form.send_sms,
    })
    ElMessage.success('已记录沟通')
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
.cl-form { display: flex; flex-direction: column; gap: 12px; }
.cl-label {
  display: block; font-size: 12.5px; font-weight: 600; color: var(--tui-text-secondary); margin-bottom: 8px;
}
.cl-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.cl-ctx {
  display: flex; align-items: flex-start; gap: 7px;
  background: var(--tui-brand-soft); border-radius: var(--tui-radius-sm); padding: 9px 12px;
}
.cl-ctx .el-icon { flex-shrink: 0; margin-top: 1px; font-size: 13px; color: var(--tui-brand-strong); }
.cl-ctx-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cl-ctx-name { font-size: 12.5px; font-weight: 600; color: var(--tui-text); }
.cl-ctx-name em { font-style: normal; font-weight: 400; color: var(--tui-text-tertiary); }
.cl-ctx-text small { font-size: 11.5px; color: var(--tui-warn); }
.cl-sms {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--tui-surface-muted); border-radius: var(--tui-radius-sm); padding: 9px 12px;
}
.cl-sms-text { display: flex; flex-direction: column; gap: 2px; }
.cl-sms-text span { font-size: 13px; color: var(--tui-text-secondary); font-weight: 500; }
.cl-sms-text small { font-size: 11.5px; color: var(--tui-text-quiet); }
.cl-warn {
  display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--tui-warn);
  background: var(--tui-warn-soft); border-radius: var(--tui-radius-sm); padding: 9px 12px;
}
@media (max-width: 767px) {
  .cl-grid2 { grid-template-columns: 1fr; }
}
</style>