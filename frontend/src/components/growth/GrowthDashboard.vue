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
        <div class="gd-next">
          <div class="gd-next-label">下一节课</div>
          <template v-if="nextCourse">
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
      <KpiStat label="今日课程" :value="todayCourses.length" unit="门" tone="primary" />
      <KpiStat label="待办" :value="pendingTodos" unit="项" :tone="pendingTodos > 0 ? 'warning' : 'neutral'" />
      <KpiStat label="综合评分" :value="score || '--'" />
      <KpiStat label="成长记录" :value="profile?.total_records ?? 0" unit="条" />
    </section>

    <!-- 可配置卡片区（编辑态可排序 / 显隐） -->
    <div class="gd-stack">
      <!-- 今日课程 -->
      <section class="gd-card" data-card="today" :class="cardClass('today')" :style="{ order: orderOf('today') }" v-show="show('today')">
        <div v-if="editMode" class="gd-veil" aria-hidden="true"></div>
        <CardToolbar
          v-if="editMode" :can-up="canUp('today')" :can-down="canDown('today')" :hidden="!isVisible('today')"
          @up="move('today', -1)" @down="move('today', 1)" @toggle="toggle('today')"
        />
        <div class="gd-head">
          <h3 class="gd-title">今日课程</h3>
          <span class="gd-cap">{{ isHoliday ? '假期中' : `${todayCourses.length} 门` }}</span>
        </div>
        <TimelineToday v-if="todayCourses.length" :courses="todayCourses" :period-times="periodTimes" />
        <p v-else class="gd-empty-line">{{ isHoliday ? '当前为假期，好好休息～' : '今日没有课程安排' }}</p>
      </section>

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
        <div v-if="!discoverLoading && proactiveActions.length === 0" class="gd-ai-empty">
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

      <!-- 我的学业 -->
      <section class="gd-card" data-card="academic" :class="cardClass('academic')" :style="{ order: orderOf('academic') }" v-show="show('academic')">
        <div v-if="editMode" class="gd-veil" aria-hidden="true"></div>
        <CardToolbar
          v-if="editMode" :can-up="canUp('academic')" :can-down="canDown('academic')" :hidden="!isVisible('academic')"
          @up="move('academic', -1)" @down="move('academic', 1)" @toggle="toggle('academic')"
        />
        <div class="gd-head">
          <h3 class="gd-title">我的学业</h3>
          <span class="gd-cap">一键直达</span>
        </div>
        <div class="gd-link-list">
          <button type="button" class="gd-link-row" @click="emit('open', 'schedule')">
            <span class="gd-link-icon"><el-icon :size="18"><Calendar /></el-icon></span>
            <span class="gd-link-title">课程表</span>
            <el-icon class="gd-link-chevron" :size="16"><ArrowRight /></el-icon>
          </button>
          <button type="button" class="gd-link-row" @click="emit('open', 'grades')">
            <span class="gd-link-icon"><el-icon :size="18"><DataLine /></el-icon></span>
            <span class="gd-link-title">成绩分析</span>
            <el-icon class="gd-link-chevron" :size="16"><ArrowRight /></el-icon>
          </button>
          <button type="button" class="gd-link-row" @click="emit('open', 'growth')">
            <span class="gd-link-icon"><el-icon :size="18"><TrendCharts /></el-icon></span>
            <span class="gd-link-title">成长轨迹</span>
            <el-icon class="gd-link-chevron" :size="16"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>

      <!-- 五维成长（渐进披露，默认折叠） -->
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
        <p v-else-if="!radarDims.length && !dimsCollapsed" class="gd-empty-line">暂无五维数据，完善成长记录后自动生成</p>
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
          <button type="button" class="gd-space-item" @click="go('/student/plan')">
            <span class="gd-space-icon"><el-icon :size="21"><Calendar /></el-icon></span>
            <span class="gd-space-label">学习计划</span>
          </button>
          <button type="button" class="gd-space-item" @click="go('/student/portfolio')">
            <span class="gd-space-icon"><el-icon :size="21"><Collection /></el-icon></span>
            <span class="gd-space-label">作品集</span>
          </button>
          <button type="button" class="gd-space-item" @click="go('/student/growth')">
            <span class="gd-space-icon"><el-icon :size="21"><TrendCharts /></el-icon></span>
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
  CircleCheckFilled, Calendar, DataLine, ArrowRight, ArrowDown, FirstAidKit
} from '@element-plus/icons-vue'
import { getGrowthProfile, type GrowthProfile } from '@/api/growth'
import { fetchProactiveActions, type ProactiveAction } from '@/api/agent'
import { getToday, type TodayTask } from '@/api/plan'
import { useAuthStore } from '@/stores/auth'
import type { Course } from '@/types'
import KpiStat from './dashboard/KpiStat.vue'
import TimelineToday from './dashboard/TimelineToday.vue'
import CardToolbar from './dashboard/CardToolbar.vue'

const props = withDefaults(defineProps<{
  courses?: Course[]
  currentWeek?: number
  periodTimes?: Record<number, string>
  isHoliday?: boolean
}>(), {
  courses: () => [],
  currentWeek: 1,
  periodTimes: () => ({}),
  isHoliday: false,
})

const emit = defineEmits<{ (e: 'open', tab: 'schedule' | 'grades' | 'growth'): void }>()
const router = useRouter()
const auth = useAuthStore()
const discoverLoading = ref(false)
const profile = ref<GrowthProfile | null>(null)
const proactiveActions = ref<ProactiveAction[]>([])
const todayTasks = ref<TodayTask[]>([])
const dimsCollapsed = ref(true)
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
type CardId = 'today' | 'ai' | 'academic' | 'dims' | 'space'
const CARD_IDS: CardId[] = ['today', 'ai', 'academic', 'dims', 'space']
const cardOrder = ref<CardId[]>([...CARD_IDS])
const hiddenIds = ref<CardId[]>([])
const editMode = ref(false)
const storageKey = `cm.dashboard.cards.${auth.user?.id ?? 'anon'}`

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
function pillClass(p: number) {
  return p >= 80 ? 'gd-pill-danger' : p >= 60 ? 'gd-pill-warning' : 'gd-pill-primary'
}
function actionLabel(p: number) { return p >= 80 ? '重点关注' : p >= 60 ? '值得关注' : '温馨提醒' }

async function loadOverview() {
  try { profile.value = await getGrowthProfile() } catch { /* ignore */ }
}
async function loadDiscover() {
  discoverLoading.value = true
  try {
    const all = await fetchProactiveActions()
    proactiveActions.value = all.filter(a => a.target_role === 'student')
  } catch { proactiveActions.value = [] }
  finally { discoverLoading.value = false }
}
async function loadTodayTasks() {
  try { todayTasks.value = await getToday() } catch { todayTasks.value = [] }
}

onMounted(() => { loadCards(); loadOverview(); loadDiscover(); loadTodayTasks() })
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
.gd-next-label { font-size: 11px; font-weight: 600; color: var(--gd-primary); letter-spacing: 0.02em; }
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
.gd-dim-name { flex: none; width: 56px; font-size: 13px; color: var(--gd-ink-2); white-space: nowrap; }
.gd-dim-track { flex: 1 1 auto; min-width: 0; height: 7px; border-radius: 999px; background: var(--gd-primary-track); overflow: hidden; }
.gd-dim-fill { display: block; height: 100%; border-radius: 999px; background: var(--gd-primary); transition: width 0.7s cubic-bezier(.22,.61,.36,1); }
.gd-dim-value { flex: none; width: 26px; text-align: right; font-size: 13px; font-weight: 600; color: var(--gd-ink); font-variant-numeric: tabular-nums; }
.gd-empty-line { margin: 0; font-size: 12px; color: var(--gd-ink-3); padding: 4px 0; }

/* ===== 我的学业 ===== */
.gd-link-list { display: flex; flex-direction: column; }
.gd-link-row {
  display: flex; align-items: center; gap: 10px;
  width: 100%; min-height: 44px; padding: 0 4px;
  border: none; background: transparent; text-align: left;
  font-family: inherit; color: inherit; cursor: pointer;
  border-radius: var(--gd-radius-md);
  transition: background-color .18s ease, transform .18s ease;
}
.gd-link-row + .gd-link-row { border-top: 1px solid var(--gd-border); }
.gd-link-icon { flex: none; width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; color: var(--gd-primary); }
.gd-link-title { flex: 1 1 auto; min-width: 0; font-size: 14px; font-weight: 600; color: var(--gd-ink); }
.gd-link-chevron { flex: none; color: #c0c4cc; }
.gd-link-row:hover { background: var(--gd-muted); }
.gd-link-row:active { transform: scale(.99); }
.gd-link-row:focus-visible { outline: 2px solid var(--gd-primary); outline-offset: 2px; }

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
  .gd-link-row, .gd-space-item, .gd-icon-btn, .gd-mini-btn { transition: none; }
}
</style>