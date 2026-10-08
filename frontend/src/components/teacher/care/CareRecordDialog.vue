<template>
  <el-dialog
    :model-value="modelValue"
    :title="dialogTitle"
    :width="isMobile ? '92%' : '460px'"
    align-center
    destroy-on-close
    class="care-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="care-form">
      <div v-if="studentName" class="care-student">
        <el-icon :size="15"><User /></el-icon>
        <span>{{ studentName }}</span>
        <span v-if="taskTitle" class="care-from-task">来自任务：{{ taskTitle }}</span>
      </div>

      <!-- 记录类型 -->
      <div class="care-field">
        <label class="care-label">记录类型</label>
        <div class="care-type-row">
          <button
            v-for="opt in typeOptions"
            :key="opt.value"
            class="care-type"
            :class="[`type-${opt.value}`, { active: form.record_type === opt.value }]"
            @click="form.record_type = opt.value"
          >
            <el-icon :size="15"><component :is="opt.icon" /></el-icon>
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 内容 -->
      <div class="care-field">
        <label class="care-label">记录内容</label>
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="4"
          maxlength="500"
          show-word-limit
          :placeholder="placeholder"
        />
      </div>

      <!-- 仅教师可见 -->
      <div class="care-private">
        <div class="care-private-text">
          <span>仅教师可见</span>
          <small>开启后学生档案中不展示该条记录</small>
        </div>
        <el-switch v-model="form.is_private" />
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!form.content.trim()" @click="submit">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ChatDotRound, EditPen, Sunny, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createCareRecord,
  updateCareRecord,
  type CareRecord,
  type CareRecordType,
} from '@/api/careRecord'

const props = defineProps<{
  modelValue: boolean
  studentId: number
  studentName?: string
  taskId?: number
  taskTitle?: string
  /** 传入则为编辑模式 */
  record?: CareRecord | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [record: CareRecord]
}>()

const { isMobile } = useResponsive()

const typeOptions: { value: CareRecordType; label: string; icon: unknown }[] = [
  { value: 'care', label: '关怀记录', icon: Sunny },
  { value: 'talk', label: '谈心谈话', icon: ChatDotRound },
  { value: 'comment', label: '评语', icon: EditPen },
]

const placeholderMap: Record<CareRecordType, string> = {
  care: '记录本次关怀的经过与结果，例如：天气转凉提醒加衣，学生状态良好……',
  talk: '记录谈话时间、学生主要困扰与疏导要点……',
  comment: '撰写对学生的阶段性评价，例如：本学期进步明显，竞赛表现突出……',
}

const form = reactive<{ record_type: CareRecordType; content: string; is_private: boolean }>({
  record_type: 'care',
  content: '',
  is_private: true,
})
const saving = ref(false)

const isEdit = computed(() => !!props.record)
const dialogTitle = computed(() => (isEdit.value ? '编辑工作记录' : '新增工作记录'))
const placeholder = computed(() => placeholderMap[form.record_type])

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.record) {
      form.record_type = props.record.record_type
      form.content = props.record.content
      form.is_private = props.record.is_private
    } else {
      form.record_type = 'care'
      form.content = ''
      form.is_private = true
    }
  }
)

async function submit() {
  const content = form.content.trim()
  if (!content) return
  saving.value = true
  try {
    let saved: CareRecord
    if (isEdit.value && props.record) {
      saved = await updateCareRecord(props.record.id, {
        content,
        is_private: form.is_private,
      })
    } else {
      saved = await createCareRecord({
        student_id: props.studentId,
        record_type: form.record_type,
        content,
        is_private: form.is_private,
        task_id: props.taskId,
      })
    }
    ElMessage.success(isEdit.value ? '记录已更新' : '记录已保存')
    emit('update:modelValue', false)
    emit('saved', saved)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.care-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.care-student {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #101828;
  background: #f9fafb;
  border-radius: 10px;
  padding: 9px 12px;
}
.care-from-task {
  margin-left: auto;
  font-size: 11.5px;
  font-weight: 400;
  color: #98a2b3;
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.care-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}

.care-type-row {
  display: flex;
  gap: 8px;
}
.care-type {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 4px;
  border: 1px solid #e4e7ec;
  border-radius: 10px;
  background: #fff;
  color: #667085;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
}
.care-type.active.type-care { border-color: #f04438; background: #fef3f2; color: #d92d20; font-weight: 600; }
.care-type.active.type-talk { border-color: #7c3aed; background: #f4f3ff; color: #6941c6; font-weight: 600; }
.care-type.active.type-comment { border-color: #2563eb; background: #eff4ff; color: #2563eb; font-weight: 600; }

.care-private {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 10px;
}
.care-private-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.care-private-text span {
  font-size: 13px;
  font-weight: 500;
  color: #344054;
}
.care-private-text small {
  font-size: 11.5px;
  color: #98a2b3;
}
</style>
