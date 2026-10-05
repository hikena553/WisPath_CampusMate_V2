<template>
  <el-dialog
    :model-value="modelValue"
    title="记录沟通"
    :width="isMobile ? '94%' : '540px'"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="cl-form">
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
        <el-radio-group v-model="form.channel">
          <el-radio-button v-for="c in channelOptions" :key="c" :value="c">
            {{ GUARDIAN_CHANNEL_LABEL[c] }}
          </el-radio-button>
        </el-radio-group>
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

      <div class="cl-field">
        <label class="cl-label">沟通内容摘要</label>
        <el-input v-model="form.content_summary" type="textarea" :rows="4" maxlength="600" show-word-limit
          placeholder="沟通对象、主要事项、达成的共识……" />
      </div>
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
import { reactive, ref, watch } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createContactLog, GUARDIAN_CHANNEL_LABEL, GUARDIAN_SCENE_LABEL,
  type Guardian, type GuardianChannel, type GuardianScene,
} from '@/api/guardian'

const props = defineProps<{
  modelValue: boolean
  studentId: number
  guardians: Guardian[]
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

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.scene = 'care'
    form.guardian_id = props.guardians.find((g) => g.is_primary)?.id
    form.channel = 'note'
    form.send_sms = false
    form.content_summary = ''
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
.cl-form { display: flex; flex-direction: column; gap: 16px; }
.cl-label {
  display: block; font-size: 12.5px; font-weight: 600; color: #475467; margin-bottom: 8px;
}
.cl-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.cl-sms {
  display: flex; align-items: center; justify-content: space-between;
  background: #f9fafb; border-radius: 10px; padding: 10px 12px;
}
.cl-sms-text { display: flex; flex-direction: column; gap: 2px; }
.cl-sms-text span { font-size: 13px; color: #344054; font-weight: 500; }
.cl-sms-text small { font-size: 11.5px; color: #98a2b3; }
.cl-warn {
  display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: #b54708;
  background: #fffaeb; border-radius: 10px; padding: 9px 12px;
}
@media (max-width: 767px) {
  .cl-grid2 { grid-template-columns: 1fr; }
}
</style>