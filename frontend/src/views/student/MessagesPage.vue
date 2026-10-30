<template>
  <div class="msg-page no-dock-inset">
    <!-- 移动端吸顶栏：与其它学生页统一走 SubPageHeader -->
    <SubPageHeader v-if="isMobile" title="消息" fallback="/student" />
    <!-- 桌面端页头 -->
    <header v-else class="msg-head">
      <div class="msg-head-title">
        <h2>消息</h2>
        <span class="msg-head-sub">会话 · 通讯录 · 互动</span>
      </div>
      <div class="msg-head-actions">
        <button type="button" class="msg-ghost-btn" @click="refreshAll">
          <el-icon :size="14"><Refresh /></el-icon><span>刷新</span>
        </button>
      </div>
    </header>

    <div class="msg-main">
      <!-- 左侧：搜索 + 三栏页签 + 列表 -->
      <aside class="msg-side">
        <div class="msg-search">
          <el-icon :size="14"><Search /></el-icon>
          <input v-model="keyword" type="search" placeholder="搜索会话或联系人" />
        </div>

        <nav class="msg-tabs">
          <button
            v-for="t in mainTabs"
            :key="t.value"
            type="button"
            :class="['msg-tab', { active: activeTab === t.value }]"
            @click="activeTab = t.value"
          >
            {{ t.label }}
            <i v-if="tabBadge(t.value)" class="msg-tab-badge">{{ tabBadge(t.value) }}</i>
          </button>
        </nav>

        <div
          class="msg-list"
          @touchstart.passive="pull.onStart"
          @touchmove="pull.onMove"
          @touchend="pull.onEnd"
          @touchcancel="pull.onCancel"
        >
          <!-- 下拉刷新指示器：作为列表的第一个内容（吸顶栏在 .msg-list 之外，保持不动） -->
          <PullRefreshIndicator
            v-if="isMobile"
            :indicator-style="pull.indicatorStyle"
            :active="pull.active"
          />
          <!-- 会话：私聊 + 群聊合并，按最后消息时间排序 -->
          <template v-if="activeTab === 'sessions'">
            <div v-if="!filteredSessions.length" class="msg-empty">
              <el-icon :size="26"><ChatDotRound /></el-icon>
              <p>还没有会话</p>
              <span>去通讯录找人聊两句吧</span>
            </div>
            <button
              v-for="s in filteredSessions"
              :key="s.key"
              type="button"
              :class="['msg-session', { active: activeSession?.key === s.key }]"
              @click="openSession(s)"
            >
              <div class="msg-avatar">
                <el-avatar :size="40" :src="s.avatar || undefined">{{ s.name.slice(0, 1) }}</el-avatar>
                <i v-if="s.type === 'private' && isOnline(s.rawId)" class="msg-online-dot" aria-hidden="true"></i>
              </div>
              <div class="msg-session-main">
                <div class="msg-session-row">
                  <span class="msg-session-name">
                    <i v-if="s.type === 'group'" class="msg-group-mark">群</i>{{ s.name }}
                  </span>
                  <span class="msg-session-time">{{ formatTime(s.time) }}</span>
                </div>
                <div class="msg-session-row">
                  <span class="msg-session-last">{{ s.lastMessage || '暂无消息' }}</span>
                  <span v-if="s.unread" class="msg-unread">{{ s.unread > 99 ? '99+' : s.unread }}</span>
                </div>
              </div>
            </button>
          </template>

          <!-- 通讯录：好友（互关）/ 我关注的 / 关注我的 -->
          <template v-else-if="activeTab === 'contacts'">
            <div class="msg-sub-tabs">
              <button
                v-for="t in contactTabs"
                :key="t.value"
                type="button"
                :class="['msg-sub-tab', { active: contactTab === t.value }]"
                @click="switchContactTab(t.value)"
              >
                {{ t.label }}
              </button>
            </div>
            <div v-if="contactsLoading" class="msg-empty"><p>加载中…</p></div>
            <div v-else-if="!filteredContacts.length" class="msg-empty">
              <el-icon :size="26"><User /></el-icon>
              <p>{{ contactEmptyText }}</p>
              <span>{{ contactTab === 'following' ? '在交流社区关注感兴趣的同学' : '互相关注后自动成为好友' }}</span>
            </div>
            <div v-for="c in filteredContacts" v-else :key="c.id" class="msg-contact">
              <button type="button" class="msg-contact-main" @click="openHomepage(c.id)">
                <el-avatar :size="40" :src="c.avatar || undefined">{{ c.name.slice(0, 1) }}</el-avatar>
                <div class="msg-contact-info">
                  <span class="msg-contact-name">{{ c.name }}</span>
                  <span class="msg-contact-meta">{{ contactMeta(c) }}</span>
                </div>
              </button>
              <div class="msg-contact-actions">
                <button type="button" class="msg-ghost-btn" @click="chatWith(c)">发消息</button>
                <button
                  type="button"
                  :class="['msg-follow-btn', { following: c.is_following }]"
                  @click="toggleFollow(c)"
                >
                  {{ actionLabel(c) }}
                </button>
              </div>
            </div>
          </template>

          <!-- 互动：论坛的赞 / 收藏 / 评论 / 新粉丝，与聊天彻底分开 -->
          <template v-else>
            <div class="msg-inbox-head">
              <span>对我帖子的互动</span>
              <button v-if="forumUnread" type="button" class="msg-link-btn" @click="readAllForum">全部已读</button>
            </div>
            <div v-if="!forumList.length" class="msg-empty">
              <el-icon :size="26"><Star /></el-icon>
              <p>还没有互动消息</p>
              <span>点赞、收藏、评论都会汇总在这里</span>
            </div>
            <button
              v-for="m in forumList"
              v-else
              :key="m.id"
              type="button"
              :class="['msg-forum', { unread: !m.is_read }]"
              @click="openForum(m)"
            >
              <el-avatar :size="34" :src="m.actor_avatar || undefined">
                {{ (m.actor_name || '同学').slice(0, 1) }}
              </el-avatar>
              <div class="msg-forum-main">
                <div class="msg-forum-line">
                  <b>{{ m.actor_name || '同学' }}</b>
                  <span>{{ forumAction(m.kind) }}</span>
                  <span v-if="m.post_title" class="msg-forum-title">《{{ m.post_title }}》</span>
                </div>
                <p v-if="m.kind === 'comment' && m.content" class="msg-forum-quote">{{ m.content }}</p>
                <span class="msg-forum-time">{{ formatTime(m.created_at) }}</span>
              </div>
            </button>
          </template>
        </div>
      </aside>

      <!-- 右侧 / 移动端覆盖：会话窗口 -->
      <section v-if="!isMobile || chatOpen" :class="['msg-pane', { 'is-mobile-chat': isMobile }]">
        <template v-if="activeSession">
          <header class="msg-pane-head">
            <button v-if="isMobile" type="button" class="msg-back" aria-label="返回" @click="closeChat">
              <el-icon :size="18"><ArrowLeft /></el-icon>
            </button>
            <div class="msg-pane-title">
              <span class="msg-pane-name">{{ activeSession.name }}</span>
              <span v-if="activeSession.type === 'group'" class="msg-pane-meta">{{ groupMeta }}</span>
              <span v-else class="msg-pane-meta">{{ isOnline(activeSession.rawId) ? '在线' : '离线' }}</span>
            </div>
            <button
              v-if="activeSession.type === 'private'"
              type="button"
              class="msg-ghost-btn"
              @click="openHomepage(activeSession.rawId)"
            >
              主页
            </button>
          </header>

          <div ref="scrollEl" class="msg-chat-scroll">
            <div v-if="chatLoading" class="msg-empty"><p>加载中…</p></div>
            <div v-else-if="!messages.length" class="msg-empty">
              <el-icon :size="26"><ChatDotRound /></el-icon>
              <p>还没有聊天记录</p>
              <span>发条消息打个招呼吧</span>
            </div>
            <div v-else class="msg-bubbles">
              <div
                v-for="m in messages"
                :key="m.id"
                :class="['msg-bubble-row', { mine: isMine(m) }]"
              >
                <el-avatar
                  v-if="!isMine(m)"
                  :size="30"
                  :src="senderAvatar(m) || undefined"
                  class="msg-bubble-avatar"
                >
                  {{ senderName(m).slice(0, 1) }}
                </el-avatar>
                <div class="msg-bubble-wrap">
                  <span v-if="activeSession.type === 'group' && !isMine(m)" class="msg-bubble-sender">
                    {{ senderName(m) }}
                  </span>
                  <div class="msg-bubble">{{ m.content }}</div>
                  <span class="msg-bubble-time">{{ formatTime(m.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>

          <footer class="msg-composer">
            <textarea
              v-model="draft"
              rows="1"
              placeholder="输入消息，Enter 发送"
              @keydown.enter.exact.prevent="send"
            />
            <button type="button" class="msg-send" :disabled="sending || !draft.trim()" @click="send">
              <el-icon :size="16"><Promotion /></el-icon>
              <span>发送</span>
            </button>
          </footer>
        </template>
        <div v-else class="msg-pane-placeholder">
          <el-icon :size="34"><ChatLineRound /></el-icon>
          <p>选择一个会话开始聊天</p>
          <span>也可以从通讯录发消息</span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  ChatDotRound,
  ChatLineRound,
  Promotion,
  Refresh,
  Search,
  Star,
  User,
} from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useResponsive } from '@/composables/useResponsive'
import { useMobileSubPage } from '@/composables/useMobileSubPage'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { openUserHomepage } from '@/composables/useUserHomepage'
import {
  getConversations,
  getMessages,
  sendMessage,
  markRead,
  type ConversationOut,
  type MessageOut,
} from '@/api/messages'
import {
  getGroups,
  getGroupMessages,
  sendGroupMessage,
  markGroupRead,
  type GroupOut,
  type GroupMessageOut,
} from '@/api/groups'
import {
  getContacts,
  followUser,
  unfollowUser,
  getForumMessages,
  markForumRead,
  type ContactUser,
  type ForumMessageOut,
  type ForumKind,
} from '@/api/social'

const router = useRouter()
const { isMobile } = useResponsive()
const auth = useAuthStore()
const { refresh: refreshUnread, forum: forumUnread, isOnline, syncPresence } = useUnreadSummary()

type TabValue = 'sessions' | 'contacts' | 'forum'
type ContactTabValue = 'friends' | 'following' | 'followers'
type ChatMessage = MessageOut | GroupMessageOut

interface SessionItem {
  key: string
  type: 'private' | 'group'
  rawId: number
  name: string
  avatar: string | null
  lastMessage: string
  time: string | null
  unread: number
}

const mainTabs: Array<{ label: string; value: TabValue }> = [
  { label: '会话', value: 'sessions' },
  { label: '通讯录', value: 'contacts' },
  { label: '互动', value: 'forum' },
]
const contactTabs: Array<{ label: string; value: ContactTabValue }> = [
  { label: '好友', value: 'friends' },
  { label: '我关注的', value: 'following' },
  { label: '关注我的', value: 'followers' },
]

const activeTab = ref<TabValue>('sessions')
const contactTab = ref<ContactTabValue>('friends')
const keyword = ref('')

const conversations = ref<ConversationOut[]>([])
const groups = ref<GroupOut[]>([])
const activeSession = ref<SessionItem | null>(null)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const chatOpen = ref(false)
const chatLoading = ref(false)
const sending = ref(false)
const scrollEl = ref<HTMLElement | null>(null)

// 移动端进入会话属于二级页，聊天中让出底部悬浮导航
useMobileSubPage(computed(() => isMobile.value && chatOpen.value))

const contacts = ref<ContactUser[]>([])
const contactsLoading = ref(false)
const forumList = ref<ForumMessageOut[]>([])

let pollTimer: ReturnType<typeof setInterval> | null = null

// ---------- 会话合并 ----------
const sessions = computed<SessionItem[]>(() => {
  const list: SessionItem[] = []
  for (const c of conversations.value) {
    list.push({
      key: `s-${c.user_id}`,
      type: 'private',
      rawId: c.user_id,
      name: c.user_name,
      avatar: c.user_avatar,
      lastMessage: c.last_message,
      time: c.last_message_time,
      unread: c.unread_count || 0,
    })
  }
  for (const g of groups.value) {
    if (g.is_dismissed) continue
    list.push({
      key: `g-${g.id}`,
      type: 'group',
      rawId: g.id,
      name: g.name,
      avatar: g.avatar,
      lastMessage: g.last_message,
      time: g.last_message_time,
      unread: g.unread_count || 0,
    })
  }
  return list.sort((a, b) => (b.time ? Date.parse(b.time) : 0) - (a.time ? Date.parse(a.time) : 0))
})

const filteredSessions = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return sessions.value
  return sessions.value.filter((s) => s.name.toLowerCase().includes(kw))
})

const filteredContacts = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return contacts.value
  return contacts.value.filter(
    (c) => c.name.toLowerCase().includes(kw) || (c.class_name || '').toLowerCase().includes(kw),
  )
})

const groupMeta = computed(() => {
  if (!activeSession.value || activeSession.value.type !== 'group') return ''
  const g = groups.value.find((x) => x.id === activeSession.value?.rawId)
  if (!g) return ''
  return `${g.member_count} 人 · ${g.online_count} 在线${g.is_muted ? ' · 免打扰' : ''}`
})

const contactEmptyText = computed(
  () =>
    ({
      friends: '还没有好友',
      following: '还没有关注任何人',
      followers: '还没有人关注你',
    })[contactTab.value],
)

function tabBadge(tab: TabValue) {
  if (tab === 'sessions') return sessionUnreadTotal.value
  if (tab === 'forum') return forumUnread.value
  return 0
}

const sessionUnreadTotal = computed(() => sessions.value.reduce((sum, s) => sum + (s.unread || 0), 0))

// ---------- 数据加载 ----------
async function loadSessions() {
  try {
    const [conv, grp] = await Promise.all([getConversations(), getGroups()])
    conversations.value = conv
    groups.value = grp
    syncPresence(conv.map((c) => ({ user_id: c.user_id, online: c.online })))
  } catch {
    conversations.value = []
    groups.value = []
  }
}

async function loadContacts() {
  contactsLoading.value = true
  try {
    contacts.value = await getContacts({ tab: contactTab.value, keyword: keyword.value.trim() || undefined })
  } catch {
    contacts.value = []
  } finally {
    contactsLoading.value = false
  }
}

async function loadForum() {
  try {
    forumList.value = await getForumMessages({ limit: 50 })
  } catch {
    forumList.value = []
  }
}

async function refreshAll() {
  await Promise.all([loadSessions(), loadForum()])
  if (activeTab.value === 'contacts') await loadContacts()
  if (activeSession.value) await loadChat(false)
  void refreshUnread()
}

// 下拉刷新：复用桌面刷新按钮的 refreshAll，仅移动端生效（桌面左栏同样是 .msg-list）
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

function switchContactTab(tab: ContactTabValue) {
  if (contactTab.value === tab) return
  contactTab.value = tab
  void loadContacts()
}

// ---------- 会话窗口 ----------
function openSession(s: SessionItem) {
  activeSession.value = s
  chatOpen.value = true
  void loadChat(true)
}

function closeChat() {
  chatOpen.value = false
  activeSession.value = null
  messages.value = []
}

function chatWith(user: { id: number; name: string; avatar: string | null }) {
  openSession({
    key: `s-${user.id}`,
    type: 'private',
    rawId: user.id,
    name: user.name,
    avatar: user.avatar,
    lastMessage: '',
    time: null,
    unread: 0,
  })
}

async function loadChat(scrollToBottom: boolean) {
  const session = activeSession.value
  if (!session) return
  chatLoading.value = true
  try {
    if (session.type === 'group') {
      messages.value = await getGroupMessages(session.rawId)
      void markGroupRead(session.rawId)
      const g = groups.value.find((x) => x.id === session.rawId)
      if (g) g.unread_count = 0
    } else {
      messages.value = await getMessages(session.rawId)
      void markRead(session.rawId)
      const c = conversations.value.find((x) => x.user_id === session.rawId)
      if (c) c.unread_count = 0
    }
    void refreshUnread()
    if (scrollToBottom) await scrollBottom()
  } catch {
    messages.value = []
  } finally {
    chatLoading.value = false
  }
}

async function scrollBottom() {
  await nextTick()
  const el = scrollEl.value
  if (el) el.scrollTop = el.scrollHeight
}

async function send() {
  const session = activeSession.value
  const text = draft.value.trim()
  if (!session || !text || sending.value) return
  sending.value = true
  try {
    if (session.type === 'group') await sendGroupMessage(session.rawId, text)
    else await sendMessage(session.rawId, text)
    draft.value = ''
    await loadChat(true)
    await loadSessions()
  } catch {
    /* 失败保留草稿，用户可重试 */
  } finally {
    sending.value = false
  }
}

function isMine(m: ChatMessage) {
  return m.sender_id === (auth.user?.id ?? -1)
}

function senderName(m: ChatMessage) {
  if ('sender_name' in m) return m.sender_name
  return isMine(m) ? (auth.userName || '我') : activeSession.value?.name || ''
}

function senderAvatar(m: ChatMessage) {
  return 'sender_avatar' in m ? m.sender_avatar : null
}

// ---------- 通讯录 ------
function contactMeta(c: ContactUser) {
  const parts: string[] = []
  if (c.is_friend) parts.push('好友')
  if (c.class_name) parts.push(c.class_name)
  else if (c.college) parts.push(c.college)
  else if (c.role === 'teacher') parts.push('教师')
  return parts.join(' · ') || (c.is_following ? '已关注' : '')
}

function actionLabel(c: ContactUser) {
  if (c.is_following) return '已关注'
  return c.is_follower ? '回关' : '关注'
}

async function toggleFollow(c: ContactUser) {
  try {
    const state = c.is_following ? await unfollowUser(c.id) : await followUser(c.id)
    c.is_following = state.is_following
    c.is_follower = state.is_follower
    c.is_friend = state.is_friend
  } catch {
    /* 失败保持原状 */
  }
}

function openHomepage(id: number) {
  void openUserHomepage(id)
}

// ---------- 互动 ----------
function forumAction(kind: ForumKind) {
  return (
    { like: '赞了你的帖子', favorite: '收藏了你的帖子', comment: '评论了你的帖子', follow: '关注了你' }[kind] ||
    '与你互动'
  )
}

function openForum(m: ForumMessageOut) {
  if (m.kind === 'follow') {
    void openUserHomepage(m.actor_id)
    return
  }
  if (!m.post_id) return
  router.push({ name: 'student-community', query: { post: String(m.post_id) } })
}

async function readAllForum() {
  try {
    await markForumRead()
  } finally {
    forumList.value = forumList.value.map((m) => ({ ...m, is_read: true }))
    forumUnread.value = 0
    void refreshUnread()
  }
}

// ---------- 时间 ----------
function formatTime(t: string | null) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const pad = (n: number) => String(n).padStart(2, '0')
  if (sameDay) return `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}-${pad(d.getDate())}`
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

watch(activeTab, (tab) => {
  if (tab === 'contacts') void loadContacts()
  if (tab === 'forum') void loadForum()
})

onMounted(async () => {
  await loadSessions()
  void loadForum()
  // 会话未读与聊天轮询：移动端回到页面时不重复拉，靠 visibility 判断
  pollTimer = setInterval(() => {
    if (document.visibilityState !== 'visible') return
    void loadSessions()
    if (activeSession.value) void loadChat(false)
  }, 6000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
})
</script>

<style scoped>
/* ================= 页面骨架 ================= */
.msg-page { display: flex; flex-direction: column; height: 100%; min-height: 0; background: #f5f6f8; color: #1f2329; }
.msg-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 22px; background: #fff; border-bottom: 1px solid #f0f1f3; }
.msg-head-title { display: flex; align-items: baseline; gap: 10px; }
.msg-head-title h2 { margin: 0; font-size: 18px; font-weight: 600; }
.msg-head-sub { font-size: 12px; color: #9aa0a6; }
.msg-head-actions { display: flex; gap: 8px; }

.msg-main { flex: 1; min-height: 0; display: flex; gap: 0; }
.msg-side { width: 320px; flex-shrink: 0; display: flex; flex-direction: column; background: #fff; border-right: 1px solid #f0f1f3; min-height: 0; }

/* ================= 搜索 / 页签 ================= */
.msg-search { display: flex; align-items: center; gap: 6px; margin: 12px 14px 8px; padding: 7px 10px; background: #f5f6f8; border-radius: 9px; color: #9aa0a6; }
.msg-search input { flex: 1; border: none; outline: none; background: transparent; font-size: 13px; color: #1f2329; }
.msg-tabs { display: flex; gap: 4px; padding: 0 14px 8px; }
.msg-tab { position: relative; flex: 1; border: none; background: transparent; font-size: 13px; color: #6b7280; padding: 7px 0; border-radius: 8px; cursor: pointer; }
.msg-tab.active { background: #111827; color: #fff; font-weight: 500; }
.msg-tab-badge { position: absolute; top: 1px; right: 4px; min-width: 15px; padding: 1px 4px; border-radius: 8px; background: #111827; color: #fff; font-size: 10px; font-style: normal; line-height: 1.4; }
.msg-tab.active .msg-tab-badge { background: #fff; color: #111827; }

/* ================= 列表 ================= */
.msg-list { flex: 1; min-height: 0; overflow-y: auto; padding-bottom: 12px; scrollbar-width: thin; }
.msg-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 54px 20px; color: #9aa0a6; font-size: 13px; text-align: center; }
.msg-empty p { margin: 4px 0 0; color: #4b5563; font-size: 14px; }
.msg-empty span { font-size: 12px; }

.msg-session { width: 100%; display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: none; border: none; text-align: left; cursor: pointer; }
.msg-session:hover { background: #fafbfc; }
.msg-session.active { background: #f2f3f5; }
.msg-avatar { position: relative; flex-shrink: 0; }
.msg-online-dot { position: absolute; right: 1px; bottom: 1px; width: 8px; height: 8px; border-radius: 50%; background: #16a34a; border: 1.5px solid #fff; }
.msg-session-main { flex: 1; min-width: 0; }
.msg-session-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.msg-session-name { font-size: 14px; color: #1f2329; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.msg-group-mark { display: inline-block; margin-right: 4px; padding: 0 4px; border-radius: 4px; background: #eef0f3; color: #6b7280; font-size: 10px; font-style: normal; vertical-align: 1px; }
.msg-session-time { font-size: 11px; color: #9aa0a6; flex-shrink: 0; }
.msg-session-last { font-size: 12px; color: #9aa0a6; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.msg-unread { flex-shrink: 0; min-width: 16px; padding: 1px 5px; border-radius: 8px; background: #111827; color: #fff; font-size: 10px; text-align: center; }

/* ================= 通讯录 ================= */
.msg-sub-tabs { display: flex; gap: 6px; padding: 4px 14px 8px; }
.msg-sub-tab { border: 1px solid #e5e7eb; background: #fff; color: #6b7280; font-size: 12px; padding: 4px 12px; border-radius: 999px; cursor: pointer; }
.msg-sub-tab.active { border-color: #111827; background: #111827; color: #fff; }
.msg-contact { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid #f5f6f8; }
.msg-contact-main { flex: 1; min-width: 0; display: flex; align-items: center; gap: 10px; background: none; border: none; padding: 0; text-align: left; cursor: pointer; }
.msg-contact-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.msg-contact-name { font-size: 14px; color: #1f2329; font-weight: 500; }
.msg-contact-meta { font-size: 11px; color: #9aa0a6; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.msg-contact-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.msg-ghost-btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e7eb; background: #fff; color: #4b5563; font-size: 12px; padding: 4px 10px; border-radius: 999px; cursor: pointer; }
.msg-ghost-btn:hover { border-color: #d1d5db; color: #111827; }
.msg-follow-btn { border: 1px solid #e5e7eb; background: #fff; color: #111827; font-size: 12px; padding: 4px 12px; border-radius: 999px; cursor: pointer; }
.msg-follow-btn.following { border-color: #e5e7eb; color: #9aa0a6; background: #f5f6f8; }

/* ================= 互动 ================= */
.msg-inbox-head { display: flex; align-items: center; justify-content: space-between; padding: 6px 14px 8px; font-size: 12px; color: #9aa0a6; }
.msg-link-btn { border: none; background: none; color: #6b7280; font-size: 12px; cursor: pointer; }
.msg-link-btn:hover { color: #111827; text-decoration: underline; }
.msg-forum { width: 100%; display: flex; align-items: flex-start; gap: 10px; padding: 10px 14px; background: none; border: none; border-bottom: 1px solid #f5f6f8; text-align: left; cursor: pointer; }
.msg-forum.unread { background: #f7f8fa; }
.msg-forum-main { flex: 1; min-width: 0; }
.msg-forum-line { font-size: 13px; color: #4b5563; line-height: 1.45; }
.msg-forum-line b { color: #111827; margin-right: 3px; }
.msg-forum-title { color: #111827; }
.msg-forum-quote { margin: 4px 0 0; padding: 5px 8px; background: #f4f5f7; border-radius: 6px; font-size: 12px; color: #6b7280; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.msg-forum-time { display: inline-block; margin-top: 4px; font-size: 11px; color: #9aa0a6; }

/* ================= 会话窗口 ================= */
.msg-pane { flex: 1; min-width: 0; display: flex; flex-direction: column; background: #fff; }
.msg-pane-head { display: flex; align-items: center; gap: 8px; padding: 12px 18px; border-bottom: 1px solid #f0f1f3; }
.msg-pane-title { flex: 1; display: flex; flex-direction: column; gap: 1px; }
.msg-pane-name { font-size: 15px; font-weight: 600; color: #1f2329; }
.msg-pane-meta { font-size: 11px; color: #9aa0a6; }
.msg-back { border: none; background: #f4f5f7; width: 30px; height: 30px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: #4b5563; cursor: pointer; }
.msg-chat-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 18px; background: #f7f8fa; }
.msg-bubble-row { display: flex; gap: 8px; margin-bottom: 12px; align-items: flex-start; }
.msg-bubble-row.mine { flex-direction: row-reverse; }
.msg-bubble-avatar { flex-shrink: 0; background: #e9ebee; color: #6b7280; }
.msg-bubble-wrap { display: flex; flex-direction: column; max-width: 76%; }
.msg-bubble-row.mine .msg-bubble-wrap { align-items: flex-end; }
.msg-bubble-sender { font-size: 11px; color: #9aa0a6; margin-bottom: 3px; }
.msg-bubble { padding: 8px 12px; border-radius: 10px; background: #fff; font-size: 13.5px; line-height: 1.55; color: #1f2329; white-space: pre-wrap; word-break: break-word; }
.msg-bubble-row.mine .msg-bubble { background: #111827; color: #fff; }
.msg-bubble-time { margin-top: 3px; font-size: 10.5px; color: #9aa0a6; }
.msg-composer { display: flex; align-items: flex-end; gap: 8px; padding: 10px 14px calc(10px + env(safe-area-inset-bottom, 0px)); border-top: 1px solid #f0f1f3; background: #fff; }
.msg-composer textarea { flex: 1; resize: none; border: none; outline: none; background: #f5f6f8; border-radius: 10px; padding: 9px 12px; font-size: 13.5px; line-height: 1.5; max-height: 110px; color: #1f2329; }
.msg-send { display: inline-flex; align-items: center; gap: 4px; border: none; background: #111827; color: #fff; font-size: 13px; padding: 8px 14px; border-radius: 10px; cursor: pointer; }
.msg-send:disabled { background: #d1d5db; cursor: default; }
.msg-pane-placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; color: #9aa0a6; font-size: 13px; }
.msg-pane-placeholder p { margin: 6px 0 0; color: #4b5563; font-size: 14px; }
.msg-pane-placeholder span { font-size: 12px; }

/* ================= 移动端 ================= */
@media (max-width: 767px) {
  .msg-page { background: #fff; }
  .msg-head { display: none; }
  .msg-main { flex-direction: column; }
  .msg-side { width: 100%; border-right: none; flex: 1; }
  .msg-list { padding-bottom: calc(84px + env(safe-area-inset-bottom, 0px)); overscroll-behavior-y: contain; }
  .msg-pane.is-mobile-chat { position: fixed; inset: 0; z-index: 2600; background: #fff; }
  .msg-pane.is-mobile-chat .msg-pane-head { padding-top: calc(12px + env(safe-area-inset-top, 0px)); }
  .msg-pane.is-mobile-chat .msg-chat-scroll { padding-bottom: 18px; }
}
@media (min-width: 768px) {
  .msg-side { max-width: 340px; }
}
</style>
