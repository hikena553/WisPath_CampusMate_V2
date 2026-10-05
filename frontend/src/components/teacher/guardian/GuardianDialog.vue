<template>
  <el-dialog
    :model-value="modelValue"
    :title="guardian ? '编辑联系人' : '新增联系人'"
    :width="isMobile ? '94%' : '480px'"
    align-center
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="gd-form">
      <div class="gd-grid2">
        <div class="gd-field">
          <label class="gd-label">姓名</label>
          <el-input v-model="form.name" maxlength="50" placeholder="如：王女士" />
        </div>
        <div class="gd-field">
          <label class="gd-label">关系</label>
          <el-input v-model="form.relation" maxlength="20" placeholder="母亲 / 父亲 / 监护人" />
        </div>
      </div>

      <div class="gd-field">
        <label class="gd-label">手机号<small>仅用于短信通道，展示时自动脱敏</small></label>
        <el-input v-model="form.phone" maxlength="20" placeholder="选填" />
      </div>

      <div class="gd-field gd-inline">
        <div class="gd-inline-text">
          <span>设为主要联系人</span>
          <small>优先作为家校沟通对象</small>
        </div>
        <el-switch v-model="form.is_primary" />
      </div>

      <div class="gd-field">
        <label class="gd-label">备注</label>
        <el-input v-model="form.remark" maxlength="200" placeholder="如：工作日晚间联系（选填）" />
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!form.name.trim()" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { createGuardian, updateGuardian, type Guardian } from '@/api/guardian'

const props = defineProps<{ modelValue: boolean; studentId: number; guardian?: Guardian | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const saving = ref(false)

const form = reactive({
  name: '',
  relation: '家长',
  phone: '',
  is_primary: false,
  remark: '',
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.guardian) {
      form.name = props.guardian.name
      form.relation = props.guardian.relation
      form.phone = ''
      form.is_primary = props.guardian.is_primary
      form.remark = props.guardian.remark || ''
    } else {
      form.name = ''
      form.relation = '家长'
      form.phone = ''
      form.is_primary = false
      form.remark = ''
    }
  }
)

async function submit() {
  if (!form.name.trim()) return
  saving.value = true
  try {
    if (props.guardian) {
      // 编辑时手机号仅脱敏回显，留空表示不修改（避免误清空）
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        relation: form.relation.trim() || '家长',
        is_primary: form.is_primary,
        remark: form.remark.trim() || null,
      }
      if (form.phone.trim()) payload.phone = form.phone.trim()
      await updateGuardian(props.guardian.id, payload)
    } else {
      await createGuardian({
        student_id: props.studentId,
        name: form.name.trim(),
        relation: form.relation.trim() || '家长',
        phone: form.phone.trim() || null,
        is_primary: form.is_primary,
        remark: form.remark.trim() || null,
      })
    }
    ElMessage.success('已保存')
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
.gd-form { display: flex; flex-direction: column; gap: 16px; }
.gd-label {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 12.5px; font-weight: 600; color: #475467; margin-bottom: 8px;
}
.gd-label small { font-size: 11px; font-weight: 400; color: #98a2b3; }
.gd-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.gd-inline {
  display: flex; align-items: center; justify-content: space-between;
  background: #f9fafb; border-radius: 10px; padding: 10px 12px;
}
.gd-inline-text { display: flex; flex-direction: column; gap: 2px; }
.gd-inline-text span { font-size: 13px; color: #344054; font-weight: 500; }
.gd-inline-text small { font-size: 11.5px; color: #98a2b3; }
@media (max-width: 767px) {
  .gd-grid2 { grid-template-columns: 1fr; }
}
</style>