<template>
  <!-- 互动消息面板：论坛侧（赞 / 收藏 / 评论 / 新粉丝）。
       与聊天消息彻底分开——这里只展示「谁对我的帖子做了什么」，
       点一条直接落到对应帖子（?post=<id>），交流社区页负责打开详情。 -->
  <el-drawer
    v-model="open"
    :with-header="false"
    :size="isMobile ? '100%' : '420px'"
    class="forum-inbox-drawer"
    append-to-body
    @open="onOpen"
  >
    <div class="fi-root">
      <header class="fi-head">
        <div class="fi-title-row">
          <!-- 移动端：左上角返回（与全站子页 52px 顶栏同一语义，只关这一层）；
               桌面端抽屉仍用右上角 ✕。两者的关闭回调一致，都只收当前浮层。 -->
          <button type="button" class="fi-back" aria-label="返回" @click="open = false">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <span class="fi-title">互动消息</span>
          <div class="fi-acts">
            <button v-if="unreadTotal" type="button" class="fi-read-all" @click="markAllRead">全部已读</button>
            <button type="button" class="fi-close" aria-label="关闭" @click="open = false">
              <el-icon :size="16"><Close /></el-icon>
            </button>
          </div>
        </div>
        <div class="fi-tabs">
          <button
            v-for="t in tabs"
            :key="t.value"
            type="button"
            :class="['fi-tab', { active: activeTab === t.value }]"
            @click="switchTab(t.value)"
          >
            {{ t.label }}
            <i v-if="countOf(t.value)" class="fi-tab-dot">{{ countOf(t.value) > 99 ? '99+' : countOf(t.value) }}</i>
          </button>
        </div>
      </header>

      <div class="fi-body">
        <div v-if="loading && !list.length" class="fi-hint">加载中…</div>
        <div v-else-if="!list.length" class="fi-empty">
          <el-icon :size="28"><Message /></el-icon>
          <p>还没有互动消息</p>
          <span>别人赞、收藏或评论你的帖子时会出现在这里</span>
        </div>
        <div v-else class="fi-list">
          <button
            v-for="item in sortedList"
            :key="item.id"
            type="button"
            :class="['fi-item', { unread: !item.is_read }]"
            @click="openItem(item)"
          >
            <div class="fi-avatar-wrap">
              <el-avatar
                :size="isMobile ? 44 : 40"
                :src="item.actor_avatar || undefined"
                class="fi-avatar"
                :style="avatarStyle(item.actor_name)"
              >
                {{ initialOf(item.actor_name) }}
              </el-avatar>
              <!-- 动作徽标：一眼分清是赞、收藏、评论还是新粉丝 -->
              <span :class="['fi-kind', `k-${item.kind}`]" :aria-label="actionText(item.kind)">
                <el-icon :size="11"><component :is="KIND_ICON[item.kind]" /></el-icon>
              </span>
            </div>

            <div class="fi-main">
              <p class="fi-line">
                <b class="fi-actor">{{ item.actor_name || '同学' }}</b>
                <span class="fi-action">{{ actionText(item.kind) }}</span>
              </p>
              <p v-if="item.post_title" class="fi-post">{{ item.post_title }}</p>
              <p v-if="item.kind === 'comment' && item.content" class="fi-quote">{{ item.content }}</p>
              <span class="fi-time">
                <i v-if="!item.is_read" class="fi-dot" aria-label="未读" />
                {{ formatTime(item.created_at) }}
              </span>
            </div>

            <div v-if="item.post_cover" class="fi-thumb">
              <img :src="item.post_cover" alt="" loading="lazy" />
            </div>
          </button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Message,
  Close,
  ArrowLeft,
  Pointer,
  Star,
  ChatDotRound,
  UserFilled,
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import { useBackLayer } from '@/composables/useBackLayer'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { parseServerTime } from '@/utils/datetime'
import {
  getForumMessages,
  markForumRead,
  type ForumKind,
  type ForumMessageOut,
} from '@/api/social'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const router = useRouter()
const { isMobile } = useResponsive()
const { forum, refresh: refreshUnread } = useUnreadSummary()

const open = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

/**
 * 移动端返回层级：面板打开时在历史顶部压一条同地址哨兵，
 * 系统返回键 / 全面屏侧滑先把这一层收掉，而不是直接退掉整个「校园资讯」页
 * （与帖子详情、个人中心子页、聊天窗口同一套，见 composables/useBackLayer.ts）。
 */
useBackLayer(computed(() => isMobile.value && props.modelValue), () => {
  open.value = false
})

type TabValue = 'all' | ForumKind
const tabs: Array<{ label: string; value: TabValue }> = [
  { label: '全部', value: 'all' },
  { label: '赞', value: 'like' },
  { label: '收藏', value: 'favorite' },
  { label: '评论', value: 'comment' },
  { label: '关注', value: 'follow' },
]

/** 每种互动的角标图标：赞=手型、收藏=星、评论=气泡、关注=人 */
const KIND_ICON = {
  like: Pointer,
  favorite: Star,
  comment: ChatDotRound,
  follow: UserFilled,
} as const

const activeTab = ref<TabValue>('all')
const list = ref<ForumMessageOut[]>([])
const loading = ref(false)
const unreadTotal = ref(0)
/** 各类型的未读条数（页签角标）：一次全量请求本地分组，避免 5 次请求 */
const allUnread = ref<ForumMessageOut[]>([])

const unreadCounts = computed(() => {
  const map: Record<string, number> = { all: 0, like: 0, favorite: 0, comment: 0, follow: 0 }
  for (const m of allUnread.value) {
    map.all += 1
    map[m.kind] = (map[m.kind] || 0) + 1
  }
  return map
})

/** 未读置顶、其余按时间倒序：进箱后马上全部标已读，这里保留本次打开时的顺序供回溯 */
const sortedList = computed(() =>
  [...list.value].sort((a, b) => {
    if (a.is_read !== b.is_read) return a.is_read ? 1 : -1
    return (parseServerTime(b.created_at) || 0) - (parseServerTime(a.created_at) || 0)
  }),
)

function countOf(tab: TabValue) {
  return unreadCounts.value[tab] || 0
}

function actionText(kind: ForumKind) {
  return (
    { like: '赞了你的帖子', favorite: '收藏了你的帖子', comment: '评论了你的帖子', follow: '关注了你' }[kind] ||
    '与你互动'
  )
}

/** 无头像时的首字底色：按名字取固定色，同一个人每次打开都是同一个颜色 */
const AVATAR_COLORS: Array<[string, string]> = [
  ['#e8f0fe', '#1a63c9'],
  ['#e7f4ea', '#217a3c'],
  ['#fdeaea', '#b03a3a'],
  ['#fdf1e3', '#a2661a'],
  ['#efeaf9', '#6a4bb0'],
  ['#e4f4f6', '#1f7180'],
]

function avatarStyle(name: string) {
  const s = (name || '同学').trim()
  let h = 0
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) % 997
  const [bg, fg] = AVATAR_COLORS[h % AVATAR_COLORS.length]
  return { background: bg, color: fg }
}

function initialOf(name: string) {
  const s = (name || '同学').trim()
  if (!s) return '同'
  const first = s[0]
  return /[a-zA-Z]/.test(first) ? first.toUpperCase() : first
}

/**
 * 相对时间：刚刚 / x 分钟前 / x 小时前 / 昨天 HH:mm / M-D / YYYY-M-D。
 * 后端时间是不带时区的 UTC，必须先按 UTC 解析，否则凌晨的互动会被算成「昨天」。
 */
function formatTime(t: string) {
  const ms = parseServerTime(t)
  if (Number.isNaN(ms)) return ''
  const d = new Date(ms)
  const now = new Date()
  const diff = now.getTime() - ms
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  const pad = (n: number) => String(n).padStart(2, '0')
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  if (sameDay) return `${Math.max(1, Math.floor(diff / 3_600_000))} 小时前`
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)
  if (d >= yesterday) return `昨天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}-${pad(d.getDate())}`
  return `${d.getFullYear()}-${d.getMonth() + 1}-${pad(d.getDate())}`
}

async function load(keepTab = false) {
  loading.value = true
  try {
    const [rows, unread] = await Promise.all([
      getForumMessages({ kind: activeTab.value === 'all' ? undefined : (activeTab.value as ForumKind), limit: 50 }),
      getForumMessages({ unread_only: true, limit: 100 }),
    ])
    list.value = rows
    allUnread.value = unread
    unreadTotal.value = unread.length
    if (!keepTab) emit('update:modelValue', true)
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function switchTab(tab: TabValue) {
  if (activeTab.value === tab) return
  activeTab.value = tab
  await load(true)
}

async function markAllRead() {
  try {
    await markForumRead()
  } finally {
    allUnread.value = []
    unreadTotal.value = 0
    // 刻意不改 list 里的 is_read：导航红点与页签角标清零，但本次打开的列表
    // 仍保留未读底色，方便刚进来时回看哪些是新的（重开面板会重新拉成已读态）
    forum.value = 0
    void refreshUnread()
  }
}

/** 打开某条：评论/赞/收藏 → 对应帖子；新粉丝 → 对方主页 */
function openItem(item: ForumMessageOut) {
  if (item.kind === 'follow') {
    open.value = false
    void openUserHomepage(item.actor_id)
    return
  }
  if (!item.post_id) return
  open.value = false
  router.push({ path: '/student/campus', query: { tab: 'community', post: String(item.post_id) } })
}

async function onOpen() {
  // 打开即把当前互动流全部标记已读：与 QQ / 微博的「进箱即读」一致，
  // 导航红点与社区页角标立刻归零，列表保留未读底色供回溯
  await load()
  if (unreadTotal.value) void markAllRead()
}

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    void onOpen()
  },
)

// 兜底：未读角标与全局汇总可能因轮询时序不同步，打开时以明细为准
watch(forum, (v) => {
  if (v > unreadTotal.value) void load(true)
})
</script>

<style scoped>
.fi-root { display: flex; flex-direction: column; height: 100%; background: #fff; color: #1f2329; }
.fi-head { padding: 16px 16px 10px; border-bottom: 1px solid #f0f1f3; }
.fi-title-row { display: flex; align-items: center; gap: 10px; }
.fi-title { font-size: 17px; font-weight: 600; flex: 1; letter-spacing: .2px; }
.fi-read-all { border: none; background: none; color: #6b7280; font-size: 12px; cursor: pointer; }
.fi-read-all:hover { color: #111827; text-decoration: underline; }
.fi-close { border: none; background: #f4f5f7; width: 26px; height: 26px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; color: #6b7280; }
.fi-acts { display: flex; align-items: center; gap: 10px; }
.fi-back { display: none; }
.fi-tabs { display: flex; gap: 8px; margin-top: 12px; overflow-x: auto; scrollbar-width: none; }
.fi-tabs::-webkit-scrollbar { display: none; }
.fi-tab { position: relative; border: 1px solid transparent; background: #f5f6f8; color: #4b5563; font-size: 12px; padding: 5px 12px; border-radius: 999px; cursor: pointer; white-space: nowrap; }
.fi-tab.active { background: #111827; color: #fff; }
.fi-tab-dot { position: absolute; top: -5px; right: -4px; background: #111827; color: #fff; font-size: 10px; line-height: 1; padding: 2px 4px; border-radius: 6px; font-style: normal; }
.fi-tab.active .fi-tab-dot { background: #fff; color: #111827; }
.fi-body { flex: 1; overflow-y: auto; padding: 2px 0 20px; }
.fi-hint, .fi-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; color: #9aa0a6; font-size: 13px; padding: 56px 24px; text-align: center; }
.fi-empty p { margin: 4px 0 0; color: #4b5563; font-size: 14px; }
.fi-empty span { font-size: 12px; }

/* ===== 行 ===== */
.fi-item {
  position: relative;
  width: 100%; display: flex; gap: 12px; align-items: flex-start;
  padding: 13px 16px;
  background: none; border: none; border-bottom: 1px solid #f3f4f6;
  text-align: left; cursor: pointer;
  transition: background .12s ease;
}
.fi-item:last-child { border-bottom: 0; }
.fi-item:hover { background: #fafbfc; }
.fi-item.unread { background: #f7f8fa; }
.fi-item.unread:hover { background: #f4f5f7; }

/* 头像 + 动作角标 */
.fi-avatar-wrap { position: relative; flex: none; width: 40px; height: 40px; }
.fi-avatar { display: block; font-size: 15px; font-weight: 600; background: #eef0f3; color: #6b7280; }
.fi-kind {
  position: absolute; right: -4px; bottom: -4px;
  width: 17px; height: 17px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  border: 2px solid #fff;
}
.k-like { background: #ffece8; color: #d4380d; }
.k-favorite { background: #fff7e6; color: #d46b08; }
.k-comment { background: #e6f4ff; color: #0958d9; }
.k-follow { background: #f0f9eb; color: #3f8f2e; }

.fi-main { flex: 1; min-width: 0; }
.fi-line { margin: 0; font-size: 13px; line-height: 1.5; color: #6b7280; }
.fi-actor { color: #111827; font-weight: 600; margin-right: 5px; }
.fi-action { color: #6b7280; }
/* 帖子标题独占一行，单行省略：三个 tab 里都能一眼看到「说的是哪篇」 */
.fi-post {
  margin: 3px 0 0;
  font-size: 13px; line-height: 1.45; color: #1f2329;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.fi-quote {
  margin: 6px 0 0; font-size: 12px; line-height: 1.5; color: #6b7280;
  background: #f4f5f7; border-radius: 6px; padding: 6px 8px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.fi-time { display: inline-flex; align-items: center; gap: 5px; margin-top: 5px; font-size: 11px; color: #9aa0a6; }
.fi-dot { width: 5px; height: 5px; border-radius: 50%; background: #1d2129; }

.fi-thumb { flex: none; width: 56px; height: 56px; border-radius: 8px; overflow: hidden; background: #f4f5f7; }
.fi-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* ==================== 移动端（≤767px）：按全站子页口径适配 ====================
   这个抽屉被 teleport 到 body，不在 #app 的移动端 zoom 里，所以字号 / 行高 / 触控面积
   在这里单独给一套手机口径：
     · 顶部让出状态栏（--sat），底部让出系统手势条（safe-area-inset-bottom）；
     · 顶栏换成「返回箭头 + 标题 + 全部已读」的子页样式，✕ 只留给桌面抽屉；
     · 正文放大到 14~14.5px，头像 / 缩略图同步放大，与资讯流、帖子详情一致。 */
@media (max-width: 767px) {
  .fi-head { padding: calc(var(--sat, 0px) + 4px) 12px 6px; }
  .fi-title-row { min-height: 46px; gap: 4px; }
  .fi-title { font-size: 17.5px; }
  .fi-back {
    display: inline-flex; align-items: center; justify-content: center;
    width: 38px; height: 38px; margin-left: -8px;
    border: none; border-radius: 50%; background: transparent; color: #1f2329;
    -webkit-tap-highlight-color: transparent;
  }
  .fi-back:active { background: #f2f3f5; }
  .fi-close { display: none; }
  .fi-acts { gap: 6px; }
  .fi-read-all { font-size: 13px; padding: 8px 4px; }
  .fi-tabs { margin-top: 4px; gap: 8px; padding: 2px 0; -webkit-overflow-scrolling: touch; }
  .fi-tab { font-size: 13px; padding: 7px 14px; }
  .fi-body {
    padding: 0 0 calc(18px + env(safe-area-inset-bottom, 0px));
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
  }
  .fi-avatar-wrap { width: 44px; height: 44px; }
  .fi-avatar { font-size: 16px; }
  .fi-item { padding: 13px 14px; gap: 11px; }
  .fi-item:hover { background: none; }
  .fi-item.unread:hover { background: #f7f8fa; }
  .fi-line { font-size: 14px; }
  .fi-post { font-size: 14.5px; margin-top: 4px; }
  .fi-quote { font-size: 13px; margin-top: 6px; }
  .fi-time { font-size: 12px; margin-top: 6px; }
  .fi-thumb { width: 64px; height: 64px; border-radius: 9px; }
  .fi-kind { width: 18px; height: 18px; }
  .fi-empty { padding: 64px 24px; }
  .fi-empty p { font-size: 15px; }
  .fi-empty span { font-size: 13px; }
}

</style>

<!-- 不能写在 scoped 里：抽屉被 teleport 到 body 下，是页面级浮层。
     全局 admin-components.css 在 ≤768px 给所有 .el-drawer 加了
     max-width: calc(100% - 24px)（桌面端留一条缝是为了露出背后的页面，看得出来是浮层），
     但这个抽屉在移动端是整页级交互：自带标题栏和页签，留缝只会把资讯页的半截文字
     露在左边，右侧又贴边，左右不对称。这里只对本类放行，其余抽屉维持原样。 -->
<style>
@media (max-width: 768px) {
  .el-drawer.forum-inbox-drawer {
    max-width: 100% !important;
  }
}
</style>
