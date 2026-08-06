<template>
  <div class="upload-btn-wrap">
    <el-upload
      :show-file-list="false"
      :http-request="handleUpload"
      :before-upload="beforeUpload"
    >
      <el-button size="small" :type="modelValue ? 'success' : 'primary'">
        <el-icon style="margin-right:4px"><Upload /></el-icon>
        {{ modelValue ? '已上传' : '选择文件' }}
      </el-button>
    </el-upload>
    <span v-if="modelValue" class="uploaded-hint">
      <el-icon style="margin-right:2px"><Document /></el-icon>
      {{ fileName || '已上传' }}
      <el-tag size="small" closable type="info" style="margin-left:6px" @close="$emit('update:modelValue', '')">
        移除
      </el-tag>
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Document } from '@element-plus/icons-vue'
import { getToken } from '@/utils/token'

defineProps<{ modelValue?: string }>()
const emit = defineEmits<{ 'update:modelValue': [url: string]; uploaded: [url: string] }>()

const fileName = ref('')

function beforeUpload(file: File) {
  const maxSize = 10 * 1024 * 1024
  const allowed = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pdf', '.doc', '.docx', '.zip', '.rar']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  if (file.size > maxSize) {
    ElMessage.error('文件不能超过 10MB')
    return false
  }
  return true
}

async function handleUpload({ file }: { file: File }) {
  const formData = new FormData()
  formData.append('file', file)
  const token = getToken()
  try {
    const resp = await fetch('/api/upload', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!resp.ok) { ElMessage.error('上传失败'); return }
    const data = await resp.json()
    fileName.value = data.filename
    emit('update:modelValue', data.url)
    emit('uploaded', data.url)
    ElMessage.success('上传成功')
  } catch {
    ElMessage.error('上传失败')
  }
}
</script>

<style scoped>
.upload-btn-wrap { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.uploaded-hint { display: inline-flex; align-items: center; font-size: 12px; color: #666; }
</style>
