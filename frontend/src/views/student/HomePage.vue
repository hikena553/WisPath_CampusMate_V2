<template>
  <div class="home-page">
    <div v-if="unreadAnnouncements.length > 0" class="announce-banner">
      <div
        v-for="a in unreadAnnouncements.slice(0, 3)"
        :key="a.id"
        class="banner-item"
        :class="`banner-${a.urgency}`"
        @click="showAnnouncementDetail(a)"
      >
        <span class="banner-dot"></span>
        <span class="banner-text">{{ a.title }}</span>
        <el-tag :type="urgencyTag(a.urgency)" size="small" effect="dark" class="banner-tag">
          {{ urgencyLabel(a.urgency) }}
        </el-tag>
      </div>
      <div class="banner-footer">
        <el-button text size="small" type="primary" @click="goCampusAnnounce">
          查看全部公告 →
        </el-button>
      </div>
    </div>
    <div class="chat-main">
      <ChatShell />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStudentAnnouncements, getUnreadCount, markAnnouncementRead, type AnnouncementItem } from '@/api/announcement'
import { ElMessageBox } from 'element-plus'
import ChatShell from '@/components/agent/ChatShell.vue'

const router = useRouter()
const unreadAnnouncements = ref<AnnouncementItem[]>([])

function urgencyTag(u: string) {
  const map: Record<string, string> = { urgent: 'danger', important: 'warning', normal: '' }
  return map[u] || ''
}
function urgencyLabel(u: string) {
  const map: Record<string, string> = { urgent: '紧急', important: '重要', normal: '普通' }
  return map[u] || u
}

async function checkUnread() {
  try {
    const { count } = await getUnreadCount()
    if (count > 0) {
      const items = await getStudentAnnouncements(true)
      unreadAnnouncements.value = items
      if (items.length > 0) {
        const msg = items.slice(0, 5).map(a =>
          `[${urgencyLabel(a.urgency)}] ${a.title}`
        ).join('\n')
        await ElMessageBox.alert(msg, `您有 ${count} 条未读公告`, {
          confirmButtonText: '我知道了',
          type: 'info',
          dangerouslyUseHTMLString: false,
        })
        for (const a of items) {
          try { await markAnnouncementRead(a.id) } catch { /* ignore */ }
        }
        unreadAnnouncements.value = []
      }
    }
  } catch { /* ignore */ }
}

function showAnnouncementDetail(a: AnnouncementItem) {
  ElMessageBox.alert(a.content, a.title, {
    confirmButtonText: '我知道了',
    type: a.urgency === 'urgent' ? 'warning' : 'info',
  })
  markAnnouncementRead(a.id).catch(() => {})
  unreadAnnouncements.value = unreadAnnouncements.value.filter(x => x.id !== a.id)
}

function goCampusAnnounce() {
  router.push('/student/campus?tab=announcements')
}

onMounted(checkUnread)
</script>

<style scoped>
.home-page { display: flex; flex-direction: column; height: 100%; }
.chat-main { flex: 1; min-height: 0; }
.announce-banner {
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
  border-radius: 12px;
  padding: 12px 16px 8px;
  margin-bottom: 16px;
  border: 1px solid rgba(91,141,239,0.1);
}
.banner-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px;
  cursor: pointer; transition: background 0.2s;
  margin-bottom: 4px;
}
.banner-item:hover { background: rgba(91,141,239,0.08); }
.banner-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.banner-urgent .banner-dot { background: #f56c6c; box-shadow: 0 0 6px #f56c6c; }
.banner-important .banner-dot { background: #e6a23c; }
.banner-normal .banner-dot { background: #409eff; }
.banner-text {
  flex: 1; font-size: 13.5px; color: #333;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.banner-tag { flex-shrink: 0; }
.banner-footer { text-align: right; padding-top: 4px; }
</style>
