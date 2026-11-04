<template>
  <div class="ffeed">
    <!-- ============ 游客态 ============
         关注流整条链路都要登录态（关注关系 + 帖子可见性），游客进来只给一个明确入口，
         不发请求、也不渲染骨架屏 —— 否则会先闪一下「没有动态」，像是内容丢了。 -->
    <div v-if="guest" class="ffeed-state">
      <p class="ffeed-state-title">登录后查看关注动态</p>
      <p class="ffeed-state-desc">关注同学与老师，他们的新帖子会按时间排在这里</p>
      <button type="button" class="ffeed-state-btn" @click="promptLogin('查看关注动态')">去登录</button>
    </div>

    <template v-else>
      <!-- ============ ① 关注的人（横排头像） ============
           参考稿里是横向滑动的圆形头像条：头像是「我关注了谁」的最短表达，
           比一列名单省屏幕，也比纯文字更像「人」。
           排序：最近发过动态的人排前面 —— 关注流页面里，用户关心的是「谁还在更新」。
           红点 = 24 小时内有新动态（用已加载的动态推算，不额外造一个未读表）。 -->
      <section v-if="people.length" class="ffeed-people" aria-label="我关注的人">
        <button
          v-for="u in sortedPeople"
          :key="u.id"
          type="button"
          class="ffeed-person"
          :aria-label="`查看 ${u.name} 的主页`"
          @click="emit('open-user', u.id)"
        >
          <span class="ffeed-person-face">
            <el-avatar :size="52" :src="u.avatar || undefined" :style="{ background: avatarBg(u.id) }">
              {{ (u.name || '同').slice(0, 1) }}
            </el-avatar>
            <i v-if="activeIds.has(u.id)" class="ffeed-person-dot" aria-label="24 小时内有新动态" />
          </span>
          <span class="ffeed-person-name">{{ u.name }}</span>
        </button>
      </section>

      <!-- ============ ② 分区标题 ============ -->
      <div v-if="people.length" class="ffeed-section">
        <h3 class="ffeed-section-title">关注动态</h3>
        <span v-if="posts.length" class="ffeed-section-count">{{ posts.length }}{{ reachedEnd ? '' : '+' }} 条</span>
      </div>

      <!-- ============ ③ 动态卡片 ============ -->
      <p v-if="loading && !posts.length" class="ffeed-tip">加载中…</p>

      <div v-else-if="failed" class="ffeed-state">
        <p class="ffeed-state-title">动态加载失败</p>
        <p class="ffeed-state-desc">网络或服务暂时不可用，点下面重新试一次</p>
        <button type="button" class="ffeed-state-btn" @click="refresh">重新加载</button>
      </div>

      <template v-else-if="posts.length">
        <article
          v-for="p in posts"
          :key="p.id"
          class="ffeed-card"
          role="link"
          tabindex="0"
          @click="emit('open', p)"
          @keydown.enter.prevent="emit('open', p)"
        >
          <!-- 作者行：头像 / 昵称 / 分区。点头像或昵称进个人主页，点其它区域进帖子详情 -->
          <header class="ffeed-author">
            <button
              type="button"
              class="ffeed-author-hit"
              :aria-label="`查看 ${p.author_name || '同学'} 的主页`"
              @click.stop="emit('open-user', p.student_id)"
            >
              <el-avatar
                :size="34"
                :src="p.author_avatar || undefined"
                :style="{ background: avatarBg(p.student_id) }"
              >{{ (p.author_name || '同').slice(0, 1) }}</el-avatar>
              <span class="ffeed-author-name">{{ p.author_name || '同学' }}</span>
            </button>
            <span class="ffeed-author-cat">{{ p.category }}</span>
          </header>

          <h4 class="ffeed-card-title">{{ p.title }}</h4>
          <p v-if="excerpt(p)" class="ffeed-card-text">{{ excerpt(p) }}</p>

          <!-- 配图：1 张按单图给宽幅比例；2 张两列；3 张及以上三列，
               第 3 张右上角压一枚「共 N 张」—— 多于 3 张时点进详情看全量，
               列表里铺满九宫格会把下一条动态推到屏幕外。 -->
          <div v-if="p.images?.length" class="ffeed-grid" :class="gridClass(p.images.length)">
            <span v-for="(img, i) in p.images.slice(0, 3)" :key="img + i" class="ffeed-cell">
              <img :src="img" alt="" loading="lazy" />
              <i v-if="i === 2 && p.images.length > 3" class="ffeed-more">共{{ p.images.length }}张</i>
            </span>
          </div>

          <footer class="ffeed-foot">
            <span class="ffeed-foot-time">{{ postTimeLabel(p.created_at) }}</span>
            <div class="ffeed-foot-acts">
              <span class="ffeed-act" :aria-label="`评论 ${p.comment_count} 条`">
                <el-icon><ChatDotRound /></el-icon><span>{{ p.comment_count }}</span>
              </span>
              <span class="ffeed-act" :class="{ 'is-liked': p.liked }" :aria-label="`赞 ${p.like_count} 个`">
                <el-icon><StarFilled v-if="p.liked" /><Star v-else /></el-icon><span>{{ p.like_count }}</span>
              </span>
            </div>
          </footer>
        </article>

        <!-- 触底哨兵：滚到这里自动翻页，不摆「加载更多」按钮 -->
        <div ref="sentinelRef" class="ffeed-sentinel" aria-hidden="true" />
        <p v-if="loading" class="ffeed-tip">加载中…</p>
        <p v-else-if="reachedEnd" class="ffeed-tip is-end">没有更多了</p>
      </template>

      <!-- ============ ④ 空态：分「没关注人」与「关注的人没发帖」两种 ============
           这两种情况的下一步动作完全不同：前者要去关注人，后者该去社区找话题。
           合成一句「暂无内容」会把用户卡在原地。 -->
      <div v-else class="ffeed-state">
        <template v-if="!people.length">
          <p class="ffeed-state-title">还没有关注任何人</p>
          <p class="ffeed-state-desc">关注同学或老师后，他们发的帖子会按时间出现在这里</p>
          <button type="button" class="ffeed-state-btn" @click="goDiscoverPeople">去发现同学</button>
        </template>
        <template v-else>
          <p class="ffeed-state-title">关注的人还没发过帖子</p>
          <p class="ffeed-state-desc">你关注的 {{ people.length }} 位同学 / 老师都还没更新，可以去社区转转</p>
          <button type="button" class="ffeed-state-btn" @click="emit('browse')">去交流社区</button>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * 「关注」页签（校园资讯 · 关注流）。
 *
 * 数据源两路，都是既有接口，不新增表：
 *   ① 关注的人 = /social/contacts?tab=following（消息页通讯录同一份关注关系）；
 *   ② 动态内容 = /community/following（我关注的人发的帖子，按时间倒序分页）。
 *
 * 为什么单独成组件：它是「人 → 帖子」而不是「栏目 → 资讯」，
 * 版式（头像条 + 大卡片 + 九宫格配图）和 CommunityFeed 的紧凑行不是一套东西。
 *
 * 用法：<FollowingFeed @open="openPostDetail" @open-user="openUserHomepage" @browse="..." />
 *   - 父页在发帖 / 点赞 / 关注变化后调 ref.refresh() 重拉第一页。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Star, StarFilled } from '@element-plus/icons-vue'
import { getFollowingPosts, type CommunityPost } from '@/api/community'
import { getContacts, type ContactUser } from '@/api/social'
import { isGuestMode } from '@/utils/guest'
import { promptLogin } from '@/utils/loginGate'
import { parseServerTime } from '@/utils/datetime'

const emit = defineEmits<{
  (e: 'open', post: CommunityPost): void
  (e: 'open-user', userId: number): void
  /** 空态引导：父页据此切到「交流社区」页签 */
  (e: 'browse'): void
}>()

const router = useRouter()

const PAGE_SIZE = 10
/** 头像条一次取多少人：够铺满一屏横向滑动即可，再多也不会有人一路滑到底 */
const PEOPLE_LIMIT = 100
const DAY_MS = 86_400_000

const people = ref<ContactUser[]>([])
const posts = ref<CommunityPost[]>([])
/** 首帧就进「加载中」：否则挂载后第一次渲染会先闪一下空态再变成列表 */
const loading = ref(true)
const failed = ref(false)
const page = ref(1)
const reachedEnd = ref(false)
const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const guest = computed(() => isGuestMode())

/** 头像底色：按 user_id 取模落到一组柔和色上，同一个人每次进来颜色一致（与社区详情同一套） */
const AVATAR_COLORS = ['#dbeafe', '#e0e7ff', '#fce7f3', '#dcfce7', '#fef3c7', '#fee2e2', '#ede9fe', '#cffafe']
function avatarBg(id: number | null | undefined) {
  return AVATAR_COLORS[Math.abs(Number(id) || 0) % AVATAR_COLORS.length]
}

/** 每位作者最新一条动态的时间：头像条排序与红点判定都读它 */
const latestByAuthor = computed(() => {
  const map = new Map<number, number>()
  for (const p of posts.value) {
    // 后端时间是不带时区的 UTC，必须走统一解析，否则「刚刚」会被算成 8 小时前
    const t = parseServerTime(p.created_at)
    if (!t) continue
    const prev = map.get(p.student_id) ?? 0
    if (t > prev) map.set(p.student_id, t)
  }
  return map
})

/** 最近更新的人排前面；没发过的保持接口返回顺序（稳定排序，不会来回跳） */
const sortedPeople = computed(() => {
  const list = [...people.value]
  return list.sort((a, b) => (latestByAuthor.value.get(b.id) ?? 0) - (latestByAuthor.value.get(a.id) ?? 0))
})

/** 24 小时内有新动态的作者：头像右上角红点 */
const activeIds = computed(() => {
  const now = Date.now()
  const set = new Set<number>()
  latestByAuthor.value.forEach((t, id) => {
    if (now - t < DAY_MS) set.add(id)
  })
  return set
})

/** 摘要：接口在列表态已截断到 120 字，这里只把换行压成空格，避免行高被空行撑开 */
function excerpt(p: CommunityPost): string {
  const text = (p.content || '').replace(/\s+/g, ' ').trim()
  if (!text) return ''
  // 正文常以标题开头重复一遍，标题已经在上面单独展示了，这里去掉重复前缀
  const title = (p.title || '').trim()
  if (title && text.startsWith(title)) {
    return text.slice(title.length).replace(/^[。，,.!！?？:：\s]+/, '')
  }
  return text
}

function gridClass(count: number): string {
  if (count <= 1) return 'is-one'
  if (count === 2) return 'is-two'
  return 'is-three'
}

/**
 * 相对时间：刚刚 / N 分钟前 / 今天 HH:mm / 昨天 HH:mm / 前天 HH:mm / MM-DD。
 * 参考稿用的就是「昨天21:27」这种句式 —— 既有时效感，又给得到具体时刻。
 */
function postTimeLabel(iso: string | null): string {
  const t = parseServerTime(iso)
  if (Number.isNaN(t)) return ''
  const now = Date.now()
  const diff = now - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  const d = new Date(t)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const startOfToday = new Date()
  startOfToday.setHours(0, 0, 0, 0)
  const todayStart = startOfToday.getTime()
  if (t >= todayStart) return `${hh}:${mm}`
  if (t >= todayStart - DAY_MS) return `昨天${hh}:${mm}`
  if (t >= todayStart - 2 * DAY_MS) return `前天${hh}:${mm}`
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/* ---------- 数据 ---------- */

async function fetchPeople() {
  if (guest.value) { people.value = []; return }
  try {
    people.value = await getContacts({ tab: 'following', limit: PEOPLE_LIMIT })
  } catch {
    // 头像条是增强信息：取不到不影响动态列表，静默降级成「只显示动态」
    people.value = []
  }
}

async function fetchPage(target: number, append: boolean) {
  if (guest.value) {
    posts.value = []
    reachedEnd.value = true
    loading.value = false
    return
  }
  loading.value = true
  failed.value = false
  try {
    const list = await getFollowingPosts({ page: target, page_size: PAGE_SIZE })
    posts.value = append ? [...posts.value, ...list] : list
    page.value = target
    // 接口返回数组：不足一页就是到底
    reachedEnd.value = list.length < PAGE_SIZE
  } catch {
    if (!append) posts.value = []
    failed.value = true
    reachedEnd.value = true
    if (append) ElMessage.error('动态加载失败，请稍后重试')
  } finally {
    loading.value = false
    // 一页没铺满一屏时哨兵已在视口内，观察器不会二次回调，这里主动补一次
    void nextTick(ensureFill)
  }
}

/** 父页调用：重拉头像条与第一页（发帖、点赞、关注关系变化后） */
function refresh() {
  reachedEnd.value = false
  void fetchPeople()
  return fetchPage(1, false)
}

function loadMore() {
  if (loading.value || reachedEnd.value || !posts.value.length) return
  void fetchPage(page.value + 1, true)
}

/**
 * 补页：只在哨兵真的处在可视区域时追加。
 * 分页轨道（SwipePager）会把邻居页挂在视口左右两侧，
 * 那里同样「在文档流里」，不按水平位置排除就会替用户预加载下一屏。
 */
function ensureFill() {
  const el = sentinelRef.value
  if (!el) return
  if (loading.value || reachedEnd.value || !posts.value.length) return
  const r = el.getBoundingClientRect()
  if (r.right <= 0 || r.left >= window.innerWidth) return
  if (r.bottom > 0 && r.top < window.innerHeight) loadMore()
}

function setupObserver() {
  if (observer || typeof IntersectionObserver === 'undefined') return
  const el = sentinelRef.value
  if (!el) return
  observer = new IntersectionObserver(
    (entries) => { if (entries.some(e => e.isIntersecting)) loadMore() },
    { root: null, rootMargin: '0px', threshold: 0 },
  )
  observer.observe(el)
}

function goDiscoverPeople() {
  router.push({ path: '/student/messages/add' })
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
.ffeed { display: block; padding-bottom: 8px; }

/* ================= 头像条 ================= */
.ffeed-people {
  display: flex;
  gap: 14px;
  padding: 4px 0 14px;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.ffeed-people::-webkit-scrollbar { display: none; }

.ffeed-person {
  flex: 0 0 auto;
  width: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ffeed-person-face { position: relative; display: block; line-height: 0; }
.ffeed-person-face :deep(.el-avatar) {
  color: #1d2129;
  font-size: 18px;
  font-weight: 600;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(29, 33, 41, .06);
}
/* 红点：24 小时内有新动态。白描边让它在彩色头像上不糊成一团 */
.ffeed-person-dot {
  position: absolute;
  top: 0;
  right: 0;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #f53f3f;
  border: 2px solid #fff;
  box-sizing: content-box;
}
.ffeed-person-name {
  max-width: 56px;
  font-size: 11px;
  line-height: 1.3;
  color: #4e5969;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ================= 分区标题 ================= */
.ffeed-section {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 2px 0 6px;
}
.ffeed-section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1d2129;
}
.ffeed-section-count { font-size: 11px; color: #a8b0bd; }

/* ================= 动态卡片 ================= */
.ffeed-card {
  padding: 14px 0 16px;
  border-top: 1px solid #f2f3f5;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ffeed-card:first-of-type { border-top: none; }
.ffeed-card:active { background: rgba(29, 33, 41, .015); }

.ffeed-author {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.ffeed-author-hit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ffeed-author-hit :deep(.el-avatar) {
  color: #1d2129;
  font-size: 14px;
  font-weight: 600;
}
.ffeed-author-name {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 分区标签：跟着作者名右端，与参考稿「昵称 + Lv」同一位置，
   这里放的是真实信息（帖子分区），不额外造等级数字 */
.ffeed-author-cat {
  flex-shrink: 0;
  padding: 0 5px;
  border: 1px solid #e5e6eb;
  border-radius: 4px;
  font-size: 10px;
  line-height: 15px;
  color: #86909c;
}

.ffeed-card-title {
  margin: 10px 0 0;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.42;
  color: #1d2129;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ffeed-card-text {
  margin: 7px 0 0;
  font-size: 14px;
  line-height: 1.62;
  color: #4e5969;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}

/* ================= 配图 ================= */
.ffeed-grid {
  display: grid;
  gap: 4px;
  margin-top: 10px;
  border-radius: 8px;
  overflow: hidden;
}
.ffeed-grid.is-one { grid-template-columns: 1fr; width: 68%; }
.ffeed-grid.is-two { grid-template-columns: repeat(2, 1fr); width: 82%; }
.ffeed-grid.is-three { grid-template-columns: repeat(3, 1fr); }
.ffeed-cell {
  position: relative;
  display: block;
  aspect-ratio: 1 / 1;
  background: #f4f5f7;
  overflow: hidden;
}
.ffeed-grid.is-one .ffeed-cell { aspect-ratio: 4 / 3; }
.ffeed-cell img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ffeed-more {
  position: absolute;
  top: 6px;
  right: 6px;
  padding: 0 6px;
  border-radius: 9px;
  background: rgba(0, 0, 0, .55);
  color: #fff;
  font-size: 10px;
  font-style: normal;
  line-height: 17px;
}

/* ================= 卡片底部 ================= */
.ffeed-foot {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  font-size: 12px;
  color: #86909c;
}
.ffeed-foot-time { flex-shrink: 0; }
.ffeed-foot-acts {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-left: auto;
}
.ffeed-act { display: inline-flex; align-items: center; gap: 4px; }
.ffeed-act.is-liked { color: #f53f3f; }

/* ================= 空态 / 失败态 ================= */
.ffeed-state {
  padding: 46px 24px 54px;
  text-align: center;
}
.ffeed-state-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}
.ffeed-state-desc {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: #86909c;
}
.ffeed-state-btn {
  margin-top: 16px;
  height: 32px;
  padding: 0 18px;
  border: none;
  border-radius: 16px;
  background: #1d2129;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ffeed-state-btn:active { opacity: .82; }

.ffeed-tip {
  padding: 14px 0;
  text-align: center;
  font-size: 12px;
  color: #a8b0bd;
}
.ffeed-tip.is-end { color: #c3c9d4; }

/* 触底哨兵：1px 高，看不见但能被 IntersectionObserver 观察到 */
.ffeed-sentinel { height: 1px; }

/* 桌面端（宽屏里被复用时）收一收：卡片不做通栏，读起来才不散 */
@media (min-width: 768px) {
  .ffeed { max-width: 720px; margin: 0 auto; }
  .ffeed-grid.is-one { width: 46%; }
  .ffeed-grid.is-two { width: 60%; }
}
</style>
