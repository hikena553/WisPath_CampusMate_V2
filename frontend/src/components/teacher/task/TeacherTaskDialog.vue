<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑任务' : '新增任务'"
    width="520px"
    :close-on-click-modal="false"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
    @closed="onClosed"
  >
    <el-form :model="form" label-width="76px" @submit.prevent>
      <el-form-item label="任务标题" required>
        <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="例如：跟进联系张同学家长" />
      </el-form-item>

      <el-form-item label="优先级">
        <el-radio-group v-model="form.priority">
          <el-radio-button value="high">高</el-radio-button>
          <el-radio-button value="mid">中</el-radio-button>
          <el-radio-button value="low">低</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="关联学生">
        <el-select
          v-model="form.student_id"
          filterable
          remote
          clearable
          reserve-keyword
          :remote-method="searchStudents"
          :loading="studentLoading"
          placeholder="按姓名/学号搜索（可留空）"
          style="width: 100%"
        >
          <el-option
            v-for="s in studentOptions"
            :key="s.id"
            :label="`${s.name}${s.username ? ' · ' + s.username : ''}`"
            :value="s.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="提醒日">
        <el-date-picker
          v-model="form.remind_at"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="到该日期在清单中提醒我"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="截止日">
        <el-date-picker
          v-model="form.due_at"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="逾期后将在高优先级分组提示"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="任务详情">
        <el-input v-model="form.detail" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="补充说明（可选）" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">{{ isEdit ? '保存' : '创建' }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createTeacherTask, updateTeacherTask, type TaskPriority, type TeacherTask } from '@/api/teacherTask'
import { getStudents, type StudentSummary } from '@/api/teacher'

const props = defineProps<{
  modelValue: boolean
  /** 传入则为编辑模式 */
  task?: TeacherTask | null
  /** 预填：关联学生（消息页「加入任务」/ 关怀页唤起时使用） */
  presetStudentId?: number | null
  presetStudentName?: string
  /** 预填：任务标题 */
  presetTitle?: string
  /** 预填：截止/提醒日期（日程视图按选中日期新增时使用） */
  presetDueAt?: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  saved: []
}>()

const isEdit = computed(() => !!props.task)

const saving = ref(false)
const studentLoading = ref(false)
const studentOptions = ref<StudentSummary[]>([])

const form = reactive<{
  title: string
  detail: string
  student_id: number | null
  priority: TaskPriority
  remind_at: string | null
  due_at: string | null
}>({
  title: '',
  detail: '',
  student_id: null,
  priority: 'mid',
  remind_at: null,
  due_at: null,
})

/** 打开弹窗时按「编辑 / 新增（含预填）」回填表单 */
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    const t = props.task
    studentOptions.value = []
    if (t) {
      form.title = t.title
      form.detail = t.detail || ''
      form.student_id = t.student_id ?? null
      form.priority = (t.priority as TaskPriority) || 'mid'
      form.remind_at = t.remind_at || null
      form.due_at = t.due_at || null
      if (t.student_id && t.student_name) {
        // 编辑态先把当前学生放进选项，保证下拉能回显
        studentOptions.value = [{ id: t.student_id, name: t.student_name } as StudentSummary]
      }
      return
    }
    // 新增：应用外部预填（学生 / 标题 / 日期），便于从消息、关怀、日程等处一键建任务
    form.title = props.presetTitle || ''
    form.detail = ''
    form.student_id = props.presetStudentId ?? null
    form.priority = 'mid'
    form.remind_at = props.presetDueAt || null
    form.due_at = props.presetDueAt || null
    if (props.presetStudentId) {
      studentOptions.value = [
        { id: props.presetStudentId, name: props.presetStudentName || '已选学生' } as StudentSummary,
      ]
    }
  }
)

/** 学生远程搜索：走服务端检索，避免一次性拉全量 */
async function searchStudents(keyword: string) {
  if (!keyword) {
    studentOptions.value = []
    return
  }
  studentLoading.value = true
  try {
    studentOptions.value = await getStudents(keyword)
  } catch {
    studentOptions.value = []
  } finally {
    studentLoading.value = false
  }
}

function onClosed() {
  form.title = ''
  form.detail = ''
  form.student_id = null
  form.priority = 'mid'
  form.remind_at = null
  form.due_at = null
  studentOptions.value = []
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写任务标题')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      detail: form.detail || undefined,
      student_id: form.student_id ?? undefined,
      priority: form.priority,
      remind_at: form.remind_at || undefined,
      due_at: form.due_at || undefined,
    }
    if (isEdit.value && props.task) {
      await updateTeacherTask(props.task.id, {
        title: form.title.trim(),
        detail: form.detail || null,
        student_id: form.student_id ?? null,
        priority: form.priority,
        remind_at: form.remind_at || null,
        due_at: form.due_at || null,
      })
      ElMessage.success('任务已更新')
    } else {
      await createTeacherTask(payload)
      ElMessage.success('任务已创建')
    }
    emit('update:modelValue', false)
    emit('saved')
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>