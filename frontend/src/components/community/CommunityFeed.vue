<template>
  <div class="cf-root" :class="{ 'is-compact': compact }">
    <!-- 分区：椭圆胶囊分段切换，移动端整条横滑，桌面卡片同款 -->
    <div class="cf-compact-bar">
      <div class="cf-chips" role="tablist" aria-label="帖子分区">
        <button
          v-for="f in categoryFilters"
          :key="f.value"
          type="button"
          role="tab"
          class="cf-chip"
          :class="{ 'is-active': category === f.value }"
          :aria-selected="category === f.value"
          @click="switchCategory(f.value)"
        >{{ f.label }}</button>
      </div>
    </div>

    <!-- 热帖 -->
    <section v-if="!compact && hotPosts.length" class="cf-hot">
      <div class="cf-hot-head">
        <el-icon :size="14"><StarFilled /></el-icon>
        <span>热帖</span>
      </div>
      <button
        v-for="h in hotPosts"
        :key="h.id"
        type="button"
        class="cf-hot-item"
        @click="emit('open', h)"
      >
        <span class="cf-hot-title">{{ h.title }}</span>
        <span class="cf-hot-count">{{ h.like_count }} 赞</span>
      </button>
    </section>

    <div v-if="loading && !posts.length" class="cf-state">正在加载帖子…</div>
    <div v-else-if="error" class="cf-state is-error">
      <span>{{ error }}</span>
      <button type="button" class="cf-retry" @click="reload">重试</button>
    </div>
    <div v-else-if="!posts.length" class="cf-state">暂无帖子，来发布第一条吧</div>

    <div v-else class="cf-list">
      <div
        v-for="p in posts"
        :key="p.id"
        class="cf-post"
        role="button"
        tabindex="0"
        @click="emit('open', p)"
        @keydown.enter.prevent="emit('open', p)"
      >
        <div class="cf-head">
          <el-avatar
            :size="32"
            :src="p.author_avatar || undefined"
            class="cf-avatar"
            @click.stop="openUserHomepage(p.student_id)"
          >
            {{ (p.author_name || '学').slice(0, 1) }}
          </el-avatar>
          <div class="cf-author">
            <div class="cf-author-row">
              <span class="cf-name" @click.stop="openUserHomepage(p.student_id)">{{ p.author_name || '同学' }}</span>
              <span class="cf-cat">{{ p.category }}</span>
            </div>
            <span class="cf-time">{{ relativeTime(p.created_at) }}</span>
          </div>
          <button
            v-if="p.student_id !== myId"
            type="button"
            class="cf-follow"
            :class="{ 'is-following': p.author_is_following }"
            :disabled="followLoadingId === p.student_id"
            @click.stop="toggleFollow(p)"
          >{{ p.author_is_following ? '已关注' : '+ 关注' }}</button>
        </div>

        <h3 class="cf-title">{{ p.title }}</h3>
        <p v-if="p.content" class="cf-content">{{ p.content }}</p>

        <div v-if="imageList(p).length" class="cf-thumbs">
          <img
            v-for="(img, i) in imageList(p).slice(0, 3)"
            :key="img + i"
            :src="img"
            alt=""
            loading="lazy"
          />
          <span v-if="imageList(p).length > 3" class="cf-thumb-more">+{{ imageList(p).length - 3 }}</span>
        </div>

        <div class="cf-stats">
          <span class="cf-stat"><el-icon :size="14"><View /></el-icon>{{ p.view_count }}</span>
          <span class="cf-stat"><el-icon :size="14"><ChatLineRound /></el-icon>{{ p.comment_count }}</span>
          <span class="cf-stat" :class="{ 'is-liked': p.liked }">
            <el-icon :size="14"><StarFilled v-if="p.liked" /><Star v-else /></el-icon>{{ p.like_count }}
          </span>
        </div>
      </div>
    </div>

    <!-- 翻页：移动端完整帖子流；桌面卡片只展示最新几条，不占高度 -->
    <div v-if="!compact && (page > 1 || hasMore)" class="cf-pager">
      <button type="button" :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
      <span class="cf-page-num">{{ page }}</span>
      <button type="button" :disabled="!hasMore || loading" @click="goPage(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 交流社区帖子流
 *
 * 从旧独立社区页拆出，作为校园资讯页
 * 「交流社区」页签的内容（移动端整页 / 桌面端卡片 compact）。父页只负责打开详情、
 * 发布后刷新，筛选 / 排序 / 翻页 / 关注都在这里。
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatLineRound, Star, StarFilled, View } from '@element-plus/icons-vue'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { promptLogin } from '@/utils/loginGate'
import {
  COMMUNITY_CATEGORIES,
  getHotPosts,
  getPosts,
  type CommunityPost,
} from '@/api/community'
import { followUser, unfollowUser } from '@/api/social'
import { useAuthStore } from '@/stores/auth'

const props = withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })

const emit = defineEmits<{
  /** 点一条帖子：父页负责打开 PostDetailPage */
  (e: 'open', post: CommunityPost): void
}>()

const categoryFilters = [
  { label: '全部', value: 'all' },
  ...COMMUNITY_CATEGORIES.map((c) => ({ label: c, value: c })),
]

const posts = ref<CommunityPost[]>([])
const hotPosts = ref<CommunityPost[]>([])
const page = ref(1)
const pageSize = computed(() => (props.compact ? 5 : 10))
const hasMore = ref(false)
const loading = ref(false)
const error = ref('')
const category = ref('all')

const auth = useAuthStore()
const myId = computed(() => auth.user?.id ?? null)
const followLoadingId = ref<number | null>(null)

/** 请求序号：连续切分区 / 翻页时只认最后一次响应 */
let reqSeq = 0

function imageList(p: CommunityPost): string[] {
  return Array.isArray(p.images) ? p.images : []
}

async function loadPosts() {
  const seq = ++reqSeq
  loading.value = true
  error.value = ''
  try {
    const params: { category?: string; page: number; page_size: number; sort: string } = {
      page: page.value,
      page_size: pageSize.value,
      sort: 'new',
    }
    if (category.value !== 'all') params.category = category.value
    const list = await getPosts(params)
    if (seq !== reqSeq) return
    posts.value = list
    // 后端返回数组：不满一页即到底
    hasMore.value = list.length >= pageSize.value
  } catch {
    if (seq !== reqSeq) return
    posts.value = []
    hasMore.value = false
    error.value = '帖子加载失败，请稍后重试'
  } finally {
    if (seq === reqSeq) loading.value = false
  }
}

async function loadHot() {
  if (props.compact) return
  try {
    hotPosts.value = await getHotPosts(5)
  } catch {
    hotPosts.value = []
  }
}

async function refreshAll() {
  await Promise.all([loadPosts(), loadHot()])
}

/** 父页（发布成功 / 详情里点赞评论后）调用：回到第一页重新取数 */
async function refresh() {
  page.value = 1
  await refreshAll()
}

function reload() {
  void refreshAll()
}

function switchCategory(value: string) {
  if (category.value === value) return
  category.value = value
  page.value = 1
  void loadPosts()
}

function goPage(target: number) {
  if (target < 1 || loading.value) return
  page.value = target
  void loadPosts()
}

async function toggleFollow(p: CommunityPost) {
  if (!myId.value) {
    void promptLogin('关注作者')
    return
  }
  if (followLoadingId.value !== null) return
  followLoadingId.value = p.student_id
  try {
    const res = p.author_is_following
      ? await unfollowUser(p.student_id)
      : await followUser(p.student_id)
    p.author_is_following = res.is_following
    ElMessage.success(res.is_following ? `已关注 ${p.author_name || '该作者'}` : '已取消关注')
  } catch {
    ElMessage.error('操作失败，请稍后再试')
  } finally {
    followLoadingId.value = null
  }
}

/** 相对时间：刚刚 / N 分钟前 / HH:mm / MM-DD / YYYY-MM-DD */
function relativeTime(iso: string | null): string {
  if (!iso) return ''
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  const diff = Date.now() - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  const d = new Date(t)
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  if (d.toDateString() === now.toDateString()) return `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (d.getFullYear() === now.getFullYear()) return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

onMounted(() => {
  void refreshAll()
})

defineExpose({ refresh })
</script>

<style scoped>
.cf-root {
  display: flex;
  flex-direction: column;
  min-width: 0;
  color: #1d2129;
}

/* ---------- 分区：椭圆胶囊分段切换 ---------- */
.cf-compact-bar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.cf-chips {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 999px;
  background: #f2f3f5;
  overflow-x: auto;
  scrollbar-width: none;
}
.cf-chips::-webkit-scrollbar { display: none; }
.cf-chip {
  flex-shrink: 0;
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #4e5969;
  font-size: 12.5px;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease;
  -webkit-tap-highlight-color: transparent;
}
.cf-chip.is-active {
  background: #1d2129;
  color: #fff;
}
.cf-root.is-compact .cf-chip {
  height: 26px;
  padding: 0 10px;
  font-size: 12px;
}

/* ---------- 热帖 ---------- */
.cf-hot {
  margin-bottom: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f7f8fa;
}
.cf-hot-head {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
  font-size: 12.5px;
  font-weight: 600;
  color: #4e5969;
}
.cf-hot-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.cf-hot-item:active { opacity: 0.62; }
.cf-hot-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #26282c;
}
.cf-hot-count { flex-shrink: 0; font-size: 11.5px; color: #86909c; }

/* ---------- 帖子列表 ---------- */
.cf-list { display: flex; flex-direction: column; }
.cf-post {
  padding: 13px 0;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  outline: none;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.14s ease;
}
.cf-post:last-child { border-bottom: 0; }
.cf-post:active { opacity: 0.62; }
.cf-post:focus-visible { outline: 2px solid #1d2129; outline-offset: -2px; border-radius: 8px; }
.cf-post:first-child { padding-top: 4px; }

.cf-head { display: flex; align-items: center; gap: 9px; }
.cf-avatar { flex-shrink: 0; cursor: pointer; background: #f2f3f5; color: #4e5969; }
.cf-avatar:active { transform: scale(0.94); }
.cf-author { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.cf-author-row { display: flex; align-items: center; gap: 6px; }
.cf-name {
  font-size: 13px;
  font-weight: 600;
  color: #4e5969;
  cursor: pointer;
}
.cf-cat {
  flex-shrink: 0;
  padding: 1px 6px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  font-size: 10.5px;
  line-height: 1.4;
  color: #86909c;
}
.cf-time { font-size: 11px; color: #b2b2b2; }
.cf-follow {
  flex-shrink: 0;
  height: 28px;
  padding: 0 10px;
  border: 1px solid #1d2129;
  border-radius: 14px;
  background: #fff;
  color: #1d2129;
  font-size: 11.5px;
  cursor: pointer;
}
.cf-follow.is-following { border-color: #e5e6eb; color: #86909c; }
.cf-follow:disabled { opacity: 0.5; }

.cf-title {
  margin: 8px 0 0;
  font-size: 14.5px;
  font-weight: 600;
  line-height: 1.5;
  color: #1d2129;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.cf-content {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #86909c;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
}
.cf-thumbs {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}
.cf-thumbs img {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 8px;
  background: #f2f3f5;
}
.cf-thumb-more { font-size: 11px; color: #86909c; }
.cf-stats {
  display: flex;
  gap: 18px;
  margin-top: 8px;
}
.cf-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #b2b2b2;
}
.cf-stat.is-liked { color: #1d2129; }

/* ---------- 状态 / 翻页 ---------- */
.cf-state {
  padding: 28px 0;
  text-align: center;
  font-size: 13px;
  color: #b2b2b2;
}
.cf-state.is-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #86909c;
}
.cf-retry {
  height: 30px;
  padding: 0 14px;
  border: 1px solid #e5e6eb;
  border-radius: 15px;
  background: #fff;
  color: #4e5969;
  font-size: 12.5px;
  cursor: pointer;
}
.cf-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 16px 0 4px;
}
.cf-pager button {
  height: 30px;
  padding: 0 14px;
  border: 1px solid #e5e6eb;
  border-radius: 15px;
  background: #fff;
  color: #4e5969;
  font-size: 12.5px;
  cursor: pointer;
}
.cf-pager button:disabled { color: #c9cdd4; cursor: default; }
.cf-page-num { font-size: 12.5px; color: #86909c; font-variant-numeric: tabular-nums; }

/* ---------- 桌面卡片紧凑态 ---------- */
.cf-root.is-compact .cf-list { gap: 0; }
.cf-root.is-compact .cf-post { padding: 10px 0; }
.cf-root.is-compact .cf-content { -webkit-line-clamp: 1; }
.cf-root.is-compact .cf-thumbs img { width: 54px; height: 54px; }
.cf-root.is-compact .cf-stats { margin-top: 6px; }
</style>
