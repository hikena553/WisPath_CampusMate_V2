<template>
  <!-- 发布公告 Dialog -->
  <el-dialog v-model="dialogVisible" title="发布公告" width="520px">
    <el-form ref="announcementFormRef" :model="createForm" label-position="top" :rules="announcementRules">
      <el-form-item label="标题" prop="title">
        <el-input v-model="createForm.title" placeholder="请输入公告标题，如：关于五一放假安排的通知" maxlength="200" />
      </el-form-item>
      <el-form-item label="内容" prop="content">
        <el-input v-model="createForm.content" type="textarea" :rows="4" placeholder="请输入公告内容，建议包含时间、地点、注意事项等" />
      </el-form-item>
      <el-form-item label="紧急程度">
        <el-radio-group v-model="createForm.urgency">
          <el-radio value="normal">普通</el-radio>
          <el-radio value="important">重要</el-radio>
          <el-radio value="urgent">紧急</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="附件（可选）">
        <input type="file" @change="(e: any) => { if (e.target?.files?.[0]) createFile = e.target.files[0] }" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="handleCreate">发布</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { createAnnouncement } from '@/api/announcement'
import { ElMessage } from 'element-plus'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; created: [] }>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (v: boolean) => emit('update:visible', v),
})

const createForm = reactive({ title: '', content: '', urgency: 'normal' })
const createFile = ref<File | null>(null)
const announcementFormRef = ref<any>()
const announcementRules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }],
}

// 每次打开弹窗时重置表单（替代原父级 openCreateDialog 的清空逻辑）
watch(() => props.visible, (val) => {
  if (val) {
    createForm.title = ''
    createForm.content = ''
    createForm.urgency = 'normal'
    createFile.value = null
  }
})

async function handleCreate() {
  if (announcementFormRef.value) {
    try { await announcementFormRef.value.validate() } catch { return }
  }
  const fd = new FormData()
  fd.append('title', createForm.title)
  fd.append('content', createForm.content)
  fd.append('urgency', createForm.urgency)
  if (createFile.value) fd.append('file', createFile.value)
  try {
    await createAnnouncement(fd)
    ElMessage.success('发布成功')
    emit('update:visible', false)
    emit('created')
  } catch { ElMessage.error('发布失败') }
}
</script>