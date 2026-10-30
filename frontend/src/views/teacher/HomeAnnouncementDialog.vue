<template>
  <!-- 发布公告 Dialog -->
  <!-- 发布公告（表单+AI+附件：移动端=全屏子页） -->
  <ResponsivePopup
    v-model="dialogVisible"
    title="发布公告"
    width="380px"
    class="tui-dialog"
  >
    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>发布后即时推送给你名下全体学生；紧急公告会置顶并高亮角标，请确认标题与内容无误。</span>
    </div>
    <div class="an-ctx">
      <span class="an-ctx-item">发送对象：名下全体学生</span>
      <span class="an-ctx-item">公告日期：{{ today }}</span>
    </div>
    <el-form ref="announcementFormRef" :model="createForm" label-position="top" :rules="announcementRules">
      <el-form-item label="标题" prop="title">
        <el-input v-model="createForm.title" placeholder="请输入公告标题，如：关于五一放假安排的通知" maxlength="200" />
      </el-form-item>
      <el-form-item label="紧急程度">
        <el-select v-model="createForm.urgency" placeholder="请选择紧急程度" style="width: 100%">
          <el-option v-for="o in urgencyOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
      </el-form-item>
      <div class="an-draft">
        <AiDraftField
          v-model="createForm.content"
          label="公告内容"
          required
          :rows="4"
          :maxlength="1000"
          placeholder="请输入公告内容，建议包含时间、地点、注意事项等"
          :draft="aiDraft"
          :points="aiPoints"
        />
      </div>
      <el-form-item label="附件（可选）">
        <input class="tui-file" type="file" @change="(e: any) => { if (e.target?.files?.[0]) createFile = e.target.files[0] }" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="handleCreate">发布</el-button>
    </template>
  </ResponsivePopup>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
// v6.1 弹窗减负：公告表单走全屏子页承接
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { InfoFilled } from '@element-plus/icons-vue'
import { createAnnouncement } from '@/api/announcement'
import { ElMessage } from 'element-plus'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'

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
}

const urgencyOptions = [
  { value: 'normal', label: '普通通知' },
  { value: 'important', label: '重要通知' },
  { value: 'urgent', label: '紧急通知' },
]

/** 今日日期（YYYY-MM-DD）：用于上下文与 AI 草稿 */
const today = new Date().toISOString().slice(0, 10)

/** AI 建议要点：随紧急程度变化 */
const aiPoints = computed(() => {
  if (createForm.urgency === 'urgent') return ['时间节点', '紧急事项', '回复确认', '联系方式']
  if (createForm.urgency === 'important') return ['事项背景', '时间与地点', '需做的准备', '截止时间']
  return ['通知事项', '时间地点', '注意事项', '反馈方式']
})

/** AI 草稿：结合所选紧急程度 + 日期，写成正式通知口吻 */
const aiDraft = computed(() => {
  if (createForm.urgency === 'urgent') {
    return `【紧急通知 ${today}】全体同学请注意：接学校临时安排，请立即查看本次通知的具体要求，并务必于今日按规定时间完成确认与回复，逾期将影响正常学习安排。收到请回复“已阅”。如遇特殊情况，请第一时间与我联系。`
  }
  if (createForm.urgency === 'important') {
    return `【重要通知 ${today}】各位同学：现将近期重要安排通知如下，请大家认真阅读并提前做好准备。请在通知要求的时间节点前完成相应事项，如有疑问及时向我反馈。请相互转告，确保人人知晓。`
  }
  return `【班级通知 ${today}】各位同学：现将近期班级安排告知大家，请留意相关时间与要求，提前做好准备。如有疑问，可在课后或群内与我沟通。感谢大家配合。`
})

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
  if (!createForm.content.trim()) {
    ElMessage.warning('请填写公告内容，建议写清时间、地点与需要学生做的事情')
    return
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

<style scoped>
.tui-file {
  width: 100%;
  font-size: 12.5px;
  color: var(--tui-text-secondary);
}
/* 弹窗上下文信息条 */
.an-ctx {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 9px;
  background: var(--tui-surface-muted);
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
}
/* AI 草稿与后续表单项保持一致间距 */
.an-draft {
  margin-bottom: 14px;
}
</style>