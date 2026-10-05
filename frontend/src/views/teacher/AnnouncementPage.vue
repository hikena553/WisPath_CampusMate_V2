<template>
  <div class="tui-page">
    <header class="tui-header">
      <div>
        <h2 class="tui-header-title">班级公告</h2>
        <p class="tui-header-sub">面向名下学生发布通知，支持紧急程度标记</p>
      </div>
      <div class="tui-header-actions">
        <el-button type="primary" round :icon="Plus" @click="dialogVisible = true">发布公告</el-button>
      </div>
    </header>

    <div v-if="loading" class="an-state">加载中…</div>
    <div v-else-if="!items.length" class="an-state">
      <el-icon :size="34" color="#d0d5dd"><Bell /></el-icon>
      <p>还没有发布过公告</p>
      <el-button size="small" round type="primary" @click="dialogVisible = true">发布第一条</el-button>
    </div>

    <div v-else class="tui-stack">
      <article v-for="a in items" :key="a.id" class="tui-card">
        <div class="an-item">
          <div class="an-head">
            <span class="tui-chip" :class="urgencyClass(a.urgency)">{{ urgencyLabel(a.urgency) }}</span>
            <span class="an-date">{{ (a.created_at || '').slice(0, 10) }}</span>
          </div>
          <h3 class="an-title">{{ a.title }}</h3>
          <p class="an-content">{{ a.content }}</p>
          <div class="an-ops">
            <a v-if="a.attachment_url" class="an-link" :href="a.attachment_url" target="_blank" rel="noopener noreferrer">查看附件</a>
            <button class="an-link an-link-danger" @click="remove(a)">删除</button>
          </div>
        </div>
      </article>
    </div>

    <el-dialog v-model="dialogVisible" title="发布公告" :width="isMobile ? '94%' : '520px'" align-center destroy-on-close>
      <div class="an-form">
        <div class="an-field">
          <label class="an-label">标题</label>
          <el-input v-model="form.title" maxlength="100" placeholder="一句话说明通知主题" />
        </div>
        <div class="an-field">
          <label class="an-label">紧急程度</label>
          <el-radio-group v-model="form.urgency">
            <el-radio-button value="normal">普通</el-radio-button>
            <el-radio-button value="important">重要</el-radio-button>
            <el-radio-button value="urgent">紧急</el-radio-button>
          </el-radio-group>
        </div>
        <div class="an-field">
          <label class="an-label">内容</label>
          <el-input v-model="form.content" type="textarea" :rows="5" maxlength="1000" show-word-limit
            placeholder="写清时间、地点、需要学生做什么" />
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!valid" @click="submit">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Bell, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createAnnouncement,
  deleteAnnouncement,
  getTeacherAnnouncements,
  type AnnouncementItem,
} from '@/api/announcement'

defineOptions({ name: 'teacher-announcement' })

const { isMobile } = useResponsive()

const items = ref<AnnouncementItem[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const form = reactive({ title: '', content: '', urgency: 'normal' as AnnouncementItem['urgency'] })

const valid = computed(() => form.title.trim().length > 0 && form.content.trim().length > 0)

function urgencyLabel(u: AnnouncementItem['urgency']) {
  return u === 'urgent' ? '紧急' : u === 'important' ? '重要' : '普通'
}
function urgencyClass(u: AnnouncementItem['urgency']) {
  return u === 'urgent' ? 'chip-danger' : u === 'important' ? 'chip-warn' : ''
}

async function load() {
  loading.value = true
  try {
    items.value = await getTeacherAnnouncements()
  } catch {
    ElMessage.error('公告加载失败')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!valid.value) return
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.title.trim())
    fd.append('content', form.content.trim())
    fd.append('urgency', form.urgency)
    await createAnnouncement(fd)
    ElMessage.success('公告已发布')
    dialogVisible.value = false
    form.title = ''
    form.content = ''
    form.urgency = 'normal'
    load()
  } catch {
    ElMessage.error('发布失败')
  } finally {
    saving.value = false
  }
}

async function remove(a: AnnouncementItem) {
  try {
    await ElMessageBox.confirm(`确定删除公告「${a.title}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteAnnouncement(a.id)
    ElMessage.success('已删除')
    load()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.an-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 52px 0;
  color: #98a2b3;
  font-size: 13px;
}
.an-state p { margin: 0; }

.an-item { padding: 15px 16px; }
.an-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 7px;
}
.an-date { font-size: 12px; color: #98a2b3; }
.tui-chip.chip-warn { background: #fffaeb; color: #b54708; }
.tui-chip.chip-danger { background: #fef3f2; color: #d92d20; }

.an-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: #101828;
  line-height: 1.45;
}
.an-content {
  margin: 0;
  font-size: 13px;
  color: #475467;
  line-height: 1.7;
  white-space: pre-wrap;
}
.an-ops {
  display: flex;
  gap: 14px;
  margin-top: 10px;
}
.an-link {
  border: none;
  background: none;
  padding: 0;
  font-size: 12.5px;
  color: #2563eb;
  text-decoration: none;
  cursor: pointer;
  font-family: inherit;
}
.an-link-danger { color: #d92d20; }

.an-form { display: flex; flex-direction: column; gap: 16px; }
.an-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}
</style>