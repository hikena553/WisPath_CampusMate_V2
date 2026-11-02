<template>
  <div class="msg-page no-dock-inset" @scroll.capture.passive="onScrollCapture">
    <!-- 移动端页头：消息是底部导航的一级 Tab，故不套 SubPageHeader（子页头带返回箭头）。
         「消息 / 好友」两枚并排标题就是本页的两个主视图，点击切换 ——
         下划线滑条与文字随条染色复用 SlidingTabs（与校园资讯分类 Tab 同一套动画）；
         下方视图是一条三页轨道（SwipePager），左右拖动的进度逐帧喂给滑条，
         所以「滑条跟手指」和「页面跟手指」是同一次位移的两个投影，不会各走各的。
         两个主视图之外的「互动」不占标题位、也不进 ＋ 面板：只能从「好友」往左滑到达；
         ＋ 面板里只留「发起群聊 / 加好友 / 群 / 全部标为已读」这几件新建与清理动作。 -->
    <header
      v-if="isMobile"
      ref="appbarRef"
      class="msg-appbar subpage-underlay"
      :class="{ 'is-hidden': appbarHidden, 'is-menu-open': plusOpen, 'is-instant': appbarNoAnim, 'is-subpushed': chatPushed }"
    >
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
      <!-- 右侧动作组：搜索 + ＋。搜索从列表顶部那条胶囊收进来以后，
           列表能整块往上提一屏高，页头也只剩这两枚图标，视线不再被打断。 -->
      <div class="msg-appbar-acts">
        <button type="button" class="msg-appbar-icon" aria-label="搜索" @click="openSearchPage">
          <!-- 21 而不是 20：放大镜四周自带空白，同尺寸下看着比加号小一圈 -->
          <el-icon :size="21"><Search /></el-icon>
        </button>
        <button
          type="button"
          class="msg-appbar-icon msg-appbar-plus"
          :class="{ 'is-open': plusOpen }"
          aria-label="新建"
          aria-haspopup="menu"
          :aria-expanded="plusOpen"
          @click.stop="togglePlusMenu"
        >
          <el-icon :size="22"><Plus /></el-icon>
        </button>
      </div>
      <!-- 压暗底：面板一开，页面整体沉下去，视线只剩这张白卡（微信同款）。
           点它任意位置收起；它同时拦住底下的滚动，菜单开着时列表不再乱跑。 -->
      <Transition name="msg-plus-mask">
        <div v-if="plusOpen" class="msg-plus-mask" @click="plusOpen = false" />
      </Transition>
      <!-- 「＋」面板：新建动作在上，操作在下。
           「互动消息」不再占这一行 —— 论坛的赞 / 收藏 / 评论仍可从「好友」页往左滑到达，
           未读条数在页签与「互动」视图里给出，＋ 面板只留真能落地的三个动作。 -->
      <Transition name="msg-plus-panel">
        <div v-if="plusOpen" class="msg-plus-panel" role="menu" @click.stop>
          <button type="button" class="msg-plus-item" role="menuitem" @click="openCreateGroup">
            <el-icon :size="18"><ChatLineRound /></el-icon>
            <span>发起群聊</span>
          </button>
          <button type="button" class="msg-plus-item" role="menuitem" @click="goFindPeople">
            <el-icon :size="18"><User /></el-icon>
            <span>加好友 / 群</span>
          </button>
          <div class="msg-plus-sep" />
          <button
            type="button"
            class="msg-plus-item"
            role="menuitem"
            :disabled="!hasAnyUnread"
            @click="markAllReadFromMenu"
          >
            <el-icon :size="18"><Check /></el-icon>
            <span>全部标为已读</span>
          </button>
        </div>
      </Transition>
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
      <aside
        class="msg-side subpage-underlay"
        :class="{ 'is-subpushed': chatPushed }"
      >
        <!-- 桌面端：侧栏宽、键盘是全尺寸的，仍保持就地过滤，不多一跳。
             移动端的搜索已收进页头右侧那枚放大镜（点了进整页搜索子页）——
             手机上就地输入撑不住：键盘一弹只剩半屏，结果还得和会话列表抢地方。 -->
        <div v-if="!isMobile" class="msg-search">
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
          <div v-for="v in pagerViews" :key="v" :data-view="v" class="sw-pager-page msg-view">
            <div
              class="msg-list"
              @pointerdown="unpinLetter"
              @wheel.passive="unpinLetter"
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
                      <el-icon :size="avatarSize * 0.48"><Bell /></el-icon>
                    </span>
                    <el-avatar v-else :size="avatarSize" :src="s.avatar || undefined">{{ s.name.slice(0, 1) }}</el-avatar>
                    <i v-if="s.type === 'private' && isOnline(s.rawId)" class="msg-online-dot" aria-hidden="true"></i>
                    <!-- 移动端未读数压在头像右上角（桌面端仍用行尾那枚），两枚互斥，由媒体查询决定谁显示 -->
                    <i v-if="s.unread" class="msg-avatar-badge">{{ s.unread > 99 ? '99+' : s.unread }}</i>
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

              <!-- 通讯录 = 我关注的人，一份名单，不再分页签。
                   这一页就是「能直接发消息、能拉群」的那批人，一屏看完，不用先选分组。
                   谁关注了我，在「互动消息」里以「关注了你」逐条给出，不占这里的页签。 -->
              <template v-else-if="v === 'contacts'">
                <div v-if="contactsLoading" class="msg-empty"><p>加载中…</p></div>
                <div v-else-if="!filteredContacts.length" class="msg-empty">
                  <el-icon :size="26"><User /></el-icon>
                  <p>还没有关注任何人</p>
                  <span>在交流社区、或「添加朋友」里关注同学</span>
                  <!-- 空态给一条出路：直接进「添加朋友」搜人，比让人自己去找入口有用 -->
                  <button type="button" class="msg-empty-cta" @click="goFindPeople">
                    去添加朋友
                  </button>
                </div>
                <!-- 通讯录按姓名首字母分节（A / B / C…），右侧配字母索引。
                     行上不放按钮：整行点进个人主页（发消息、看资料都在那一页），
                     取关收进长按（移动端）/ 右键（桌面端）—— 低频动作，
                     常驻按钮只会把「谁是谁」这行信息挤没。 -->
                <template v-else>
                  <section
                    v-for="g in contactGroups"
                    :key="g.letter"
                    class="msg-alpha-group"
                    :data-letter="g.letter"
                  >
                    <h3 class="msg-alpha-head">{{ g.letter }}</h3>
                    <button
                      v-for="c in g.items"
                      :key="c.id"
                      type="button"
                      class="msg-contact"
                      @click="swallowClickAfterPress() || openHomepage(c.id)"
                      @contextmenu.prevent="askUnfollow(c)"
                      @pointerdown="onContactPressStart(c, $event)"
                      @pointermove="onContactPressMove($event)"
                      @pointerup="onContactPressEnd"
                      @pointercancel="onContactPressEnd"
                      @pointerleave="onContactPressEnd"
                    >
                      <el-avatar
                        class="msg-contact-avatar"
                        :size="46"
                        :src="c.avatar || undefined"
                      >
                        {{ c.name.slice(0, 1) }}
                      </el-avatar>
                      <div class="msg-contact-info">
                        <span class="msg-contact-name">{{ c.name }}</span>
                        <span class="msg-contact-sub">
                          <i v-if="isOnline(c.id)" class="msg-contact-online" aria-hidden="true" />
                          {{ contactLine(c) }}
                        </span>
                      </div>
                    </button>
                  </section>
                </template>
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

            <!-- A-Z 索引：只吸在右侧，不随列表滚动；点一下跳到对应分节 -->
            <div
              v-if="v === 'contacts' && !contactsLoading && contactGroups.length"
              class="msg-alpha-index"
              @click.stop
            >
              <button
                v-for="letter in indexKeys"
                :key="letter"
                type="button"
                :class="[
                  'msg-alpha-key',
                  { active: activeLetter === letter, dim: !presentLetters.has(letter) },
                ]"
                @click="jumpToLetter(letter)"
              >
                {{ letter }}
              </button>
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
                <span v-else-if="activeSession.type === 'private'" class="msg-pane-meta">{{ isOnline(activeSession.rawId) ? '在线' : '离线' }}</span>
              </div>
              <!-- 页头已经有对方名字了，再摆一个「主页」文字按钮是重复说明；
                   收成一枚三条横线的图标（汉堡菜单式），与左侧返回键同尺寸、成对。
                   自绘 SVG 而不用 el-icon：Element 的 Menu 线条偏细，这里要的是
                   参考图那种粗圆头的三条，直接画三块圆角矩形最省事。 -->
              <button
                v-if="activeSession.type === 'private'"
                type="button"
                class="msg-ghost-btn msg-ghost-icon"
                aria-label="查看主页"
                title="查看主页"
                @click="openHomepage(activeSession.rawId)"
              >
                <svg class="msg-menu-lines" width="17" height="14" viewBox="0 0 17 14" aria-hidden="true">
                  <rect x="0" y="0.8" width="17" height="2.6" rx="1.3" />
                  <rect x="0" y="5.7" width="17" height="2.6" rx="1.3" />
                  <rect x="0" y="10.6" width="17" height="2.6" rx="1.3" />
                </svg>
              </button>
            </header>

            <div ref="scrollEl" class="msg-chat-scroll">
              <div v-if="chatLoading" class="msg-empty"><p>加载中…</p></div>
              <!-- 系统通知：按「微信服务通知」的卡片排，不用气泡。
                   一条通知里有六七项键值对，压进气泡会变成一块没层次的文字墙 -->
              <div v-else-if="activeSession.type === 'notice'" class="msg-notice-list">
                <div v-for="c in noticeCards" :key="c.id" class="msg-notice-item">
                  <div class="msg-time-sep">{{ formatNoticeTime(c.created_at) }}</div>
                  <SystemNoticeCard :card="c" />
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

    <!-- 发起群聊：选人表单已抽成 components/chat/CreateGroupPopup.vue，
         「添加朋友」页共用同一份；建完直接进群，落点才是能说话的地方 -->
    <CreateGroupPopup v-model="createGroupOpen" @created="onGroupCreated" />
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
  Check,
  Plus,
  Promotion,
  Refresh,
  Search,
  Star,
  User,
} from '@element-plus/icons-vue'
// 「＋」菜单里的操作会失败（网络 / 后端校验），给一句即时反馈
import { ElMessage, ElMessageBox } from 'element-plus'
// 发起群聊：消息页与「添加朋友」页共用同一份选人表单
import CreateGroupPopup from '@/components/chat/CreateGroupPopup.vue'
// 页头两个主视图标题：滑动下划线 + 文字随条染色，与校园资讯分类 Tab 同一套动画
import SlidingTabs from '@/components/common/SlidingTabs.vue'
// 视图左右翻页：跟手位移 / 吸附 / 点标题两页对滑，与校园资讯分类分页同一个组件
import SwipePager from '@/components/common/SwipePager.vue'
import { useAuthStore } from '@/stores/auth'
import { useResponsive } from '@/composables/useResponsive'
import { useSubpagePush } from '@/composables/useMobileSubPage'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { openUserHomepage } from '@/composables/useUserHomepage'
// 通讯录的 A-Z 分节：按姓名首字母分组（汉字用 ICU 的中文排序推首字母，不引拼音词典）
import { INDEX_KEYS, indexOrder, initialOf } from '@/utils/pinyinInitial'
// 陌生人发消息时用主页接口补名字，避免开出一个没有标题的空会话
import { getUserHomepage } from '@/api/badge'
import SystemNoticeCard from '@/components/chat/SystemNoticeCard.vue'
import {
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
  clearAllUnread,
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

/**
 * 「消息 / 好友」两个主视图各自对应一条路由（见 router/index.ts）：
 *   /student/messages          → 消息（会话列表）
 *   /student/messages/friends  → 好友（通讯录 · 我关注的）
 * 两条路由渲染同一个组件，只是进入时按地址落位到对应视图；页内换标题再 replace 回地址，
 * URL 与页头高亮互为镜像 —— 刷新、分享链接、浏览器前进后退都能停在同一个视图上。
 * 「互动」是同一页里的第三个视图（移动端从「好友」往左滑进，桌面端走页签），没有独立地址，故不参与路由。
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
const keyword = ref('')
/** 会话行头像直径：移动端整行长高了（名字 17px + 独行摘要），头像跟着放大到 46，桌面维持 40 */
const avatarSize = computed(() => (isMobile.value ? 46 : 40))
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
 *
 * 2026-11 补充：悬浮导航现在有淡出淡入（.dock-fade，见 MobileTabBar.vue），
 * 但这条结论不变 —— 被覆盖层盖住是「逐帧」的，卸掉却是「一次性」的，
 * 后者哪怕加了淡出，也会和聊天页自己的滑入各走各的。所以这里仍然不登记。
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

/**
 * 通讯录分节：按姓名首字母切段，段内仍按拼音序。
 * 空段不渲染（不摆一屏「C」「D」的空标题），右侧索引里再把这些字母置灰。
 */
const contactGroups = computed(() => {
  const buckets = new Map<string, ContactUser[]>()
  for (const c of filteredContacts.value) {
    const letter = initialOf(c.name)
    const list = buckets.get(letter)
    if (list) list.push(c)
    else buckets.set(letter, [c])
  }
  return [...buckets.entries()]
    .map(([letter, items]) => ({
      letter,
      items: [...items].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN')),
    }))
    .sort((a, b) => indexOrder(a.letter) - indexOrder(b.letter))
})

const presentLetters = computed(() => new Set(contactGroups.value.map((g) => g.letter)))
/** 右栏高亮哪个字母：跟着滚动走到的那一节 */
const activeLetter = ref('A')
// 名单到手（或搜索过滤后）先点亮第一节：否则只有 C/L/W 几个人时，右栏会亮着一个不存在的 A
watch(
  contactGroups,
  (groups) => {
    if (!groups.length) return
    if (!groups.some((g) => g.letter === activeLetter.value)) activeLetter.value = groups[0].letter
  },
  { immediate: true },
)
const indexKeys = INDEX_KEYS
/**
 * 点索引跳转后先锁住高亮：跳到底部时列表滚不动那么远，
 * 滚动把高亮改写成「实际顶到页头的那一节」，点 W 却亮 S 会让人以为点错了。
 * 锁一直保持到用户在列表上真正动手（pointerdown / wheel）。
 */
let letterPinned = false
function unpinLetter() {
  letterPinned = false
}

const groupMeta = computed(() => {
  if (!activeSession.value || activeSession.value.type !== 'group') return ''
  const g = groups.value.find((x) => x.id === activeSession.value?.rawId)
  if (!g) return ''
  return `${g.member_count} 人 · ${g.online_count} 在线${g.is_muted ? ' · 免打扰' : ''}`
})

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
    contacts.value = await getContacts({ tab: 'following', keyword: keyword.value.trim() || undefined })
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

/**
 * 页内主视图的**唯一状态落点**（消息 / 好友 / 互动）。
 * 三条入口最后都收在这里：轨道回报（拖动吸附 / 点标题换页）、桌面端三栏页签、地址回填。
 * 页头高亮、搜索范围、下方轨道用的是同一份 activeTab，不会各说各话。
 */
function switchMainTab(tab: string) {
  if (!isViewKey(tab)) return
  if (activeTab.value === tab) return
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

/** 页头放大镜的点击：进整页搜索（push，返回键才回得到列表） */
function openSearchPage() {
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
  // draft 来自个人主页「发消息 / 加为好友」：加好友时预填一句问候，让用户自己按发送。
  // 一并从地址里抹掉，否则刷新一次草稿又被塞回输入框。
  const prefill = typeof route.query.draft === 'string' ? route.query.draft : ''
  const { chat: _chat, chatName: _chatName, draft: _draft, ...restQuery } = route.query
  void router.replace({ name: 'student-messages', query: restQuery })

  /** 打开会话并按需铺草稿（draft 是同一个 ref，换会话不自动清） */
  const open = (s: SessionItem) => {
    openSession(s)
    if (prefill) draft.value = prefill
  }

  const target = sessions.value.find((s) => s.key === key)
  if (target) {
    open(target)
    return
  }
  const m = /^s-(\d+)$/.exec(key)
  if (!m) return
  const uid = Number(m[1])
  // 桌面端首屏不一定拉过通讯录（只有移动端预载），这里按需补一次再找人
  if (!contacts.value.length) await loadContacts()
  const user = contacts.value.find((c) => c.id === uid)
  if (user) {
    open(privateSession(user))
    return
  }
  // 通讯录只有「我关注的」这一类人：搜索里点陌生人发消息时名单里查不到，
  // 名单里必然查不到 —— 退回个人主页接口取名字和头像，会话仍能正常打开
  try {
    const profile = await getUserHomepage(uid)
    open(privateSession({ id: profile.id, name: profile.name, avatar: profile.avatar }))
  } catch {
    /* 取不到就什么都不做：总比开一个标题是「用户 12」的空会话强 */
  }
}

/* ==================== 视图左右翻页（移动端 / 桌面端共用一份标记） ==================== */

/**
 * 三个主视图（消息 / 好友 / 互动）就是轨道上的三页。
 * 拖动 1:1 跟手、松手按位移 / 速度吸附或回弹、点标题两页对滑、邻居页的挂载与卸载，
 * 全在 components/common/SwipePager.vue（与校园资讯分类分页同一个组件）；
 * 本页只留两件事：① 告诉轨道有哪几页、给出每页内容；② 把轨道的即时状态转给页头滑条。
 *
 * 「互动」排第三页：它不是页头的一枚标题，移动端只能从「好友」往左滑进；
 * 走到这一页时页头滑条自然隐去（两个标题都不再选中）。
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
 * 切换主视图（页头标题 / 页签 / 手势）：内容横向滑过去，与手指切换同一段时长。
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

/** 现造一条单聊会话：列表里还没有这个人（没聊过、刚关注）时用，键与列表口径一致（s-<id>） */
function privateSession(user: { id: number; name: string; avatar: string | null }): SessionItem {
  return {
    key: `s-${user.id}`,
    type: 'private',
    rawId: user.id,
    name: user.name,
    avatar: user.avatar,
    lastMessage: '',
    time: null,
    unread: 0,
  }
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
/** 副标题：在线就直说「在线」，否则给签名，再退到班级 / 学院（和名片上的口径一致） */
function contactLine(c: ContactUser) {
  if (isOnline(c.id)) return '在线'
  const sig = (c.signature || '').trim()
  if (sig) return sig
  if (c.class_name) return c.class_name
  if (c.college) return c.college
  return c.role === 'teacher' ? '教师' : ''
}

/* ---------- 行的三个动作：点行发消息 / 点头像看主页 / 长按取关 ---------- */

/** 长按判定：按住不动 550ms 才算，手指一划（翻页、滚动）就取消 */
const PRESS_MS = 550
const PRESS_TOLERANCE = 8
let pressTimer: number | undefined
let pressOrigin: { x: number; y: number } | null = null
/** 长按触发过就吞掉紧跟其后的 click，否则松手会顺手把会话也打开 */
let pressConsumed = false

/**
 * 长按触发取关后，松手还会跟一次 click —— 用它把这一次吞掉，
 * 否则确认框刚弹出来、主页也跟着被推开。正常点击由行上的 openHomepage 处理。
 */
function swallowClickAfterPress() {
  if (!pressConsumed) return false
  pressConsumed = false
  return true
}

function onContactPressStart(c: ContactUser, e: PointerEvent) {
  onContactPressEnd()
  // 桌面端没有「长按」习惯，取关走右键菜单
  if (!isMobile.value) return
  pressOrigin = { x: e.clientX, y: e.clientY }
  pressConsumed = false
  pressTimer = window.setTimeout(() => {
    pressTimer = undefined
    pressConsumed = true
    void askUnfollow(c)
  }, PRESS_MS)
}

function onContactPressMove(e: PointerEvent) {
  if (!pressTimer || !pressOrigin) return
  if (Math.abs(e.clientX - pressOrigin.x) > PRESS_TOLERANCE) onContactPressEnd()
  else if (Math.abs(e.clientY - pressOrigin.y) > PRESS_TOLERANCE) onContactPressEnd()
}

function onContactPressEnd() {
  if (pressTimer) window.clearTimeout(pressTimer)
  pressTimer = undefined
  pressOrigin = null
}

/** 取关要二次确认：名单里没有别的地方能点回来，误触代价是静默少一个人 */
async function askUnfollow(c: ContactUser) {
  try {
    await ElMessageBox.confirm(`不再关注「${c.name}」？`, '取消关注', {
      confirmButtonText: '取消关注',
      cancelButtonText: '再想想',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await unfollowUser(c.id)
    contacts.value = contacts.value.filter((x) => x.id !== c.id)
    ElMessage.success('已取消关注')
  } catch {
    ElMessage.error('取消关注失败，请稍后再试')
  }
}

/* ---------- 右侧字母索引 ---------- */

/** 当前这一页的滚动词表：只有好友页会渲染 .msg-alpha-group，据此反查容器即可 */
function contactsScroller(): HTMLElement | null {
  const head = document.querySelector('.msg-alpha-group')
  return head ? (head.closest('.msg-list') as HTMLElement | null) : null
}

function jumpToLetter(letter: string) {
  if (!presentLetters.value.has(letter)) return
  const list = contactsScroller()
  const target = list?.querySelector<HTMLElement>(`.msg-alpha-group[data-letter="${letter}"]`)
  if (!list || !target) return
  activeLetter.value = letter
  letterPinned = true
  const delta = target.getBoundingClientRect().top - list.getBoundingClientRect().top
  list.scrollTo({ top: list.scrollTop + delta, behavior: 'auto' })
}

/** 滚动时点亮左栏对应的字母：取「已经滚过页头的那一节」里最靠下的一节 */
function syncActiveLetter(list: HTMLElement) {
  if (letterPinned) return
  const groups = Array.from(list.querySelectorAll<HTMLElement>('.msg-alpha-group'))
  if (!groups.length) return
  const baseline = list.getBoundingClientRect().top + 6
  let current = groups[0].dataset.letter || groups[0].textContent?.trim() || 'A'
  for (const g of groups) {
    if (g.getBoundingClientRect().top <= baseline) current = g.dataset.letter || current
    else break
  }
  if (current !== activeLetter.value) activeLetter.value = current
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

/* ==================== 右上角「＋」面板 ====================
   面板里只放**真能落地**的三件事：建群、找人、清未读。
   参考的微信截图里还有「扫一扫 / 收付款 / 创建频道」—— 本系统没有二维码支付、
   没有频道域，硬放进去只会点出一句「暂未开放」，所以不做。 */

const plusOpen = ref(false)
const hasAnyUnread = computed(
  () => sessionUnreadTotal.value > 0 || forumUnread.value > 0 || noticeSession.unread > 0,
)

function togglePlusMenu() {
  plusOpen.value = !plusOpen.value
}

/** Esc 收起（键盘 / 外接键盘场景）；点空白处收起由压暗层自己接 —— 它盖满全屏，不会再漏 */
function onPlusEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') plusOpen.value = false
}

watch(plusOpen, (open) => {
  if (open) document.addEventListener('keydown', onPlusEscape)
  else document.removeEventListener('keydown', onPlusEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onPlusEscape)
})

/* ---------- 发起群聊 ---------- */
const createGroupOpen = ref(false)

/**
 * 子页（会话 / 发起群聊）打开时，本页「非子页的那一层」整体退 30%：
 * **页头 + 侧栏列表一起走**。页头是 .msg-side 的兄弟（一个在 .msg-page 下、
 * 一个在 .msg-main 里），只推侧栏会出现「列表左移、页头钉住」，一层被拆成两半，
 * 所以两处都挂 .subpage-underlay，共用这一个开关。
 * 底部胶囊不归本页管：它属于布局层，由 useSubpagePush 登记后布局层自己推。
 * 声明放在 createGroupOpen 之后：useSubpagePush 会立即求值一次，引用早了会 TDZ。
 */
const chatPushed = computed(() => isMobile.value && (chatOpen.value || createGroupOpen.value))
useSubpagePush(chatPushed)

/** 「＋」里的建群：只负责开表单，选人与提交在 CreateGroupPopup 里 */
function openCreateGroup() {
  plusOpen.value = false
  createGroupOpen.value = true
}

/** 建群成功：刷新会话列表并直接进群 —— 新群还没有消息，time 取此刻，回列表时才排得上去 */
async function onGroupCreated(group: { id: number; name: string }) {
  await loadSessions()
  openSession({
    key: `g-${group.id}`,
    type: 'group',
    rawId: group.id,
    name: group.name,
    avatar: null,
    lastMessage: '',
    time: new Date().toISOString(),
    unread: 0,
  })
}

/** 加好友 / 群：进「添加朋友」子页（搜索找人 / 建群 / 推荐 / 名片都在那一页） */
function goFindPeople() {
  plusOpen.value = false
  void router.push({ name: 'student-message-add' })
}

/** 全部标为已读：单聊 / 群聊走后端 read-all，互动走 markForumRead，系统通知是本地状态 */
async function markAllReadFromMenu() {
  plusOpen.value = false
  if (!hasAnyUnread.value) return
  try {
    const jobs: Array<Promise<unknown>> = [clearAllUnread()]
    if (forumUnread.value) jobs.push(markForumRead())
    await Promise.all(jobs)
    noticeSession.unread = 0
    forumUnread.value = 0
    await loadSessions()
    void refreshUnread()
  } catch {
    ElMessage.error('操作失败，请稍后再试')
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
/** 临时关掉页头的 margin-top 过渡：换视图时归位要「瞬间完成」，与列表的 scrollTop 回退同帧抵消 */
const appbarNoAnim = ref(false)

/** 取某个视图的滚动列表：换视图时靠它把页头归位带来的 48px 抵消掉 */
function viewListEl(view: TabValue): HTMLElement | null {
  return document.querySelector<HTMLElement>(`.msg-view[data-view="${view}"] .msg-list`)
}

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
  const el = e.target as HTMLElement | null
  // 只认视图列表；移动端聊天浮层里的 .msg-chat-scroll 不参与
  if (!el || !el.classList?.contains('msg-list')) return

  // 好友页的字母索引跟着滚动点亮（桌面端不跑页头逻辑，但索引一样要跟）
  if (activeTab.value === 'contacts') syncActiveLetter(el)

  if (!isMobile.value) return

  // 「＋」面板开着时不收页头：面板锚在页头上，页头一滑走面板就跟着飞出去。
  // 位置记账照做（否则收起面板后第一下手势会拿旧坐标算出一次假位移），只是不改状态。
  if (plusOpen.value) {
    lastTop.set(el, el.scrollTop)
    scrolledBy = 0
    return
  }

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

/**
 * 页头归位：换视图、或开始横滑时调用。
 *
 * 收起状态是「上一个视图的滚动位置」的产物，带到下一个视图没有意义，所以要放回来；
 * 但**不能用那条 0.24s 的 margin-top 过渡**：页头是参与布局的，
 * 它一边展开、列表顶边就一边往下走，切页那几十毫秒里整条列表（自然包括第一行）
 * 会明显地往下滑一下 —— 这就是「切到好友，第一行往下掉」的根源。
 *
 * 所以这里同一帧做两件事，让「动」互相抵消：
 *   ① 关掉过渡，页头立刻归位（列表顶边因此下移 h）；
 *   ② 把仍在屏幕上的那条列表的 scrollTop 加上 h —— 滚动量增加会把内容往上带，
 *      正好抵消这一截。
 * 两者相等，画面上一行都不动。新视图是这一帧才挂载的，
 * 它的第一行天生就落在「页头已展开」的位置上，不需要（也没法）补。
 */
function settleAppbar(view: TabValue) {
  if (!appbarHidden.value) return
  const h = appbarRef.value?.offsetHeight ?? 0
  const list = viewListEl(view)
  appbarNoAnim.value = true
  appbarHidden.value = false
  scrolledBy = 0
  void nextTick(() => {
    // 页头此刻已经归位（列表顶边下移 h），把 scrollTop 加上同样的距离 ——
    // 滚动量增加会把内容往上带，正好抵消这一截，屏幕上一行都不动。
    // 放在 nextTick 里而不是同一次赋值：页头还是收起态时，scrollTop 会被旧的
    // 滚动上限截断，补偿量会丢一截。nextTick 仍在同一帧内（绘制之前），看不到中间态。
    if (h && list?.isConnected) {
      list.scrollTop += h
      // 记账同步：这段是我们自己挪的，下一次滚动不该把它算成一次真实位移
      lastTop.set(list, list.scrollTop)
    }
    // 先把「无过渡 + 已归位」这一帧结算掉，再恢复过渡，避免之后收起时补一段动画
    void appbarRef.value?.offsetHeight
    appbarNoAnim.value = false
  })
}

/** 换视图（含拖动切页 / 空格键 / 地址回填）时把页头放回来 */
watch(activeTab, (_tab, prev) => {
  settleAppbar(prev ?? activeTab.value)
})

/**
 * 开始横滑就归位，而不是等吸附完成：
 * 吸附结束时新页已经停在屏幕正中、且它是刚挂载的（scrollTop 为 0），
 * 那一刻再展开页头，就是 48px 直接「跳」一下，补不回来。
 */
watch(
  () => pagerState.value.dragging,
  (dragging) => {
    if (dragging) settleAppbar(activeTab.value)
  },
)

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
      activeTab.value = tab
  },
)

/**
 * 地址里的 chat 也要 watch：/student/messages/friends 与 /student/messages 是同一个组件，
 * 从好友页跳过来时 Vue Router 会复用实例、不重跑 onMounted —— 只写在 onMounted 里的话，
 * 从好友列表「点人 → 主页 → 发消息」过来，会话根本不会打开。
 */
watch(
  () => route.query.chat,
  (chat) => {
    if (chat) void openChatFromQuery()
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
  z-index: 20;
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  height: 48px;
  background: #fff;
  border-bottom: 1px solid #f0f1f3;
  /* 收起用 margin-top 而不是 transform：整条页头要真的「让出位置」，
     下面的搜索条和列表一起跟着上移。只做 transform 会在顶上留一条底色的空带。
     页头顶边一旦越过 .msg-page 的顶沿就被 .main-area 的 overflow:hidden 裁掉，
     不会画到全局导航栏上面去。
     transform 那一项是给「子页让位」用的（.subpage-underlay 的 -30%）：
     这里不显式列出来的话，本条的 transition 会盖掉全局那条，
     页头就从「和列表一起滑」变成「瞬移 117px」。 */
  transition: margin-top 0.24s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s ease;
}
/* --ab-h 由 measureAppbar() 按实测高度写进来（含下边框） */
.msg-appbar.is-hidden { margin-top: calc(-1 * var(--ab-h, 49px)); }
/* 换视图时页头必须「瞬间」归位：只要让 margin-top 走过渡，列表顶边就会跟着页头
   一起往下挪，切页那 200ms 里整条列表（包括第一行）都会肉眼可见地滑一下。
   归位本身挪掉的高度由 JS 在同帧回退列表的 scrollTop 抵掉，所以这里必须无过渡。 */
.msg-appbar.is-instant { transition: none; }
@media (prefers-reduced-motion: reduce) {
  .msg-appbar { transition: none; }
}
/* 外观全部通过 CSS 变量喂给组件，组件内部的动画逻辑一行都不用改。
   左右各 82px：右边给「搜索 + ＋」两枚图标让位（36+2+36+8），左边对称留白，
   标题组因此仍落在页面正中。
   两层文字必须同宽才能对齐裁剪，所以选中态只改颜色、不改字重（统一 700）。 */
.msg-appbar-tabs {
  flex: 1;
  min-width: 0;
  --st-height: 48px;
  --st-pad: 0 82px;
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
/* 页头右侧动作组：搜索 + ＋ 两枚图标贴着右上角排，间距 2px。
   搜索从列表顶部那条胶囊收进来之后，列表整体上提了 46px，页头也只剩这两枚图标。 */
.msg-appbar-acts {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 2px;
}
.msg-appbar-icon {
  position: relative;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #1d2129;
  cursor: pointer;
  transition: background 0.16s ease;
}
.msg-appbar-icon:active { background: #f2f3f5; }
/* 「＋」：只负责开面板，不再挂互动未读红点 —— 那一行已经不在面板里，
   红点点开也找不到落点；互动未读改在页签与「互动」视图内呈现。 */
.msg-appbar-plus.is-open { background: #f2f3f5; }
/* 展开时加号转成叉：同一枚按钮既是「开」也是「关」，形状得跟着变 */
.msg-appbar-plus .el-icon {
  transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}
.msg-appbar-plus.is-open .el-icon { transform: rotate(45deg); }

/* 面板展开时整条页头提到浮层之上：压暗层是页头的子元素，
   靠页头自己的 z-index 才能盖住底部悬浮导航（1000）—— 否则导航亮着、上面全暗，像穿帮 */
.msg-appbar.is-menu-open { z-index: 1900; }

/* 压暗底：盖满全屏（连页头标题与底部导航一起压），只有面板浮在最上面。
   深浅按参考图量过：原图白底被压到 ≈217/255，即约 15% 黑 —— 再重就成「遮罩弹窗」，
   轻到看不出层次；这里取 18%，比参考略深一点，因为本页底色本身是 #f5f6f8 的浅灰。 */
.msg-plus-mask {
  position: fixed;
  inset: 0;
  z-index: 1;
  background: rgba(17, 24, 39, 0.18);
}
.msg-plus-mask-enter-active { transition: opacity 0.2s ease; }
.msg-plus-mask-leave-active { transition: opacity 0.16s ease; }
.msg-plus-mask-enter-from,
.msg-plus-mask-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  .msg-plus-mask-enter-active,
  .msg-plus-mask-leave-active { transition: none; }
}

/* 「＋」面板：白卡片 + 指向按钮的小尖角，圆角与面积对齐参考图 */
.msg-plus-panel {
  position: absolute;
  right: 8px;
  top: calc(100% + 10px);
  z-index: 40;
  min-width: 186px;
  padding: 6px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 14px 36px rgba(17, 24, 39, 0.16), 0 2px 8px rgba(17, 24, 39, 0.06);
  transform-origin: top right;
}
.msg-plus-panel::before {
  content: '';
  position: absolute;
  top: -5px;
  right: 20px;
  width: 11px;
  height: 11px;
  background: #fff;
  transform: rotate(45deg);
  border-radius: 2px;
}
.msg-plus-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 46px;
  padding: 0 12px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #1d2129;
  font-size: 15px;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.msg-plus-item:active { background: #f4f5f7; }
.msg-plus-item:disabled { color: #c2c6cc; cursor: default; }
.msg-plus-item:disabled .el-icon { color: #c9ccd2; }
/* 灰掉的行不该还有按压反馈 */
.msg-plus-item:disabled:active { background: transparent; }
.msg-plus-sep { height: 1px; margin: 5px 8px; background: #f0f1f3; }
.msg-plus-panel-enter-active { transition: opacity 0.16s ease, transform 0.18s cubic-bezier(0.2, 0.8, 0.2, 1); }
.msg-plus-panel-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.msg-plus-panel-enter-from,
.msg-plus-panel-leave-to { opacity: 0; transform: translateY(-6px) scale(0.94); }

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
.msg-view { position: relative; display: flex; flex-direction: column; height: 100%; min-height: 0; background: #fff; }

/* ================= 列表 ================= */
.msg-list { flex: 1; min-height: 0; overflow-y: auto; padding-bottom: 12px; scrollbar-width: thin; }
.msg-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 54px 20px; color: #9aa0a6; font-size: 13px; text-align: center; }
.msg-empty p { margin: 4px 0 0; color: #4b5563; font-size: 14px; }
.msg-empty span { font-size: 12px; }
/* 空态里的唯一动作：给它一颗胶囊，别做成一行蓝字 —— 空态本来就缺锚点，字太小会被忽略 */
.msg-empty-cta { margin-top: 12px; height: 32px; padding: 0 16px; border: 1px solid #3b82f6; border-radius: 16px; background: #fff; color: #3b82f6; font-size: 13px; font-family: inherit; cursor: pointer; }
.msg-empty-cta:active { background: #eef4ff; }

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
/* 移动端专用：未读数挂在头像右上角。桌面端由行尾那枚 .msg-unread 承担，这里默认不出现 */
.msg-avatar-badge {
  display: none;
  position: absolute;
  top: -3px;
  right: -5px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  box-sizing: border-box;
  border-radius: 9px;
  background: #fa5151;
  color: #fff;
  font-size: 11px;
  font-style: normal;
  font-weight: 500;
  line-height: 18px;
  text-align: center;
  letter-spacing: -0.2px;
  /* 白描边把红点和头像切开：头像底色深浅不定，靠分隔环才始终立得住 */
  box-shadow: 0 0 0 2px #fff;
}

/* ================= 通讯录 ================= */
/* 通讯录：字母分节 + 姓名 / 签名两行，行上不放按钮 */
.msg-alpha-head {
  /* 吸顶的字母条：滚到哪一节就顶哪一节，右侧索引点它也是落到这一行 */
  position: sticky;
  top: 0;
  z-index: 1;
  margin: 0;
  padding: 7px 24px 5px 16px;
  background: #fff;
  color: #9aa0a6;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.2;
}
.msg-contact {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  /* 右边留 24px 给字母索引，长签名不会钻到字母底下 */
  padding: 11px 24px 11px 16px;
  border: 0;
  background: none;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.msg-contact:active { background: #f3f4f6; }
.msg-contact-avatar { flex-shrink: 0; color: #fff; font-size: 16px; }
.msg-contact-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.msg-contact-name {
  font-size: 17px;
  line-height: 1.25;
  color: #16181d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-contact-sub {
  /* 必须是 block：flex 容器里的文本会变成匿名 flex item，text-overflow 不生效，
     长签名会被硬切在字母索引边上（没有省略号） */
  display: block;
  min-width: 0;
  font-size: 13px;
  line-height: 1.3;
  color: #9aa0a6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-contact-online {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 5px;
  border-radius: 50%;
  background: #22c55e;
  vertical-align: 1px;
}
.msg-ghost-btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e7eb; background: #fff; color: #4b5563; font-size: 12px; padding: 4px 10px; border-radius: 999px; cursor: pointer; }
.msg-ghost-btn:hover { border-color: #d1d5db; color: #111827; }
/* 只剩图标的那种（会话页头「主页」）：方形胶囊改成圆形，并且与左侧返回键同一套外观 ——
   页头两端各一枚 30px 灰底圆，中间放名字，视觉上才是成对的 */
.msg-ghost-icon {
  width: 30px;
  height: 30px;
  padding: 0;
  flex-shrink: 0;
  justify-content: center;
  border: 0;
  border-radius: 50%;
  background: #f4f5f7;
  color: #4b5563;
}
.msg-ghost-icon:hover { background: #eceef1; color: #1f2329; }
/* 三条横线：填 currentColor，跟着按钮的文字色走 */
.msg-menu-lines { display: block; fill: currentColor; }

/* 右侧 A-Z 索引：整列贴在视图右边垂直居中，点一下跳到对应分节 */
.msg-alpha-index {
  position: absolute;
  right: 2px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 0;
  user-select: none;
}
.msg-alpha-key {
  width: 20px;
  padding: 0;
  border: 0;
  background: none;
  font-family: inherit;
  font-size: 11.5px;
  line-height: 15px;
  color: #5b6069;
  cursor: pointer;
}
.msg-alpha-key.dim { color: #c9ccd1; cursor: default; }
.msg-alpha-key.active { color: #3b82f6; font-weight: 600; }

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
     互动只在「好友」页往左滑到达。页签行留着只会和标题重复一层。 */
  .msg-tabs { display: none; }
  /* 移动端列表顶到页头下方：搜索胶囊已收进页头，不再需要它那一行的留白 */
  .msg-main { flex-direction: column; }
  .msg-side { width: 100%; border-right: none; flex: 1; }
  .msg-list { padding-bottom: calc(84px + env(safe-area-inset-bottom, 0px)); overscroll-behavior-y: contain; }

  /* ===== 会话行：移动端换成「大头像 + 大名字 + 独行摘要」的消息列表版式 =====
     未读数从左下角那枚行尾徽标挪到头像右上角：摘要单独占一行以后，
     行尾没有纵向空间留给它，压在摘要右侧又会把摘要挤成一条窄缝。 */
  .msg-session { padding: 12px 16px; gap: 12px; }
  .msg-session:active { background: #f3f4f6; }
  .msg-notice-avatar { width: 46px; height: 46px; }
  .msg-online-dot { right: 0; bottom: 0; width: 10px; height: 10px; border-width: 2px; }
  .msg-avatar-badge { display: block; }
  .msg-session-main { display: flex; flex-direction: column; justify-content: center; gap: 3px; }
  /* 名字与时间按基线对齐：两者字号差 4.5px，居中对齐会让时间看着偏高或偏低 */
  .msg-session-row { align-items: baseline; }
  .msg-session-row:last-child { align-items: center; margin-top: 1px; }
  .msg-session-name { flex: 1; min-width: 0; font-size: 17px; font-weight: 400; line-height: 1.3; color: #16181d; }
  .msg-group-mark { margin-right: 5px; padding: 0 5px; font-size: 10.5px; vertical-align: 2px; }
  .msg-session-time { font-size: 12.5px; color: #b6b9be; padding: 0; }
  .msg-session-last { flex: 1; min-width: 0; font-size: 13.5px; color: #8b8f97; line-height: 1.4; }
  /* 摘要行不再挂未读徽标：移动端已挪到头像上，留着会显示两遍 */
  .msg-unread { display: none; }

  .msg-pane.is-mobile-chat { position: fixed; inset: 0; z-index: 2600; background: #fff; }
  .msg-pane.is-mobile-chat .msg-pane-head { padding-top: calc(12px + env(safe-area-inset-top, 0px)); }
  .msg-pane.is-mobile-chat .msg-chat-scroll { padding-bottom: 18px; }
}
@media (min-width: 768px) {
  .msg-side { max-width: 340px; }
}
</style>
