<template>
  <!-- 消息搜索子页：从消息页页头的放大镜进入（/student/messages/search）。
       独立成页而不是列表里的内嵌搜索：移动端键盘弹起后只剩半屏，
       把「输入 → 分区结果 → 点进去」这件事放在整页里做，比挤在 320px 侧栏里稳。
       桌面端同一个地址同样可用（居中 720px 面板），只是桌面侧栏本来就能就地过滤，
       所以入口只在移动端出现。 -->
  <div class="ms-page">
    <header class="ms-head">
      <button type="button" class="ms-back" aria-label="返回" @click="goBack">
        <el-icon :size="22"><ArrowLeft /></el-icon>
      </button>
      <div class="ms-field">
        <el-icon class="ms-field-icon" :size="16"><Search /></el-icon>
        <input
          ref="inputRef"
          v-model="keyword"
          class="ms-input"
          type="search"
          enterkeyhint="search"
          placeholder="搜索"
          @keyup.enter="remember"
          @keyup.esc="goBack"
        />
        <button
          v-if="keyword"
          type="button"
          class="ms-clear"
          aria-label="清空关键词"
          @click="clearKeyword"
        >
          <el-icon :size="15"><CircleCloseFilled /></el-icon>
        </button>
      </div>
      <!-- 「取消」常驻：它是这页的退出入口，不该等输入了才出现 ——
           否则空态时右边一片空，用户找不到「不搜了」的出口 -->
      <button type="button" class="ms-cancel" @click="cancelSearch">取消</button>
    </header>

    <div class="ms-body">
      <!-- Ⅰ 还没输入：最近搜索 + 提示。历史为空时只留一句提示，
             不硬凑「热门搜索」这类假入口（消息域没有可推荐的公共热词）。 -->
      <template v-if="!kw">
        <section v-if="history.length" class="ms-sec">
          <div class="ms-sec-head">
            <h2>最近搜索</h2>
            <button type="button" class="ms-text-btn" @click="clearHistory">
              <el-icon :size="14"><Delete /></el-icon>
              <span>清空</span>
            </button>
          </div>
          <div class="ms-chips">
            <button
              v-for="h in history"
              :key="h"
              type="button"
              class="ms-chip"
              @click="applyHistory(h)"
            >{{ h }}</button>
          </div>
        </section>
        <div class="ms-blank">
          <el-icon :size="30"><Search /></el-icon>
          <p>搜索会话、好友和互动消息</p>
          <span>输入姓名、班级或聊天内容里的关键词</span>
        </div>
      </template>

      <!-- Ⅱ 结果：三块分区，各自独立成组，组内不再二次筛选 -->
      <template v-else>
        <p v-if="loading" class="ms-status">加载中…</p>
        <div v-else-if="!totalHits" class="ms-blank">
          <el-icon :size="30"><Search /></el-icon>
          <p>没有找到与「{{ kw }}」相关的内容</p>
          <span>换个关键词试试，也可以搜聊天内容里的词</span>
        </div>
        <template v-else>
          <!-- 会话：私聊 + 群聊，名字与最后一条消息都参与匹配 -->
          <section v-if="sessionHits.length" class="ms-sec">
            <h2 class="ms-sec-head is-plain">会话<i>{{ sessionHits.length }}</i></h2>
            <button
              v-for="s in sessionHits"
              :key="s.key"
              type="button"
              class="ms-row"
              @click="openSessionHit(s)"
            >
              <span v-if="s.type === 'notice'" class="ms-notice-avatar" aria-hidden="true">
                <el-icon :size="17"><Bell /></el-icon>
              </span>
              <el-avatar v-else :size="38" :src="s.avatar || undefined">{{ s.name.slice(0, 1) }}</el-avatar>
              <div class="ms-row-main">
                <span class="ms-row-title">
                  <i v-if="s.type === 'group'" class="ms-group-mark">群</i>
                  <span v-html="hl(s.name)"></span>
                </span>
                <span class="ms-row-sub" v-html="hl(s.lastMessage || '暂无消息')"></span>
              </div>
              <span class="ms-row-time">{{ formatTime(s.time) }}</span>
            </button>
          </section>

          <!-- 好友：与好友页同一份名单（我关注的），互关的排前面 -->
          <section v-if="contactHits.length" class="ms-sec">
            <h2 class="ms-sec-head is-plain">好友<i>{{ contactHits.length }}</i></h2>
            <button
              v-for="c in contactHits"
              :key="c.id"
              type="button"
              class="ms-row"
              @click="openContactHit(c)"
            >
              <el-avatar :size="38" :src="c.avatar || undefined">{{ c.name.slice(0, 1) }}</el-avatar>
              <div class="ms-row-main">
                <span class="ms-row-title" v-html="hl(c.name)"></span>
                <span class="ms-row-sub" v-html="hl(c.meta)"></span>
              </div>
              <span class="ms-row-action">发消息</span>
            </button>
          </section>

          <!-- 互动：论坛的赞 / 收藏 / 评论 / 新粉丝，帖子标题与评论内容都参与匹配 -->
          <section v-if="forumHits.length" class="ms-sec">
            <h2 class="ms-sec-head is-plain">互动消息<i>{{ forumHits.length }}</i></h2>
            <button
              v-for="m in forumHits"
              :key="m.id"
              type="button"
              class="ms-row"
              @click="openForumHit(m)"
            >
              <el-avatar :size="38" :src="m.actorAvatar || undefined">
                {{ m.actorName.slice(0, 1) }}
              </el-avatar>
              <div class="ms-row-main">
                <span class="ms-row-title" v-html="hl(m.actorName)"></span>
                <span class="ms-row-sub">
                  <span v-html="hl(forumSub(m))"></span>
                </span>
              </div>
              <span class="ms-row-time">{{ formatTime(m.createdAt) }}</span>
            </button>
          </section>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  Bell,
  CircleCloseFilled,
  Delete,
  Search,
} from '@element-plus/icons-vue'
import { getConversations, type ConversationOut } from '@/api/messages'
import { getGroups, type GroupOut } from '@/api/groups'
import {
  getContacts,
  getForumMessages,
  type ContactUser,
  type ForumKind,
  type ForumMessageOut,
} from '@/api/social'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { highlightMatches } from '@/utils/textHighlight'
import { SYSTEM_NOTICE, minutesAgo } from '@/utils/systemNotice'

const router = useRouter()

/* ==================== 检索数据 ====================
   一次进页面把四个池子拉全，此后全在前端过滤 —— 与消息页的搜索口径一致
   （会话按名字、好友按姓名/班级、互动按标题与评论内容），不发第二趟请求。
   任一路失败只让它那块为空，不影响其它分区出结果。 */

const loading = ref(true)
const conversations = ref<ConversationOut[]>([])
const groups = ref<GroupOut[]>([])
const contacts = ref<ContactUser[]>([])
const forum = ref<ForumMessageOut[]>([])

async function loadAll() {
  loading.value = true
  try {
    const [conv, grp, following, forumList] = await Promise.all([
      getConversations().catch(() => [] as ConversationOut[]),
      getGroups().catch(() => [] as GroupOut[]),
      // 「好友」就是「我关注的」，与好友页同一口径：只拉这一档，不再并入「关注我的」。
      // 并进来的话，那些人会以「好友」身份出现在结果里、还带「发消息」——
      // 而按规则没关注就不能发消息，两处口径就打架了。
      getContacts({ tab: 'following' }).catch(() => [] as ContactUser[]),
      getForumMessages({ limit: 50 }).catch(() => [] as ForumMessageOut[]),
    ])
    conversations.value = conv
    groups.value = grp.filter((g) => !g.is_dismissed)
    forum.value = forumList
    contacts.value = following
  } finally {
    loading.value = false
  }
}

/* ==================== 关键词与命中 ==================== */

const keyword = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

/** 去掉首尾空格后的词：空串 = 未进入搜索态（显示历史而不是「没有结果」） */
const kw = computed(() => keyword.value.trim())
const kwLower = computed(() => kw.value.toLowerCase())

/** 单个字段是否命中：空字段一律不算命中，避免 null 被 String() 成 "null" */
function hit(text: string | null | undefined): boolean {
  if (!text) return false
  return text.toLowerCase().includes(kwLower.value)
}

interface SessionHit {
  key: string
  type: 'private' | 'group' | 'notice'
  name: string
  avatar: string | null
  lastMessage: string
  time: string | null
}

const sessionHits = computed<SessionHit[]>(() => {
  if (!kw.value) return []
  const list: SessionHit[] = []
  // 「消息通知」也算会话列表里的一条，搜索口径要和消息页对齐：
  // 搜「通知」「教务」都能把它捞出来
  if (hit(SYSTEM_NOTICE.name) || hit(SYSTEM_NOTICE.summary)) {
    list.push({
      key: SYSTEM_NOTICE.key,
      type: 'notice',
      name: SYSTEM_NOTICE.name,
      avatar: null,
      lastMessage: SYSTEM_NOTICE.summary,
      time: minutesAgo(26),
    })
  }
  for (const c of conversations.value) {
    if (!hit(c.user_name) && !hit(c.last_message)) continue
    list.push({
      key: `s-${c.user_id}`,
      type: 'private',
      name: c.user_name,
      avatar: c.user_avatar,
      lastMessage: c.last_message,
      time: c.last_message_time,
    })
  }
  for (const g of groups.value) {
    if (!hit(g.name) && !hit(g.last_message)) continue
    list.push({
      key: `g-${g.id}`,
      type: 'group',
      name: g.name,
      avatar: g.avatar,
      lastMessage: g.last_message,
      time: g.last_message_time,
    })
  }
  // 与消息页的会话列表同一口径：最后一条消息越新越靠前，没有时间的沉底
  return list
    .sort((a, b) => (b.time ? Date.parse(b.time) : 0) - (a.time ? Date.parse(a.time) : 0))
    .slice(0, 30)
})

interface ContactHit {
  id: number
  name: string
  avatar: string | null
  meta: string
}

const contactHits = computed<ContactHit[]>(() => {
  if (!kw.value) return []
  const matched = contacts.value.filter(
    (c) => hit(c.name) || hit(c.class_name) || hit(c.college) || hit(c.username),
  )
  // 互关 > 单向关注：搜同一个名字时，能直接开聊的排在最前
  const rank = (c: ContactUser) => (c.is_friend ? 0 : c.is_following ? 1 : 2)
  return matched
    .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name, 'zh-Hans-CN'))
    .slice(0, 20)
    .map((c) => ({ id: c.id, name: c.name, avatar: c.avatar, meta: contactMeta(c) }))
})

interface ForumHit {
  id: number
  kind: ForumKind
  actorId: number
  actorName: string
  actorAvatar: string | null
  postId: number | null
  postTitle: string
  /** 评论正文：命中它时优先展示，用户才看得懂这条为什么被搜出来 */
  content: string
  createdAt: string
}

const forumHits = computed<ForumHit[]>(() => {
  if (!kw.value) return []
  return forum.value
    .filter((m) => hit(m.actor_name) || hit(m.post_title) || hit(m.content))
    .slice(0, 20)
    .map((m) => ({
      id: m.id,
      kind: m.kind,
      actorId: m.actor_id,
      actorName: m.actor_name || '同学',
      actorAvatar: m.actor_avatar,
      postId: m.post_id,
      postTitle: m.post_title || '',
      content: m.content || '',
      createdAt: m.created_at,
    }))
})

/** 互动行的副标题：命中点在评论正文上就显示正文（否则用户看不出为什么命中），
 *  否则退回「评论了你的帖子《标题》」这类动作描述 */
function forumSub(m: ForumHit) {
  if (m.content && hit(m.content)) return m.content
  return forumAction(m.kind) + (m.postTitle ? `《${m.postTitle}》` : '')
}

const totalHits = computed(
  () => sessionHits.value.length + contactHits.value.length + forumHits.value.length,
)

/** 高亮片段（已转义的安全 HTML）：关键词为空时原样返回，不做标记 */
function hl(text: string | null | undefined) {
  return highlightMatches(text || '', kw.value)
}

function contactMeta(c: ContactUser) {
  const parts: string[] = []
  // 这一行说的是「双向」这层额外关系：好友 = 我关注的，单写「好友」等于把所有人都标一遍
  if (c.is_friend) parts.push('互相关注')
  if (c.class_name) parts.push(c.class_name)
  else if (c.college) parts.push(c.college)
  else if (c.role === 'teacher') parts.push('教师')
  return parts.join(' · ') || (c.is_following ? '已关注' : '同学')
}

function forumAction(kind: ForumKind) {
  return (
    { like: '赞了你的帖子', favorite: '收藏了你的帖子', comment: '评论了你的帖子', follow: '关注了你' }[kind] ||
    '与你互动'
  )
}

function formatTime(t: string | null) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  if (d.toDateString() === now.toDateString()) return `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}-${pad(d.getDate())}`
  return `${d.getFullYear()}-${d.getMonth() + 1}-${pad(d.getDate())}`
}

/* ==================== 点结果 ====================
   会话 / 好友都落到「消息页 + 打开这一条会话」：用 replace 而不是 push，
   返回键才会直接回聊天列表 —— 若用 push，从会话返回会先退回搜索页，
   而这一轮搜索其实已经结束了（主流 IM 也是这个手感）。
   消息页读 query.chat 打开对应会话，读完就把参数抹掉，刷新不会重复弹一次。 */

function openSessionHit(s: SessionHit) {
  remember()
  void router.replace({ name: 'student-messages', query: { chat: s.key } })
}

function openContactHit(c: ContactHit) {
  remember()
  void router.replace({ name: 'student-messages', query: { chat: `s-${c.id}` } })
}

function openForumHit(m: ForumHit) {
  remember()
  // 新粉丝这类互动没有帖子可去，直接拉起对方个人主页（与消息页互动列表同一处理）
  if (m.kind === 'follow' || !m.postId) {
    void openUserHomepage(m.actorId)
    return
  }
  void router.push({ name: 'student-community', query: { post: String(m.postId) } })
}

/* ==================== 最近搜索 ==================== */

const HISTORY_KEY = 'wispath_msg_search_history'
const HISTORY_MAX = 10

const history = ref<string[]>(loadHistory())

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string').slice(0, HISTORY_MAX)
      : []
  } catch {
    return []
  }
}

function persistHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
  } catch {
    /* 隐私模式存不进去就算了，本次会话内仍可用 */
  }
}

/** 记一笔关键词：同一词去重后置顶。输入即搜、没有「提交」按钮，
 *  所以记录时机放在「点开某条结果」（＝这次搜索确实有用）与回车提交。 */
function remember() {
  const k = kw.value
  if (!k) return
  history.value = [k, ...history.value.filter((h) => h !== k)].slice(0, HISTORY_MAX)
  persistHistory()
}

function applyHistory(h: string) {
  keyword.value = h
  inputRef.value?.focus()
}

function clearHistory() {
  history.value = []
  try {
    localStorage.removeItem(HISTORY_KEY)
  } catch {
    /* 忽略 */
  }
}

function clearKeyword() {
  keyword.value = ''
  inputRef.value?.focus()
}

/* ==================== 进出 ==================== */

/** 返回上一页；直接从地址栏进来（没有历史）时兜底回消息列表。
 *  进出场都交给全站统一的页面过渡，这里不再单独指定 —— 搜索子页没有专属动效。 */
function goBack() {
  // 判断「有没有站内上一页」不能看 history.length：它把站外页面也算进去，
  // 新开标签直接进这个地址时回退会退到空白页/上一站，而不是消息列表。
  // vue-router 会把自己的上一条路径写进 history.state.back，没有就是直接进来的。
  const prev = (window.history.state as { back?: string | null } | null)?.back
  if (prev) router.back()
  else void router.replace({ name: 'student-messages' })
}

/** 「取消」＝放弃这次搜索、退回消息列表（先清词，回来时输入框是空的）。
 *  只清词不退页交给框内的 ×，「清空」和「退出」各管一件事，不做双语义。 */
function cancelSearch() {
  keyword.value = ''
  goBack()
}

onMounted(() => {
  // 等这一趟页面过渡走完再聚焦：过渡途中聚焦会把正在动的页面顶得跳一下
  window.setTimeout(() => inputRef.value?.focus(), 320)
  void loadAll()
})
</script>

<style scoped>
/* ================= 骨架 =================
   与消息页同一套色板（#fff 面 + #f5f6f8 底 + 13~15px 字），
   让「从列表进搜索」看起来是同一页的延伸，而不是跳到了另一个模块。 */
.ms-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #fff;
  color: #1f2329;
  -webkit-tap-highlight-color: transparent;
}

/* 移动端：本页是路由级「二级子页」，进出场走 animations.css 的 route-subpage ——
   那套过渡在移动端的前提是「进场页自身 fixed 脱流」，这样离开的消息页留在
   .main-area（flex column）里也不会被分摊成一半高度；不写这条，两页会在 0.3s 内
   各占一半、页面抽一下。顶栏与本条路由上的底部导航本来都不显示（不在 TAB_BAR_ROUTES），
   所以 fixed 整屏 == 流内的那块区域，落位前后没有任何位移。 */
@media (max-width: 767px) {
  .ms-page {
    position: fixed;
    inset: 0;
    z-index: 1500;
  }
}

/* ================= 顶栏 ================= */
.ms-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: calc(8px + env(safe-area-inset-top, 0px)) 12px 8px;
  background: #fff;
  border-bottom: 1px solid #f0f1f3;
  /* 顶栏只是个静态条：这页不再演进场位移，整页交给全站统一的页面过渡 */
  position: relative;
  z-index: 3;
}
.ms-back {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: -4px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: none;
  color: #1f2329;
  cursor: pointer;
}
.ms-back:active { background: rgba(20, 23, 26, 0.06); }
.ms-field {
  flex: 1;
  min-width: 0;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border-radius: 10px;
  background: #f5f6f8;
}
.ms-field-icon { color: #9aa0a6; flex-shrink: 0; }
.ms-input {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0;
  border: 0;
  outline: none;
  background: transparent;
  /* 16px：iOS 上小于 16px 的输入框聚焦会自动放大整页 */
  font-size: 16px;
  color: #1f2329;
}
.ms-input::placeholder { color: #9aa0a6; }
/* 浏览器自带的搜索清除按钮样式不统一（Safari 是个灰叉、Chrome 在右侧），
   统一关掉，改用下面这枚自己画的 × */
.ms-input::-webkit-search-cancel-button { display: none; }
.ms-clear {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  padding: 0;
  border: 0;
  background: none;
  color: #b0b3b8;
  cursor: pointer;
}
/* 「取消」常驻在最右：不随输入出现/消失，输入框宽度就不会跟着跳。
   高度撑到与搜索框齐平（36px），拇指侧边点击不至于滑空。 */
.ms-cancel {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  height: 36px;
  padding: 0 2px;
  border: 0;
  background: none;
  font-size: 15px;
  color: #1f2329;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ms-cancel:active { opacity: 0.5; }

/* ================= 内容区 ================= */
.ms-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 4px 16px calc(28px + env(safe-area-inset-bottom, 0px));
}
.ms-sec { margin-top: 16px; }
.ms-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 30px;
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
}
/* 分区标题：左侧标题 + 右侧灰色条数，不用彩色徽标抢注意力 */
.ms-sec-head h2 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
}
.ms-sec-head.is-plain { margin-bottom: 2px; }
.ms-sec-head i {
  font-style: normal;
  font-weight: 400;
  font-size: 12px;
  color: #b0b3b8;
}
.ms-text-btn {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 2px;
  border: 0;
  background: none;
  font-size: 13px;
  color: #9aa0a6;
  cursor: pointer;
}

/* 最近搜索：胶囊标签，一行放不下就换行 */
.ms-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ms-chip {
  max-width: 100%;
  height: 30px;
  padding: 0 12px;
  border: 0;
  border-radius: 6px;
  background: #f2f3f5;
  color: #4e5969;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}
.ms-chip:active { background: #e9eaec; }

/* ================= 结果行 ================= */
.ms-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 0;
  border: 0;
  background: none;
  text-align: left;
  cursor: pointer;
}
.ms-row:active { background: #fafbfc; }
/* 系统通知的铃铛头像：和 el-avatar 38px 同尺寸、同圆心，整行不会因为 `- ` 错位 */
.ms-notice-avatar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #111827;
  color: #fff;
}
.ms-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.ms-row-title {
  display: block;
  font-size: 14.5px;
  font-weight: 500;
  color: #1f2329;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ms-row-sub {
  display: block;
  font-size: 12.5px;
  color: #9aa0a6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ms-row-time {
  flex-shrink: 0;
  font-size: 11.5px;
  color: #b0b3b8;
}
.ms-row-action {
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 6px;
  background: #f2f3f5;
  font-size: 12px;
  color: #4e5969;
}
.ms-group-mark {
  display: inline-block;
  margin-right: 4px;
  padding: 0 4px;
  border-radius: 4px;
  background: #eef0f3;
  color: #6b7280;
  font-size: 11px;
  font-style: normal;
  line-height: 16px;
  vertical-align: 1px;
}

/* v-html 注入的 <mark> 不带 scope 属性，必须 :deep 才命中；
   默认的黄底在浅灰列表里太扎眼，改成主色描字 */
.ms-row :deep(mark.hl) {
  background: transparent;
  color: #2563eb;
  font-weight: 600;
}

/* ================= 空态 / 加载 ================= */
.ms-blank {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 64px 24px 0;
  color: #c0c4cc;
  text-align: center;
}
.ms-blank p {
  margin: 8px 0 0;
  font-size: 14px;
  color: #4b5563;
}
.ms-blank span {
  font-size: 12.5px;
  color: #9aa0a6;
  line-height: 1.5;
}
.ms-status {
  margin: 40px 0;
  text-align: center;
  font-size: 13px;
  color: #9aa0a6;
}

/* ================= 桌面端 =================
   侧栏那种 320px 的窄栏版式搬到整页会显得空，收成 720px 居中面板，
   顶栏与内容同宽对齐（左右各留 16px 呼吸位）。 */
@media (min-width: 768px) {
  .ms-page { background: #f5f6f8; }
  .ms-head,
  .ms-body {
    width: 100%;
    max-width: 720px;
    margin: 0 auto;
  }
  .ms-head {
    margin-top: 16px;
    border: 1px solid #f0f1f3;
    border-radius: 12px 12px 0 0;
  }
  .ms-body {
    background: #fff;
    border: 1px solid #f0f1f3;
    border-top: 0;
    border-radius: 0 0 12px 12px;
    min-height: 420px;
  }
  .ms-row:hover { background: #fafbfc; }
}
</style>
