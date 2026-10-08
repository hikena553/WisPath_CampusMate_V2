<template>
  <div ref="rootRef" class="growth-dashboard">
    <!-- Hero：问候 + 周次/日期 + 下一节课 + 成长指数 -->
    <section class="gd-hero">
      <div class="gd-hero-top">
        <div class="gd-hero-hello">
          <div class="gd-greet">{{ greeting }}，同学</div>
        </div>
        <div class="gd-hero-actions">
          <button v-if="editMode" type="button" class="gd-mini-btn" @click="resetCards">恢复默认</button>
          <button
            type="button"
            class="gd-mini-btn"
            :class="{ 'gd-mini-btn--on': editMode }"
            @click="editMode = !editMode"
          >{{ editMode ? '完成' : '编辑' }}</button>
        </div>
      </div>

      <div class="gd-hero-main">
        <!-- 下一节课卡：整卡可点推入课程表（查看全部课程入口移入此处）；编辑卡片模式下禁用跳转 -->
        <div
          class="gd-next"
          :class="{ 'is-link': !editMode }"
          :role="editMode ? undefined : 'button'"
          :tabindex="editMode ? -1 : 0"
          :aria-label="editMode ? undefined : '查看全部课程'"
          @click="openSchedule"
          @keydown.enter.prevent="openSchedule"
        >
          <div class="gd-next-label-row">
            <div class="gd-next-label">下一节课</div>
            <span class="gd-next-more">查看全部课程<el-icon :size="11"><ArrowRight /></el-icon></span>
          </div>
          <!-- 课程数据加载中：骨架占位（尺寸对齐 time/name/meta），避免先闪「今日没有课程安排」再出内容 -->
          <template v-if="coursesLoading">
            <div class="gd-skel gd-next-skel-time"></div>
            <div class="gd-skel gd-next-skel-name"></div>
            <div class="gd-skel gd-next-skel-meta"></div>
          </template>
          <template v-else-if="nextCourse">
            <div class="gd-next-time">{{ timeLabel(nextCourse.start_period) }}</div>
            <div class="gd-next-name">{{ nextCourse.name }}</div>
            <div class="gd-next-meta">
              <span>{{ nextCourse.location }}</span>
              <span v-if="nextCourse.teacher"> · {{ nextCourse.teacher }}</span>
            </div>
          </template>
          <div v-else class="gd-next-none">{{ nextEmptyText }}</div>
        </div>

        <div class="gd-ring-wrap">
          <svg class="gd-ring" viewBox="0 0 120 120" role="img" :aria-label="`成长指数 ${score} 分`">
            <defs>
              <linearGradient id="gdRingGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#409eff" />
                <stop offset="100%" stop-color="#2f7fd8" />
              </linearGradient>
            </defs>
            <circle class="gd-ring-track" cx="60" cy="60" r="52" fill="none" stroke-width="10" />
            <circle
              class="gd-ring-progress"
              cx="60" cy="60" r="52" fill="none" stroke-width="10" stroke-linecap="round"
              :stroke-dasharray="`${(score / 100) * 326.7} 326.7`"
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div class="gd-ring-center">
            <span class="gd-ring-value">{{ score }}</span>
            <span class="gd-ring-label">成长指数</span>
          </div>
        </div>
      </div>
    </section>

    <!-- KPI 行 -->
    <section class="gd-kpi-row">
      <KpiStat label="今日课程" :value="coursesLoading ? '--' : todayCourses.length" :unit="coursesLoading ? '' : '门'" tone="primary" />
      <KpiStat label="待办" :value="pendingTodos" unit="项" :tone="pendingTodos > 0 ? 'warning' : 'neutral'" />
      <KpiStat label="综合评分" :value="score || '--'" />
      <KpiStat label="成长记录" :value="profile?.total_records ?? 0" unit="条" />
    </section>

    <!-- 可配置卡片区（编辑态可排序 / 显隐） -->
    <div class="gd-stack">
      <!-- 今日课程卡已删除：课程表入口在 Hero「下一节课」卡（查看全部课程），
           今日课次与下一节课信息也都在 Hero/KPI 中，无需重复成卡 -->

      <!-- AI 主动发现 -->
      <section class="gd-card" data-card="ai" :class="cardClass('ai')" :style="{ order: orderOf('ai') }" v-show="show('ai')">
        <div v-if="editMode" class="gd-veil" aria-hidden="true"></div>
        <CardToolbar
          v-if="editMode" :can-up="canUp('ai')" :can-down="canDown('ai')" :hidden="!isVisible('ai')"
          @up="move('ai', -1)" @down="move('ai', 1)" @toggle="toggle('ai')"
        />
        <div class="gd-head">
          <h3 class="gd-title gd-title-icon">
            <el-icon class="gd-title-glyph" :size="17"><MagicStick /></el-icon>AI 主动发现
          </h3>
          <button type="button" class="gd-icon-btn" :aria-label="'刷新 AI 洞察'" @click="loadDiscover">
            <el-icon :size="14" :class="{ 'is-loading': discoverLoading }"><Refresh /></el-icon>
          </button>
        </div>
        <!-- LLM 洞察引导句：仅在有待处理事项时出现；容器高度固定，
             异步拿到洞察时不改变卡片高度（此前的高度跳变曾表现为抽搐） -->
        <div v-if="proactiveActions.length" class="gd-ai-insight">
          <el-icon class="gd-ai-insight-ico" :size="13"><MagicStick /></el-icon>
          <span v-if="insight" class="gd-ai-insight-text">{{ insight }}</span>
          <span v-else-if="insightPending" class="gd-skel gd-ai-insight-skel" aria-hidden="true"></span>
        </div>
        <!-- 加载中且尚无数据：首帧即骨架占位，
             避免「空态文案 → 空列表 → 行内容」连续三次高度变化造成卡片抽搐 -->
        <div v-if="discoverLoading && !proactiveActions.length" class="gd-insight-list">
          <div class="gd-skel gd-ai-skel-row"></div>
          <div class="gd-skel gd-ai-skel-row"></div>
        </div>
        <!-- 空态只在首次加载真正完成后才出现，避免先闪一下「状态良好」又被行内容顶掉 -->
        <div v-else-if="discoverLoaded && !proactiveActions.length" class="gd-ai-empty">
          <el-icon class="gd-ai-empty-icon" :size="17"><CircleCheckFilled /></el-icon>
          <span>状态良好，AI 持续守护你的成长</span>
        </div>
        <div v-else class="gd-insight-list">
          <div
            v-for="act in proactiveActions"
            :key="act.trigger + '-' + act.student_id"
            class="gd-insight-row"
          >
            <span class="gd-pill" :class="pillClass(act.priority)">{{ actionLabel(act.priority) }}</span>
            <p class="gd-insight-text"><span class="gd-insight-strong">{{ act.title }}</span> · {{ act.content }}</p>
          </div>
        </div>
      </section>

      <!-- 我的学业卡已删除：课程表入口在 Hero「下一节课」卡（查看全部课程），成绩分析/成长轨迹在快捷空间 -->

      <!-- 五维成长（默认展开，点标题行可收起） -->
      <section class="gd-card" data-card="dims" :class="cardClass('dims')" :style="{ order: orderOf('dims') }" v-show="show('dims')">
        <div v-if="editMode" class="gd-veil" aria-hidden="true"></div>
        <CardToolbar
          v-if="editMode" :can-up="canUp('dims')" :can-down="canDown('dims')" :hidden="!isVisible('dims')"
          @up="move('dims', -1)" @down="move('dims', 1)" @toggle="toggle('dims')"
        />
        <div class="gd-head">
          <h3 class="gd-title">五维成长</h3>
          <button
            type="button"
            class="gd-collapse-btn"
            :aria-expanded="!dimsCollapsed"
            aria-label="展开或收起五维成长"
            @click="dimsCollapsed = !dimsCollapsed"
          >
            <span class="gd-cap">综合评分构成</span>
            <el-icon class="gd-collapse-ico" :class="{ 'is-collapsed': dimsCollapsed }" :size="14"><ArrowDown /></el-icon>
          </button>
        </div>
        <ul v-if="radarDims.length && !dimsCollapsed" class="gd-dim-list">
          <li v-for="d in radarDims" :key="d.name" class="gd-dim-row">
            <span class="gd-dim-name">{{ d.name }}</span>
            <span class="gd-dim-track">
              <span class="gd-dim-fill" :style="{ width: d.value + '%', opacity: dimOpacity(d.value) }"></span>
            </span>
            <span class="gd-dim-value">{{ Math.round(d.value) }}</span>
          </li>
        </ul>
        <!-- 画像尚未返回：骨架占位（行高对齐真实五维行），避免先闪「暂无数据」再撑开 5 行 -->
        <div v-else-if="!dimsCollapsed && !profileLoaded" class="gd-dim-skel">
          <div v-for="i in 5" :key="i" class="gd-skel gd-dim-skel-row"></div>
        </div>
        <p v-else-if="!dimsCollapsed" class="gd-empty-line">暂无五维数据，完善成长记录后自动生成</p>
      </section>

      <!-- 快捷空间 -->
      <section class="gd-card" data-card="space" :class="cardClass('space')" :style="{ order: orderOf('space') }" v-show="show('space')">
        <div v-if="editMode" class="gd-veil" aria-hidden="true"></div>
        <CardToolbar
          v-if="editMode" :can-up="canUp('space')" :can-down="canDown('space')" :hidden="!isVisible('space')"
          @up="move('space', -1)" @down="move('space', 1)" @toggle="toggle('space')"
        />
        <div class="gd-head">
          <h3 class="gd-title">快捷空间</h3>
          <span class="gd-cap">常用服务</span>
        </div>
        <div class="gd-space-grid">
          <!-- 成绩分析 / 成长轨迹：从「我的学业」移入，走 open 事件推入学业中心对应子页（非路由跳转） -->
          <button type="button" class="gd-space-item" @click="emit('open', 'grades')">
            <span class="gd-space-icon"><el-icon :size="21"><DataLine /></el-icon></span>
            <span class="gd-space-label">成绩分析</span>
          </button>
          <button type="button" class="gd-space-item" @click="emit('open', 'growth')">
            <span class="gd-space-icon"><el-icon :size="21"><TrendCharts /></el-icon></span>
            <span class="gd-space-label">成长轨迹</span>
          </button>
          <button type="button" class="gd-space-item" @click="go('/student/plan')">
            <span class="gd-space-icon"><el-icon :size="21"><Calendar /></el-icon></span>
            <span class="gd-space-label">学习计划</span>
          </button>
          <button type="button" class="gd-space-item" @click="go('/student/portfolio')">
            <span class="gd-space-icon"><el-icon :size="21"><Collection /></el-icon></span>
            <span class="gd-space-label">作品集</span>
          </button>
          <!-- 成长档案图标由 TrendCharts 改为 FolderOpened：与相邻的「成长轨迹」区分（原文/图重复易混淆） -->
          <button type="button" class="gd-space-item" @click="go('/student/growth')">
            <span class="gd-space-icon"><el-icon :size="21"><FolderOpened /></el-icon></span>
            <span class="gd-space-label">成长档案</span>
          </button>
          <button type="button" class="gd-space-item" @click="go('/student/emotion')">
            <span class="gd-space-icon"><el-icon :size="21"><FirstAidKit /></el-icon></span>
            <span class="gd-space-label">情绪树洞</span>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  TrendCharts, Collection, MagicStick, Refresh,
  CircleCheckFilled, Calendar, DataLine, ArrowRight, ArrowDown, FirstAidKit, FolderOpened
} from '@element-plus/icons-vue'
import { getGrowthProfile, type GrowthProfile } from '@/api/growth'
import { fetchProactiveFeed, fetchProactiveInsight, type ProactiveAction } from '@/api/agent'
import { getToday, type TodayTask } from '@/api/plan'
import { useAuthStore } from '@/stores/auth'
import type { Course } from '@/types'
import { studentDataCache } from '@/utils/studentDataCache'
import KpiStat from './dashboard/KpiStat.vue'
import CardToolbar from './dashboard/CardToolbar.vue'

const props = withDefaults(defineProps<{
  courses?: Course[]
  currentWeek?: number
  periodTimes?: Record<number, string>
  isHoliday?: boolean
  /** 课程数据是否仍在加载：为 true 时 Hero/今日课程显示骨架占位而非空态文案 */
  coursesLoading?: boolean
}>(), {
  courses: () => [],
  currentWeek: 1,
  periodTimes: () => ({}),
  isHoliday: false,
  coursesLoading: false,
})

const emit = defineEmits<{ (e: 'open', tab: 'schedule' | 'grades' | 'growth'): void }>()
const router = useRouter()
const auth = useAuthStore()
// 数据初值取自模块级缓存：从其它页签切回驾驶舱时组件会重建，命中缓存即可首帧渲染真实内容，
// 不再出现「骨架 → 内容」的高度变化（否则下方卡片会被推动，看起来像抽搐）；挂载后仍静默刷新
const discoverLoading = ref(!studentDataCache.actions)
/** 首次请求是否已完成：空态只在完成后出现，避免未加载完就先弹「状态良好」 */
const discoverLoaded = ref(!!studentDataCache.actions)
const profile = ref<GrowthProfile | null>(studentDataCache.profile)
/** 画像是否已加载完成：五维成长默认展开，用它区分「还没回来」与「确实没有数据」 */
const profileLoaded = ref(!!studentDataCache.profile)
const proactiveActions = ref<ProactiveAction[]>(studentDataCache.actions ?? [])
/** LLM 个性化洞察（异步补充，不阻塞卡片；服务端缓存 30 分钟） */
const insight = ref<string>(studentDataCache.insight ?? '')
const insightPending = ref(false)
const todayTasks = ref<TodayTask[]>(studentDataCache.tasks ?? [])
/** 五维成长默认展开（点标题行可收起） */
const dimsCollapsed = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const score = computed(() => profile.value?.total_score ?? 0)

// ===== 今日课程 / 下一节课（数据来自 SchedulePage 下传）=====
const now = new Date()
const todayDayN = now.getDay() === 0 ? 7 : now.getDay()
const nowMin = now.getHours() * 60 + now.getMinutes()

function toMin(p: number): number {
  const t = props.periodTimes[p]
  if (!t) return 0
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}
function timeLabel(p: number) { return props.periodTimes[p] || '--:--' }

const todayCourses = computed(() =>
  props.courses
    .filter(c => c.day_of_week === todayDayN && props.currentWeek >= c.week_start && props.currentWeek <= c.week_end)
    .slice()
    .sort((a, b) => a.start_period - b.start_period)
)
const nextCourse = computed(() =>
  props.isHoliday ? null : (todayCourses.value.find(c => toMin(c.start_period) >= nowMin) || null)
)
const nextEmptyText = computed(() => {
  if (props.isHoliday) return '假期中，好好休息～'
  if (!todayCourses.value.length) return '今日没有课程安排'
  return '今日课程已结束'
})

const greeting = computed(() => {
  const h = now.getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const pendingTodos = computed(() => todayTasks.value.filter(t => !t.checked_today && t.status !== 'done').length)

/** 五维：单一品牌色不同明度步进，不使用多色系 */
const radarDims = computed(() => {
  const src = profile.value?.radar ?? []
  return src.map(d => ({ name: d.name, value: Math.max(0, Math.min(100, d.value)) }))
})

// ===== 卡片配置化：显隐 / 排序 + 本地持久化 =====
// 默认顺序：快捷空间 → AI 主动发现 → 五维成长（今日课程卡已删除）
type CardId = 'ai' | 'space' | 'dims'
const CARD_IDS: CardId[] = ['space', 'ai', 'dims']
const cardOrder = ref<CardId[]>([...CARD_IDS])
const hiddenIds = ref<CardId[]>([])
const editMode = ref(false)
// 存储键带版本号：默认卡片结构（增删卡/默认顺序）变更时升级版本，
// 旧键整体作废回落新默认，避免浏览器里残留的旧排序盖住新布局。
// 注：仅删除卡片时无需升版——loadCards 的 isCardId 过滤会自动剔除已删除的 id，
// 并按原相对顺序保留用户自定义排序
const storageKey = `cm.dashboard.cards.v2.${auth.user?.id ?? 'anon'}`

function isCardId(v: unknown): v is CardId {
  return typeof v === 'string' && (CARD_IDS as string[]).includes(v)
}
function loadCards() {
  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) return
    const parsed = JSON.parse(raw) as { order?: unknown; hidden?: unknown }
    if (Array.isArray(parsed.order)) {
      const valid = parsed.order.filter(isCardId)
      const missing = CARD_IDS.filter(id => !valid.includes(id))
      cardOrder.value = [...valid, ...missing]
    }
    if (Array.isArray(parsed.hidden)) hiddenIds.value = parsed.hidden.filter(isCardId)
  } catch { /* ignore */ }
}
// 首帧前就应用本地保存的排序/显隐：原先放在 onMounted 里会在挂载后第二次渲染才生效，
// 卡片位置与显隐会当场跳变（与页面切换动画叠加后尤其明显）
loadCards()
function saveCards() {
  try { localStorage.setItem(storageKey, JSON.stringify({ order: cardOrder.value, hidden: hiddenIds.value })) } catch { /* ignore */ }
}
function orderOf(id: CardId) { return cardOrder.value.indexOf(id) + 1 }
function isVisible(id: CardId) { return !hiddenIds.value.includes(id) }
function show(id: CardId) { return editMode.value || isVisible(id) }
function cardClass(id: CardId) {
  return { 'gd-editing': editMode.value, 'gd-card--hidden': editMode.value && !isVisible(id) }
}
function canUp(id: CardId) { return cardOrder.value.indexOf(id) > 0 }
function canDown(id: CardId) { return cardOrder.value.indexOf(id) < cardOrder.value.length - 1 }
const prefersReducedMotion = typeof window !== 'undefined' && typeof window.matchMedia === 'function'
  ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
  : false

function cardEls(): HTMLElement[] {
  if (!rootRef.value) return []
  return Array.from(rootRef.value.querySelectorAll<HTMLElement>('[data-card]'))
}

async function move(id: CardId, dir: number) {
  const arr = [...cardOrder.value]
  const i = arr.indexOf(id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= arr.length) return

  // FLIP：先记录旧位置 → 改变顺序 → 下一帧测量新位置 → 反向后过渡回位
  const els = cardEls()
  const first = new Map<HTMLElement, DOMRect>()
  els.forEach(el => first.set(el, el.getBoundingClientRect()))

  ;[arr[i], arr[j]] = [arr[j], arr[i]]
  cardOrder.value = arr
  saveCards()

  if (prefersReducedMotion) return
  await nextTick()

  els.forEach(el => {
    const f = first.get(el)
    if (!f) return
    const l = el.getBoundingClientRect()
    const dx = f.left - l.left
    const dy = f.top - l.top
    if (!dx && !dy) return
    el.style.transition = 'none'
    el.style.transform = `translate(${dx}px, ${dy}px)`
    void el.offsetHeight
    el.style.transition = 'transform 0.32s cubic-bezier(0.16, 1, 0.3, 1)'
    el.style.transform = ''
  })

  window.setTimeout(() => {
    els.forEach(el => { el.style.transition = '' })
  }, 380)
}
function toggle(id: CardId) {
  hiddenIds.value = hiddenIds.value.includes(id)
    ? hiddenIds.value.filter(x => x !== id)
    : [...hiddenIds.value, id]
  saveCards()
}
function resetCards() {
  cardOrder.value = [...CARD_IDS]
  hiddenIds.value = []
  saveCards()
}

function dimOpacity(v: number) {
  return 0.55 + (v / 100) * 0.45
}

function go(p: string) { router.push(p) }
/** 下一节课卡（查看全部课程入口）：整卡点击推入课程表；卡片编辑模式下不跳转 */
function openSchedule() { if (!editMode.value) emit('open', 'schedule') }
function pillClass(p: number) {
  return p >= 80 ? 'gd-pill-danger' : p >= 60 ? 'gd-pill-warning' : 'gd-pill-primary'
}
function actionLabel(p: number) { return p >= 80 ? '重点关注' : p >= 60 ? '值得关注' : '温馨提醒' }

async function loadOverview() {
  try {
    profile.value = await getGrowthProfile()
    studentDataCache.profile = profile.value
  } catch { /* ignore：保留缓存/上次数据，不清空 */ }
  finally { profileLoaded.value = true }
}
async function loadDiscover() {
  discoverLoading.value = true
  try {
    const feed = await fetchProactiveFeed()
    proactiveActions.value = feed.actions.filter(a => a.target_role === 'student')
    studentDataCache.actions = proactiveActions.value

    // 动作指纹变化（如待办已完成、临考提醒换了一条）说明旧洞察已经过时，作废后重新生成
    const sig = proactiveActions.value.map(a => `${a.trigger}:${a.title}`).sort().join('|')
    if (studentDataCache.insightSig !== sig) {
      studentDataCache.insightSig = sig
      studentDataCache.insight = null
      insight.value = ''
    }

    if (feed.insight) {
      insight.value = feed.insight
      studentDataCache.insight = feed.insight
    } else if (proactiveActions.value.length) {
      // 服务端缓存未命中：后台补一次 LLM 洞察（不阻塞卡片，失败保持规则文案）
      void loadInsight()
    }
  } catch {
    // 失败时保留缓存/上次结果（而非清空），避免卡片高度凭空变化
    if (!proactiveActions.value.length && studentDataCache.actions) proactiveActions.value = studentDataCache.actions
  }
  finally { discoverLoading.value = false; discoverLoaded.value = true }
}

/** 拉取 LLM 洞察：结果写入缓存供二次进入首帧显示；拿不到就不显示（占位区高度固定，不会跳变） */
async function loadInsight() {
  if (insight.value || insightPending.value) return
  insightPending.value = true
  try {
    const text = await fetchProactiveInsight()
    if (text) {
      insight.value = text
      studentDataCache.insight = text
    }
  } finally {
    insightPending.value = false
  }
}
async function loadTodayTasks() {
  try {
    todayTasks.value = await getToday()
    studentDataCache.tasks = todayTasks.value
  } catch {
    if (!todayTasks.value.length && studentDataCache.tasks) todayTasks.value = studentDataCache.tasks
  }
}

onMounted(() => { loadOverview(); loadDiscover(); loadTodayTasks() })
</script>

<style scoped>
/* ===== 组件级 token（沿用全局品牌蓝，单一主色） ===== */
.growth-dashboard {
  --gd-primary: #409eff;
  --gd-primary-strong: #2f7fd8;
  --gd-primary-soft: #eaf3ff;
  --gd-primary-track: #e8eef7;
  --gd-ink: #1a1a2e;
  --gd-ink-2: #666666;
  --gd-ink-3: #999999;
  --gd-border: rgba(0, 0, 0, 0.06);
  --gd-muted: #f6f8fc;
  --gd-warning: #e6a23c;
  --gd-warning-soft: #fdf4e5;
  --gd-danger: #f56c6c;
  --gd-danger-soft: #fef0f0;
  --gd-radius-lg: 16px;
  --gd-radius-md: 12px;

  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ===== Hero ===== */
.gd-hero {
  background: linear-gradient(135deg, #eaf3ff 0%, #f4f9ff 100%);
  border: 1px solid var(--gd-border);
  border-radius: var(--gd-radius-lg);
  padding: 15px 14px;
}
.gd-hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.gd-greet { font-size: 18px; font-weight: 800; color: var(--gd-ink); letter-spacing: -0.02em; }

.gd-hero-actions { flex: none; display: inline-flex; align-items: center; gap: 6px; }
.gd-mini-btn {
  padding: 3px 11px; border-radius: 999px;
  border: 1px solid var(--gd-border); background: #ffffff;
  font-family: inherit; font-size: 11.5px; font-weight: 600; color: var(--gd-ink-2);
  cursor: pointer; transition: color .18s ease, border-color .18s ease, background-color .18s ease;
}
.gd-mini-btn:hover { color: var(--gd-primary); border-color: var(--gd-primary); }
.gd-mini-btn--on { background: var(--gd-primary); border-color: var(--gd-primary); color: #ffffff; }
.gd-mini-btn:focus-visible { outline: 2px solid var(--gd-primary); outline-offset: 2px; }

.gd-hero-main { display: flex; align-items: center; gap: 12px; }
.gd-next {
  flex: 1 1 auto; min-width: 0;
  background: #ffffff;
  border: 1px solid var(--gd-border);
  border-left: 4px solid var(--gd-primary);
  border-radius: var(--gd-radius-md);
  padding: 11px 13px;
}
/* 下一节课卡：整卡可点推入课程表（查看全部课程入口），编辑卡片模式恢复为静态卡 */
.gd-next.is-link {
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: transform .15s ease, box-shadow .18s ease, border-color .18s ease;
}
.gd-next.is-link:active { transform: scale(.985); box-shadow: 0 2px 10px rgba(47, 127, 216, 0.14); }
.gd-next.is-link:focus-visible { outline: 2px solid var(--gd-primary); outline-offset: 2px; }
.gd-next-label-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.gd-next-label { font-size: 11px; font-weight: 600; color: var(--gd-primary); letter-spacing: 0.02em; }
.gd-next-more { flex: none; display: inline-flex; align-items: center; gap: 1px; font-size: 11px; font-weight: 600; color: var(--gd-primary); white-space: nowrap; }
.gd-next-time { margin-top: 3px; font-size: 20px; font-weight: 800; color: var(--gd-ink); letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.gd-next-name {
  margin-top: 1px; font-size: 14px; font-weight: 600; color: var(--gd-ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.gd-next-meta {
  margin-top: 2px; font-size: 11.5px; color: var(--gd-ink-3);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.gd-next-none { margin-top: 6px; font-size: 13px; color: var(--gd-ink-2); }

/* ===== 课程数据加载骨架（Hero 下一节课 / 今日课程卡）：占位条尺寸对齐真实内容，卡片高度不跳变 ===== */
.gd-skel {
  border-radius: 6px;
  background: linear-gradient(90deg, #eef2f8 25%, #e2e9f3 50%, #eef2f8 75%);
  background-size: 200% 100%;
  animation: gd-skel-shimmer 1.2s ease-in-out infinite;
}
@keyframes gd-skel-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.gd-next-skel-time { margin-top: 5px; height: 20px; width: 56px; }
.gd-next-skel-name { margin-top: 7px; height: 14px; width: 72%; }
.gd-next-skel-meta { margin-top: 6px; height: 11px; width: 48%; }
@media (prefers-reduced-motion: reduce) { .gd-skel { animation: none; } }

.gd-ring-wrap { position: relative; width: 92px; height: 92px; flex: none; }
.gd-ring { display: block; width: 100%; height: 100%; }
.gd-ring-track { stroke: var(--gd-primary-track); }
.gd-ring-progress { stroke: url(#gdRingGrad); transition: stroke-dasharray 0.9s cubic-bezier(.22,.61,.36,1); }
.gd-ring-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
}
.gd-ring-value { font-size: 26px; line-height: 1; font-weight: 800; color: var(--gd-ink); letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
.gd-ring-label { font-size: 10.5px; color: var(--gd-ink-3); }

/* ===== KPI 行 ===== */
.gd-kpi-row { display: flex; gap: 8px; }

/* ===== 可配置卡片区 ===== */
.gd-stack { display: flex; flex-direction: column; gap: 10px; }

/* ===== 统一卡片：描边分层，静态卡不加阴影 ===== */
.gd-card {
  position: relative;
  background: #ffffff;
  border: 1px solid var(--gd-border);
  border-radius: var(--gd-radius-lg);
  padding: 14px;
}
.gd-card.gd-editing { outline: 2px dashed rgba(64, 158, 255, 0.45); outline-offset: -2px; }
.gd-card.gd-card--hidden { opacity: 0.5; }
.gd-veil { position: absolute; inset: 0; z-index: 1; background: transparent; border-radius: inherit; }

/* ===== 卡内标题行 ===== */
.gd-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.gd-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--gd-ink);
  letter-spacing: -0.01em;
}
.gd-title-icon { display: flex; align-items: center; gap: 6px; }
.gd-title-glyph { color: var(--gd-primary); }
.gd-cap {
  flex: none;
  font-size: 11px;
  color: var(--gd-ink-3);
  white-space: nowrap;
}
.gd-collapse-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 4px; border: none; background: transparent;
  font-family: inherit; cursor: pointer; border-radius: 8px;
}
.gd-collapse-btn:hover { background: var(--gd-muted); }
.gd-collapse-btn:focus-visible { outline: 2px solid var(--gd-primary); outline-offset: 2px; }
.gd-collapse-ico { color: var(--gd-ink-3); transition: transform 0.2s ease; }
.gd-collapse-ico.is-collapsed { transform: rotate(-90deg); }

/* ===== 五维成长 ===== */
.gd-dim-list { list-style: none; margin: 0; padding: 0; }
.gd-dim-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; }
.gd-dim-row + .gd-dim-row { border-top: 1px solid var(--gd-border); }
/* 五维成长骨架：行高对齐 gd-dim-row（5 行），画像返回时高度基本不跳 */
.gd-dim-skel { display: flex; flex-direction: column; }
.gd-dim-skel-row { height: 26px; border-radius: 6px; }
.gd-dim-skel-row + .gd-dim-skel-row { margin-top: 7px; }
.gd-dim-name { flex: none; width: 56px; font-size: 13px; color: var(--gd-ink-2); white-space: nowrap; }
.gd-dim-track { flex: 1 1 auto; min-width: 0; height: 7px; border-radius: 999px; background: var(--gd-primary-track); overflow: hidden; }
.gd-dim-fill { display: block; height: 100%; border-radius: 999px; background: var(--gd-primary); transition: width 0.7s cubic-bezier(.22,.61,.36,1); }
.gd-dim-value { flex: none; width: 26px; text-align: right; font-size: 13px; font-weight: 600; color: var(--gd-ink); font-variant-numeric: tabular-nums; }
.gd-empty-line { margin: 0; font-size: 12px; color: var(--gd-ink-3); padding: 4px 0; }

/* ===== 快捷空间 ===== */
.gd-space-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); row-gap: 8px; column-gap: 6px; }
.gd-space-item {
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 5px 2px;
  border: none; background: transparent; font-family: inherit; cursor: pointer;
  border-radius: var(--gd-radius-md);
  transition: background-color .18s ease, transform .18s ease;
}
.gd-space-icon { display: inline-flex; align-items: center; justify-content: center; color: var(--gd-primary); }
.gd-space-label { font-size: 11px; line-height: 1.2; color: var(--gd-ink-2); white-space: nowrap; }
.gd-space-item:hover { background: var(--gd-muted); }
.gd-space-item:active { transform: scale(.96); }
.gd-space-item:focus-visible { outline: 2px solid var(--gd-primary); outline-offset: 2px; }

/* ===== AI 主动发现 ===== */
.gd-icon-btn {
  flex: none; width: 28px; height: 28px;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--gd-border); border-radius: var(--gd-radius-md);
  background: #ffffff; color: var(--gd-ink-2); cursor: pointer;
  transition: background-color .18s ease, color .18s ease, transform .18s ease;
}
.gd-icon-btn:hover { background: var(--gd-muted); color: var(--gd-primary); }
.gd-icon-btn:active { transform: scale(.92); }
.gd-icon-btn:focus-visible { outline: 2px solid var(--gd-primary); outline-offset: 2px; }

.gd-ai-empty { display: flex; align-items: center; gap: 8px; color: var(--gd-ink-3); font-size: 12.5px; padding: 6px 0; }
.gd-ai-empty-icon { color: #34d399; }
/* LLM 洞察引导句：高度固定 50px（容纳 2 行 12px/1.45 文案 + 内边距），
   异步到达或始终拿不到洞察时卡片高度都不变，避免推动下方卡片 */
.gd-ai-insight {
  display: flex; align-items: flex-start; gap: 6px;
  height: 50px; box-sizing: border-box; margin-bottom: 8px; padding: 7px 9px;
  border-radius: 8px; background: var(--gd-primary-soft); overflow: hidden;
  font-size: 12px; line-height: 1.45; color: var(--gd-primary-strong);
}
.gd-ai-insight-ico { flex: none; margin-top: 2px; color: var(--gd-primary); }
.gd-ai-insight-text {
  flex: 1 1 auto; min-width: 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.gd-ai-insight-skel { flex: 1 1 auto; height: 12px; margin-top: 3px; }
/* AI 主动发现加载骨架：行高对齐 gd-insight-row（2 行文案 + 内边距），加载完成时高度基本不跳 */
.gd-ai-skel-row { height: 50px; border-radius: 8px; }
.gd-ai-skel-row + .gd-ai-skel-row { margin-top: 8px; }

.gd-insight-list { display: flex; flex-direction: column; }
.gd-insight-row { display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; min-width: 0; }
.gd-insight-row + .gd-insight-row { border-top: 1px solid var(--gd-border); }
.gd-pill {
  flex: none; display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: 999px;
  font-size: 11px; font-weight: 600; white-space: nowrap;
}
.gd-pill-primary { background: var(--gd-primary-soft); color: var(--gd-primary); }
.gd-pill-warning { background: var(--gd-warning-soft); color: var(--gd-warning); }
.gd-pill-danger { background: var(--gd-danger-soft); color: var(--gd-danger); }
.gd-insight-text {
  margin: 0; flex: 1 1 auto; min-width: 0;
  font-size: 12px; line-height: 1.5; color: var(--gd-ink-2);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.gd-insight-strong { font-weight: 600; color: var(--gd-ink); }

@media (prefers-reduced-motion: reduce) {
  .gd-ring-progress, .gd-dim-fill, .gd-collapse-ico { transition: none; }
  .gd-next.is-link, .gd-space-item, .gd-icon-btn, .gd-mini-btn { transition: none; }
}
</style>