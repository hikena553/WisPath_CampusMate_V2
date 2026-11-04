<template>
  <div class="cfeed">
    <!-- 分类筛选 + 排序：两者都直接落到接口参数上，切一次拉一次，不做本地过滤
         （本地过滤只能作用于已加载的这一页，会出现「切到提问却只看到 3 条」） -->
    <div class="cfeed-bar">
      <div class="cfeed-chips">
        <button
          v-for="c in chips" :key="c.value" type="button"
          class="cfeed-chip" :class="{ 'is-active': category === c.value }"
          @click="setCategory(c.value)"
        >{{ c.label }}</button>
      </div>
      <div class="cfeed-sort">
        <button type="button" :class="{ 'is-active': sort === 'new' }" @click="setSort('new')">最新</button>
        <button type="button" :class="{ 'is-active': sort === 'hot' }" @click="setSort('hot')">最热</button>
      </div>
    </div>

    <div class="cfeed-list">
      <div
        v-for="p in posts" :key="p.id"
        class="cfeed-item"
        role="link" tabindex="0"
        @click="emit('open', p)"
        @keydown.enter.prevent="emit('open', p)"
      >
        <div class="cfeed-body">
          <h3 class="cfeed-title">{{ p.title }}</h3>
          <div class="cfeed-meta">
            <span class="cfeed-time">{{ timeLabel(p.created_at) }}</span>
            <span class="cfeed-dot">·</span>
            <span class="cfeed-source">{{ p.author_name || '同学' }} · {{ p.category }}</span>
            <div class="cfeed-acts">
              <span class="cfeed-act" :aria-label="`评论 ${p.comment_count} 条`">
                <el-icon><ChatDotRound /></el-icon><span>{{ p.comment_count }}</span>
              </span>
              <span class="cfeed-act" :aria-label="`浏览 ${p.view_count} 次`">
                <el-icon><View /></el-icon><span>{{ p.view_count }}</span>
              </span>
            </div>
          </div>
        </div>
        <div v-if="p.images?.length" class="cfeed-thumb">
          <img :src="p.images[0]" alt="" loading="lazy" />
        </div>
      </div>

      <p v-if="loading && !posts.length" class="cfeed-empty">加载中…</p>
      <p v-else-if="!posts.length" class="cfeed-empty">{{ emptyText }}</p>
    </div>

    <!-- 底部状态：滚动到底自动翻页，不再让用户点按钮 -->
    <div ref="sentinelRef" class="cfeed-sentinel" aria-hidden="true" />
    <p v-if="loading && posts.length" class="cfeed-tip">加载中…</p>
    <p v-else-if="showEndTip" class="cfeed-tip is-end">没有更多了</p>
  </div>
</template>

<script setup lang="ts">
/**
 * 交流社区帖子流（校园资讯「交流社区」页签 / 桌面端社区卡片共用）。
 *
 * 为什么单独成组件：帖子有自己的筛选（分区）、排序（最新 / 最热）与分页，
 * 和资讯流的「按栏目过滤」不是一套东西；塞进 FeedItem 只会让两边的特例越堆越多。
 *
 * 用法：<CommunityFeed ref="feedRef" @open="openPost" />
 *   - 父页发布成功后调 feedRef.refresh() 重新拉第一页；
 *   - 点某条 → 父页打开 PostDetailPage。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, View } from '@element-plus/icons-vue'
import { getPosts, COMMUNITY_CATEGORIES, type CommunityPost } from '@/api/community'
import { isGuestMode } from '@/utils/guest'
import { parseServerTime } from '@/utils/datetime'

const props = withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
const emit = defineEmits<{ (e: 'open', post: CommunityPost): void }>()

const PAGE_SIZE = 10

const posts = ref<CommunityPost[]>([])
const loading = ref(false)
const category = ref('all')
const sort = ref<'new' | 'hot'>('new')
const page = ref(1)
const reachedEnd = ref(false)
const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const chips = [{ label: '全部', value: 'all' }, ...COMMUNITY_CATEGORIES.map(c => ({ label: c, value: c }))]

const hasMore = computed(() => !reachedEnd.value && posts.value.length > 0)

/** 只有一页也要提示「没有更多了」会很吵，攒够一页再说 */
const showEndTip = computed(
  () => !props.compact && !hasMore.value && posts.value.length >= PAGE_SIZE,
)

const emptyText = computed(() => {
  if (isGuestMode()) return '登录后查看社区帖子'
  if (category.value !== 'all') return `「${category.value}」下还没有帖子`
  return '还没有帖子，点右下角「+」发布第一条'
})

function timeLabel(t: string | null): string {
  // 后端时间是不带时区的 UTC：先按 UTC 解析，再落到本地日期上比「今天 / 昨天」，
  // 否则凌晨发的帖子（UTC 还是前一天）会被标成「昨天」
  const ms = parseServerTime(t)
  if (Number.isNaN(ms)) return ''
  const d = new Date(ms)
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diffDays = Math.round((today.getTime() - target.getTime()) / 86400000)
  if (diffDays <= 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays === 2) return '前天'
  if (diffDays < 7) return `${diffDays} 天前`
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

async function fetchPage(target: number, append: boolean) {
  if (isGuestMode()) { posts.value = []; reachedEnd.value = true; return }
  loading.value = true
  try {
    const size = props.compact ? 6 : PAGE_SIZE
    const params: Record<string, unknown> = { page: target, page_size: size, sort: sort.value }
    if (category.value !== 'all') params.category = category.value
    const list = await getPosts(params)
    posts.value = append ? [...posts.value, ...list] : list
    page.value = target
    // 后端返回数组：不足一页说明到底（compact 模式只取首屏一批，不参与翻页）
    reachedEnd.value = props.compact || list.length < size
  } catch {
    if (!append) posts.value = []
    reachedEnd.value = true
    ElMessage.error('帖子加载失败，请稍后重试')
  } finally {
    loading.value = false
    // 追加完再看一眼：哨兵还在视口里就继续补，避免「不满一屏就卡住」
    void nextTick(ensureFill)
  }
}

function refresh() {
  reachedEnd.value = false
  return fetchPage(1, false)
}

/** 滚到底自动翻页；到底（reachedEnd）或空列表时不再请求 */
function loadMore() {
  if (loading.value || reachedEnd.value || !posts.value.length) return
  void fetchPage(page.value + 1, true)
}

/**
 * 补页：一页没填满一屏时，哨兵虽然已经进入视口，但观察器只在「相交状态变化」时回调，
 * 首次相交若正好撞上 loading 被挡掉，之后就再也不会通知 —— 每次请求结束都主动复核一次。
 * 分页轨道（SwipePager）里邻居页挂在视口左右两侧，按水平位置把它们排除掉，别替用户预加载。
 */
function ensureFill() {
  const el = sentinelRef.value
  if (!el || props.compact) return
  if (loading.value || !hasMore.value) return
  const r = el.getBoundingClientRect()
  if (r.right <= 0 || r.left >= window.innerWidth) return
  if (r.bottom > 0 && r.top < window.innerHeight) loadMore()
}

function setCategory(c: string) {
  if (category.value === c) return
  category.value = c
  void refresh()
}

function setSort(s: 'new' | 'hot') {
  if (sort.value === s) return
  sort.value = s
  void refresh()
}

/* ---------- 触底自动加载 ---------- */
function setupObserver() {
  if (observer || props.compact) return
  if (typeof IntersectionObserver === 'undefined') return
  const el = sentinelRef.value
  if (!el) return
  observer = new IntersectionObserver(
    (entries) => { if (entries.some(e => e.isIntersecting)) loadMore() },
    // 不用 rootMargin 预取：留余量会让首屏就立刻判定「已见底」，一进来就拉两页
    { root: null, rootMargin: '0px', threshold: 0 },
  )
  observer.observe(el)
}

onMounted(() => {
  void refresh()
  void nextTick(setupObserver)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})

defineExpose({ refresh })
</script>

<style scoped>
.cfeed { display: block; }

/* ===== 筛选条 ===== */
.cfeed-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 0 8px;
}
.cfeed-chips {
  display: flex; gap: 8px; flex: 1; min-width: 0;
  overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch;
}
.cfeed-chips::-webkit-scrollbar { display: none; }
.cfeed-chip {
  flex: 0 0 auto;
  height: 28px; padding: 0 12px;
  border: 1px solid rgba(15, 23, 42, .08); border-radius: 14px;
  background: #f4f5f7; color: #5b6474; font-size: 12px;
  cursor: pointer; transition: background .15s ease, color .15s ease;
}
.cfeed-chip.is-active { background: #1d2129; border-color: #1d2129; color: #fff; }

.cfeed-sort { display: flex; gap: 2px; flex-shrink: 0; }
.cfeed-sort button {
  border: 0; background: none; padding: 4px 6px;
  font-size: 12px; color: #98a2b3; cursor: pointer;
}
.cfeed-sort button.is-active { color: #1d2129; font-weight: 600; }

/* ===== 行 ===== */
.cfeed-list { display: block; }
.cfeed-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(15, 23, 42, .06);
  cursor: pointer;
}
.cfeed-item:last-child { border-bottom: 0; }
.cfeed-item:active { background: rgba(15, 23, 42, .02); }
.cfeed-body { flex: 1; min-width: 0; }
.cfeed-title {
  margin: 0;
  font-size: 15px; font-weight: 700; line-height: 1.45; color: #1a1a2e;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.cfeed-meta {
  display: flex; align-items: center; gap: 6px;
  margin-top: 6px; font-size: 12px; color: #98a2b3;
}
.cfeed-time, .cfeed-source { flex-shrink: 0; }
.cfeed-source { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cfeed-dot { color: #d0d5dd; }
.cfeed-acts { display: flex; gap: 12px; margin-left: auto; }
.cfeed-act { display: inline-flex; align-items: center; gap: 3px; }

.cfeed-thumb {
  width: 96px; height: 72px; flex-shrink: 0;
  border-radius: 8px; overflow: hidden; background: #f4f5f7;
}
.cfeed-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }

.cfeed-empty { padding: 36px 0; text-align: center; font-size: 13px; color: #98a2b3; }

/* 触底哨兵：高度 1px，看不见但能被 IntersectionObserver 观察到 */
.cfeed-sentinel { height: 1px; }
.cfeed-tip {
  padding: 10px 0 14px;
  text-align: center;
  font-size: 12px;
  color: #a8b0bd;
}
.cfeed-tip.is-end { color: #c3c9d4; }

/* 桌面端（校园资讯桌面卡片里）：行内边距略收，缩略图小一点 */
@media (min-width: 768px) {
  .cfeed-thumb { width: 84px; height: 62px; }
  .cfeed-item { padding: 10px 0; }
}
</style>
