<template>
  <div class="msg-page no-dock-inset" @scroll.capture.passive="onScrollCapture">
    <!-- 移动端页头：消息是底部导航的一级 Tab，故不套 SubPageHeader（子页头带返回箭头）。
         「消息 / 好友」两枚并排标题就是本页的两个主视图，点击切换 ——
         下划线滑条与文字随条染色复用 SlidingTabs（与校园资讯分类 Tab 同一套动画）；
         下方视图是一条三页轨道（SwipePager），左右拖动的进度逐帧喂给滑条，
         所以「滑条跟手指」和「页面跟手指」是同一次位移的两个投影，不会各走各的。
         两个主视图之外的「互动」收成右侧一枚星标图标，不再和两个大标题抢位置。 -->
    <header v-if="isMobile" ref="appbarRef" class="msg-appbar" :class="{ 'is-hidden': appbarHidden }">
      <SlidingTabs
        class="msg-appbar-tabs"
        :tabs="headerTabs"
        :model-value="activeTab"
        :progress="pagerState.progress"
        :direction="pagerState.direction"
        :dragging="pagerState.dragging"
        :resetting="pagerState.resetting"
        :instant-sweep="pagerState.sliding"
        @select="selectMainTab"
      />
      <button
        type="button"
        class="msg-appbar-forum"
        aria-label="互动消息"
        :class="{ active: activeTab === 'forum' }"
        @click="selectMainTab('forum')"
      >
        <el-icon :size="18"><Star /></el-icon>
        <i v-if="forumUnread" class="msg-appbar-forum-dot">{{ forumUnread > 99 ? '99+' : forumUnread }}</i>
      </button>
    </header>
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
        <!-- 移动端：这一块是**入口**，点了进整页的搜索子页（/student/messages/search）。
             手机上就地输入撑不住 —— 键盘一弹只剩半屏，结果还得和会话列表抢同一块地方；
             整页做好「输入 → 分区结果 → 点进会话」，键盘收起也不丢上下文。
             桌面端侧栏宽、键盘是全尺寸的，仍保持就地过滤，不多一跳。 -->
        <button
          v-if="isMobile"
          ref="searchEntryRef"
          type="button"
          class="msg-search msg-search-entry"
          @click="openSearchPage"
        >
          <el-icon :size="14"><Search /></el-icon>
          <span>搜索</span>
        </button>
        <div v-else class="msg-search">
          <el-icon :size="14"><Search /></el-icon>
          <!-- 占位文案固定为「搜索」：三个视图的搜索入口是同一个框，
               跟着 activeTab 换字会让文案长短不一，居中时整组左右跳 -->
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索"
          />
        </div>

        <nav class="msg-tabs">
          <button
            v-for="t in mainTabs"
            :key="t.value"
            type="button"
            :class="['msg-tab', { active: activeTab === t.value }]"
            @click="switchMainTab(t.value)"
          >
            {{ t.label }}
            <i v-if="tabBadge(t.value)" class="msg-tab-badge">{{ tabBadge(t.value) }}</i>
          </button>
        </nav>

        <!-- 视图分页轨道：消息 / 好友 / 互动三个视图各占一页，左右滑动或点页头标题切换。
             跟手位移、松手吸附、点标题两页对滑、邻居页的挂载与卸载全部在
             components/common/SwipePager.vue，与校园资讯的分类分页是同一个组件。
             每页各自持有一份 .msg-list（自己滚、自己下拉刷新）：
             切走再切回不会串到另一个视图的滚动位置上。
             ignore-selector 传空：本页整行都是 <button>（会话行 / 互动行），
             默认忽略按钮会让「从行上起手」永远拖不动，滑动后的误触由组件吞 click 兜住。 -->
        <SwipePager
          ref="pagerRef"
          class="msg-pager"
          :model-value="activeTab"
          :pages="pagerKeys"
          ignore-selector=""
          @update:model-value="onPagerChange"
        >
          <div v-for="v in pagerViews" :key="v" class="sw-pager-page msg-view">
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
              <template v-if="v === 'sessions'">
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
                    <!-- 系统通知会话没有真人头像，用一枚铃铛占同样的位置和尺寸 -->
                    <span v-if="s.type === 'notice'" class="msg-notice-avatar" aria-hidden="true">
                      <el-icon :size="19"><Bell /></el-icon>
                    </span>
                    <el-avatar v-else :size="40" :src="s.avatar || undefined">{{ s.name.slice(0, 1) }}</el-avatar>
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
              <template v-else-if="v === 'contacts'">
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
          </div>
        </SwipePager>
      </aside>

      <!-- 右侧 / 移动端覆盖：会话窗口
           移动端点开会话 = 打开一个覆盖式二级页，进出场直接复用全站那套 .subpage
           （从右滑入 / 向右滑出，本体在 styles/subpage-transition.css，这里不另写动画）。
           桌面端这个节点恒存在（!isMobile），Transition 全程不触发，桌面零变化。 -->
      <Transition name="subpage" :duration="320" @after-leave="onChatClosed">
        <section v-if="!isMobile || chatOpen" :class="['msg-pane', { 'is-mobile-chat': isMobile }]">
          <template v-if="activeSession">
            <header class="msg-pane-head">
              <button v-if="isMobile" type="button" class="msg-back" aria-label="返回" @click="closeChat">
                <el-icon :size="18"><ArrowLeft /></el-icon>
              </button>
              <div class="msg-pane-title">
                <span class="msg-pane-name">{{ activeSession.name }}</span>
                <span v-if="activeSession.type === 'group'" class="msg-pane-meta">{{ groupMeta }}</span>
                <span v-else-if="activeSession.type === 'notice'" class="msg-pane-meta">系统通知 · 仅可查看</span>
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
              <!-- 系统通知：按「微信服务通知」的卡片排，不用气泡。
                   一条通知里有六七项键值对，压进气泡会变成一块没层次的文字墙 -->
              <div v-else-if="activeSession.type === 'notice'" class="msg-notice-list">
                <div v-for="c in noticeCards" :key="c.id" class="msg-notice-item">
                  <div class="msg-time-sep">{{ formatNoticeTime(c.created_at) }}</div>
                  <SystemNoticeCard :card="c" @open="openNoticeTarget" />
                </div>
              </div>
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

            <!-- 系统通知是单向的：没有输入框，换成一条说明，避免用户打完字才发现发不出去 -->
            <div v-if="activeSession.type === 'notice'" class="msg-notice-tip">系统通知不支持回复</div>
            <footer v-else class="msg-composer">
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
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  Bell,
  ChatDotRound,
  ChatLineRound,
  Promotion,
  Refresh,
  Search,
  Star,
  User,
} from '@element-plus/icons-vue'
// 页头两个主视图标题：滑动下划线 + 文字随条染色，与校园资讯分类 Tab 同一套动画
import SlidingTabs from '@/components/common/SlidingTabs.vue'
// 视图左右翻页：跟手位移 / 吸附 / 点标题两页对滑，与校园资讯分类分页同一个组件
import SwipePager from '@/components/common/SwipePager.vue'
import { useAuthStore } from '@/stores/auth'
import { useResponsive } from '@/composables/useResponsive'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { captureSearchFieldFlight } from '@/utils/searchFieldFlight'
import SystemNoticeCard from '@/components/chat/SystemNoticeCard.vue'
import {
  NOTICE_ORIGIN,
  SYSTEM_NOTICE,
  formatNoticeTime,
  minutesAgo,
  systemNoticeCards,
  type SystemNoticeCard as NoticeCard,
} from '@/utils/systemNotice'
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
const route = useRoute()
const { isMobile } = useResponsive()
const auth = useAuthStore()
const { refresh: refreshUnread, forum: forumUnread, isOnline, syncPresence } = useUnreadSummary()

type TabValue = 'sessions' | 'contacts' | 'forum'
type ContactTabValue = 'friends' | 'following' | 'followers'
type ChatMessage = MessageOut | GroupMessageOut

interface SessionItem {
  key: string
  /** notice = 系统通知会话（「消息通知」），它没有对方用户，只读不回复 */
  type: 'private' | 'group' | 'notice'
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
/** 移动端页头的两个主视图标题：一对一映射「会话 / 通讯录」，点标题即切页（喂给 SlidingTabs） */
const headerTabs: Array<{ key: Extract<TabValue, 'sessions' | 'contacts'>; label: string }> = [
  { key: 'sessions', label: '消息' },
  { key: 'contacts', label: '好友' },
]
const contactTabs: Array<{ label: string; value: ContactTabValue }> = [
  { label: '好友', value: 'friends' },
  { label: '我关注的', value: 'following' },
  { label: '关注我的', value: 'followers' },
]

/**
 * 「消息 / 好友」两个主视图各自对应一条路由（见 router/index.ts）：
 *   /student/messages          → 消息（会话列表）
 *   /student/messages/friends  → 好友（通讯录 · 好友分组）
 * 两条路由渲染同一个组件，只是进入时按地址落位到对应视图；页内换标题再 replace 回地址，
 * URL 与页头高亮互为镜像 —— 刷新、分享链接、浏览器前进后退都能停在同一个视图上。
 * 「互动」是同一页里的第三个视图（右上角星标进），没有独立地址，故不参与路由。
 */
const ROUTE_OF_TAB = {
  sessions: 'student-messages',
  contacts: 'student-message-friends',
} as const

/** 地址 → 视图。返回 null 表示这条地址与本页的两个视图无关（例如正在离开本页） */
function tabFromRoute(name: unknown): Exclude<TabValue, 'forum'> | null {
  if (name === ROUTE_OF_TAB.contacts) return 'contacts'
  if (name === ROUTE_OF_TAB.sessions) return 'sessions'
  return null
}

const activeTab = ref<TabValue>(tabFromRoute(route.name) ?? 'sessions')
const contactTab = ref<ContactTabValue>('friends')
const keyword = ref('')
/** 移动端那条搜索条本身：进子页时量它的位置当「起飞点」 */
const searchEntryRef = ref<HTMLButtonElement | null>(null)

const conversations = ref<ConversationOut[]>([])
const groups = ref<GroupOut[]>([])
const activeSession = ref<SessionItem | null>(null)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const chatOpen = ref(false)
const chatLoading = ref(false)
const sending = ref(false)
const scrollEl = ref<HTMLElement | null>(null)

/*
 * 会话窗口**不登记**为「页内二级页」，底部悬浮导航因此全程留在 DOM 里。
 *
 * 聊天页本身是 position: fixed; inset: 0; z-index: 2600 的整屏覆盖层，
 * 层级压过悬浮导航（1000）—— 滑到位以后它自己就把导航盖住了。
 * 反过来，一打开就 v-if 卸掉导航，会在滑入动画的头一帧（约 30ms 内）
 * 凭空挖掉屏幕底部一块：列表还在原地，导航已经没了，看上去像布局塌了；
 * 同时 useDockInset 撤掉页面根的 82px 让位，页面还会跟着抖一下。
 * 交给覆盖层逐帧「盖上去」，才是子页推入该有的观感（返回时也是一层层露出来）。
 */

const contacts = ref<ContactUser[]>([])
const contactsLoading = ref(false)
const forumList = ref<ForumMessageOut[]>([])

let pollTimer: ReturnType<typeof setInterval> | null = null

// ---------- 「消息通知」系统会话 ----------
/* 会话列表顶部的一条系统通知会话：长得和私聊 / 群聊一样，只是头顶是铃铛。
   展示数据放在 utils/systemNotice.ts（消息搜索页共用同一份），这里只是把它包成本页的
   SessionItem。unread 是本地状态（点开即清零），所以用 reactive 而不是直接引用常量。 */
const noticeSession = reactive<SessionItem>({
  key: SYSTEM_NOTICE.key,
  type: 'notice',
  rawId: 0,
  name: SYSTEM_NOTICE.name,
  avatar: null,
  lastMessage: SYSTEM_NOTICE.summary,
  time: minutesAgo(26),
  unread: SYSTEM_NOTICE.unread,
})

/** 打开「消息通知」后展示的三条系统通知（卡片式，只读） */
const noticeCards = ref<NoticeCard[]>([])

/** 卡片入口跳转中：两条导航（改写 + 跳走）之间有个空档，连点会多压一条历史 */
const noticeJumping = ref(false)

/**
 * 通知卡片底部入口：跳到站内对应的业务页。
 * 通知本身是「告知」，真正要办的事都在业务页里，所以这里直接把人送过去，
 * 而不是弹一句「请自行前往」再让用户自己找。
 *
 * 跳之前先把**当前这条历史记录**改写成「消息通知打开着」的地址：
 * 会话是页内覆盖层，本身不占一条历史 —— 不改的话，从业务页按返回落回来的是
 * 会话列表（甚至别的视图），用户还得凭记忆重新点进「消息通知」。
 * 改写后返回落到 `?chat=n-notice`，onMounted 里的 openChatFromQuery 会把会话摆回原样。
 */
async function openNoticeTarget(card: NoticeCard) {
  if (!card.to || noticeJumping.value) return
  noticeJumping.value = true
  try {
    await router.replace({ name: 'student-messages', query: { ...route.query, chat: SYSTEM_NOTICE.key } })
    await router.push({ path: card.to.path, query: { ...card.to.query, from: NOTICE_ORIGIN } })
  } finally {
    noticeJumping.value = false
  }
}

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
  list.sort((a, b) => (b.time ? Date.parse(b.time) : 0) - (a.time ? Date.parse(a.time) : 0))
  // 「消息通知」钉在最前，不参与按时间排序：系统会话不该被几十条私聊挤到看不见的位置
  return [noticeSession, ...list]
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

/**
 * 页内主视图的**唯一状态落点**（消息 / 好友 / 互动）。
 * 三条入口最后都收在这里：轨道回报（拖动吸附 / 点标题换页）、桌面端三栏页签、地址回填。
 * contactTab 先落位再切 activeTab —— activeTab 的 watch 会带着新分组去拉数据；
 * 页头高亮、搜索范围、下方轨道用的是同一份 activeTab，不会各说各话。
 */
function switchMainTab(tab: string) {
  if (!isViewKey(tab)) return
  if (activeTab.value === tab) return
  if (tab === 'contacts' && contactTab.value !== 'friends') contactTab.value = 'friends'
  activeTab.value = tab
  // 「互动」没有自己的地址：URL 停在上一枚标题对应的位置上，刷新后回到那个视图
  if (tab !== 'forum') syncRouteForTab(tab)
}

/**
 * 换视图 = 换地址。用 replace 而不是 push：两个标题是同一个页面的两个视图，
 * 来回点不该在历史里堆出一串记录（返回键应当直接离开消息页）。
 * query / hash 一并带上，页面上其它靠 query 的入口不会因为换标题被抹掉。
 */
function syncRouteForTab(tab: Exclude<TabValue, 'forum'>) {
  const name = ROUTE_OF_TAB[tab]
  if (route.name === name) return
  void router.replace({ name, query: route.query, hash: route.hash })
}

/* ==================== 搜索子页 ==================== */

/** 移动端搜索框的点击：进整页搜索（push，返回键才回得到列表）。
 *  跳转前先把这条搜索条的屏幕位置交给下一页，那边会从同一处把框「飞」到顶栏 —
 *  否则整页是淡入的，搜索框凭空出现在最上方，动作前后接不上。 */
function openSearchPage() {
  captureSearchFieldFlight(searchEntryRef.value)
  void router.push({ name: 'student-message-search' })
}

/**
 * 地址 → 会话：搜索子页点结果后 replace 到 /student/messages?chat=<key>，
 * 由这里把那条会话打开，随后把 chat 参数抹掉 —— 留着的话刷新 / 返回会重复弹一次。
 *
 * 好友不一定已经聊过（会话列表里没有它），所以找不到会话时回落到通讯录：
 * 用 id 现造一条空会话，点搜索结果一样能直接开聊。
 * 抹参数放在打开之前：即便目标已经不存在（被删好友 / 退群），地址也先回到干净状态。
 */
async function openChatFromQuery() {
  if (typeof route.query.chat !== 'string' || !route.query.chat) return
  const key = route.query.chat
  const { chat: _chat, ...restQuery } = route.query
  void router.replace({ name: 'student-messages', query: restQuery })

  const target = sessions.value.find((s) => s.key === key)
  if (target) {
    openSession(target)
    return
  }
  const m = /^s-(\d+)$/.exec(key)
  if (!m) return
  // 桌面端首屏不一定拉过通讯录（只有移动端预载），这里按需补一次再找人
  if (!contacts.value.length) await loadContacts()
  const user = contacts.value.find((c) => c.id === Number(m[1]))
  if (user) chatWith({ id: user.id, name: user.name, avatar: user.avatar })
}

/* ==================== 视图左右翻页（移动端 / 桌面端共用一份标记） ==================== */

/**
 * 三个主视图（消息 / 好友 / 互动）就是轨道上的三页。
 * 拖动 1:1 跟手、松手按位移 / 速度吸附或回弹、点标题两页对滑、邻居页的挂载与卸载，
 * 全在 components/common/SwipePager.vue（与校园资讯分类分页同一个组件）；
 * 本页只留两件事：① 告诉轨道有哪几页、给出每页内容；② 把轨道的即时状态转给页头滑条。
 *
 * 「互动」排第三页：它不是页头的一枚标题，只能从「好友」往左滑、或点右上角星标进；
 * 走到这一页时页头滑条自然隐去（两个标题都不再选中），高亮交给星标自身。
 *
 * 桌面端 pagerKeys 只剩当前视图一页 —— 轨道没有邻居，手势天然不接管，
 * 同一份标记两档共用，不必为桌面另写一套列表。
 */
const pagerRef = ref<InstanceType<typeof SwipePager> | null>(null)

/** 轨道上的页序（有序）：组件据此判断左右邻居与首尾边界 */
const VIEW_KEYS: TabValue[] = ['sessions', 'contacts', 'forum']

const pagerKeys = computed<TabValue[]>(() => (isMobile.value ? VIEW_KEYS : [activeTab.value]))

/**
 * 轨道上正在渲染的页：静止 = 当前页，拖动 / 吸附 = 加上左右邻居，点标题换页 = 出发页 + 目标页。
 * 摆哪几页由组件算（renderedPages），本页按 key 渲染对应视图即可 ——
 * 邻居页只在拖动开始时挂载，静止时只有当前页，页面不会被邻居撑高。
 */
const pagerViews = computed<TabValue[]>(() => {
  const keys = pagerRef.value?.renderedPages ?? [activeTab.value]
  return keys.filter((k): k is TabValue => (VIEW_KEYS as string[]).includes(k))
})

/**
 * 组件状态 → 页头滑条（口径与校园资讯一致）：
 *   · progress：拖动时 = |位移| / 页宽，滑条与页面严格同步；
 *     点标题换页时为 null —— 那一趟位移只为推动页面轨道，滑条已直接落到目标位；
 *   · direction：往左拖 = 下一页，往右拖 = 上一页；
 *   · dragging / resetting / sliding：逐帧写入时关掉过渡的三个状态位。
 */
const pagerState = computed(() => ({
  progress: pagerRef.value?.progress ?? null,
  direction: pagerRef.value?.direction ?? 0,
  dragging: pagerRef.value?.dragging ?? false,
  resetting: pagerRef.value?.resetting ?? false,
  sliding: pagerRef.value?.sliding ?? false,
}))

function isViewKey(key: string): key is TabValue {
  return key === 'sessions' || key === 'contacts' || key === 'forum'
}

/**
 * 点页头标题 / 右上角星标：内容横向滑过去，与手指切换同一段时长。
 * 状态不在此刻落，交给轨道回报（onPagerChange）统一写 —— 拖动与点按因此只有一条落点。
 * 已在目标视图时只收掉可能还在跑的拖动 / 吸附残留，避免半路卡在邻居页上。
 */
function selectMainTab(key: string) {
  if (!isViewKey(key)) return
  if (!isMobile.value || !pagerRef.value) {
    switchMainTab(key)
    return
  }
  if (key === activeTab.value) {
    pagerRef.value.cancel()
    return
  }
  pagerRef.value.slideTo(key)
}

/** 轨道回报「当前页变了」（拖动吸附完成、或点标题换页出发那一刻） */
function onPagerChange(key: string) {
  switchMainTab(key)
}

// ---------- 会话窗口 ----------
function openSession(s: SessionItem) {
  activeSession.value = s
  chatOpen.value = true
  void loadChat(true)
}

/**
 * 关闭会话（移动端返回键）：只收起覆盖层，让 .subpage 的离场动画把整页滑出去。
 * activeSession / messages 留到 after-leave 再清 —— 提前清会让滑走的是一张
 * 「选择一个会话开始聊天」的占位页，闪一下再走，观感很差。
 */
function closeChat() {
  chatOpen.value = false
}

/** 离场动画播完再丢弃会话上下文；若动画期间又点开了别的会话，则不清 */
function onChatClosed() {
  if (chatOpen.value) return
  activeSession.value = null
  messages.value = []
  noticeCards.value = []
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
  // 系统通知：内容在本地（utils/systemNotice.ts），不发请求、也不走已读上报；
  // 打开即视为读过，把列表上那枚红点清掉
  if (session.type === 'notice') {
    noticeCards.value = systemNoticeCards()
    messages.value = []
    noticeSession.unread = 0
    chatLoading.value = false
    if (scrollToBottom) await scrollBottom()
    return
  }
  noticeCards.value = []
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

/* ==================== 移动端页头：随滚动平滑上滑收起 ====================
   一级 Tab 页的标题栏占 48px，会话多的时候一直钉在顶上不划算：往下翻时让它滑走、
   往回翻时滑回来（微信 / 小红书都是这个手感）。桌面端页头是另一套 .msg-head，不参与。 */

const appbarRef = ref<HTMLElement | null>(null)
/** 页头是否收起。收起 = margin-top 变负，整条滑出页面顶边（由 .main-area 的 overflow 裁掉） */
const appbarHidden = ref(false)

/** 位移用实测高度而不是写死 48px：字体缩放或边框算进/不算进盒高都会让「收干净」差一点，
    差一点就会在顶边留一条白线 */
function measureAppbar() {
  const el = appbarRef.value
  if (el) el.style.setProperty('--ab-h', `${el.offsetHeight}px`)
}

const HIDE_AFTER = 48 // 滚过这么远才允许收起：页面刚进来轻微回弹时不该让标题栏闪一下
const DELTA = 14 // 单向累计位移阈值（px）：手指抖一两像素不切状态，避免来回抽动

/** 每条列表各自的上一帧位置：三条视图是三个独立滚动容器，混着记会算出假位移 */
const lastTop = new WeakMap<EventTarget, number>()
/** 单向累计位移，方向一翻就清零 */
let scrolledBy = 0

function onScrollCapture(e: Event) {
  if (!isMobile.value) return
  const el = e.target as HTMLElement | null
  // 只认视图列表；移动端聊天浮层里的 .msg-chat-scroll 不参与
  if (!el || !el.classList?.contains('msg-list')) return

  const y = el.scrollTop
  // 第一次收到这条列表的滚动时按「原来在 0」算：不必白扔一帧，
  // 否则用户从顶部一次性甩出去的那一下会被吞掉（列表短的时候往往只有这一个事件）
  const prev = lastTop.get(el) ?? 0
  lastTop.set(el, y)

  const dy = y - prev
  // 换方向就清零：否则「先下滑 300px、再上滑 20px」会被上面的余量吃成仍然向下
  if ((dy > 0) !== (scrolledBy > 0)) scrolledBy = 0
  scrolledBy += dy

  // 到顶一律展开 —— 这是「我在最上面」的强信号，也顺手修掉下拉刷新时的错位
  if (y <= 4) {
    scrolledBy = 0
    appbarHidden.value = false
    return
  }
  if (scrolledBy > DELTA && y > HIDE_AFTER) {
    scrolledBy = 0
    appbarHidden.value = true
  } else if (scrolledBy < -DELTA) {
    scrolledBy = 0
    appbarHidden.value = false
  }
}

/** 换视图（含拖动切页 / 空格键 / 地址回填）时把页头放回来：
 *  收起状态是「上一个视图的滚动位置」的产物，带到下一个视图没有意义 */
watch(activeTab, () => {
  scrolledBy = 0
  appbarHidden.value = false
})

// 断点来回切：桌面端没有这条页头，回到移动端时不该带着上一次的收起状态
watch(isMobile, (mobile) => {
  if (!mobile) return
  appbarHidden.value = false
  void nextTick(measureAppbar)
})

watch(activeTab, (tab) => {
  if (tab === 'contacts') void loadContacts()
  if (tab === 'forum') void loadForum()
})

/**
 * 地址 → 页内状态：浏览器前进 / 后退、从别处直接跳到 /student/messages/friends 时以地址为准。
 * 页内换视图是先改 activeTab 再 replace，这里算出来的视图与当前一致，天然空转，
 * 所以不需要「忽略下一次路由变化」那种标记位。
 */
watch(
  () => route.name,
  (name) => {
    const tab = tabFromRoute(name)
    // tab 为 null = 正在离开本页（跳到校园资讯等），交给路由去换页面，不改页内状态
    if (!tab || tab === activeTab.value) return
    if (tab === 'contacts' && contactTab.value !== 'friends') contactTab.value = 'friends'
    activeTab.value = tab
  },
)

onMounted(async () => {
  // 页头收起要按实测高度位移：字体缩放 / 边框算不算进盒高，都会让「收干净」差一两个像素
  void nextTick(measureAppbar)
  window.addEventListener('resize', measureAppbar)
  await loadSessions()
  // 好友列表按需预载，这里改成 await 是为了下面 openChatFromQuery 的兜底能查到人：
  // ① 直接落到 /student/messages/friends 时 activeTab 的 watch 首帧不跑，需要补一次；
  // ② 移动端「好友」是轨道的邻居页，手指一拖就要立刻上屏，等到切过去再拉会闪一张空态；
  // ③ 从搜索子页点一个「还没聊过」的好友回来时，会话列表里没有它，只能靠通讯录按 id 现造会话。
  if (activeTab.value === 'contacts' || isMobile.value) await loadContacts()
  // 地址里带 chat（搜索子页刚点了某条结果）：直接把那条会话打开
  await openChatFromQuery()
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
  window.removeEventListener('resize', measureAppbar)
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

/* ================= 移动端页头 =================
   一级 Tab 页头：两枚并排标题「消息 / 好友」就是本页的两个主视图，
   点击切换 —— 下划线滑条与文字随条染色用的是抽出来的 SlidingTabs（与校园资讯同一套动画）。
   标题取 20px：两枚并排时 26px 在 390px 屏上会挤，20px 既醒目又给右侧互动图标留得出位置。 */
.msg-appbar {
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  height: 48px;
  background: #fff;
  border-bottom: 1px solid #f0f1f3;
  /* 收起用 margin-top 而不是 transform：整条页头要真的「让出位置」，
     下面的搜索条和列表一起跟着上移。只做 transform 会在顶上留一条底色的空带。
     页头顶边一旦越过 .msg-page 的顶沿就被 .main-area 的 overflow:hidden 裁掉，
     不会画到全局导航栏上面去。 */
  transition: margin-top 0.24s cubic-bezier(0.4, 0, 0.2, 1);
}
/* --ab-h 由 measureAppbar() 按实测高度写进来（含下边框） */
.msg-appbar.is-hidden { margin-top: calc(-1 * var(--ab-h, 49px)); }
@media (prefers-reduced-motion: reduce) {
  .msg-appbar { transition: none; }
}
/* 外观全部通过 CSS 变量喂给组件，组件内部的动画逻辑一行都不用改。
   左右各 44px：右边给互动图标让位，左边对称留白，标题组因此落在页面正中。
   两层文字必须同宽才能对齐裁剪，所以选中态只改颜色、不改字重（统一 700）。 */
.msg-appbar-tabs {
  flex: 1;
  min-width: 0;
  --st-height: 48px;
  --st-pad: 0 44px;
  --st-justify: center;
  --st-gap: 28px;
  --st-font: 20px;
  --st-font-weight: 700;
  --st-color: #9aa0a8;
  --st-color-active: #1d2129;
  --st-bg: transparent;
  --st-shadow: none;
  --st-tab-pad-b: 0px;
  --st-indicator-h: 2.5px;
  --st-indicator-bottom: 6px;
  --st-indicator-radius: 2px;
}
/* 互动入口：不属于「消息 / 好友」两个主视图，收成右上角一枚星标，未读挂红点 */
.msg-appbar-forum {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #9aa0a8;
  cursor: pointer;
}
.msg-appbar-forum.active { color: #1d2129; background: #f4f5f7; }
.msg-appbar-forum-dot {
  position: absolute;
  top: 3px;
  right: 1px;
  min-width: 14px;
  padding: 0 3px;
  border-radius: 7px;
  background: #ef4444;
  color: #fff;
  font-size: 9.5px;
  font-style: normal;
  line-height: 14px;
  text-align: center;
}

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

/* ================= 视图分页轨道 =================
   消息 / 好友 / 互动三个视图各占一页，左右滑动或点页头标题切换。
   高度链必须逐层给死，否则「页内自己滚」会退化成「整条轨道被最高的那页撑高」：
     .msg-side（列，高度由 .msg-main 定死）
       → 轨道（flex: 1 1 0，吃掉剩余高度，与内容高度无关）
         → 轨道内容器 100% → 页 100% → 页内 .msg-list 自己 overflow-y: auto
   只有最后一层在滚，所以每个视图各自持有滚动位置，切走再切回不会串位。 */
.msg-pager { flex: 1 1 0; min-height: 0; --sw-track-bg: #fff; }
.msg-pager :deep(.sw-pager) { height: 100%; }
.msg-view { display: flex; flex-direction: column; height: 100%; min-height: 0; background: #fff; }

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
/* 系统通知会话的头像：铃铛，尺寸与 el-avatar 一致（40 / 气泡里 30），
   底色跟着列表的中性灰走，不用主题蓝 —— 这一页整体是黑白灰，突然一块彩色反而像广告位 */
.msg-notice-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #111827;
  color: #fff;
}
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

/* ================= 系统通知（卡片流） =================
   时间居中浮在卡片上方、卡片整宽铺开，是微信服务通知的固定版式：
   时间属于「这一刻收到了什么」，不属于卡片本身，所以它不画进卡片里。 */
.msg-notice-list { display: flex; flex-direction: column; gap: 20px; }
.msg-notice-item { display: flex; flex-direction: column; gap: 9px; }
.msg-time-sep { text-align: center; font-size: 11.5px; color: #9aa0a6; }
.msg-composer { display: flex; align-items: flex-end; gap: 8px; padding: 10px 14px calc(10px + env(safe-area-inset-bottom, 0px)); border-top: 1px solid #f0f1f3; background: #fff; }
/* 通知会话底部：替掉输入框的位置，高度接近输入区，避免切换会话时整页跳一下 */
.msg-notice-tip {
  flex-shrink: 0;
  padding: 18px 14px calc(18px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid #f0f1f3;
  background: #fafbfc;
  color: #9aa0a6;
  font-size: 12px;
  text-align: center;
}
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
  /* 移动端不再有「会话 / 通讯录 / 互动」三栏页签：主切换已上移到页头的两枚标题，
     互动收成页头右上角星标。页签行留着只会和标题重复一层。 */
  .msg-tabs { display: none; }
  /* 搜索入口：整块是一枚按钮（点了进搜索子页），图标 + 文案作为一组居中，
     与页头「消息 / 好友」同一根中轴。列表页在移动端不再有可输入的搜索框。 */
  .msg-search { justify-content: center; }
  .msg-search-entry { border: 0; font: inherit; cursor: pointer; -webkit-tap-highlight-color: transparent;
    /* 28px（原输入框的自然高度）当按钮偏矮，拇指点不准；抬到 34px 仍比会话行矮，不抢视觉 */
    min-height: 34px; }
  .msg-search-entry > span { font-size: 13px; line-height: 1; }
  .msg-search-entry:active { background: #eceef1; }
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
