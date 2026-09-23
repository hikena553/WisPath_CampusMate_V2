<template>
  <div class="announcement-panel">
    <!-- 加载中 -->
    <div v-if="loading" class="ann-loading">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!list.length" class="ann-empty">
      <el-icon :size="44" class="ann-empty-icon"><Bell /></el-icon>
      <p class="ann-empty-title">暂无班级公告</p>
      <p class="ann-empty-sub">辅导员发布的班级通知会显示在这里</p>
    </div>

    <!-- 公告列表 -->
    <template v-else>
      <div
        v-for="a in list"
        :key="a.id"
        class="ann-item"
        :class="{ 'is-read': isRead(a.id) }"
        @click="markRead(a)"
      >
        <span class="ann-bar" :style="{ background: urgencyColor(a.urgency) }"></span>
        <div class="ann-main">
          <div class="ann-head">
            <span class="ann-title">{{ a.title }}</span>
            <el-tag :type="urgencyTagType(a.urgency)" size="small" effect="light" round>
              {{ urgencyLabel(a.urgency) }}
            </el-tag>
          </div>
          <p class="ann-content">{{ a.content }}</p>
          <div class="ann-meta">
            <span class="ann-meta-item"><el-icon><User /></el-icon>{{ a.teacher_name }}</span>
            <span class="ann-meta-item"><el-icon><Clock /></el-icon>{{ formatTime(a.created_at) }}</span>
            <a
              v-if="a.attachment_url"
              class="ann-attach"
              :href="a.attachment_url"
              target="_blank"
              @click.stop
            >
              <el-icon><Paperclip /></el-icon>附件
            </a>
          </div>
        </div>
        <el-icon v-if="!isRead(a.id)" class="ann-unread-dot"><Bell /></el-icon>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElSkeleton, ElTag, ElIcon } from 'element-plus'
import { Bell, User, Clock, Paperclip } from '@element-plus/icons-vue'
import {
  getStudentAnnouncements,
  markAnnouncementRead,
  type AnnouncementItem,
} from '@/api/announcement'

const emit = defineEmits<{ (e: 'read'): void }>()

const list = ref<AnnouncementItem[]>([])
const loading = ref(false)
const readIds = reactive(new Set<number>())

onMounted(load)

async function load() {
  loading.value = true
  try {
    list.value = await getStudentAnnouncements()
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function markRead(a: AnnouncementItem) {
  if (readIds.has(a.id)) return
  try {
    await markAnnouncementRead(a.id)
    readIds.add(a.id)
    emit('read')
  } catch {
    /* 标记失败不阻塞浏览 */
  }
}

function isRead(id: number) {
  return readIds.has(id)
}

function urgencyLabel(u: string) {
  const map: Record<string, string> = { urgent: '紧急', important: '重要', normal: '普通' }
  return map[u] || '普通'
}

function urgencyTagType(u: string): 'danger' | 'warning' | 'info' {
  if (u === 'urgent') return 'danger'
  if (u === 'important') return 'warning'
  return 'info'
}

function urgencyColor(u: string) {
  const map: Record<string, string> = { urgent: '#f56c6c', important: '#e6a23c', normal: '#409eff' }
  return map[u] || '#409eff'
}

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.announcement-panel {
  padding: 4px 0 8px;
}
.ann-loading {
  padding: 8px 4px;
}
.ann-empty {
  padding: 40px 16px;
  text-align: center;
  color: #c0c4cc;
}
.ann-empty-icon {
  color: #d6d9df;
  margin-bottom: 8px;
}
.ann-empty-title {
  font-size: 15px;
  color: #606266;
  margin: 0 0 6px;
}
.ann-empty-sub {
  font-size: 12px;
  color: #a8abb2;
  margin: 0;
}

.ann-item {
  position: relative;
  display: flex;
  gap: 12px;
  padding: 14px 12px;
  margin-bottom: 10px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.ann-item:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}
.ann-item.is-read {
  opacity: 0.82;
}
.ann-bar {
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 4px;
  border-radius: 0 4px 4px 0;
}
.ann-main {
  flex: 1;
  min-width: 0;
  padding-left: 4px;
}
.ann-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.ann-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ann-content {
  margin: 0 0 10px;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
  word-break: break-word;
  white-space: pre-wrap;
}
.ann-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: #909399;
}
.ann-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.ann-attach {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #409eff;
  text-decoration: none;
}
.ann-attach:hover {
  text-decoration: underline;
}
.ann-unread-dot {
  align-self: center;
  color: #409eff;
  font-size: 14px;
}
</style>