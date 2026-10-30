<template>
  <ResponsivePopup
    :model-value="modelValue"
    :title="guardian ? '编辑联系人' : '新增联系人'"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    destroy-on-close
    class="tui-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="gd-form">
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>建档后可对该家长发短信、生成只读链接并留痕；设为主要联系人后会作为默认沟通对象。</span>
      </div>

      <div v-if="student" class="gd-ctx">
        <el-icon><User /></el-icon>
        <span>{{ student.name }}<em v-if="student.college"> · {{ student.college }}</em></span>
      </div>

      <div class="gd-grid2">
        <div class="gd-field">
          <label class="gd-label">关系</label>
          <el-select
            v-model="form.relation"
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入关系"
            style="width:100%"
          >
            <el-option v-for="r in relationOptions" :key="r" :label="r" :value="r" />
          </el-select>
        </div>
        <div class="gd-field">
          <label class="gd-label">姓名</label>
          <el-input v-model="form.name" maxlength="50" placeholder="如：王女士" />
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

      <AiDraftField
        v-model="form.remark"
        label="备注"
        :rows="3"
        :maxlength="200"
        placeholder="如：工作日晚间联系，涉及学业问题请先电话……"
        :draft="aiDraft"
        :points="aiPoints"
      />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!form.name.trim()" @click="submit">保存</el-button>
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
import { createGuardian, updateGuardian, type Guardian } from '@/api/guardian'
import type { StudentSummary } from '@/api/teacher'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'

const props = defineProps<{
  modelValue: boolean
  studentId: number
  guardian?: Guardian | null
  /** 当前已选学生：用于在弹窗内确认操作对象 */
  student?: StudentSummary | null
}>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const saving = ref(false)

const relationOptions = ['父亲', '母亲', '家长', '监护人', '祖父', '祖母', '外祖父', '外祖母', '其他']

const form = reactive({
  name: '',
  relation: '家长',
  phone: '',
  is_primary: false,
  remark: '',
})

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** AI 草稿：结合所选关系 + 学生姓名 + 当天日期，写成真实教师口吻的备注 */
const aiDraft = computed(() => {
  const name = props.student?.name || '孩子'
  const relation = (form.relation || '家长').trim()
  return `${name}的${relation}，日常主要负责家校联络。${today()}沟通确认：工作日晚间与周末方便接听电话，涉及${name}的学业进度与情绪波动请及时同步，遇突发情况先电话联系，再以书面形式补充说明。`
})
const aiPoints = ['联系时段与方式', '由谁主要负责对接', '需要重点关注的情况', '家庭配合注意事项']

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
.gd-form { display: flex; flex-direction: column; gap: 12px; }
.gd-label {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 12.5px; font-weight: 600; color: var(--tui-text-secondary); margin-bottom: 8px;
}
.gd-label small { font-size: 11px; font-weight: 400; color: var(--tui-text-quiet); }
.gd-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.gd-ctx {
  display: flex; align-items: center; gap: 7px;
  background: var(--tui-brand-soft); border-radius: var(--tui-radius-sm); padding: 8px 12px;
  font-size: 12.5px; font-weight: 600; color: var(--tui-text);
}
.gd-ctx .el-icon { font-size: 13px; color: var(--tui-brand-strong); }
.gd-ctx em { font-style: normal; font-weight: 400; color: var(--tui-text-tertiary); }
.gd-inline {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--tui-surface-muted); border-radius: var(--tui-radius-sm); padding: 9px 12px;
}
.gd-inline-text { display: flex; flex-direction: column; gap: 2px; }
.gd-inline-text span { font-size: 13px; color: var(--tui-text-secondary); font-weight: 500; }
.gd-inline-text small { font-size: 11.5px; color: var(--tui-text-quiet); }
@media (max-width: 767px) {
  .gd-grid2 { grid-template-columns: 1fr; }
}
</style>