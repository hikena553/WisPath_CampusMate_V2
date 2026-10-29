<template>
  <div class="fi">
    <!-- 分类快捷入口：淡色圆底 + 彩色图标 + 下方标签（对齐参考图）。
         点按不再就地筛列表，而是各自进入独立子页（ForumCategoryPage）：
         评论（评论我的/我评论的双页签）、赞和收藏（按帖聚合）、关注消息、@我的。 -->
    <div class="fi-cats" role="tablist" aria-label="互动消息分类">
      <button
        v-for="c in cats"
        :key="c.key"
        type="button"
        role="tab"
        class="fi-cat"
        :style="{ '--c': c.color }"
        @click="activePage = c.key"
      >
        <span class="fi-cat-ring">
          <DtIcon :name="c.icon" :size="24" :filled="c.filled" />
        </span>
        <span class="fi-cat-label">{{ c.label }}</span>
      </button>
    </div>

    <div class="fi-scroll">
      <div v-if="loading" class="fi-tip">加载中…</div>
      <div v-else-if="!allItems.length" class="fi-empty">
        <DtIcon name="thumbUp" :size="44" style="color: var(--dt-text-quiet)" />
        <span>还没有互动消息</span>
        <span class="fi-empty-hint">同学评论、点赞、收藏你的帖子或关注你时，会出现在这里</span>
      </div>
      <div v-else class="fi-list">
        <button
          v-for="m in allItems"
          :key="m.id"
          type="button"
          class="fi-row"
          :class="{ unread: !m.is_read }"
          @click="openMessage(m)"
        >
          <!-- 左侧圆形标识：
               - 关注类优先用对方头像（「谁关注了我」这件事，人脸比图标有用）
               - 其余按互动类型给实心渐变圆 + 白色实心图标
               未读用右上角红色数字角标（与参考设计一致），不用小圆点。 -->
          <span class="fi-ico" :class="'fi-ico--' + m.kind">
            <img v-if="m.kind === 'follow' && m.actor_avatar" :src="m.actor_avatar" alt="" loading="lazy" />
            <DtIcon v-else :name="iconOf(m.kind)" :size="22" filled />
            <i v-if="!m.is_read" class="fi-badge" aria-label="未读">1</i>
          </span>
          <span class="fi-body">
            <span class="fi-title">{{ m.actor_name }}</span>
            <span class="fi-desc">{{ previewOf(m) }}</span>
          </span>
          <span class="fi-time">{{ formatTime(m.created_at) }}</span>
        </button>
      </div>
    </div>

    <!-- ===== 分类子页层：盖在面板上，复用全站 .subpage 滑入动画 ===== -->
    <Transition name="subpage" :duration="320">
      <ForumCategoryPage
        v-if="activePage"
        :key="activePage"
        :page="activePage"
        :messages="allItems"
        @close="activePage = null"
        @open-message="openMessage"
        @open-post="openPost"
        @open-profile="(id: number) => emit('open-profile', id)"
      />
    </Transition>
  </div>
</template>

<script setup lang="ts">
/**
 * 论坛互动消息（赞 / 收藏 / 评论 / 新粉丝）
 *
 * 与聊天彻底隔离——这里只读 forum_messages，绝不混入 messages / group_messages；
 * 未读也单独统计，所以「论坛有人评论我」不会让聊天会话列表多出红点。
 * 入口在交流社区页右上角的信封图标（见 ForumInboxSheet），消息页不出现本组件。
 *
 * 版式（对齐参考图）：主列表 = 全部互动消息一条条排；顶部四个圆入口是**导航**——
 * 点进去各自是一个独立子页（ForumCategoryPage），不再在主列表上就地筛选；
 * 搜索也收进子页（页头放大镜 → openSearch）。
 * 数据一次拉全量（最多 100 条）：子页聚合、搜索兜底全部在前端内存里做，不发额外请求。
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DtIcon from '@/components/common/DtIcon.vue'
import ForumCategoryPage from '@/components/messages/ForumCategoryPage.vue'
import {
  getForumMessages, getForumUnread, readAllForumMessages, readForumMessage,
  type ForumMessageItem, type ForumMessageKind, type ForumUnread,
} from '@/api/social'

// 事件签名用 TS 的「调用签名」写法（`(e: 'x'): void`）。
// 写成 `(e: 'x') => void` 在类型字面量里是非法语法：tsc 报 "':' expected"，
// Babel 报 "Unexpected token"，Vite 解析 SFC 时整个组件都会加载失败。
const emit = defineEmits<{
  (e: 'open-profile', userId: number): void
  /** 未读总数变化 —— 父级的入口角标据此同步，避免「已全部已读但角标还在」 */
  (e: 'unread-change', total: number): void
}>()
const router = useRouter()

/** 子页键：四个分类 + 搜索（搜索只从页头放大镜进，不在圆入口里） */
type PageKey = 'comment' | 'likeFav' | 'follow' | 'mention' | 'search'

const activePage = ref<PageKey | null>(null)
const allItems = ref<ForumMessageItem[]>([])
const unread = ref<ForumUnread>({ total: 0, comment: 0, like: 0, favorite: 0, follow: 0 })
const loading = ref(false)

/** 四个入口的配色与图标（顺序、色相均对齐参考图：蓝 / 蓝紫 / 紫 / 天蓝）。
 *  filled 仅对闭合外形图标开启；@ 是纯描边图形，filled 会糊成实心块。 */
const cats: Array<{ key: PageKey; label: string; icon: string; color: string; filled: boolean }> = [
  { key: 'comment', label: '所有评论', icon: 'message', color: '#4d8bf8', filled: true },
  { key: 'likeFav', label: '赞和收藏', icon: 'thumbUp', color: '#5865e6', filled: true },
  { key: 'follow', label: '关注', icon: 'user', color: '#8b6cf0', filled: true },
  { key: 'mention', label: '@我的', icon: 'at', color: '#38a0f2', filled: false },
]

/** 行内类型图标：与分类入口同一套语义、同一套颜色 */
function iconOf(kind: ForumMessageKind) {
  if (kind === 'comment') return 'message'
  if (kind === 'like') return 'thumbUp'
  if (kind === 'favorite') return 'heart'
  return 'user'
}

/** 摘要一行：动作 + 内容/帖子标题。列表只用一行，长文本交给 CSS 省略号。 */
function previewOf(m: ForumMessageItem) {
  if (m.kind === 'comment') {
    const text = (m.content || '').trim()
    return text ? `评论了你：${text}` : '评论了你的帖子'
  }
  if (m.kind === 'like') return m.post_title ? `赞了你：${m.post_title}` : '赞了你的帖子'
  if (m.kind === 'favorite') return m.post_title ? `收藏了你：${m.post_title}` : '收藏了你的帖子'
  return '关注了你'
}

function parseTime(iso: string) {
  return new Date(iso + (iso.includes('Z') || iso.includes('+') ? '' : 'Z'))
}

/** 列表时间用短格式（参考设计右侧是「昨天 02:05 / 10-24 / 2025-08-31」这种紧凑写法） */
function formatTime(iso: string) {
  if (!iso) return ''
  const d = parseTime(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  if (diff < 60_000) return '刚刚'
  if (d.toDateString() === now.toDateString()) return hm
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return `昨天 ${hm}`
  const mmdd = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  if (d.getFullYear() === now.getFullYear()) return mmdd
  return `${d.getFullYear()}-${mmdd}`
}

async function load() {
  loading.value = true
  try {
    const [list, un] = await Promise.all([
      // 一次拉满（后端上限 100）：子页聚合 / 搜索兜底都在前端做，不再发请求。
      getForumMessages({ page_size: 100 }),
      getForumUnread(),
    ])
    allItems.value = list
    unread.value = un
    emit('unread-change', un.total || 0)
  } catch {
    allItems.value = []
  } finally {
    loading.value = false
  }
}

/** 本地未读归零（单条）：不重拉列表，角标即时熄灭 */
function markReadLocal(m: ForumMessageItem) {
  if (m.is_read) return
  m.is_read = true
  unread.value = {
    total: Math.max(0, unread.value.total - 1),
    comment: Math.max(0, unread.value.comment - (m.kind === 'comment' ? 1 : 0)),
    like: Math.max(0, unread.value.like - (m.kind === 'like' ? 1 : 0)),
    favorite: Math.max(0, unread.value.favorite - (m.kind === 'favorite' ? 1 : 0)),
    follow: Math.max(0, unread.value.follow - (m.kind === 'follow' ? 1 : 0)),
  }
  emit('unread-change', unread.value.total)
  readForumMessage(m.id).catch(() => {})
}

function openMessage(m: ForumMessageItem) {
  markReadLocal(m)
  if (m.post_id) {
    // 帖子详情走校园资讯页的 ?post= 直达（社区已并入校园资讯「交流社区」Tab）
    router.push({ path: '/student/campus', query: { post: String(m.post_id) } })
  } else {
    emit('open-profile', m.actor_id)
  }
}

/** 子页里点了「原帖」卡片：把该帖的互动一并标为已读再进帖（一次访问全部消掉） */
function openPost(postId: number | null) {
  if (postId == null) return
  for (const m of allItems.value) {
    if (m.post_id === postId) markReadLocal(m)
  }
  router.push({ path: '/student/campus', query: { post: String(postId) } })
}

/** 全部已读（页头勾选按钮）：清掉所有类型的未读 */
async function readAll() {
  if (unread.value.total === 0) return
  try {
    await readAllForumMessages()
    allItems.value = allItems.value.map((m) => ({ ...m, is_read: true }))
    unread.value = { total: 0, comment: 0, like: 0, favorite: 0, follow: 0 }
    emit('unread-change', 0)
    ElMessage.success('已全部标记为已读')
  } catch {
    ElMessage.error('操作失败，请稍后重试')
  }
}

onMounted(load)

/** 页头（ForumInboxSheet）要指挥内部：放大镜开搜索子页、勾选清未读 */
defineExpose({
  reload: load,
  unread,
  readAll,
  openSearch: () => { activePage.value = 'search' },
  /** Esc 语义：子页开着就先退子页，返回 true 表示已消费 */
  handleEsc(): boolean {
    if (!activePage.value) return false
    activePage.value = null
    return true
  },
})
</script>

<style scoped>
.fi {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  /* 与页头、会话流同宽（桌面端 880 居中） */
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
}

/* ================= 分类快捷入口 =================
   对齐参考图：淡色圆底（入口色混 12% 白）+ 同色彩色图标，
   它们是导航入口（各自进子页），不再有选中态。 */
.fi-cats {
  display: flex;
  align-items: flex-start;
  flex-shrink: 0;
  padding: 6px 4px 12px;
}
.fi-cat {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 4px 2px;
  border: 0;
  background: transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fi-cat-ring {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--c) 12%, #fff);
  color: var(--c);
  transition: background .2s ease;
}
.fi-cat:active .fi-cat-ring {
  background: color-mix(in srgb, var(--c) 20%, #fff);
}
.fi-cat-label {
  font-size: 12px;
  line-height: 1.2;
  color: var(--dt-text-secondary, #4e5969);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ================= 列表 =================
   参考设计的列表没有分隔线，靠行高与留白分区；未读只靠角标表达，
   标题颜色不跟着变（避免整列深浅不一的噪点）。 */
.fi-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 16px 24px;
  scrollbar-width: none;
}
.fi-scroll::-webkit-scrollbar { display: none; }

.fi-list { display: flex; flex-direction: column; }

.fi-row {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 12px 0;
  border: 0;
  border-radius: 12px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fi-row:active { background: var(--dt-hover, rgba(0, 0, 0, .035)); }

/* 圆形标识：46px，实心渐变 + 白色实心图标；关注类直接用对方头像 */
.fi-ico {
  position: relative;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  color: #fff;
  background: var(--dt-fill, #f2f3f5);
}
.fi-ico img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}
.fi-ico--comment { background: linear-gradient(135deg, #6aa9f8, #3a7ff0); }
/* 赞用偏青的蓝，与评论的蓝拉开一档：列表里连续几条都是赞时不会显得全都一样 */
.fi-ico--like { background: linear-gradient(135deg, #56c2ee, #1596d1); }
.fi-ico--favorite { background: linear-gradient(135deg, #f7b955, #ef940f); }
.fi-ico--follow { background: linear-gradient(135deg, #5fc7a8, #22a67f); }

/* 未读角标：右上角红色数字，白描边把它从圆形底色上切出来 */
.fi-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 999px;
  border: 1.5px solid var(--dt-surface, #fff);
  background: var(--dt-danger, #f53f3f);
  color: #fff;
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
  line-height: 15px;
  text-align: center;
  box-sizing: border-box;
}

.fi-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.fi-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--dt-text, #171a1d);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fi-desc {
  font-size: 13px;
  line-height: 1.35;
  color: var(--dt-text-tertiary, #86909c);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fi-time {
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 2px;
  font-size: 12px;
  color: var(--dt-text-quiet, #a9aeb8);
}

.fi-tip { padding: 20px 0; text-align: center; font-size: 12px; color: var(--dt-text-tertiary); }
.fi-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--dt-text-tertiary);
}
.fi-empty-hint { font-size: 12px; color: var(--dt-text-quiet); }

@media (max-width: 767px) {
  .fi-cats { padding: 4px 0 10px; }
  .fi-scroll { padding: 0 16px 16px; }
  .fi-cat-ring { width: 52px; height: 52px; }
  .fi-ico { width: 46px; height: 46px; }
}
</style>
