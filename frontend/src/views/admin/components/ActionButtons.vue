<template>
  <div class="table-actions">
    <el-tooltip v-if="showViewStudents" content="查看学生" placement="top">
      <el-button class="action-btn primary" circle @click.stop="$emit('viewStudents')">
        <el-icon><View /></el-icon>
      </el-button>
    </el-tooltip>
    <el-tooltip content="重置密码" placement="top">
      <el-button class="action-btn warn" circle @click.stop="showDialog = true">
        <el-icon><Key /></el-icon>
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
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { View, Key } from '@element-plus/icons-vue'
import { resetPassword } from '@/api/admin'

const props = defineProps<{
  userId: number
  userName: string
  showViewStudents?: boolean
}>()

const emit = defineEmits<{
  viewStudents: []
  resetSuccess: []
}>()

const showDialog = ref(false)
const loading = ref(false)

async function handleReset() {
  loading.value = true
  try {
    const res = await resetPassword(props.userId)
    ElMessage.success(res.message)
    showDialog.value = false
    emit('resetSuccess')
  } catch {
    ElMessage.error('重置密码失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.table-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>