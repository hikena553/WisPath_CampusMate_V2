<template>
  <el-dialog
    :model-value="modelValue"
    :title="dialogTitle"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    destroy-on-close
    class="tui-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="care-form">
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>
          这条记录会沉淀到「{{ studentName || '当前学生' }}」的工作记录与成长档案；开启「仅教师可见」后该条记录不会展示给学生。
        </span>
      </div>

      <!-- 上下文信息条：确认操作对象 -->
      <div class="care-ctx">
        <el-icon><User /></el-icon>
        <span>
          记录对象：<b>{{ studentName || '当前学生' }}</b>
          <template v-if="taskTitle"> · 来自任务「{{ taskTitle }}」</template>
          <template v-else> · 无关联任务</template>
        </span>
      </div>

      <!-- 记录类型 -->
      <div class="care-field">
        <label class="care-label">记录类型</label>
        <el-select
          v-model="form.record_type"
          :disabled="isEdit"
          placeholder="请选择记录类型"
          style="width:100%"
        >
          <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <p v-if="isEdit" class="care-tip">编辑时仅可修改内容与可见范围。</p>
      </div>

      <!-- 内容 -->
      <AiDraftField
        v-model="form.content"
        label="记录内容"
        required
        :rows="4"
        :maxlength="500"
        :placeholder="placeholder"
        :draft="aiDraft"
        :points="aiPoints"
      />

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
import { InfoFilled, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
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

const typeOptions: { value: CareRecordType; label: string }[] = [
  { value: 'care', label: '关怀记录' },
  { value: 'talk', label: '谈心谈话' },
  { value: 'comment', label: '评语' },
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

/** 草稿日期：编辑态取原记录日期，新建取今天 */
const today = new Date().toISOString().slice(0, 10)
const draftDate = computed(() => (props.record?.created_at ? props.record.created_at.slice(0, 10) : today))
const who = computed(() => props.studentName || '该生')

/** AI 草稿：结合所选类型 + 学生姓名 + 日期，写成真实教师口吻 */
const aiDraft = computed(() => {
  const d = draftDate.value
  const n = who.value
  switch (form.record_type) {
    case 'talk':
      return `${d}，我与${n}进行了一次谈心谈话。了解到其近期因人际与学业压力有些困扰，我耐心倾听并与其一起梳理了应对思路，约定先从小目标做起。谈话后${n}情绪明显放松，后续我会在一周内回访其状态。`
    case 'comment':
      return `${d}，对${n}本阶段的表现评价：课堂参与积极，作业按时完成，与同学相处融洽，较之前有可见进步。建议继续保持，并在薄弱环节再下功夫，期待更大突破。`
    default:
      return `${d}，我留意到${n}近期状态有些变化，主动进行了关心。了解情况后给予力所能及的帮助，并提醒其注意作息与情绪调节。目前${n}情绪平稳，我会持续关注其后续情况。`
  }
})

/** AI 建议要点：随类型变化 */
const aiPoints = computed<string[]>(() => {
  switch (form.record_type) {
    case 'talk':
      return ['谈话时间与地点', '学生主要困扰', '疏导要点', '学生反馈', '后续回访计划']
    case 'comment':
      return ['学习与课堂表现', '行为与习惯', '进步亮点', '改进建议']
    default:
      return ['学生近期表现', '触发事件', '已采取的措施', '后续跟进安排']
  }
})

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
  gap: 12px;
}
.care-form .tui-section-hint {
  margin-bottom: 0;
}

.care-ctx {
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
.care-ctx .el-icon {
  flex-shrink: 0;
  color: var(--tui-text-tertiary);
}
.care-ctx b {
  color: var(--tui-text);
  font-weight: 600;
}

.care-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 8px;
}
.care-tip {
  margin: 6px 0 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}

.care-private {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 12px;
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
}
.care-private-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.care-private-text span {
  font-size: 13px;
  font-weight: 500;
  color: var(--tui-text-secondary);
}
.care-private-text small {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
</style>