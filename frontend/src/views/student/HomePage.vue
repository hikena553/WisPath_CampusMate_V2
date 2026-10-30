<template>
  <div class="home-page">
    <!-- 公告横幅：分级提醒 —— 紧急/重要才进横幅（紧急置顶强样式），普通公告只计红点 -->
    <div v-if="unreadAnnouncements.length > 0" class="announce-banner">
      <div
        v-for="a in bannerList"
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
      <!-- 只有普通公告时：不占横幅，仅一行轻提示，保留进入公告的入口 -->
      <div v-if="!bannerList.length" class="banner-item banner-item-quiet">
        <span class="banner-dot banner-dot-quiet"></span>
        <span class="banner-text">有 {{ unreadAnnouncements.length }} 条新通知</span>
      </div>
      <div class="banner-footer">
        <el-button text size="small" type="primary" @click="goCampusAnnounce">
          查看全部公告 →
        </el-button>
      </div>
    </div>
    <div class="chat-main">
      <ChatShell pull-refresh />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStudentAnnouncements, getUnreadCount, markAnnouncementRead, type AnnouncementItem } from '@/api/announcement'
// v6.1 弹窗减负：公告提醒用底部动作面板替代居中弹窗
import { actionAlert } from '@/composables/useActionSheet'
import ChatShell from '@/components/agent/ChatShell.vue'

const router = useRouter()
const unreadAnnouncements = ref<AnnouncementItem[]>([])

/** 会话内已强提醒过的紧急公告 id：避免同一次使用里反复弹窗 */
const urgentShown = new Set<number>()

/** 横幅只放「紧急 / 重要」：紧急在前；普通公告不进横幅，仅计红点 */
const bannerList = computed(() =>
  [...unreadAnnouncements.value]
    .filter((a) => a.urgency !== 'normal')
    .sort((a, b) => (a.urgency === 'urgent' ? 0 : 1) - (b.urgency === 'urgent' ? 0 : 1))
    .slice(0, 3)
)

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
    if (count <= 0) return
    const items = await getStudentAnnouncements(true)
    unreadAnnouncements.value = items

    // 紧急公告：无论学生当前停留在哪一屏，都强提醒一次（阻塞式确认）
    const fresh = items.filter((a) => a.urgency === 'urgent' && !urgentShown.has(a.id))
    if (fresh.length) {
      fresh.forEach((a) => urgentShown.add(a.id))
      try {
        await actionAlert(
          fresh.map((a) => `【${a.title}】\n${a.content}`).join('\n\n'),
          '紧急公告',
          { confirmButtonText: '我知道了' }
        )
      } catch {
        /* 用户关闭弹窗也视为已知晓，继续走已读标记 */
      }
      fresh.forEach((a) => markAnnouncementRead(a.id).catch(() => {}))
      unreadAnnouncements.value = unreadAnnouncements.value.filter((x) => !fresh.some((f) => f.id === x.id))
    }
  } catch { /* ignore */ }
}

function showAnnouncementDetail(a: AnnouncementItem) {
  actionAlert(a.content, a.title, { confirmButtonText: '我知道了' })
  markAnnouncementRead(a.id).catch(() => {})
  unreadAnnouncements.value = unreadAnnouncements.value.filter(x => x.id !== a.id)
}

function goCampusAnnounce() {
  router.push('/student/campus')
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
/* 仅普通公告时的弱提示行 */
.banner-item-quiet { cursor: default; }
.banner-dot-quiet { background: #c0c4cc; }
.banner-text {
  flex: 1; font-size: 13.5px; color: #333;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.banner-tag { flex-shrink: 0; }
.banner-footer { text-align: right; padding-top: 4px; }
</style>