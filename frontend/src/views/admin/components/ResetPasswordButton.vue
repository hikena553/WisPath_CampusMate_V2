<template>
  <el-button type="warning" link @click.stop="showDialog = true">重置密码</el-button>
  
  <el-dialog
    v-model="showDialog"
    title="确认重置密码"
    width="400px"
    :close-on-click-modal="false"
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
import { resetPassword } from '@/api/admin'

const props = defineProps<{
  userId: number
  userName: string
}>()

const emit = defineEmits<{
  success: []
}>()

const showDialog = ref(false)
const loading = ref(false)

async function handleReset() {
  loading.value = true
  try {
    const res = await resetPassword(props.userId)
    ElMessage.success(res.message)
    showDialog.value = false
    emit('success')
  } catch {
    ElMessage.error('重置密码失败')
  } finally {
    loading.value = false
  }
}
</script>
