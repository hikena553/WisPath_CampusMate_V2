<template>
  <div class="cfeed">
    <!-- 分区筛选 + 排序：两者都直接落到接口参数上，切一次拉一次，不做本地过滤
         （本地过滤只能作用于已加载的这一页，会出现「切到提问却只看到 3 条」）。
         「失物 / 招领」也在这排胶囊里：它们不是帖子的分区，而是社区里另一份数据
         （/lost-found/items），但同属「社区里别人发的东西」，放在同一条筛选行里
         比单独再开一排切换更顺手 —— 列表行也统一按帖子的版式渲染。 -->
    <div class="cfeed-bar">
      <div class="cfeed-chips">
        <button
          v-for="c in chips" :key="c.value" type="button"
          class="cfeed-chip" :class="{ 'is-active': category === c.value }"
          @click="setCategory(c.value)"
        >{{ c.label }}</button>
      </div>
      <!-- 排序对两种数据源都生效：帖子走接口的 sort 参数，失物招领走
           /lost-found/items?sort=（最新按发布时间、最热按留言数）。
           两个视图都常驻，切换分区时控件不消失。 -->
      <div class="cfeed-sort">
        <button type="button" :class="{ 'is-active': sort === 'new' }" @click="setSort('new')">最新</button>
        <button type="button" :class="{ 'is-active': sort === 'hot' }" @click="setSort('hot')">最热</button>
      </div>
    </div>

    <div class="cfeed-list">
      <div
        v-for="row in rows" :key="row.key"
        class="cfeed-item"
        role="link" tabindex="0"
        @click="openRow(row)"
        @keydown.enter.prevent="openRow(row)"
      >
        <div class="cfeed-body">
          <h3 class="cfeed-title">{{ row.title }}</h3>
          <div class="cfeed-meta">
            <span class="cfeed-time">{{ row.time }}</span>
            <template v-for="(seg, i) in row.segments" :key="i">
              <span class="cfeed-dot">·</span>
              <span class="cfeed-source">{{ seg }}</span>
            </template>
            <div v-if="row.commentCount !== null" class="cfeed-acts">
              <span class="cfeed-act" :aria-label="`评论 ${row.commentCount} 条`">
                <el-icon><ChatDotRound /></el-icon><span>{{ row.commentCount }}</span>
              </span>
              <span v-if="row.viewCount !== null" class="cfeed-act" :aria-label="`浏览 ${row.viewCount} 次`">
                <el-icon><View /></el-icon><span>{{ row.viewCount }}</span>
              </span>
            </div>
          </div>
        </div>
        <div v-if="row.thumb" class="cfeed-thumb">
          <img :src="row.thumb" alt="" loading="lazy" />
        </div>
      </div>

      <p v-if="loading && !rows.length" class="cfeed-empty">加载中…</p>
      <p v-else-if="!rows.length" class="cfeed-empty">{{ emptyText }}</p>
    </div>

    <!-- 底部状态：滚动到底自动翻页，不再让用户点按钮 -->
    <div ref="sentinelRef" class="cfeed-sentinel" aria-hidden="true" />
    <p v-if="loading && rows.length" class="cfeed-tip">加载中…</p>
    <p v-else-if="showEndTip" class="cfeed-tip is-end">没有更多了</p>

    <!-- 失物 / 招领的发布与详情弹窗：挂在列表这一层，两个视图共用一套 -->
    <LostFoundDialogs ref="dialogsRef" @changed="refresh" />
  </div>
</template>

<script setup lang="ts">
/**
 * 交流社区内容流（校园资讯「交流社区」页签 / 桌面端社区卡片共用）。
 *
 * 一份筛选行，两种数据源：
 *   - 全部 / 技术 / 提问 / 分享 / 求助 / 资讯 → 帖子（/community/posts，有分区 / 排序 / 分页）；
 *   - 失物 / 招领 → 失物招领（/lost-found/items，按 type 过滤，一次拉全；同样支持最新 / 最热）。
 * 两条链路的数据结构不同，但展示层统一成同一种行（标题 + 元信息 + 缩略图），
 * 所以先把两边都映射成 FeedRow，模板只认这一种形状 —— 以后加第三种内容也只需再写一个映射。
 *
 * 用法：<CommunityFeed ref="feedRef" @open="openPost" @compose="openCompose" />
 *   - feedRef.refresh()     重新拉当前视图
 *   - feedRef.openCreate()  当前是帖子就发帖子（交给父页），是失物 / 招领就开登记弹窗
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, View } from '@element-plus/icons-vue'
import { getPosts, COMMUNITY_CATEGORIES, type CommunityPost } from '@/api/community'
import { getLostFoundItems } from '@/api/lostFound'
import LostFoundDialogs from '@/components/community/LostFoundDialogs.vue'
import { isGuestMode } from '@/utils/guest'
import { promptLogin } from '@/utils/loginGate'
import { parseServerTime } from '@/utils/datetime'
import type { LostFoundItem } from '@/types'

const props = withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
const emit = defineEmits<{
  (e: 'open', post: CommunityPost): void
  /** 帖子视图的「发布」交给父页（全屏编辑器），失物 / 招领则由本组件自己开弹窗 */
  (e: 'compose'): void
}>()

const PAGE_SIZE = 10
/** 分区行末尾的两个特殊项：不是帖子分区，切过去就换成失物招领的数据 */
const LOST_CHIPS = [
  { label: '失物', value: 'lost' },
  { label: '招领', value: 'found' },
]

const posts = ref<CommunityPost[]>([])
const lostItems = ref<LostFoundItem[]>([])
const loading = ref(false)
/** 'all' | 帖子分区名 | 'lost' | 'found' */
const category = ref('all')
const sort = ref<'new' | 'hot'>('new')
const page = ref(1)
const reachedEnd = ref(false)
const sentinelRef = ref<HTMLElement | null>(null)
const dialogsRef = ref<InstanceType<typeof LostFoundDialogs> | null>(null)
let observer: IntersectionObserver | null = null

const chips = [
  { label: '全部', value: 'all' },
  ...COMMUNITY_CATEGORIES.map(c => ({ label: c, value: c })),
  ...LOST_CHIPS,
]

const isLostMode = computed(() => category.value === 'lost' || category.value === 'found')
const lostType = computed<'lost' | 'found'>(() => (category.value === 'found' ? 'found' : 'lost'))

/** 统一的行模型：帖子与失物招领都映射成这个形状，模板只写一套 */
interface FeedRow {
  key: string
  title: string
  time: string
  /** 时间之后用「·」连起来的几段：帖子是 作者 / 分区，失物招领是 失物|招领 / 地点 / 状态 */
  segments: string[]
  /** null = 这条内容没有这个计数（失物招领没有浏览量，但留言数是有的） */
  commentCount: number | null
  viewCount: number | null
  thumb: string | null
  post?: CommunityPost
  lostId?: number
}

const STATUS_TEXT: Record<string, string> = { claimed: '已认领', closed: '已结束' }

const rows = computed<FeedRow[]>(() => {
  if (isLostMode.value) {
    return lostItems.value.map(it => ({
      key: `lf-${it.id}`,
      title: it.title,
      time: timeLabel(it.created_at),
      segments: [
        it.type === 'lost' ? '失物' : '招领',
        it.location || '地点不详',
        ...(STATUS_TEXT[it.status] ? [STATUS_TEXT[it.status]] : []),
      ],
      commentCount: it.comment_count ?? 0,
      viewCount: null,
      thumb: it.image_url || null,
      lostId: it.id,
    }))
  }
  return posts.value.map(p => ({
    key: `post-${p.id}`,
    title: p.title,
    time: timeLabel(p.created_at),
    segments: [p.author_name || '同学', p.category],
    commentCount: p.comment_count,
    viewCount: p.view_count,
    thumb: p.images?.[0] || null,
    post: p,
  }))
})

const hasMore = computed(() => !isLostMode.value && !reachedEnd.value && posts.value.length > 0)

/** 只有一页也要提示「没有更多了」会很吵，攒够一页再说；失物招领一次拉全，也不提示 */
const showEndTip = computed(
  () => !props.compact && !isLostMode.value && !hasMore.value && posts.value.length >= PAGE_SIZE,
)

const emptyText = computed(() => {
  if (isGuestMode()) return '登录后查看社区内容'
  if (isLostMode.value) return lostType.value === 'lost' ? '还没有寻物启事' : '还没有失物招领'
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

/** 失物招领：接口一次返回该类型的全部登记，没有分页；sort 决定最新 / 留言最多的在前 */
async function loadLost() {
  if (isGuestMode()) { lostItems.value = []; return }
  loading.value = true
  try {
    lostItems.value = await getLostFoundItems({ type: lostType.value, sort: sort.value })
  } catch {
    lostItems.value = []
    ElMessage.error('失物招领加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function refresh() {
  if (isLostMode.value) return loadLost()
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
  posts.value = []
  lostItems.value = []
  if (isLostMode.value) {
    reachedEnd.value = true
    void loadLost()
    return
  }
  reachedEnd.value = false
  void fetchPage(1, false)
}

function setSort(s: 'new' | 'hot') {
  if (sort.value === s) return
  sort.value = s
  void refresh()
}

function openRow(row: FeedRow) {
  if (row.post) {
    emit('open', row.post)
    return
  }
  if (row.lostId) dialogsRef.value?.openDetail(row.lostId)
}

/**
 * 「发布」统一入口（父页的悬浮「+」/ 桌面分区标题按钮都走这里）：
 * 帖子视图把活交回父页的全屏编辑器；失物 / 招领视图直接开登记弹窗，
 * 类型预置成当前分区（在「招领」里点发布，默认就是发一条招领）。
 */
function openCreate() {
  if (!isLostMode.value) {
    emit('compose')
    return
  }
  if (isGuestMode()) {
    void promptLogin(lostType.value === 'lost' ? '发布寻物启事' : '发布失物招领')
    return
  }
  dialogsRef.value?.openCreate(lostType.value)
}

/** 外部指定分区（深链用：老地址 /student/lost-found 落地即选中「失物」） */
function setMode(c: string) {
  if (!chips.some(x => x.value === c)) return
  if (category.value === c) {
    void refresh()
    return
  }
  setCategory(c)
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

defineExpose({ refresh, openCreate, setMode, mode: category })
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
  min-width: 0;
}
.cfeed-time, .cfeed-source { flex-shrink: 0; }
.cfeed-source { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cfeed-dot { color: #d0d5dd; flex-shrink: 0; }
.cfeed-acts { display: flex; gap: 12px; margin-left: auto; padding-left: 6px; }
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
