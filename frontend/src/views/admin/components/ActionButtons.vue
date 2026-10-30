<template>
  <div class="table-actions">
    <el-tooltip v-if="showViewStudents" content="查看学生" placement="top">
      <el-button class="action-btn primary" circle @click.stop="$emit('viewStudents')">
        <el-icon><Eye /></el-icon>
      </el-button>
    </el-tooltip>
    <el-tooltip content="下发任务" placement="top">
      <el-button class="action-btn brand" circle @click.stop="openTask">
        <el-icon><Send /></el-icon>
      </el-button>
    </el-tooltip>
    <el-tooltip content="重置密码" placement="top">
      <el-button class="action-btn warn" circle @click.stop="showDialog = true">
        <el-icon><KeyRound /></el-icon>
      </el-button>
    </el-tooltip>
  </div>

  <el-dialog
    v-model="showDialog"
    title="确认重置密码"
    width="460px"
    :close-on-click-modal="false"
    append-to-body
  >
    <p>确定要重置 <strong>{{ userName }}</strong> 的密码为 <code>123456</code> 吗？</p>
    <template #footer>
      <el-button @click="showDialog = false">取消</el-button>
      <el-button type="primary" @click="handleReset" :loading="loading">确定</el-button>
    </template>
  </el-dialog>

  <!-- 下发任务：写入教师的任务日程并推送站内通知 -->
  <el-dialog
    v-model="taskVisible"
    :title="`向 ${userName} 下发任务`"
    width="520px"
    :close-on-click-modal="false"
    append-to-body
  >
    <el-form :model="taskForm" label-width="80px" @submit.prevent>
      <el-form-item label="任务标题" required>
        <el-input v-model="taskForm.title" maxlength="200" show-word-limit placeholder="例如：本周完成班级心理摸排并提交小结" />
      </el-form-item>
      <el-form-item label="优先级">
        <el-radio-group v-model="taskForm.priority">
          <el-radio-button value="high">高</el-radio-button>
          <el-radio-button value="mid">中</el-radio-button>
          <el-radio-button value="low">低</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="提醒日">
        <el-date-picker v-model="taskForm.remind_at" type="date" value-format="YYYY-MM-DD" placeholder="到该日期在教师日程提醒" style="width:100%" />
      </el-form-item>
      <el-form-item label="截止日">
        <el-date-picker v-model="taskForm.due_at" type="date" value-format="YYYY-MM-DD" placeholder="逾期将在教师日程高亮" style="width:100%" />
      </el-form-item>
      <el-form-item label="任务说明">
        <el-input v-model="taskForm.detail" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="补充要求（可选）" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="taskVisible = false">取消</el-button>
      <el-button type="primary" :loading="taskLoading" @click="handleDispatch">下发</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Eye, KeyRound, Send } from 'lucide-vue-next'
import { dispatchTeacherTask, resetPassword } from '@/api/admin'

const props = defineProps<{
  userId: number
  userName: string
  showViewStudents?: boolean
}>()

const emit = defineEmits<{
  viewStudents: []
  resetSuccess: []
  taskDispatched: []
}>()

const showDialog = ref(false)
const loading = ref(false)

async function handleReset() {
  loading.value = true
  try {
    const res = await resetPassword(props.userId)
    ElMessage.success(res.message)
    showDialog.value = false
    // 重置成功后通知顶栏消息组件刷新，已闭环的重置申请红点即时消失
    window.dispatchEvent(new Event('admin:messages-refresh'))
    emit('resetSuccess')
  } catch {
    ElMessage.error('重置密码失败')
  } finally {
    loading.value = false
  }
}

// ===== 下发任务 =====
const taskVisible = ref(false)
const taskLoading = ref(false)
const taskForm = reactive<{
  title: string
  detail: string
  priority: 'high' | 'mid' | 'low'
  remind_at: string | null
  due_at: string | null
}>({ title: '', detail: '', priority: 'mid', remind_at: null, due_at: null })

function openTask() {
  taskForm.title = ''
  taskForm.detail = ''
  taskForm.priority = 'mid'
  taskForm.remind_at = null
  taskForm.due_at = null
  taskVisible.value = true
}

async function handleDispatch() {
  if (!taskForm.title.trim()) {
    ElMessage.warning('请填写任务标题')
    return
  }
  taskLoading.value = true
  try {
    await dispatchTeacherTask({
      teacher_id: props.userId,
      title: taskForm.title.trim(),
      detail: taskForm.detail || null,
      priority: taskForm.priority,
      remind_at: taskForm.remind_at || null,
      due_at: taskForm.due_at || null,
    })
    ElMessage.success('任务已下发，将出现在该教师的日程中')
    taskVisible.value = false
    emit('taskDispatched')
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '下发失败')
  } finally {
    taskLoading.value = false
  }
}
</script>

<style scoped>
.table-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.action-btn.brand {
  color: #2563eb;
  border-color: rgba(37, 99, 235, 0.3);
}
</style>