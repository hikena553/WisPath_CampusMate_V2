<template>
  <div class="msg-page">
    <!-- ===== 顶部：标题 + 两个页签（消息 / 通讯录）=====
         论坛的赞、收藏、评论、新粉丝不在这里——它们在交流社区页右上角的互动消息里 -->
    <header class="msg-header">
      <div class="msg-header-inner">
        <div class="msg-title-row">
          <h1 class="msg-title">消息</h1>
          <button type="button" class="msg-icon-btn" aria-label="搜索" @click="openSearch">
            <DtIcon name="search" :size="20" />
          </button>
        </div>
        <div class="msg-tabs" role="tablist">
          <button
            v-for="t in tabs"
            :key="t.key"
            type="button"
            role="tab"
            class="msg-tab"
            :class="{ active: tab === t.key }"
            :aria-selected="tab === t.key"
            @click="switchTab(t.key)"
          >
            {{ t.label }}
            <i v-if="badgeOf(t.key)" class="msg-tab-badge">{{ badgeOf(t.key) > 99 ? '99+' : badgeOf(t.key) }}</i>
          </button>
        </div>
      </div>
    </header>

    <!-- ===== 内容区 ===== -->
    <div class="msg-body">
      <!-- 消息：常驻会话 + 群聊 + 好友私聊（论坛互动不混进来） -->
      <div v-if="tab === 'chats'" class="msg-scroll">
        <div class="msg-scroll-inner">
          <div class="msg-quick">
            <button
              v-for="q in quickEntries"
              :key="q.key"
              type="button"
              class="msg-quick-item"
              @click="q.action()"
            >
              <span class="msg-quick-icon" :style="{ background: q.bg, color: q.color }">
                <DtIcon :name="q.icon" :size="24" :filled="q.filled" />
                <i v-if="q.badge" class="msg-quick-badge">{{ q.badge > 99 ? '99+' : q.badge }}</i>
              </span>
              <span class="msg-quick-label">{{ q.label }}</span>
            </button>
          </div>

          <div v-if="feedingLoading" class="msg-tip">加载中…</div>
          <div v-else-if="!feedRows.length" class="msg-empty">
            <DtIcon name="empty" :size="48" style="color: var(--dt-text-quiet)" />
            <span>还没有聊天</span>
            <span class="msg-empty-hint">去「通讯录」互关好友后即可开始聊天</span>
            <button type="button" class="msg-empty-btn" @click="switchTab('contacts')">去通讯录</button>
          </div>
          <div v-else class="msg-list">
            <button
              v-for="row in feedRows"
              :key="row.key"
              type="button"
              class="msg-row"
              @click="openRow(row)"
            >
              <span class="msg-row-avatar">
                <el-avatar
                  :size="48"
                  :src="row.avatar || undefined"
                  class="msg-avatar-clickable"
                  title="查看个人主页"
                  @click.stop="!row.isGroup && openProfile(row.id)"
                >{{ row.name?.[0] }}</el-avatar>
                <i v-if="row.isGroup" class="msg-group-tag">群</i>
                <i v-if="row.unread" class="msg-unread">{{ row.unread > 99 ? '99+' : row.unread }}</i>
                <i v-if="!row.isGroup && row.online" class="msg-online" title="在线" />
              </span>
              <span class="msg-row-main">
                <span class="msg-row-top">
                  <span class="msg-row-name">{{ row.name }}</span>
                  <DtIcon v-if="row.muted" name="bellOff" :size="13" class="msg-muted" />
                  <span class="msg-row-time">{{ formatListTime(row.time) }}</span>
                </span>
                <span class="msg-row-preview">
                  <span v-if="row.isGroup && row.onlineCount" class="msg-online-count">{{ row.onlineCount }} 人在线</span>
                  <span class="msg-preview-text">{{ row.last || '暂无消息' }}</span>
                </span>
              </span>
            </button>
          </div>
        </div>
      </div>

      <!-- 通讯录：关注 / 粉丝 / 好友（互关） -->
      <ContactDirectory
        v-else
        ref="contactRef"
        @open-chat="openDirectUser"
        @open-profile="openProfile"
      />
    </div>

    <!-- ===== 搜索浮层：联系人 / 群聊 / 全站同学 ===== -->
    <Transition name="msg-fade">
      <div v-if="searchOpen" class="msg-search">
        <div class="msg-search-inner">
          <div class="msg-search-head">
            <button type="button" class="msg-icon-btn" aria-label="关闭搜索" @click="closeSearch">
              <DtIcon name="back" :size="22" />
            </button>
            <div class="msg-search-field">
              <DtIcon name="search" :size="16" class="msg-search-field-icon" />
              <input
                ref="searchInputRef"
                v-model="searchKw"
                type="search"
                class="msg-search-input"
                placeholder="搜索会话、同学或群聊"
              />
              <button v-if="searchKw" type="button" class="msg-search-clear" aria-label="清空" @click="searchKw = ''">
                <DtIcon name="close" :size="12" />
              </button>
            </div>
          </div>

          <div class="msg-search-body">
            <template v-if="!searchKw.trim()">
              <div class="msg-tip">输入姓名、学号或群名开始搜索</div>
            </template>
            <template v-else>
              <template v-if="searchRows.length">
                <div class="msg-search-section">会话与群聊</div>
                <div class="msg-list">
                  <button
                    v-for="row in searchRows"
                    :key="'r-' + row.key"
                    type="button"
                    class="msg-row"
                    @click="openRow(row); closeSearch()"
                  >
                    <span class="msg-row-avatar">
                      <el-avatar :size="44" :src="row.avatar || undefined">{{ row.name?.[0] }}</el-avatar>
                      <i v-if="row.isGroup" class="msg-group-tag">群</i>
                    </span>
                    <span class="msg-row-main">
                      <span class="msg-row-top"><span class="msg-row-name">{{ row.name }}</span></span>
                      <span class="msg-row-preview"><span class="msg-preview-text">{{ row.last || (row.isGroup ? '群聊' : '私聊') }}</span></span>
                    </span>
                  </button>
                </div>
              </template>

              <template v-if="searchUsers.length">
                <div class="msg-search-section">同学</div>
                <div class="msg-list">
                  <button
                    v-for="u in searchUsers"
                    :key="'u-' + u.id"
                    type="button"
                    class="msg-row"
                    @click="openDirectUser(u); closeSearch()"
                  >
                    <span class="msg-row-avatar">
                      <el-avatar :size="44" :src="u.avatar || undefined">{{ u.name?.[0] }}</el-avatar>
                    </span>
                    <span class="msg-row-main">
                      <span class="msg-row-top">
                        <span class="msg-row-name">{{ u.name }}</span>
                        <span v-if="u.is_friend" class="msg-friend-tag">互关</span>
                      </span>
                      <span class="msg-row-preview">
                        <span class="msg-preview-text">{{ u.class_name || u.college || (u.role === 'teacher' ? '教师' : '学生') }}</span>
                      </span>
                    </span>
                  </button>
                </div>
              </template>

              <div v-if="!searchRows.length && !searchUsers.length && !searchingUsers" class="msg-empty">
                <DtIcon name="grid" :size="44" style="color: var(--dt-text-quiet)" />
                <span>没有找到相关内容</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ===== 子页：聊天 / 小绵管家 / 通知 / 文件 ===== -->
    <Transition name="msg-slide">
      <div v-if="view" class="msg-sub">
        <header class="msg-sub-head">
          <button type="button" class="msg-icon-btn" aria-label="返回" @click="closeView">
            <DtIcon name="back" :size="22" />
          </button>
          <div class="msg-sub-title">
            <template v-if="view === 'chat'">
              <el-avatar
                v-if="chatKind === 'direct'"
                :size="26"
                :src="chatAvatar || undefined"
                class="msg-sub-avatar"
              >{{ chatName?.[0] }}</el-avatar>
              <span class="msg-sub-name">{{ chatName }}</span>
              <span v-if="chatKind === 'group'" class="msg-sub-sub">{{ chatGroup?.member_count || 0 }} 人</span>
              <span v-else-if="chatOnline" class="msg-sub-sub is-online">在线</span>
            </template>
            <template v-else-if="view === 'butler'">{{ agentName || '小绵' }}管家</template>
            <template v-else-if="view === 'notifications'">通知</template>
            <template v-else>文件</template>
          </div>
          <button
            v-if="view === 'chat' && chatKind === 'direct' && chatUserId"
            type="button"
            class="msg-icon-btn"
            title="查看对方主页"
            @click="openProfile(chatUserId)"
          >
            <DtIcon name="user" :size="19" />
          </button>
          <button
            v-else-if="view === 'notifications' && notifUnread"
            type="button"
            class="msg-sub-action"
            @click="readAllNotifications"
          >全部已读</button>
          <span v-else class="msg-sub-holder" />
        </header>

        <!-- 聊天 -->
        <template v-if="view === 'chat'">
          <div ref="chatScrollRef" class="msg-chat">
            <div v-if="!chatMsgs.length" class="msg-empty">
              <DtIcon name="empty" :size="46" style="color: var(--dt-text-quiet)" />
              <span>暂无消息，打个招呼吧</span>
            </div>
            <template v-for="item in chatTimeline" :key="item.type === 'date' ? 'd-' + item.date : 'm-' + item.msg.id">
              <div v-if="item.type === 'date'" class="msg-date-sep"><span>{{ item.label }}</span></div>
              <div v-else class="msg-bubble-row" :class="item.msg.sender_id === auth.user?.id ? 'mine' : 'theirs'">
                <div class="msg-bubble-wrap">
                  <div v-if="chatKind === 'group' && item.msg.sender_id !== auth.user?.id" class="msg-bubble-sender">
                    {{ item.msg.sender_name || '同学' }}
                  </div>
                  <div class="msg-bubble">{{ renderContent(item.msg.content) }}</div>
                </div>
              </div>
            </template>
          </div>
          <div class="msg-input-bar">
            <div class="msg-input-box">
              <textarea
                v-model="chatDraft"
                class="msg-textarea"
                rows="1"
                placeholder="输入消息…"
                @keydown.enter.prevent="sendChat"
              />
              <button type="button" class="msg-send" :disabled="!chatDraft.trim()" @click="sendChat">
                <DtIcon name="send" :size="18" :filled="true" />
              </button>
            </div>
          </div>
        </template>

        <!-- 小绵管家：常驻 AI 会话，自动推送资讯 / 总结对话 -->
        <ButlerChat v-else-if="view === 'butler'" role="student" class="msg-butler" />

        <!-- 通知：审批 / 请假 / 公告 / 预警 -->
        <div v-else-if="view === 'notifications'" class="msg-scroll">
          <div class="msg-scroll-inner">
            <div v-if="notifLoading" class="msg-tip">加载中…</div>
            <div v-else-if="!notifications.length" class="msg-empty">
              <DtIcon name="bell" :size="46" style="color: var(--dt-text-quiet)" />
              <span>暂无通知</span>
            </div>
            <div v-else class="msg-list">
              <button
                v-for="n in notifications"
                :key="n.id"
                type="button"
                class="msg-notif"
                :class="{ unread: !n.is_read }"
                @click="openNotification(n)"
              >
                <i class="msg-notif-dot" :class="{ hidden: n.is_read }" />
                <span class="msg-notif-main">
                  <span class="msg-notif-top">
                    <span class="msg-notif-title">{{ n.title }}</span>
                    <span class="msg-row-time">{{ formatListTime(n.created_at) }}</span>
                  </span>
                  <span class="msg-preview-text">{{ n.content }}</span>
                </span>
              </button>
            </div>
          </div>
        </div>

        <!-- 文件：跨会话文件汇总 -->
        <div v-else class="msg-scroll">
          <div class="msg-scroll-inner">
            <div class="msg-file-filters">
              <button
                v-for="f in FILE_FILTERS"
                :key="f.key"
                type="button"
                class="msg-file-filter"
                :class="{ active: fileType === f.key }"
                @click="setFileType(f.key)"
              >{{ f.label }}</button>
            </div>
            <div v-if="filesLoading" class="msg-tip">加载中…</div>
            <div v-else-if="!files.length" class="msg-empty">
              <DtIcon name="file" :size="44" style="color: var(--dt-text-quiet)" />
              <span>暂无聊天文件</span>
            </div>
            <div v-else class="msg-list">
              <button v-for="f in files" :key="f.id" type="button" class="msg-file-row" @click="openFile(f)">
                <span class="msg-file-thumb">
                  <img v-if="f.file_type === 'image'" :src="f.url" alt="" loading="lazy" />
                  <DtIcon v-else :name="f.file_type === 'voice' ? 'microphone' : 'document'" :size="18" />
                </span>
                <span class="msg-row-main">
                  <span class="msg-row-top">
                    <span class="msg-row-name">{{ f.name || '(未命名)' }}</span>
                    <span class="msg-row-time">{{ formatListTime(f.created_at) }}</span>
                  </span>
                  <span class="msg-row-preview">
                    <span class="msg-preview-text">{{ f.sender_name }} · {{ f.is_group ? '群聊' : '私聊' }}「{{ f.session_name }}」</span>
                  </span>
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 发起群聊：勾选互关好友 -->
    <el-dialog v-model="groupDialog" title="发起群聊" width="420px" :close-on-click-modal="false">
      <div class="msg-group-form">
        <el-input v-model="groupName" placeholder="群名称（例如：算法小组）" maxlength="30" show-word-limit />
        <div class="msg-group-hint">只能邀请互关好友，入群后可继续拉人</div>
        <div v-if="!groupCandidates.length" class="msg-tip">还没有互关好友，先去通讯录关注同学吧</div>
        <div v-else class="msg-group-picker">
          <button
            v-for="u in groupCandidates"
            :key="u.id"
            type="button"
            class="msg-group-member"
            :class="{ picked: groupMemberIds.includes(u.id) }"
            @click="toggleGroupMember(u.id)"
          >
            <el-avatar :size="38" :src="u.avatar || undefined">{{ u.name?.[0] }}</el-avatar>
            <span class="msg-group-member-name">{{ u.name }}</span>
            <DtIcon v-if="groupMemberIds.includes(u.id)" name="check" :size="14" class="msg-group-check" />
          </button>
        </div>
      </div>
      <template #footer>
        <el-button @click="groupDialog = false">取消</el-button>
        <el-button type="primary" :loading="creatingGroup" @click="createNewGroup">创建群聊</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 学生端「消息」页（原「工作台」页签位）
 *
 * 信息架构（2026-10 改版）：
 *   消息    —— 小绵管家 / 通知 / 文件 / 发起群聊 + 好友私聊与群聊会话流
 *   通讯录  —— 关注 / 粉丝 / 好友（互关），互关后才出现「私信」，也支持搜索同学
 *
 * 论坛互动（赞 / 收藏 / 评论 / 新粉丝）**不在本页**：它归交流社区页右上角的
 * 互动消息入口（ForumInboxSheet），另一套表、另一份未读，两边彻底分开。
 * 「好友」= 互相关注，聊天、论坛、个人主页共用同一套关注关系（/api/social），
 * 因此不会出现「主页显示互关、消息页却没有」的割裂。
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import DtIcon from '@/components/common/DtIcon.vue'
import ContactDirectory from '@/components/messages/ContactDirectory.vue'
import ButlerChat from '@/components/butler/ButlerChat.vue'

import {
  getConversations, getMessages, sendMessage, markRead,
  getSharedFiles, type ConversationOut, type SharedFile,
} from '@/api/messages'
import {
  getGroups, getGroupMessages, sendGroupMessage, markGroupRead, createGroup,
  type GroupOut, type GroupMessageOut,
} from '@/api/groups'
import {
  getNotifications, markNotificationsRead, markAllNotificationsRead,
  type Notification as NotificationItem,
} from '@/api/notification'
import {
  searchSocialUsers, getFriends,
  type SocialUser,
} from '@/api/social'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { openUserHomepage } from '@/composables/useUserHomepage'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { agentName } = useSiteConfig()

// 全局未读（单聊 + 群聊 + 站内通知）：与布局层共用同一份计数。
// 论坛互动未读不在本页（归交流社区页的互动消息入口），所以这里不取 forum。
const {
  chat: chatUnread, group: groupUnread, notification: notifUnread,
  isOnline, syncPresence, refresh: refreshUnread,
} = useUnreadSummary()

type TabKey = 'chats' | 'contacts'
const tabs: Array<{ key: TabKey; label: string }> = [
  { key: 'chats', label: '消息' },
  { key: 'contacts', label: '通讯录' },
]
const tab = ref<TabKey>('chats')

const contactRef = ref<InstanceType<typeof ContactDirectory> | null>(null)

function badgeOf(key: TabKey) {
  if (key === 'chats') return (chatUnread.value || 0) + (groupUnread.value || 0)
  return 0
}

function switchTab(key: TabKey) {
  tab.value = key
  if (key === 'contacts') void contactRef.value?.reload()
  if (key === 'chats') void loadChats()
}

// ===== 会话流（群聊 + 私聊混排） =====
const conversations = ref<ConversationOut[]>([])
const myGroups = ref<GroupOut[]>([])
const feedingLoading = ref(false)

interface FeedRow {
  key: string
  isGroup: boolean
  id: number
  name: string
  avatar: string | null
  last: string
  time: string | null
  unread: number
  muted: boolean
  online: boolean
  onlineCount: number
}

function rowTime(ts: string | null) {
  return ts ? parseTime(ts).getTime() : 0
}

const feedRows = computed<FeedRow[]>(() => {
  const rows: FeedRow[] = [
    ...myGroups.value.map((g) => ({
      key: `g-${g.id}`, isGroup: true, id: g.id, name: g.name, avatar: g.avatar,
      last: g.last_message, time: g.last_message_time, unread: g.unread_count || 0,
      muted: !!g.is_muted, online: false, onlineCount: g.online_count || 0,
    })),
    ...conversations.value.map((c) => ({
      key: `s-${c.user_id}`, isGroup: false, id: c.user_id, name: c.user_name, avatar: c.user_avatar,
      last: c.last_message, time: c.last_message_time, unread: c.unread_count || 0,
      muted: false, online: isOnline(c.user_id) || !!c.online, onlineCount: 0,
    })),
  ]
  return rows.sort((a, b) => rowTime(b.time) - rowTime(a.time))
})

async function loadChats() {
  feedingLoading.value = !conversations.value.length && !myGroups.value.length
  try {
    const [convs, groups] = await Promise.all([getConversations(), getGroups()])
    conversations.value = convs
    myGroups.value = groups
    syncPresence(convs.map((c) => ({ user_id: c.user_id, online: !!c.online })))
  } catch {
    /* 网络异常保留旧数据 */
  } finally {
    feedingLoading.value = false
  }
}

// ===== 快捷入口 =====
const quickEntries = computed(() => [
  {
    key: 'butler', label: `${agentName.value || '小绵'}管家`, icon: 'robot', filled: false,
    bg: '#e8f3ff', color: '#0089ff', action: () => { view.value = 'butler' },
  },
  {
    key: 'notif', label: '通知', icon: 'bell', filled: false,
    bg: '#fff7e8', color: '#ff7d00', badge: notifUnread.value, action: () => openNotifications(),
  },
  {
    key: 'files', label: '文件', icon: 'document', filled: false,
    bg: '#f2f3f5', color: '#5c6269', action: () => openFiles(),
  },
  {
    key: 'group', label: '发起群聊', icon: 'users', filled: false,
    bg: '#e8ffea', color: '#00b42a', action: () => openGroupDialog(),
  },
])

// ===== 子页路由（聊天 / 通知 / 文件 / 管家） =====
const view = ref<'' | 'chat' | 'butler' | 'notifications' | 'files'>('')

// ===== 聊天 =====
const chatKind = ref<'direct' | 'group'>('direct')
const chatUserId = ref(0)
const chatGroup = ref<GroupOut | null>(null)
const chatMsgs = ref<Array<{ id: number; sender_id: number; content: string; created_at: string; sender_name?: string }>>([])
const chatDraft = ref('')
const chatScrollRef = ref<HTMLElement>()
const directName = ref('')
const chatAvatar = ref('')
const chatName = computed(() => (chatKind.value === 'group' ? chatGroup.value?.name || '群聊' : directName.value))
const chatOnline = computed(() => (chatKind.value === 'direct' ? isOnline(chatUserId.value) : false))

let chatTimer: ReturnType<typeof setInterval> | null = null

function stopChatPolling() {
  if (chatTimer) { clearInterval(chatTimer); chatTimer = null }
}

function startChatPolling() {
  stopChatPolling()
  // 聊天页轮询兜底：WS 只负责刷新未读，会话内的新消息靠轻量轮询补上
  chatTimer = setInterval(() => {
    if (view.value !== 'chat' || document.hidden) return
    void reloadChatSilently()
  }, 5000)
}

function openDirectUser(u: Pick<SocialUser, 'id' | 'name' | 'avatar'> | ConversationOut) {
  const id = 'id' in u ? u.id : (u as ConversationOut).user_id
  const name = 'name' in u ? u.name : (u as ConversationOut).user_name
  const avatar = 'avatar' in u ? u.avatar : (u as ConversationOut).user_avatar
  chatKind.value = 'direct'
  chatUserId.value = id
  directName.value = name || ''
  chatAvatar.value = avatar || ''
  chatGroup.value = null
  chatMsgs.value = []
  view.value = 'chat'
  void loadDirectMessages()
  startChatPolling()
}

function openGroupChat(g: GroupOut) {
  chatKind.value = 'group'
  chatGroup.value = g
  chatMsgs.value = []
  view.value = 'chat'
  void loadGroupMessages()
  startChatPolling()
}

function openRow(row: FeedRow) {
  if (row.isGroup) {
    const g = myGroups.value.find((x) => x.id === row.id)
    if (g) openGroupChat(g)
  } else {
    const conv = conversations.value.find((c) => c.user_id === row.id)
    openDirectUser(conv || { user_id: row.id, user_name: row.name, user_avatar: row.avatar } as ConversationOut)
  }
}

async function loadDirectMessages() {
  try {
    chatMsgs.value = (await getMessages(chatUserId.value)) as any
    await markRead(chatUserId.value)
    const conv = conversations.value.find((c) => c.user_id === chatUserId.value)
    if (conv) conv.unread_count = 0
    void refreshUnread()
    await nextTick()
    scrollChatToBottom()
  } catch {
    chatMsgs.value = []
  }
}

async function loadGroupMessages() {
  const g = chatGroup.value
  if (!g) return
  try {
    chatMsgs.value = (await getGroupMessages(g.id)) as GroupMessageOut[]
    await markGroupRead(g.id)
    g.unread_count = 0
    void refreshUnread()
    await nextTick()
    scrollChatToBottom()
  } catch {
    chatMsgs.value = []
  }
}

/** 轮询静默刷新：只在消息数量变化时替换 + 滚到底，避免打断用户上翻历史 */
async function reloadChatSilently() {
  try {
    const list = chatKind.value === 'group' && chatGroup.value
      ? await getGroupMessages(chatGroup.value.id)
      : await getMessages(chatUserId.value)
    if (list.length !== chatMsgs.value.length) {
      chatMsgs.value = list as any
      await nextTick()
      scrollChatToBottom()
    }
  } catch { /* 轮询失败静默 */ }
}

async function sendChat() {
  const text = chatDraft.value.trim()
  if (!text) return
  try {
    if (chatKind.value === 'group' && chatGroup.value) {
      const res = await sendGroupMessage(chatGroup.value.id, text)
      chatMsgs.value.push({
        id: res.id, sender_id: auth.user?.id || 0, content: text,
        created_at: res.created_at, sender_name: auth.userName || '我',
      })
    } else if (chatUserId.value) {
      const res = await sendMessage(chatUserId.value, text)
      chatMsgs.value.push({
        id: res.id, sender_id: auth.user?.id || 0, content: text, created_at: res.created_at,
      })
    }
    chatDraft.value = ''
    await nextTick()
    scrollChatToBottom()
  } catch {
    ElMessage.error('发送失败，请稍后重试')
  }
}

function scrollChatToBottom() {
  const el = chatScrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

/** 附件类消息（文件 / 图片 / 语音）内容是一段 JSON，气泡里只展示可读摘要 */
function renderContent(content: string) {
  if (!content || !content.startsWith('{')) return content
  try {
    const data = JSON.parse(content)
    if (!data?.type || !data?.url) return content
    if (data.type === 'image') return data.text ? `[图片] ${data.text}` : '[图片]'
    if (data.type === 'voice') return `[语音] ${Math.round(data.duration || 0)}"`
    return `[文件] ${data.text || '未命名文件'}`
  } catch {
    return content
  }
}

// ===== 聊天时间线（按本地日期插入分隔线） =====
function parseTime(iso: string) {
  return new Date(iso + (iso.includes('Z') || iso.includes('+') ? '' : 'Z'))
}
function dateStr(t: string) {
  const d = parseTime(t)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}
function dateLabel(t: string) {
  const date = parseTime(t)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.round((today.getTime() - target.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff === 2) return '前天'
  if (diff < 7) return `${diff}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

const chatTimeline = computed(() => {
  const items: Array<{ type: 'date'; date: string; label: string } | { type: 'msg'; msg: any }> = []
  let last = ''
  for (const m of chatMsgs.value) {
    const d = dateStr(m.created_at)
    if (d !== last) {
      items.push({ type: 'date', date: d, label: dateLabel(m.created_at) })
      last = d
    }
    items.push({ type: 'msg', msg: m })
  }
  return items
})

function formatListTime(iso: string | null) {
  if (!iso) return ''
  const d = parseTime(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  if (sameDay) return hm
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return `昨天`
  if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}/${d.getDate()}`
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
}

function closeView() {
  stopChatPolling()
  view.value = ''
  chatDraft.value = ''
  void loadChats()
  void refreshUnread()
}

/** 打开他人主页：浮层常驻在布局层，关闭后仍回到消息页 */
function openProfile(userId: number) {
  openUserHomepage(userId)
}

// ===== 通知 =====
const notifications = ref<NotificationItem[]>([])
const notifLoading = ref(false)
const notifLocalUnread = ref(0)

async function openNotifications() {
  view.value = 'notifications'
  notifLoading.value = true
  try {
    notifications.value = await getNotifications({ page_size: 50 })
    notifLocalUnread.value = notifications.value.filter((n) => !n.is_read).length
    notifUnread.value = notifLocalUnread.value
  } catch {
    notifications.value = []
  } finally {
    notifLoading.value = false
  }
}

async function openNotification(n: NotificationItem) {
  if (!n.is_read) {
    try {
      await markNotificationsRead([n.id])
      n.is_read = true
      notifLocalUnread.value = Math.max(0, notifLocalUnread.value - 1)
      notifUnread.value = notifLocalUnread.value
    } catch { /* 标记失败不阻断跳转 */ }
  }
  if (n.link) router.push(n.link)
  else ElMessage.info(n.content || '该通知暂无关联页面')
}

async function readAllNotifications() {
  try {
    await markAllNotificationsRead()
    notifications.value = notifications.value.map((n) => ({ ...n, is_read: true }))
    notifLocalUnread.value = 0
    notifUnread.value = 0
    void refreshUnread()
    ElMessage.success('已全部标记为已读')
  } catch {
    ElMessage.error('操作失败，请稍后重试')
  }
}

// ===== 文件 =====
const files = ref<SharedFile[]>([])
const filesLoading = ref(false)
const fileType = ref<'' | 'file' | 'image' | 'voice'>('')
const FILE_FILTERS = [
  { key: '' as const, label: '全部' },
  { key: 'image' as const, label: '图片' },
  { key: 'file' as const, label: '文档' },
  { key: 'voice' as const, label: '语音' },
]

async function openFiles() {
  view.value = 'files'
  await loadFiles()
}

async function loadFiles() {
  filesLoading.value = true
  try {
    const res = await getSharedFiles({ file_type: fileType.value || undefined })
    files.value = res.items || []
  } catch {
    files.value = []
  } finally {
    filesLoading.value = false
  }
}

function setFileType(key: '' | 'file' | 'image' | 'voice') {
  fileType.value = key
  void loadFiles()
}

function openFile(f: SharedFile) {
  const a = document.createElement('a')
  a.href = f.url
  a.rel = 'noopener'
  if (f.file_type === 'image') a.target = '_blank'
  else a.download = f.name || '文件'
  a.click()
}

// ===== 搜索浮层 =====
const searchOpen = ref(false)
const searchKw = ref('')
const searchInputRef = ref<HTMLInputElement>()
const searchUsers = ref<SocialUser[]>([])
const searchingUsers = ref(false)

const searchRows = computed(() => {
  const kw = searchKw.value.trim().toLowerCase()
  if (!kw) return []
  return feedRows.value.filter((r) => r.name.toLowerCase().includes(kw))
})

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchKw, (kw) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!kw.trim()) { searchUsers.value = []; return }
  searchTimer = setTimeout(async () => {
    searchingUsers.value = true
    try {
      searchUsers.value = await searchSocialUsers(kw.trim(), 10)
    } catch {
      searchUsers.value = []
    } finally {
      searchingUsers.value = false
    }
  }, 260)
})

function openSearch() {
  searchOpen.value = true
  searchKw.value = ''
  nextTick(() => searchInputRef.value?.focus())
}
function closeSearch() {
  searchOpen.value = false
  searchKw.value = ''
}

// ===== 发起群聊 =====
const groupDialog = ref(false)
const groupName = ref('')
const groupCandidates = ref<SocialUser[]>([])
const groupMemberIds = ref<number[]>([])
const creatingGroup = ref(false)

async function openGroupDialog() {
  groupName.value = ''
  groupMemberIds.value = []
  groupDialog.value = true
  try {
    groupCandidates.value = await getFriends()
  } catch {
    groupCandidates.value = []
  }
}

function toggleGroupMember(id: number) {
  const idx = groupMemberIds.value.indexOf(id)
  if (idx >= 0) groupMemberIds.value.splice(idx, 1)
  else groupMemberIds.value.push(id)
}

async function createNewGroup() {
  if (!groupName.value.trim()) { ElMessage.warning('请填写群名称'); return }
  if (!groupMemberIds.value.length) { ElMessage.warning('至少邀请一位互关好友'); return }
  creatingGroup.value = true
  try {
    const res = await createGroup({ name: groupName.value.trim(), member_ids: groupMemberIds.value })
    groupDialog.value = false
    await loadChats()
    const g = myGroups.value.find((x) => x.id === res.id)
    if (g) openGroupChat(g)
    ElMessage.success('群聊已创建')
  } catch {
    ElMessage.error('创建失败，请稍后重试')
  } finally {
    creatingGroup.value = false
  }
}

// ===== 深链：?chat=<id>&chatName=&draft= / ?tab=contacts|chats =====
function applyQuery() {
  const chatId = Number(route.query.chat || 0)
  const tabQ = String(route.query.tab || '')
  if (chatId) {
    const conv = conversations.value.find((c) => c.user_id === chatId)
    openDirectUser(conv || ({
      user_id: chatId,
      user_name: String(route.query.chatName || ''),
      user_avatar: null,
    } as ConversationOut))
    if (route.query.draft) chatDraft.value = String(route.query.draft)
    void loadChats()
  } else if (tabQ === 'contacts' || tabQ === 'chats') {
    tab.value = tabQ as TabKey
    if (tabQ === 'contacts') void contactRef.value?.reload()
  }
  if (chatId || tabQ) router.replace({ query: {} })
}

onMounted(() => {
  void loadChats()
  applyQuery()
})

watch(
  () => [route.query.chat, route.query.tab],
  () => { if (route.query.chat || route.query.tab) applyQuery() },
)

// 从其他页面回到本页（keep-alive 或同路由）时刷新一次会话与未读
onUnmounted(stopChatPolling)
</script>

<style scoped>
.msg-page {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--dt-bg, #f5f6f7);
  color: var(--dt-text, #171a1d);
  overflow: hidden;
}

/* ===== 顶部 ===== */
.msg-header {
  flex-shrink: 0;
  background: var(--dt-surface, #fff);
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.msg-header-inner {
  max-width: 880px;
  margin: 0 auto;
  padding: 10px 16px 0;
}
.msg-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.msg-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: .01em;
}
.msg-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--dt-text-secondary);
  cursor: pointer;
  transition: background .18s ease;
}
.msg-icon-btn:hover { background: var(--dt-hover, rgba(0, 0, 0, .04)); }

.msg-tabs {
  display: flex;
  align-items: center;
  gap: 22px;
  margin-top: 6px;
}
.msg-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 0 10px;
  border: 0;
  background: transparent;
  color: var(--dt-text-secondary);
  font-size: 14px;
  cursor: pointer;
}
.msg-tab::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 2px;
  width: 0;
  height: 2.5px;
  border-radius: 2px;
  background: var(--dt-primary, #0089ff);
  transform: translateX(-50%);
  transition: width .22s ease;
}
.msg-tab.active { color: var(--dt-text); font-weight: 650; }
.msg-tab.active::after { width: 20px; }
.msg-tab-badge {
  font-style: normal;
  min-width: 16px;
  height: 16px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--dt-danger, #f53f3f);
  color: #fff;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
}

/* ===== 内容 ===== */
.msg-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.msg-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: none;
}
.msg-scroll::-webkit-scrollbar { display: none; }
.msg-scroll-inner {
  max-width: 880px;
  margin: 0 auto;
  padding: 12px 16px 24px;
}

/* 快捷入口 */
.msg-quick {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 14px 10px;
  margin-bottom: 12px;
  border-radius: 14px;
  background: var(--dt-surface, #fff);
}
.msg-quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.msg-quick-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  border-radius: 16px;
}
.msg-quick-badge {
  position: absolute;
  top: -4px;
  right: -6px;
  min-width: 17px;
  height: 17px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--dt-danger, #f53f3f);
  border: 1.5px solid #fff;
  color: #fff;
  font-size: 10px;
  font-style: normal;
  line-height: 14px;
  text-align: center;
}
.msg-quick-label { font-size: 12px; color: var(--dt-text-secondary); }

/* 会话列表 */
.msg-list {
  border-radius: 14px;
  background: var(--dt-surface, #fff);
  overflow: hidden;
}
.msg-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 14px;
  border: 0;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background .16s ease;
}
.msg-row:last-child { border-bottom: 0; }
.msg-row:hover { background: var(--dt-hover, rgba(0, 0, 0, .03)); }
.msg-row-avatar { position: relative; flex-shrink: 0; display: inline-flex; }
.msg-avatar-clickable { cursor: pointer; }
.msg-group-tag {
  position: absolute;
  right: -3px;
  bottom: -2px;
  padding: 0 4px;
  border-radius: 6px;
  background: var(--dt-primary, #0089ff);
  border: 1.5px solid #fff;
  color: #fff;
  font-size: 9px;
  font-style: normal;
  line-height: 14px;
}
.msg-unread {
  position: absolute;
  top: -4px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--dt-danger, #f53f3f);
  color: #fff;
  font-size: 10px;
  font-style: normal;
  line-height: 18px;
  text-align: center;
}
.msg-online {
  position: absolute;
  right: 1px;
  bottom: 1px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--dt-success, #00b42a);
  border: 2px solid #fff;
}
.msg-row-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.msg-row-top { display: flex; align-items: center; gap: 6px; min-width: 0; }
.msg-row-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--dt-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-muted { color: var(--dt-text-quiet); flex-shrink: 0; }
.msg-row-time { margin-left: auto; flex-shrink: 0; font-size: 11px; color: var(--dt-text-quiet); }
.msg-row-preview { display: flex; align-items: center; gap: 6px; min-width: 0; }
.msg-online-count {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: 5px;
  background: var(--dt-success-soft, #e8ffea);
  color: var(--dt-success, #00b42a);
  font-size: 10px;
}
.msg-preview-text {
  font-size: 12px;
  color: var(--dt-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-friend-tag {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--dt-success-soft, #e8ffea);
  color: var(--dt-success, #00b42a);
  font-size: 10px;
}

.msg-tip { padding: 20px 0; text-align: center; font-size: 12px; color: var(--dt-text-tertiary); }
.msg-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 56px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--dt-text-tertiary);
}
.msg-empty-hint { font-size: 12px; color: var(--dt-text-quiet); }
.msg-empty-btn {
  margin-top: 4px;
  height: 30px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid var(--dt-divider-strong, rgba(0, 0, 0, .1));
  background: var(--dt-surface, #fff);
  color: var(--dt-text-secondary);
  font-size: 12px;
  cursor: pointer;
}

/* ===== 搜索浮层 ===== */
.msg-search {
  position: absolute;
  inset: 0;
  z-index: 20;
  background: var(--dt-bg, #f5f6f7);
  display: flex;
  flex-direction: column;
}
.msg-search-inner {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  max-width: 880px;
  width: 100%;
  margin: 0 auto;
  background: var(--dt-bg, #f5f6f7);
}
.msg-search-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: var(--dt-surface, #fff);
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.msg-search-field {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 10px;
  border-radius: 10px;
  background: var(--dt-bg, #f5f6f7);
}
.msg-search-field-icon { color: var(--dt-text-quiet); flex-shrink: 0; }
.msg-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: 13px;
  color: var(--dt-text);
}
.msg-search-input::placeholder { color: var(--dt-text-quiet); }
.msg-search-clear {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  border: 0; background: var(--dt-surface-press, #eaebed);
  color: var(--dt-text-tertiary); cursor: pointer;
}
.msg-search-body { flex: 1; min-height: 0; overflow-y: auto; padding: 12px 16px 24px; }
.msg-search-section {
  padding: 10px 2px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--dt-text-tertiary);
  letter-spacing: .04em;
}

/* ===== 子页（聊天 / 通知 / 文件 / 管家）=====
   与资讯详情、工作台子页同一范式：整屏覆盖、自带返回按钮，不切路由也不换底部页签。
   移动端 z-index 1500 盖过悬浮胶囊(1000)、低于 Element 弹层(2000+)；
   桌面端避开 56px 顶栏，并把宽度收在 880px 内居中。 */
.msg-sub {
  position: fixed;
  top: 56px;
  right: 0;
  bottom: 0;
  left: 0;
  margin: 0 auto;
  max-width: 880px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  background: var(--dt-bg, #f5f6f7);
}
@media (max-width: 767px) {
  .msg-sub {
    top: 0;
    max-width: 440px;
    z-index: 1500;
  }
}
.msg-sub-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 52px;
  padding: 0 10px;
  background: var(--dt-surface, #fff);
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.msg-sub-title {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 650;
  color: var(--dt-text);
}
.msg-sub-avatar { flex-shrink: 0; }
.msg-sub-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.msg-sub-sub { font-size: 11px; font-weight: 400; color: var(--dt-text-tertiary); }
.msg-sub-sub.is-online { color: var(--dt-success, #00b42a); }
.msg-sub-action {
  border: 0;
  background: transparent;
  color: var(--dt-link, #0070d9);
  font-size: 12px;
  padding: 6px 4px;
  cursor: pointer;
}
.msg-sub-holder { width: 32px; flex-shrink: 0; }

/* 聊天区 */
.msg-chat {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 16px 8px;
  scrollbar-width: none;
}
.msg-chat::-webkit-scrollbar { display: none; }
.msg-date-sep {
  display: flex;
  justify-content: center;
  margin: 12px 0 10px;
}
.msg-date-sep span {
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, .05);
  color: var(--dt-text-tertiary);
  font-size: 11px;
}
.msg-bubble-row { display: flex; margin-bottom: 10px; }
.msg-bubble-row.mine { justify-content: flex-end; }
.msg-bubble-wrap { max-width: 74%; display: flex; flex-direction: column; gap: 3px; }
.msg-bubble-sender { font-size: 11px; color: var(--dt-text-quiet); padding-left: 2px; }
.msg-bubble {
  padding: 9px 12px;
  border-radius: 14px;
  background: var(--dt-surface, #fff);
  color: var(--dt-text);
  font-size: 14px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .04);
}
.msg-bubble-row.mine .msg-bubble {
  background: var(--dt-primary, #0089ff);
  color: #fff;
}
.msg-input-bar {
  flex-shrink: 0;
  padding: 8px 12px calc(10px + env(safe-area-inset-bottom, 0px));
  background: var(--dt-surface, #fff);
  border-top: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.msg-input-box {
  max-width: 880px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 6px 6px 6px 12px;
  border-radius: 14px;
  background: var(--dt-bg, #f5f6f7);
}
.msg-textarea {
  flex: 1;
  min-height: 22px;
  max-height: 96px;
  border: 0;
  outline: 0;
  resize: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.5;
  color: var(--dt-text);
  font-family: inherit;
}
.msg-send {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border: 0;
  border-radius: 11px;
  background: var(--dt-primary, #0089ff);
  color: #fff;
  cursor: pointer;
  transition: opacity .18s ease;
}
.msg-send:disabled { opacity: .4; cursor: default; }

.msg-butler { flex: 1; min-height: 0; }

/* 通知 */
.msg-notif {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: 0;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.msg-notif:last-child { border-bottom: 0; }
.msg-notif-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.msg-notif-top { display: flex; align-items: baseline; gap: 8px; }
.msg-notif-title { font-size: 13px; font-weight: 600; color: var(--dt-text); }
.msg-notif-dot {
  flex-shrink: 0;
  width: 7px;
  height: 7px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--dt-danger, #f53f3f);
}
.msg-notif-dot.hidden { background: transparent; }

/* 文件 */
.msg-file-filters { display: flex; gap: 6px; margin-bottom: 10px; }
.msg-file-filter {
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: var(--dt-surface, #fff);
  color: var(--dt-text-secondary);
  font-size: 12px;
  cursor: pointer;
}
.msg-file-filter.active {
  background: var(--dt-primary-soft, #e8f3ff);
  color: var(--dt-primary-strong, #0070d9);
  font-weight: 600;
}
.msg-file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 14px;
  border: 0;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.msg-file-row:last-child { border-bottom: 0; }
.msg-file-thumb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--dt-surface-z1, #fafbfc);
  color: var(--dt-text-tertiary);
  flex-shrink: 0;
  overflow: hidden;
}
.msg-file-thumb img { width: 100%; height: 100%; object-fit: cover; }

/* 群聊创建 */
.msg-group-form { display: flex; flex-direction: column; gap: 10px; }
.msg-group-hint { font-size: 12px; color: var(--dt-text-tertiary); }
.msg-group-picker {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}
.msg-group-member {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 4px;
  border-radius: 12px;
  border: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
  background: var(--dt-surface, #fff);
  cursor: pointer;
}
.msg-group-member.picked { border-color: var(--dt-primary, #0089ff); background: var(--dt-primary-soft, #e8f3ff); }
.msg-group-member-name { font-size: 12px; color: var(--dt-text-secondary); }
.msg-group-check { position: absolute; top: 6px; right: 6px; color: var(--dt-primary, #0089ff); }

/* ===== 过渡 ===== */
.msg-slide-enter-active { animation: msg-slide-in .26s cubic-bezier(.22, .61, .36, 1) both; }
.msg-slide-leave-active { animation: msg-slide-out .2s ease both; }
@keyframes msg-slide-in { from { transform: translateX(24px); opacity: .6; } to { transform: none; opacity: 1; } }
@keyframes msg-slide-out { from { transform: none; opacity: 1; } to { transform: translateX(20px); opacity: 0; } }

.msg-fade-enter-active, .msg-fade-leave-active { transition: opacity .18s ease; }
.msg-fade-enter-from, .msg-fade-leave-to { opacity: 0; }

@media (max-width: 767px) {
  .msg-header-inner { padding: 8px 12px 0; }
  .msg-title { font-size: 18px; }
  .msg-scroll-inner { padding: 10px 12px 20px; }
  .msg-quick { padding: 12px 6px; border-radius: 12px; }
  .msg-quick-icon { width: 46px; height: 46px; border-radius: 14px; }
  .msg-search-body { padding: 10px 12px 20px; }
  .msg-list { border-radius: 12px; }
}
</style>
