<template>
  <div class="fcp">
    <!-- ===== 评论：页头就是「评论我的 | 我评论的」双页签（参考图 1 / 4） ===== -->
    <template v-if="page === 'comment'">
      <header class="fcp-head">
        <button type="button" class="fcp-back" aria-label="返回" @click="emit('close')">
          <DtIcon name="back" :size="20" />
        </button>
        <div class="fcp-tabs" role="tablist">
          <button
            type="button" role="tab" :aria-selected="commentTab === 'in'"
            class="fcp-tab" :class="{ active: commentTab === 'in' }"
            @click="commentTab = 'in'"
          >评论我的</button>
          <button
            type="button" role="tab" :aria-selected="commentTab === 'out'"
            class="fcp-tab" :class="{ active: commentTab === 'out' }"
            @click="commentTab = 'out'"
          >我评论的</button>
        </div>
        <span class="fcp-head-pad" />
      </header>
      <div class="fcp-scroll">
        <template v-if="commentTab === 'in'">
          <article v-for="m in commentIn" :key="m.id" class="fcp-item" @click="emit('open-message', m)">
            <div class="fcp-who">
              <img v-if="m.actor_avatar" class="fcp-avatar" :src="m.actor_avatar" alt="" loading="lazy" />
              <span v-else class="fcp-avatar fcp-avatar--txt">{{ m.actor_name[0] }}</span>
              <div class="fcp-who-main">
                <span class="fcp-name">{{ m.actor_name }}</span>
                <span class="fcp-meta">{{ formatDay(m.created_at) }} · 回复了我的评论</span>
              </div>
            </div>
            <p class="fcp-content">{{ m.content || '评论了我的帖子' }}</p>
            <div class="fcp-quote">
              <span class="fcp-quote-label">原帖</span>
              <span class="fcp-quote-text">{{ m.post_title || '查看帖子' }}</span>
            </div>
            <button type="button" class="fcp-reply" @click.stop="emit('open-message', m)">
              <DtIcon name="message" :size="14" />回复
            </button>
          </article>
          <div v-if="!commentIn.length" class="fcp-empty"><DtIcon name="empty" :size="44" class="fcp-empty-ico" /><span>还没有人评论你</span></div>
        </template>
        <template v-else>
          <article v-for="c in myComments" :key="c.id" class="fcp-item" @click="emit('open-post', c.post_id)">
            <div class="fcp-who">
              <img v-if="meAvatar" class="fcp-avatar" :src="meAvatar" alt="" loading="lazy" />
              <span v-else class="fcp-avatar fcp-avatar--txt">{{ meName[0] }}</span>
              <div class="fcp-who-main">
                <span class="fcp-name">{{ meName }}</span>
                <span class="fcp-meta">{{ formatDay(c.created_at) }} · 回复评论</span>
              </div>
            </div>
            <p class="fcp-content">{{ c.content }}</p>
            <div class="fcp-quote">
              <span class="fcp-quote-label">原帖</span>
              <span class="fcp-quote-text">{{ c.post_title }}</span>
            </div>
          </article>
          <div v-if="myCommentsLoading" class="fcp-tip">加载中…</div>
          <div v-else-if="!myComments.length" class="fcp-empty"><DtIcon name="empty" :size="44" class="fcp-empty-ico" /><span>你还没有评论过</span></div>
        </template>
      </div>
    </template>

    <!-- ===== 赞和收藏：同一篇帖子的互动聚合成一行（参考图 6） ===== -->
    <template v-else-if="page === 'likeFav'">
      <header class="fcp-head">
        <button type="button" class="fcp-back" aria-label="返回" @click="emit('close')">
          <DtIcon name="back" :size="20" />
        </button>
        <h2 class="fcp-title">赞和收藏</h2>
        <span class="fcp-head-pad" />
      </header>
      <div class="fcp-scroll">
        <article v-for="g in likeFavGroups" :key="g.key" class="fcp-item" @click="emit('open-post', g.post_id)">
          <div class="fcp-who">
            <span class="fcp-avatar-wrap">
              <img v-if="g.actors[0]?.avatar" class="fcp-avatar" :src="g.actors[0]!.avatar!" alt="" loading="lazy" />
              <span v-else class="fcp-avatar fcp-avatar--txt">{{ (g.actors[0]?.name || '同') [0] }}</span>
              <i class="fcp-kind-badge" :class="{ 'is-fav': !g.kinds.has('like') }">
                <DtIcon :name="g.kinds.has('like') ? 'thumbUp' : 'heart'" :size="10" filled />
              </i>
            </span>
            <div class="fcp-who-main">
              <span class="fcp-name">{{ groupTitle(g) }}</span>
              <span class="fcp-meta">{{ formatDay(g.latest) }} · {{ groupAction(g) }}</span>
            </div>
          </div>
          <div class="fcp-quote">
            <span class="fcp-quote-label">原帖</span>
            <span class="fcp-quote-text">{{ g.post_title || '查看帖子' }}</span>
          </div>
        </article>
        <div v-if="!likeFavGroups.length" class="fcp-empty"><DtIcon name="thumbUp" :size="44" class="fcp-empty-ico" /><span>还没有赞和收藏</span></div>
      </div>
    </template>

    <!-- ===== 关注消息：谁关注了你 + 关系按钮（参考图 3） ===== -->
    <template v-else-if="page === 'follow'">
      <header class="fcp-head">
        <button type="button" class="fcp-back" aria-label="返回" @click="emit('close')">
          <DtIcon name="back" :size="20" />
        </button>
        <h2 class="fcp-title">关注消息</h2>
        <span class="fcp-head-pad" />
      </header>
      <div class="fcp-scroll">
        <div v-for="m in followList" :key="m.id" class="fcp-follow-row" @click="emit('open-profile', m.actor_id)">
          <img v-if="m.actor_avatar" class="fcp-avatar" :src="m.actor_avatar" alt="" loading="lazy" />
          <span v-else class="fcp-avatar fcp-avatar--txt">{{ m.actor_name[0] }}</span>
          <div class="fcp-who-main">
            <span class="fcp-name">{{ m.actor_name }}</span>
            <span class="fcp-meta">关注了你</span>
          </div>
          <button
            type="button"
            class="fcp-rel-btn"
            :class="{ 'is-dark': relOf(m.actor_id) === 'back' }"
            @click.stop="onRelClick(m)"
          >{{ relText(m.actor_id) }}</button>
        </div>
        <div v-if="!followList.length" class="fcp-empty"><DtIcon name="user" :size="44" class="fcp-empty-ico" /><span>还没有新关注</span></div>
      </div>
    </template>

    <!-- ===== @我的：站内暂无提及功能，占位空态（参考图 2） ===== -->
    <template v-else-if="page === 'mention'">
      <header class="fcp-head">
        <button type="button" class="fcp-back" aria-label="返回" @click="emit('close')">
          <DtIcon name="back" :size="20" />
        </button>
        <h2 class="fcp-title">@我的</h2>
        <span class="fcp-head-pad" />
      </header>
      <div class="fcp-scroll fcp-scroll--center">
        <div class="fcp-empty"><DtIcon name="grid" :size="44" class="fcp-empty-ico" /><span>暂无内容</span></div>
      </div>
    </template>

    <!-- ===== 搜索：联系人人 / 群聊语义 + 本面板消息兜底（参考图 5 / 7） ===== -->
    <template v-else-if="page === 'search'">
      <header class="fcp-head fcp-head--search">
        <button type="button" class="fcp-back" aria-label="返回" @click="emit('close')">
          <DtIcon name="back" :size="20" />
        </button>
        <div class="fcp-search-field">
          <DtIcon name="search" :size="16" class="fcp-search-ico" />
          <input
            ref="searchRef"
            v-model="kw"
            class="fcp-search-input"
            type="search"
            placeholder="搜索联系人或群聊"
            enterkeyhint="search"
          />
          <button v-if="kw" type="button" class="fcp-search-clear" aria-label="清空" @click="kw = ''">
            <DtIcon name="close" :size="14" />
          </button>
        </div>
      </header>
      <div class="fcp-scroll">
        <template v-if="kw.trim()">
          <template v-if="searchUsers.length">
            <p class="fcp-section">联系人</p>
            <div v-for="u in searchUsers" :key="u.id" class="fcp-follow-row">
              <img v-if="u.avatar" class="fcp-avatar" :src="u.avatar" alt="" loading="lazy" />
              <span v-else class="fcp-avatar fcp-avatar--txt">{{ u.name[0] }}</span>
              <div class="fcp-who-main">
                <span class="fcp-name">{{ u.name }}</span>
                <span class="fcp-meta">{{ u.class_name || u.college || (u.role === 'teacher' ? '教师' : '学生') }}</span>
              </div>
              <button type="button" class="fcp-rel-btn" @click.stop="goChat(u)">去聊天</button>
            </div>
          </template>
          <template v-if="hitMessages.length">
            <p class="fcp-section">相关消息</p>
            <button v-for="m in hitMessages" :key="m.id" type="button" class="fcp-msg-row" @click="emit('open-message', m)">
              <span class="fcp-ico" :class="'fcp-ico--' + m.kind">
                <img v-if="m.actor_avatar" :src="m.actor_avatar" alt="" loading="lazy" />
                <DtIcon v-else :name="kindIcon(m.kind)" :size="20" filled />
              </span>
              <span class="fcp-who-main">
                <span class="fcp-name">{{ m.actor_name }}</span>
                <span class="fcp-meta">{{ previewOf(m) }}</span>
              </span>
              <span class="fcp-time">{{ formatDay(m.created_at) }}</span>
            </button>
          </template>
          <div v-if="!searchUsers.length && !hitMessages.length && !searching" class="fcp-empty">
            <DtIcon name="search" :size="44" class="fcp-empty-ico" /><span>没有找到相关内容</span>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * 互动消息的分类子页（ForumInbox 的第二层）
 *
 * 参考图版式：每个圆入口都进一个独立子页，而不是在主列表上就地筛——
 * - 评论：页头双页签「评论我的 | 我评论的」，条目 = 头像 + 姓名 + 时间动作 + 内容 + 原帖卡片 + 回复
 * - 赞和收藏：同一篇帖子的点赞/收藏聚合成一行（「XXX、YYY 等 N 人」）
 * - 关注消息：头像 + 「关注了你」 + 右侧关系按钮（互相关注 / 已关注 / 回关）
 * - @我的：暂无提及功能，占位空态
 * - 搜索：页头输入框，搜联系人（去聊天）+ 本面板消息兜底
 *
 * 子页只做展示与跳转：已读标记、进帖、进主页统一回调父级（open-message / open-post /
 * open-profile），保证未读数与入口角标只有一处状态源。
 */
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import DtIcon from '@/components/common/DtIcon.vue'
import { useAuthStore } from '@/stores/auth'
import {
  getFollowers, followUser, searchSocialUsers,
  type ForumMessageItem, type ForumMessageKind, type SocialUser,
} from '@/api/social'
import { getMyComments, type MyComment } from '@/api/community'

type FcpPage = 'comment' | 'likeFav' | 'follow' | 'mention' | 'search'

const props = defineProps<{ page: FcpPage; messages: ForumMessageItem[] }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'open-message', m: ForumMessageItem): void
  (e: 'open-post', postId: number | null): void
  (e: 'open-profile', userId: number): void
}>()

const router = useRouter()
const auth = useAuthStore()
const meName = computed(() => auth.user?.name || '我')
const meAvatar = computed(() => auth.user?.avatar || '')

/* ==================== 评论 ==================== */
const commentTab = ref<'in' | 'out'>('in')
const commentIn = computed(() => props.messages.filter((m) => m.kind === 'comment'))

const myComments = ref<MyComment[]>([])
const myCommentsLoading = ref(false)
const myCommentsLoaded = ref(false)

watch(
  () => props.page,
  async (p) => {
    if (p !== 'comment' || myCommentsLoaded.value) return
    myCommentsLoading.value = true
    try {
      myComments.value = await getMyComments(50)
      myCommentsLoaded.value = true
    } catch {
      myComments.value = []
    } finally {
      myCommentsLoading.value = false
    }
  },
  { immediate: true },
)

/* ==================== 赞和收藏（按帖子聚合） ==================== */
interface LikeFavGroup {
  key: string
  post_id: number | null
  post_title: string
  actors: { id: number; name: string; avatar: string | null }[]
  kinds: Set<ForumMessageKind>
  latest: string
}

const likeFavGroups = computed<LikeFavGroup[]>(() => {
  const map = new Map<string, LikeFavGroup>()
  // messages 按时间倒序：先见到的就是最近的互动者
  for (const m of props.messages) {
    if (m.kind !== 'like' && m.kind !== 'favorite') continue
    const key = String(m.post_id ?? -m.id)
    let g = map.get(key)
    if (!g) {
      g = { key, post_id: m.post_id, post_title: m.post_title, actors: [], kinds: new Set(), latest: m.created_at }
      map.set(key, g)
    }
    if (!g.actors.some((a) => a.id === m.actor_id)) {
      g.actors.push({ id: m.actor_id, name: m.actor_name, avatar: m.actor_avatar })
    }
    g.kinds.add(m.kind)
    if (m.created_at > g.latest) g.latest = m.created_at
  }
  return [...map.values()]
})

/** 标题：「A、B 等 N 人」，两人以内直接列名 */
function groupTitle(g: LikeFavGroup) {
  const names = g.actors.slice(0, 2).map((a) => a.name)
  if (g.actors.length > 2) return `${names.join('、')} 等 ${g.actors.length} 人`
  return names.join('、')
}

function groupAction(g: LikeFavGroup) {
  if (g.kinds.has('like') && g.kinds.has('favorite')) return '赞和收藏了我的帖子'
  if (g.kinds.has('favorite')) return '收藏了我的帖子'
  return '赞了我的帖子'
}

/* ==================== 关注消息（关系按钮） ==================== */
const followList = computed(() => props.messages.filter((m) => m.kind === 'follow'))

/** actor_id → 关注关系。粉丝名单一次拉齐：关注消息的发起者必然在我粉丝里 */
const followMap = ref<Map<number, SocialUser>>(new Map())
const followMapLoaded = ref(false)

watch(
  () => props.page,
  async (p) => {
    if (p !== 'follow' || followMapLoaded.value) return
    try {
      const followers = await getFollowers()
      followMap.value = new Map(followers.map((u) => [u.id, u]))
      followMapLoaded.value = true
    } catch {
      /* 拉不到就统一显示「回关」，点击时以服务端为准 */
    }
  },
  { immediate: true },
)

type Rel = 'mutual' | 'following' | 'back'
function relOf(userId: number): Rel {
  const u = followMap.value.get(userId)
  if (!u) return 'back'
  if (u.is_friend) return 'mutual'
  return u.is_following ? 'following' : 'back'
}
function relText(userId: number) {
  const r = relOf(userId)
  return r === 'mutual' ? '互相关注' : r === 'following' ? '已关注' : '回关'
}

async function onRelClick(m: ForumMessageItem) {
  const r = relOf(m.actor_id)
  if (r === 'mutual') {
    goChat({ id: m.actor_id, name: m.actor_name })
    return
  }
  if (r === 'following') {
    emit('open-profile', m.actor_id)
    return
  }
  try {
    const st = await followUser(m.actor_id)
    const prev = followMap.value.get(m.actor_id)
    followMap.value.set(m.actor_id, {
      ...(prev || ({
        id: m.actor_id, name: m.actor_name, username: '', avatar: m.actor_avatar,
        role: 'student', college: null, class_name: null, title: null, signature: null, followed_at: null,
      } as SocialUser)),
      is_following: st.is_following,
      is_follower: st.is_follower ?? prev?.is_follower ?? true,
      is_friend: st.is_friend,
    })
  } catch {
    /* 静默：失败保持原按钮态 */
  }
}

/* ==================== 搜索 ==================== */
const searchRef = ref<HTMLInputElement | null>(null)
const kw = ref('')
const searchUsers = ref<SocialUser[]>([])
const searching = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(kw, () => {
  if (searchTimer) clearTimeout(searchTimer)
  const q = kw.value.trim()
  if (!q) {
    searchUsers.value = []
    searching.value = false
    return
  }
  searching.value = true
  searchTimer = setTimeout(async () => {
    try {
      searchUsers.value = await searchSocialUsers(q, 20)
    } catch {
      searchUsers.value = []
    } finally {
      searching.value = false
    }
  }, 280)
})

/** 本面板消息兜底：姓名 / 内容 / 帖子标题命中都算 */
const hitMessages = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return []
  return props.messages.filter(
    (m) =>
      m.actor_name.toLowerCase().includes(q) ||
      (m.content || '').toLowerCase().includes(q) ||
      (m.post_title || '').toLowerCase().includes(q),
  )
})

function goChat(u: { id: number; name: string }) {
  router.push({ path: '/student/messages', query: { chat: String(u.id), chatName: u.name } })
}

/* ==================== 公共小件 ==================== */
function parseTime(iso: string) {
  return new Date(iso + (iso.includes('Z') || iso.includes('+') ? '' : 'Z'))
}

/** 子页时间用日期态：今天 HH:MM / 昨天 / 本年 MM-DD / 跨年 YYYY-MM-DD */
function formatDay(iso: string | null) {
  if (!iso) return ''
  const d = parseTime(iso)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return '昨天'
  const md = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return d.getFullYear() === now.getFullYear() ? md : `${d.getFullYear()}-${md}`
}

function kindIcon(kind: ForumMessageKind) {
  if (kind === 'comment') return 'message'
  if (kind === 'like') return 'thumbUp'
  if (kind === 'favorite') return 'heart'
  return 'user'
}

function previewOf(m: ForumMessageItem) {
  if (m.kind === 'comment') {
    const text = (m.content || '').trim()
    return text ? `评论了你：${text}` : '评论了你的帖子'
  }
  if (m.kind === 'like') return m.post_title ? `赞了你：${m.post_title}` : '赞了你的帖子'
  if (m.kind === 'favorite') return m.post_title ? `收藏了你：${m.post_title}` : '收藏了你的帖子'
  return '关注了你'
}

/** 搜索页打开时聚焦输入框（父级 v-if 挂载后） */
watch(
  () => props.page,
  async (p) => {
    if (p !== 'search') return
    kw.value = ''
    await nextTick()
    searchRef.value?.focus()
  },
)
</script>

<style scoped>
/* 子页覆盖在 ForumInbox 之上（父级 .fi 为 relative），进场/退场走全局 .subpage 动画 */
.fcp {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  background: var(--dt-surface, #fff);
}

/* ===== 页头 ===== */
.fcp-head {
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 50px;
  padding: 0 10px;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.fcp-head-pad { width: 36px; flex-shrink: 0; }
.fcp-back {
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--dt-text, #171a1d);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fcp-back:hover { background: var(--dt-hover, rgba(0, 0, 0, .04)); }
.fcp-title {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--dt-text, #171a1d);
  pointer-events: none;
}

/* 双页签（评论子页）：居中两枚，选中加粗 + 短下划线 */
.fcp-tabs {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 22px;
}
.fcp-tab {
  position: relative;
  border: 0;
  background: transparent;
  padding: 6px 2px;
  font-size: 15px;
  color: var(--dt-text-tertiary, #86909c);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fcp-tab.active {
  color: var(--dt-text, #171a1d);
  font-weight: 600;
}
.fcp-tab.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  border-radius: 2px;
  background: var(--dt-text, #171a1d);
}

/* 搜索页页头：输入框占满 */
.fcp-head--search { gap: 8px; padding-right: 14px; }
.fcp-search-field {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 10px;
  border-radius: 8px;
  background: var(--dt-fill, #f2f3f5);
}
.fcp-search-ico { color: var(--dt-text-tertiary, #86909c); flex-shrink: 0; }
.fcp-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: 14px;
  color: var(--dt-text, #171a1d);
}
.fcp-search-input::-webkit-search-cancel-button { display: none; }
.fcp-search-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 0;
  border-radius: 50%;
  background: #c9ccd4;
  color: #fff;
  cursor: pointer;
}

/* ===== 列表 ===== */
.fcp-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 16px 24px;
  scrollbar-width: none;
}
.fcp-scroll::-webkit-scrollbar { display: none; }
.fcp-scroll--center { display: flex; flex-direction: column; justify-content: center; }

.fcp-section {
  margin: 14px 0 4px;
  font-size: 13px;
  color: var(--dt-text-tertiary, #86909c);
}

.fcp-item {
  padding: 14px 0;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .05));
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fcp-item:last-child { border-bottom: 0; }
.fcp-item:active { background: var(--dt-hover, rgba(0, 0, 0, .02)); }

.fcp-who {
  display: flex;
  align-items: center;
  gap: 10px;
}
.fcp-who-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.fcp-avatar-wrap { position: relative; flex-shrink: 0; display: inline-flex; }
.fcp-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--dt-fill, #f2f3f5);
  flex-shrink: 0;
}
.fcp-avatar--txt {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #a5b4fc, #6366f1);
}
/* 赞/收藏类型小徽章：头像右下角 */
.fcp-kind-badge {
  position: absolute;
  right: -2px;
  bottom: -2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid #fff;
  background: #4d8bf8;
  color: #fff;
  box-sizing: border-box;
}
.fcp-kind-badge.is-fav { background: #ef940f; }

.fcp-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--dt-text, #171a1d);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fcp-meta {
  font-size: 12px;
  color: var(--dt-text-tertiary, #86909c);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fcp-content {
  margin: 10px 0;
  font-size: 15px;
  line-height: 1.45;
  color: var(--dt-text, #171a1d);
  word-break: break-word;
}

/* 原帖引用卡：浅灰圆角块（参考图样式） */
.fcp-quote {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 8px;
  background: var(--dt-fill, #f5f6f7);
}
.fcp-quote-label {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--dt-text-tertiary, #86909c);
}
.fcp-quote-text {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--dt-text-secondary, #4e5969);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fcp-reply {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
  padding: 5px 14px;
  border: 0;
  border-radius: 6px;
  background: var(--dt-fill, #f2f3f5);
  font-size: 13px;
  color: var(--dt-text-secondary, #4e5969);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fcp-reply:active { background: #e8eaed; }

/* 关注 / 搜索联系人行：右侧行内按钮 */
.fcp-follow-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .05));
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fcp-follow-row:last-child { border-bottom: 0; }
.fcp-rel-btn {
  flex-shrink: 0;
  min-width: 76px;
  padding: 6px 12px;
  border: 0;
  border-radius: 6px;
  background: var(--dt-fill, #f2f3f5);
  font-size: 13px;
  color: var(--dt-text, #171a1d);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fcp-rel-btn.is-dark {
  background: var(--dt-text, #171a1d);
  color: #fff;
}
.fcp-rel-btn:active { opacity: .85; }

/* 搜索页消息命中行 */
.fcp-msg-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 0;
  border: 0;
  background: transparent;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .05));
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fcp-ico {
  position: relative;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  color: #fff;
  background: var(--dt-fill, #f2f3f5);
  overflow: hidden;
}
.fcp-ico img { width: 100%; height: 100%; object-fit: cover; }
.fcp-ico--comment { background: linear-gradient(135deg, #6aa9f8, #3a7ff0); }
.fcp-ico--like { background: linear-gradient(135deg, #56c2ee, #1596d1); }
.fcp-ico--favorite { background: linear-gradient(135deg, #f7b955, #ef940f); }
.fcp-ico--follow { background: linear-gradient(135deg, #5fc7a8, #22a67f); }
.fcp-time {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--dt-text-quiet, #a9aeb8);
}

.fcp-tip { padding: 20px 0; text-align: center; font-size: 12px; color: var(--dt-text-tertiary); }
.fcp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 16px;
  font-size: 13px;
  color: var(--dt-text-quiet, #a9aeb8);
}
.fcp-empty-ico { color: #c9ccd4; }

@media (max-width: 767px) {
  .fcp-scroll { padding: 4px 16px 20px; }
}
</style>
