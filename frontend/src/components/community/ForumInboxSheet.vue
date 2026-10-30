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
          <span class="fi-title">互动消息</span>
          <button v-if="unreadTotal" type="button" class="fi-read-all" @click="markAllRead">全部已读</button>
          <button type="button" class="fi-close" aria-label="关闭" @click="open = false">
            <el-icon :size="16"><Close /></el-icon>
          </button>
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
        <div v-if="loading" class="fi-hint">加载中…</div>
        <div v-else-if="!list.length" class="fi-empty">
          <el-icon :size="28"><Message /></el-icon>
          <p>还没有互动消息</p>
          <span>别人赞、收藏或评论你的帖子时会出现在这里</span>
        </div>
        <div v-else class="fi-list">
          <button
            v-for="item in list"
            :key="item.id"
            type="button"
            :class="['fi-item', { unread: !item.is_read }]"
            @click="openItem(item)"
          >
            <el-avatar :size="34" :src="item.actor_avatar || undefined" class="fi-avatar">
              {{ (item.actor_name || '同学').slice(0, 1) }}
            </el-avatar>
            <div class="fi-main">
              <div class="fi-line">
                <b class="fi-actor">{{ item.actor_name || '同学' }}</b>
                <span class="fi-action">{{ actionText(item.kind) }}</span>
                <span v-if="item.post_title" class="fi-post">《{{ item.post_title }}》</span>
              </div>
              <p v-if="item.kind === 'comment' && item.content" class="fi-quote">{{ item.content }}</p>
              <span class="fi-time">{{ formatTime(item.created_at) }}</span>
            </div>
            <i v-if="!item.is_read" class="fi-unread-dot" aria-hidden="true"></i>
          </button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Close } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { openUserHomepage } from '@/composables/useUserHomepage'
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

type TabValue = 'all' | ForumKind
const tabs: Array<{ label: string; value: TabValue }> = [
  { label: '全部', value: 'all' },
  { label: '赞', value: 'like' },
  { label: '收藏', value: 'favorite' },
  { label: '评论', value: 'comment' },
  { label: '关注', value: 'follow' },
]

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

function countOf(tab: TabValue) {
  return unreadCounts.value[tab] || 0
}

function actionText(kind: ForumKind) {
  return (
    { like: '赞了你的帖子', favorite: '收藏了你的帖子', comment: '评论了你的帖子', follow: '关注了你' }[kind] ||
    '与你互动'
  )
}

function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const now = Date.now()
  const diff = Math.max(0, now - d.getTime())
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3600_000)} 小时前`
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
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
    list.value = list.value.map((m) => ({ ...m, is_read: true }))
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
  router.push({ name: 'student-community', query: { post: String(item.post_id) } })
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
.fi-head { padding: 18px 18px 10px; border-bottom: 1px solid #f0f1f3; }
.fi-title-row { display: flex; align-items: center; gap: 10px; }
.fi-title { font-size: 16px; font-weight: 600; flex: 1; }
.fi-read-all { border: none; background: none; color: #6b7280; font-size: 12px; cursor: pointer; }
.fi-read-all:hover { color: #111827; text-decoration: underline; }
.fi-close { border: none; background: #f4f5f7; width: 26px; height: 26px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; color: #6b7280; }
.fi-tabs { display: flex; gap: 6px; margin-top: 12px; overflow-x: auto; scrollbar-width: none; }
.fi-tabs::-webkit-scrollbar { display: none; }
.fi-tab { position: relative; border: 1px solid transparent; background: #f5f6f8; color: #4b5563; font-size: 12px; padding: 5px 12px; border-radius: 999px; cursor: pointer; white-space: nowrap; }
.fi-tab.active { background: #111827; color: #fff; }
.fi-tab-dot { position: absolute; top: -5px; right: -4px; background: #111827; color: #fff; font-size: 10px; line-height: 1; padding: 2px 4px; border-radius: 6px; font-style: normal; }
.fi-tab.active .fi-tab-dot { background: #fff; color: #111827; }
.fi-body { flex: 1; overflow-y: auto; padding: 6px 0 20px; }
.fi-hint, .fi-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; color: #9aa0a6; font-size: 13px; padding: 56px 24px; text-align: center; }
.fi-empty p { margin: 4px 0 0; color: #4b5563; font-size: 14px; }
.fi-empty span { font-size: 12px; }
.fi-item { position: relative; width: 100%; display: flex; gap: 10px; align-items: flex-start; padding: 12px 18px; background: none; border: none; border-bottom: 1px solid #f5f6f8; text-align: left; cursor: pointer; }
.fi-item:hover { background: #fafbfc; }
.fi-item.unread { background: #f7f8fa; }
.fi-avatar { flex-shrink: 0; background: #e9ebee; color: #6b7280; font-size: 13px; }
.fi-main { flex: 1; min-width: 0; }
.fi-line { font-size: 13px; line-height: 1.5; color: #4b5563; }
.fi-actor { color: #111827; font-weight: 600; margin-right: 4px; }
.fi-post { color: #111827; margin-left: 4px; }
.fi-quote { margin: 4px 0 0; font-size: 12px; color: #6b7280; background: #f4f5f7; border-radius: 6px; padding: 6px 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.fi-time { display: inline-block; margin-top: 4px; font-size: 11px; color: #9aa0a6; }
.fi-unread-dot { position: absolute; right: 14px; top: 50%; transform: translateY(-50%); width: 7px; height: 7px; border-radius: 50%; background: #111827; }
</style>
