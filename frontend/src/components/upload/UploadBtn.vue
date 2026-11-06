<template>
  <div class="upload-btn-wrap">
    <el-upload
      :show-file-list="false"
      :http-request="handleUpload"
      :before-upload="beforeUpload"
    >
      <button type="button" class="upload-trigger" :class="{ 'is-done': !!modelValue }">
        <el-icon class="upload-trigger-icon"><Upload /></el-icon>
        <span>{{ modelValue ? '重新上传' : '上传文件 / 图片' }}</span>
      </button>
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
      headers: { 'X-Requested-With': 'XMLHttpRequest', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
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
/* 上传入口：中性描边胶囊，不再用蓝/绿实心按钮抢视线 */
.upload-trigger {
  display: inline-flex; align-items: center; gap: 6px;
  height: 38px; padding: 0 14px;
  border: 1px dashed #d5d9e0; border-radius: 10px;
  background: #fbfcfd; color: #4b5563;
  font-family: inherit; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: border-color .16s ease, background .16s ease, color .16s ease;
  -webkit-tap-highlight-color: transparent;
}
.upload-trigger:active { background: #f2f4f7; }
.upload-trigger.is-done { border-style: solid; border-color: #dbe1ea; background: #f2f4f7; color: #374151; }
.upload-trigger-icon { font-size: 15px; color: #6b7280; }
.uploaded-hint { display: inline-flex; align-items: center; font-size: 12px; color: #6b7280; }
</style>
