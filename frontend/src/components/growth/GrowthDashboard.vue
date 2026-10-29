<template>
  <div class="growth-dashboard">
    <!-- 日期行：固定 Head 由父级 .home-bar 承担（学业中心标题），这里只留日期语境 -->
    <section class="gd-today">
      <div class="gd-today-date">
        <b>{{ dateLabel }}</b>
        <span>第 {{ currentWeek }} 教学周</span>
        <template v-if="isHoliday"><span>·</span><span>假期</span></template>
      </div>
    </section>

    <!-- 今日学业卡：主页唯一的白卡（A+B 融合的 Hero），其余区域全部扁平化 -->
    <section class="gd-today-card" :aria-label="'今日学业概览'">
      <div class="gd-tc-head">
        <p class="gd-tc-cap">今日学业</p>
        <button v-if="!coursesLoading && todayCourses.length" type="button" class="gd-tc-all" @click="openSchedule">全部课程 ›</button>
      </div>
      <p class="gd-tc-line">
        {{ coursesLoading ? '正在读取课表…' : `${todayCourses.length} 节课` }}<template v-if="!coursesLoading && nDueToday"> ·
          <b class="gd-tc-due">{{ nDueToday }} 项作业今天截止</b></template><template v-else-if="!coursesLoading && pendingTodos"> ·
          <b class="gd-tc-due">{{ pendingTodos }} 项待办</b></template>
      </p>
      <template v-if="!coursesLoading && todayCourses.length">
        <div
          v-for="c in todayCardCourses"
          :key="c.id"
          class="gd-tl-row"
          :class="{ 'is-live': isCourseLive(c), 'is-done': isCourseDone(c) }"
        >
          <p class="gd-tl-time">{{ timeLabel(c.start_period) }}</p>
          <div class="gd-tl-main">
            <p class="gd-tl-name">{{ c.name }}</p>
            <p class="gd-tl-meta">
              <template v-if="isCourseLive(c)">进行中{{ c.location ? ' · ' + c.location : '' }}</template>
              <template v-else>{{ c.location || '待上课' }}</template>
            </p>
          </div>
        </div>
        <p v-if="todayCourses.length > todayCardCourses.length" class="gd-tl-more">
          还有 {{ todayCourses.length - todayCardCourses.length }} 节课 ›
        </p>
      </template>
      <p v-else-if="!coursesLoading" class="gd-tc-empty">{{ nextSummary }}</p>
      <button type="button" class="gd-tc-cta" @click="openSchedule">开始今天的学习</button>
    </section>

    <!-- 速览条：把今天/本周最关心的四个数字摊在同一行，避免首页只有一张卡显得空 -->
    <section class="gd-glance" aria-label="本周速览">
      <button type="button" class="gd-glance-item" @click="openSchedule">
        <b>{{ coursesLoading ? '—' : todayCourses.length }}</b>
        <span>今日课程</span>
      </button>
      <button type="button" class="gd-glance-item" @click="emit('open', 'plan')">
        <b>{{ pendingTodos }}</b>
        <span>待办未完成</span>
      </button>
      <button type="button" class="gd-glance-item" @click="openLedger">
        <b>{{ weekRecordedDays }}</b>
        <span>本周心情</span>
      </button>
      <button type="button" class="gd-glance-item" @click="emit('open', 'plan')">
        <b>{{ streakDays }}</b>
        <span>连续打卡</span>
      </button>
    </section>

    <!-- ===== 心情：扁平区（无卡片底），分区靠发丝线与留白 =====
         情绪树洞淡出后的新形态——5 档心情脸 + 本周 7 天柱 + 30 天台账弹窗。
         与 AI 外呼电话识别共用 /emotions/*：电话记录自动进台账并驱动今日情绪展示。 -->
    <section class="gd-flat gd-mood" aria-label="心情记录">
      <div class="gd-flat-head">
        <div class="gd-flat-head-main">
          <h3 class="gd-flat-title">此刻的心情</h3>
          <p class="gd-flat-sub">记下一次，绵小城会更懂你的近况</p>
        </div>
        <span v-if="voiceSynced" class="gd-mood-sync"><el-icon :size="11"><Connection /></el-icon>电话已同步</span>
      </div>
      <div class="gd-mood-faces" role="radiogroup" aria-label="选择今天的心情">
        <button
          v-for="m in MOODS" :key="m.score"
          type="button" role="radio" :aria-checked="moodValue === m.score" :aria-label="m.label"
          class="gd-mood-face" :class="{ 'is-active': moodValue === m.score }"
          :style="{ '--mood-c': m.color, '--mood-s': (28 + m.score * 2.6) + 'px' }"
          :disabled="moodSaving"
          @click="pickMood(m)"
        >
          <span class="gd-mood-face-emoji">
            <i class="gd-mood-face-shine" aria-hidden="true"></i>
            <span class="gd-mood-face-glyph">{{ m.emoji }}</span>
            <span v-if="moodValue === m.score" class="gd-mood-face-check" aria-hidden="true">✓</span>
          </span>
          <span class="gd-mood-face-label">{{ m.label }}</span>
        </button>
      </div>
      <p
        class="gd-mood-label" :class="{ 'is-set': moodValue }"
        :style="moodValue ? { '--mood-c': moodColor } : undefined"
      >
        {{ moodValue ? `今天 · ${moodLabel}` : '点一下，记下此刻的心情' }}
      </p>
      <p v-if="moodTip" class="gd-mood-tip">{{ moodTip }}</p>
      <!-- 周柱：柱子放在固定高的轨道里、轨道底对齐，日期行永远贴在同一条基线上
           （此前柱子直接和日期排在同一列，柱高不同导致日期看起来错位） -->
      <div class="gd-mood-panel">
        <div class="gd-mood-panel-head">
          <span>近 7 天</span>
          <span v-if="weekRecordedDays">已记录 {{ weekRecordedDays }} 天<template v-if="weekMoodAvgLabel"> · 平均「{{ weekMoodAvgLabel }}」</template></span>
          <span v-else>还没有记录</span>
        </div>
        <div class="gd-mood-week">
          <div
            v-for="(d, i) in weekBars" :key="i"
            class="gd-mood-col" :class="{ 'is-today': d.isToday }" :title="`${d.label}（${d.dateLabel}）`"
          >
            <span class="gd-mood-track">
              <span class="gd-mood-bar" :style="{ height: d.height + 'px', background: d.color }"></span>
            </span>
            <span class="gd-mood-day" :class="{ 'is-today': d.isToday }">{{ d.weekday }}</span>
          </div>
        </div>
      </div>
      <button type="button" class="gd-mood-ledger-btn" @click="openLedger">
        心情台账 · 近 30 天 <el-icon :size="11"><ArrowRight /></el-icon>
      </button>
    </section>

    <!-- ===== AI：压缩成一条入口（v4.2）=====
         完整内容（心情/任务/积累/天气/运势）在独立子页「今日报告」，这里只保留一行摘要 -->
    <button type="button" class="gd-flat gd-ai-entry" aria-label="查看今日报告" @click="emit('open', 'ai')">
      <span class="gd-ai-badge"><img :src="siteMascot" :alt="siteName" class="gd-ai-badge-img" /></span>
      <span class="gd-ai-entry-main">
        <span class="gd-ai-entry-title">AI 今日报告</span>
        <span class="gd-ai-entry-sub">
          <template v-if="discoverLoading && !proactiveActions.length">正在生成今日报告…</template>
          <template v-else-if="proactiveActions.length">{{ proactiveActions.length }} 条建议 · {{ proactiveActions[0].title }}</template>
          <template v-else-if="discoverLoaded">今日状态平稳，点击查看报告</template>
          <template v-else>加载中…</template>
        </span>
      </span>
      <el-icon class="gd-ai-chev" :size="13"><ArrowRight /></el-icon>
    </button>

    <!-- ===== 更多：单排横向滑动入口（v4.3）
         入口数量超过一屏后横向滑动查看，内容不足一屏时整排居中，
         保留彩色软底图标，让首页功能密度更高但不形成第二张卡片 -->
    <nav class="gd-flat gd-more" aria-label="功能入口">
      <div class="gd-flat-head">
        <h3 class="gd-flat-title">更多</h3>
        <span class="gd-flat-sub">左右滑动查看更多</span>
      </div>
      <div class="gd-tile-scroll">
        <div class="gd-tile-track">
          <button type="button" class="gd-tile" @click="openSchedule">
            <span class="gd-tile-chip" style="background:#e8f1e9"><el-icon :size="20" color="#16794c"><Calendar /></el-icon></span>
            <span class="gd-tile-label">课程表</span>
          </button>
          <button type="button" class="gd-tile" @click="emit('open', 'grades')">
            <span class="gd-tile-chip" style="background:#e3f2ec"><el-icon :size="20" color="#0f7a58"><DataLine /></el-icon></span>
            <span class="gd-tile-label">成绩分析</span>
          </button>
          <button type="button" class="gd-tile" @click="emit('open', 'growth')">
            <span class="gd-tile-chip" style="background:#e5ecfc"><el-icon :size="20" color="#1a4fd6"><TrendCharts /></el-icon></span>
            <span class="gd-tile-label">成长轨迹</span>
          </button>
          <button type="button" class="gd-tile" @click="emit('open', 'plan')">
            <span class="gd-tile-chip" style="background:#e2f1fa"><el-icon :size="20" color="#0369a1"><Notebook /></el-icon></span>
            <span class="gd-tile-label">学习计划</span>
          </button>
          <button type="button" class="gd-tile" @click="emit('open', 'service')">
            <span class="gd-tile-chip" style="background:#f0e8fc"><el-icon :size="20" color="#6d28d9"><Tickets /></el-icon></span>
            <span class="gd-tile-label">请假服务</span>
          </button>
          <button type="button" class="gd-tile" @click="go('/student/portfolio')">
            <span class="gd-tile-chip" style="background:#fdf1e3"><el-icon :size="20" color="#b45309"><Collection /></el-icon></span>
            <span class="gd-tile-label">作品集</span>
          </button>
        </div>
      </div>
    </nav>

    <!-- 心情台账弹窗：30 天日历点阵 + 近期记录列表 -->
    <el-dialog v-model="ledgerVisible" title="心情台账 · 近 30 天" width="92%" class="gd-ledger-dialog">
      <div class="gd-ledger-grid">
        <div
          v-for="d in ledgerDays" :key="d.date"
          class="gd-ledger-cell" :title="`${d.dateLabel}${d.label ? ' · ' + d.label : ''}`"
          :style="{ background: d.color }"
        ></div>
      </div>
      <div class="gd-ledger-legend">
        <span v-for="m in MOODS" :key="m.score" class="gd-ledger-lg"><i :style="{ background: m.color }"></i>{{ m.label }}</span>
        <span class="gd-ledger-lg"><i style="background:#e9ebee"></i>未记录</span>
      </div>
      <p v-if="!ledgerList.length" class="gd-ledger-empty">还没有记录，从打一个心情点开始</p>
      <ul v-else class="gd-ledger-list">
        <li v-for="r in ledgerList" :key="r.id" class="gd-ledger-row">
          <i class="gd-ledger-dot" :style="{ background: moodColorOf(r.emotion) }"></i>
          <span class="gd-ledger-lb">{{ r.label }}</span>
          <span class="gd-ledger-src">{{ r.source === 'voice_call' ? '电话识别' : '手动记录' }}</span>
          <span class="gd-ledger-tm">{{ moodTime(r.created_at) }}</span>
        </li>
      </ul>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  TrendCharts, Collection,
  Calendar, DataLine, ArrowRight, Connection, Tickets,
  Notebook
} from '@element-plus/icons-vue'
import { fetchProactiveFeed, fetchProactiveInsight, type ProactiveAction } from '@/api/agent'
import { getToday, getStreak, type TodayTask } from '@/api/plan'
import { fetchEmotionHistory, recordEmotion, type EmotionRecordItem } from '@/api/emotion'
import type { Course } from '@/types'
import { studentDataCache } from '@/utils/studentDataCache'
import { useSiteConfig } from '@/composables/useSiteConfig'

const props = withDefaults(defineProps<{
  courses?: Course[]
  currentWeek?: number
  periodTimes?: Record<number, string>
  isHoliday?: boolean
  /** 课程数据是否仍在加载：为 true 时今日学业卡显示骨架占位而非空态文案 */
  coursesLoading?: boolean
}>(), {
  courses: () => [],
  currentWeek: 1,
  periodTimes: () => ({}),
  isHoliday: false,
  coursesLoading: false,
})

const emit = defineEmits<{ (e: 'open', tab: 'schedule' | 'grades' | 'growth' | 'service' | 'plan' | 'ai'): void }>()
const router = useRouter()
const { siteMascot, siteName } = useSiteConfig()

const discoverLoading = ref(!studentDataCache.actions)
const discoverLoaded = ref(!!studentDataCache.actions)
const proactiveActions = ref<ProactiveAction[]>(studentDataCache.actions ?? [])
const insight = ref<string>(studentDataCache.insight ?? '')
const insightPending = ref(false)
const todayTasks = ref<TodayTask[]>(studentDataCache.tasks ?? [])

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

/** 日期行：10月29日 周四 · 第 N 教学周 */
const dateLabel = computed(() => {
  const d = now
  const wd = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  return `${d.getMonth() + 1}月${d.getDate()}日 ${wd}`
})

const pendingTodos = computed(() => todayTasks.value.filter(t => !t.checked_today && t.status !== 'done').length)

/**
 * v4「今日学业」卡：课程数 + 今天截止的待办数压成一行标题，
 * 下方是今日课程时间轴（最多 3 条，进行中蓝色高亮），底部主 CTA 进课程表。
 */
const nDueToday = computed(() => todayTasks.value.filter(t => {
  if (t.checked_today || t.status === 'done') return false
  if (!t.due_date) return false
  const due = new Date(t.due_date)
  return !Number.isNaN(due.getTime()) && due.toDateString() === now.toDateString()
}).length)

/** 时间轴只展示前 3 节，超出部分提示「还有 N 节」 */
const todayCardCourses = computed(() => todayCourses.value.slice(0, 3))
function courseRange(c: Course) {
  const s = toMin(c.start_period)
  const e = toMin(c.end_period) + 45
  return { s, e: e > s ? e : s + 45 }
}
function isCourseLive(c: Course) {
  const { s, e } = courseRange(c)
  return s <= nowMin && nowMin < e
}
function isCourseDone(c: Course) {
  return nowMin >= courseRange(c).e
}

/** 空态文案 */
const nextSummary = computed(() => {
  if (props.isHoliday) return '假期中，好好休息～'
  if (!todayCourses.value.length) return '今天没有课程安排'
  if (!nextCourse.value) return '今天的课已经全部上完'
  const c = nextCourse.value
  return `${timeLabel(c.start_period)} ${c.name}${c.location ? ' · ' + c.location : ''}`
})
const nextCourse = computed(() =>
  props.isHoliday ? null : (todayCourses.value.find(c => toMin(c.start_period) >= nowMin) || null)
)

// ===== 心情（Daylio 打点 + 台账） =====
// 数据源与 AI 外呼电话识别共用 /emotions/*：电话识别写入 source='voice_call' 的记录，
// 手动打点写 source='manual'。今日心情取今天最新一条；没有则未打点。
type Mood = { score: number; emotion: string; label: string; color: string; emoji: string }
const MOODS: Mood[] = [
  { score: 1, emotion: 'sad', label: '很糟', color: '#f09595', emoji: '😞' },
  { score: 2, emotion: 'fearful', label: '有点低', color: '#fac775', emoji: '😕' },
  { score: 3, emotion: 'neutral', label: '平静', color: '#b4b2a9', emoji: '😐' },
  { score: 4, emotion: 'happy', label: '不错', color: '#5dcaa5', emoji: '🙂' },
  { score: 5, emotion: 'surprised', label: '超棒', color: '#85b7eb', emoji: '😄' },
]
/** 后端 7 类情绪 → 打点色（台账点阵用；打点自身只产生 MOODS 里的 5 类） */
function moodColorOf(emotion: string): string {
  const m = MOODS.find(x => x.emotion === emotion)
  if (m) return m.color
  const extra: Record<string, string> = { angry: '#e24b4a', disgusted: '#afaaa0' }
  return extra[emotion] ?? '#e9ebee'
}
/** 后端 7 类情绪 → 1-5 分（周趋势柱高） */
function moodScoreOf(emotion: string): number {
  if (emotion === 'happy') return 4
  if (emotion === 'surprised') return 5
  if (emotion === 'neutral') return 3
  if (emotion === 'fearful') return 2
  return 1
}
const moodHistory = ref<EmotionRecordItem[]>([])
const moodSaving = ref(false)
const ledgerVisible = ref(false)

const dayKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const todayKey = dayKey(now)

/** 今日心情 = 今天最新一条记录；没有则未打点（5 个点全灰可点） */
const todayMood = computed(() => moodHistory.value.find(r => r.created_at.slice(0, 10) === todayKey) || null)
const moodValue = computed(() => (todayMood.value ? moodScoreOf(todayMood.value.emotion) : 0))
const moodLabel = computed(() => {
  const r = todayMood.value
  if (!r) return ''
  const m = MOODS.find(x => x.emotion === r.emotion)
  return m ? m.label : r.label
})
const moodColor = computed(() => (todayMood.value ? moodColorOf(todayMood.value.emotion) : ''))
/** 电话已同步：今天有来自外呼识别的记录 */
const voiceSynced = computed(() =>
  moodHistory.value.some(r => r.created_at.slice(0, 10) === todayKey && r.source === 'voice_call'),
)
/** 一句轻提示：电话识别与手动打卡不一致时温和说明（不评判） */
const moodTip = computed(() => {
  const r = todayMood.value
  if (!r) return ''
  const calls = moodHistory.value.filter(x => x.created_at.slice(0, 10) === todayKey && x.source === 'voice_call')
  if (r.source !== 'voice_call' && calls.length && calls[0].emotion !== r.emotion) {
    return `电话识别到「${calls[0].label}」，你的记录已覆盖它`
  }
  if (r.source === 'voice_call') return '来自 AI 外呼的心情识别，点圆点可调整'
  return ''
})

/** 本周 7 天柱：每天取当天最新一条记录的分数；未记录为 0（灰点占位） */
const weekBars = computed(() => {
  const out: { height: number; score: number; color: string; weekday: string; isToday: boolean; dateLabel: string; label: string }[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i)
    const key = dayKey(d)
    const rec = moodHistory.value.find(r => r.created_at.slice(0, 10) === key)
    const score = rec ? moodScoreOf(rec.emotion) : 0
    out.push({
      height: score ? 10 + score * 7 : 5,
      score,
      color: rec ? moodColorOf(rec.emotion) : '#e9ebee',
      weekday: i === 0 ? '今天' : ['日', '一', '二', '三', '四', '五', '六'][d.getDay()],
      isToday: i === 0,
      dateLabel: `${d.getMonth() + 1}月${d.getDate()}日`,
      label: rec ? rec.label : '未记录',
    })
  }
  return out
})

/** 台账：近 30 天按日取当天最新记录；列表取最近 12 条明细 */
const ledgerDays = computed(() => {
  const out: { date: string; dateLabel: string; color: string; label: string }[] = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i)
    const key = dayKey(d)
    const rec = moodHistory.value.find(r => r.created_at.slice(0, 10) === key)
    out.push({
      date: key,
      dateLabel: `${d.getMonth() + 1}月${d.getDate()}日`,
      color: rec ? moodColorOf(rec.emotion) : '#f1f2f4',
      label: rec ? rec.label : '',
    })
  }
  return out
})
const ledgerList = computed(() => moodHistory.value.slice(0, 12))
/** 近 7 天有记录的天数 + 平均心情（速览条与心情区摘要共用） */
const weekRecordedDays = computed(() => weekBars.value.filter(d => d.label !== '未记录').length)
const weekMoodAvgLabel = computed(() => {
  const scores = weekBars.value.filter(d => d.score).map(d => d.score)
  if (!scores.length) return ''
  const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
  return MOODS.find(m => m.score === avg)?.label || ''
})
function moodTime(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function openLedger() { ledgerVisible.value = true }

async function loadMood() {
  try {
    moodHistory.value = await fetchEmotionHistory(30, 300) || []
  } catch { /* 失败保持空态，区域结构不变 */ }
}
async function pickMood(m: Mood) {
  if (moodSaving.value) return
  moodSaving.value = true
  try {
    await recordEmotion(m.emotion, 1, 'manual')
    await loadMood()
  } catch { /* 失败静默：本地不假写，下次进入会重试拉取 */ }
  finally { moodSaving.value = false }
}

function go(p: string) { router.push(p) }
/** 今日学业卡（查看全部课程入口）：整卡点击推入课程表 */
function openSchedule() { emit('open', 'schedule') }

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
      void loadInsight()
    }
  } catch {
    if (!proactiveActions.value.length && studentDataCache.actions) proactiveActions.value = studentDataCache.actions
  }
  finally { discoverLoading.value = false; discoverLoaded.value = true }
}

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

/** 连续打卡天数（速览条用；失败不阻塞首页，保持 0） */
const streakDays = ref(0)
async function loadStreak() {
  try {
    const s = await getStreak()
    streakDays.value = Math.max(0, s?.current || 0)
  } catch { /* 失败保持 0 */ }
}

onMounted(() => { loadDiscover(); loadTodayTasks(); loadMood(); loadStreak() })

/** 下拉刷新（父组件学业中心首页调用）：重拉 AI 主动发现 / 今日任务 / 心情 / 打卡，同步刷新缓存 */
async function refresh() {
  await Promise.all([loadDiscover(), loadTodayTasks(), loadMood(), loadStreak()])
}
defineExpose({ refresh })
</script>

<style scoped>
/* ===== 组件级 token =====
   v4.1：主页去卡片化——唯一保留的白卡是「今日学业」Hero，
   心情 / AI 发现 / 更多 改为扁平分区，靠发丝线与留白分层。 */
.growth-dashboard {
  --gd-bg: #f5f6f7;
  --gd-surface: #ffffff;
  --gd-ink: #14171a;
  --gd-ink-2: #5b6470;
  --gd-ink-3: #8b939e;
  --gd-ink-quiet: #a8aeb6;
  --gd-border: #e9ebee;
  --gd-border-strong: #dcdfe4;
  --gd-accent: #1a4fd6;
  --gd-accent-soft: #eef3fd;
  --gd-warning: #c2410c;
  --gd-radius-lg: 16px;
  --gd-radius-md: 12px;
  --gd-radius-sm: 9px;
  --gd-shadow-card: 0 1px 2px rgba(20, 23, 26, 0.035);

  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.gd-skel { background: #eef0f3; border-radius: 6px; animation: gd-pulse 1.4s ease-in-out infinite; }
@keyframes gd-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.55; } }

/* ===== 日期行 ===== */
.gd-today { padding: 4px 2px 10px; }
.gd-today-date {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 17px;
  color: var(--gd-ink-3);
  min-width: 0;
}
.gd-today-date b { font-weight: 600; color: var(--gd-ink-2); }

/* ===== 今日学业卡（主页唯一白卡） ===== */
.gd-today-card {
  padding: 14px;
  background: var(--gd-surface);
  border: 1px solid var(--gd-border);
  border-radius: var(--gd-radius-lg);
  box-shadow: var(--gd-shadow-card);
}
.gd-tc-head { display: flex; align-items: center; justify-content: space-between; }
.gd-tc-cap { margin: 0; font-size: 11.5px; color: var(--gd-ink-3); }
.gd-tc-all {
  border: none; background: transparent; padding: 0;
  font-family: inherit; font-size: 12px; color: var(--gd-accent); cursor: pointer;
}
.gd-tc-line { margin: 5px 0 10px; font-size: 19px; line-height: 27px; font-weight: 600; letter-spacing: -0.4px; color: var(--gd-ink); }
.gd-tc-due { color: #8a5a12; font-weight: 600; }
.gd-tc-empty { margin: 2px 0 10px; font-size: 13px; color: var(--gd-ink-3); }
.gd-tl-row {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 3px 0 3px 10px; margin-bottom: 7px;
  border-left: 3px solid var(--gd-border-strong);
}
.gd-tl-row.is-live { border-left-color: var(--gd-accent); }
.gd-tl-row.is-done { opacity: 0.62; }
.gd-tl-time { flex: none; margin: 0; font-size: 12px; line-height: 18px; color: var(--gd-ink-2); font-variant-numeric: tabular-nums; }
.gd-tl-main { min-width: 0; }
.gd-tl-name { margin: 0; font-size: 13px; line-height: 18px; font-weight: 500; color: var(--gd-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gd-tl-row.is-live .gd-tl-name { color: var(--gd-accent); }
.gd-tl-meta { margin: 0; font-size: 11px; line-height: 15px; color: var(--gd-ink-3); }
.gd-tl-more { margin: 0 0 8px 13px; font-size: 11.5px; color: var(--gd-ink-3); }
.gd-tc-cta {
  display: flex; align-items: center; justify-content: center;
  width: 100%; height: 38px; margin-top: 4px;
  border: none; border-radius: var(--gd-radius-sm);
  background: var(--gd-ink); color: #fff;
  font-family: inherit; font-size: 13.5px; font-weight: 600; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.gd-tc-cta:active { transform: scale(0.985); }
.gd-tc-cta:focus-visible { outline: 2px solid var(--gd-accent); outline-offset: 2px; }

/* ===== 扁平分区：无底色无描边，区与区之间一条发丝线 ===== */
.gd-flat { padding: 16px 2px 14px; }
/* 有卡片外壳的分区（AI 入口 / 更多）之间不再画发丝线，靠卡片间距分隔 */
.gd-flat + .gd-flat { border-top: 0; }
.gd-flat-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 4px; }
.gd-flat-head-main { min-width: 0; }
.gd-flat-title { margin: 0; font-size: 14.5px; font-weight: 600; color: var(--gd-ink); letter-spacing: -0.2px; }
.gd-flat-sub { margin: 2px 0 0; font-size: 11px; line-height: 15px; color: var(--gd-ink-3); font-weight: 400; }
.gd-flat-head > .gd-flat-sub { flex: none; align-self: center; white-space: nowrap; }

/* ===== 速览条：四个数字平铺，靠竖线分隔，不形成第二张卡片 ===== */
.gd-glance {
  display: grid; grid-template-columns: repeat(4, 1fr);
  margin: 2px 0 0; padding: 12px 0 2px;
}
.gd-glance-item {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 0 2px; border: none; background: transparent; cursor: pointer;
  font-family: inherit; -webkit-tap-highlight-color: transparent;
}
.gd-glance-item + .gd-glance-item::before {
  content: ''; position: absolute; left: 0; top: 3px; bottom: 3px;
  width: 1px; background: var(--gd-border);
}
.gd-glance-item b {
  font-size: 18px; font-weight: 600; line-height: 22px; color: var(--gd-ink);
  font-variant-numeric: tabular-nums;
}
.gd-glance-item span { font-size: 10.5px; line-height: 14px; color: var(--gd-ink-3); }
.gd-glance-item:active b { color: var(--gd-accent); }
.gd-glance-item:focus-visible { outline: 2px solid var(--gd-accent); outline-offset: 2px; border-radius: 8px; }

/* ===== 更多入口：轻卡片，横向滑动 6 个入口 ===== */
.gd-flat.gd-more {
  margin: 10px 0 2px;
  padding: 14px 10px 12px;
  border: 1px solid var(--gd-border);
  border-radius: 14px;
  background: var(--gd-surface);
  box-shadow: 0 1px 2px rgba(17, 20, 24, 0.04);
}
.gd-flat.gd-more .gd-flat-head { padding: 0 3px; }

/* ===== 心情（独立软底面板：与页面灰底明显区分，承载 5 档气泡） ===== */
.gd-flat.gd-mood {
  position: relative;
  margin: 10px 0 2px;
  padding: 15px 13px 12px;
  border-top: 0;
  border-radius: 18px;
  background:
    radial-gradient(130% 100% at 4% 0%, #eef4ff 0%, rgba(238, 244, 255, 0) 58%),
    radial-gradient(120% 100% at 100% 6%, #fdeff6 0%, rgba(253, 239, 246, 0) 54%),
    linear-gradient(168deg, #ffffff 0%, #f8fafd 52%, #f5f2fa 100%);
  box-shadow:
    0 1px 2px rgba(17, 20, 24, 0.05),
    inset 0 0 0 1px rgba(17, 20, 24, 0.045);
}
.gd-flat.gd-mood + .gd-flat { border-top: 0; }
.gd-mood-sync {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 7px; border-radius: 999px;
  background: var(--gd-accent-soft); color: var(--gd-accent);
  font-size: 10.5px; font-weight: 500;
}
/* 表情气泡：带高光的立体马卡龙珠，选中后升起、描同色光环并亮出对勾 */
.gd-mood-faces {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 6px; margin: 14px 0 0; padding: 0 2px;
}
.gd-mood-face {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 4px 2px 5px;
  border: none; border-radius: 12px; background: transparent;
  cursor: pointer; font-family: inherit;
  transition: background 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}
.gd-mood-face-emoji {
  position: relative;
  width: var(--mood-s, 38px); height: var(--mood-s, 38px);
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at 50% 122%, color-mix(in srgb, var(--mood-c) 88%, #fff) 0%, color-mix(in srgb, var(--mood-c) 52%, #fff) 54%, color-mix(in srgb, var(--mood-c) 26%, #fff) 100%);
  box-shadow:
    inset 0 -5px 9px color-mix(in srgb, var(--mood-c) 42%, transparent),
    inset 0 2px 3px rgba(255, 255, 255, 0.9),
    0 3px 8px color-mix(in srgb, var(--mood-c) 24%, transparent);
  opacity: 0.86;
  transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, opacity 0.2s ease;
}
/* 左上高光：让气泡有玻璃珠的受光面 */
.gd-mood-face-shine {
  position: absolute;
  top: calc(var(--mood-s, 38px) * 0.16); left: calc(var(--mood-s, 38px) * 0.24);
  width: calc(var(--mood-s, 38px) * 0.32); height: calc(var(--mood-s, 38px) * 0.18);
  border-radius: 50%;
  transform: rotate(-20deg);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(255, 255, 255, 0) 100%);
  pointer-events: none;
}
.gd-mood-face-glyph {
  position: relative;
  font-size: calc(var(--mood-s, 38px) * 0.54); line-height: 1;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.16));
}
/* 选中对勾：挂在气泡右下，和光环一起构成明确的「已记录」状态 */
.gd-mood-face-check {
  position: absolute;
  right: -3px; bottom: -3px;
  width: 15px; height: 15px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: var(--mood-c); color: #fff;
  font-size: 9px; font-weight: 700; line-height: 1;
  box-shadow: 0 0 0 1.5px #fff, 0 2px 4px rgba(17, 20, 24, 0.18);
}
.gd-mood-face-label {
  font-size: 10.5px; line-height: 14px; color: var(--gd-ink-3);
  transition: color 0.18s ease;
}
.gd-mood-face:hover .gd-mood-face-emoji { opacity: 1; transform: translateY(-2px); }
.gd-mood-face.is-active .gd-mood-face-emoji {
  opacity: 1;
  transform: translateY(-3px) scale(1.08);
  box-shadow:
    0 0 0 2.5px #fff,
    0 0 0 4px color-mix(in srgb, var(--mood-c) 78%, transparent),
    0 6px 14px color-mix(in srgb, var(--mood-c) 38%, transparent);
  animation: gd-mood-pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.gd-mood-face.is-active .gd-mood-face-label { color: var(--gd-ink); font-weight: 600; }
.gd-mood-face.is-active::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 16px; height: 2px;
  transform: translateX(-50%);
  border-radius: 2px;
  background: color-mix(in srgb, var(--mood-c) 70%, transparent);
}
.gd-mood-face { position: relative; }
.gd-mood-face:disabled { cursor: default; }
.gd-mood-face:focus-visible { outline: 2px solid var(--gd-accent); outline-offset: 2px; }
@keyframes gd-mood-pop {
  0% { transform: translateY(0) scale(0.92); }
  60% { transform: translateY(-4px) scale(1.12); }
  100% { transform: translateY(-3px) scale(1.08); }
}
@media (prefers-reduced-motion: reduce) {
  .gd-mood-face.is-active .gd-mood-face-emoji { animation: none; }
}
.gd-mood-label { margin: 10px 0 0; text-align: center; font-size: 13px; font-weight: 600; color: var(--gd-ink-3); }
/* 已记录时用同色加深，保留心情色彩又不牺牲可读性（浅色气泡色直接做文字会看不清） */
.gd-mood-label.is-set { color: color-mix(in srgb, var(--mood-c) 52%, #14171b); }
.gd-mood-tip { margin: 3px 0 0; text-align: center; font-size: 11px; line-height: 16px; color: var(--gd-ink-3); }
/* 近 7 天：白底面板（与心情区的软色底形成层次），承载柱状与摘要 */
.gd-mood-panel {
  margin-top: 12px; padding: 10px 10px 8px;
  border-radius: 14px;
  background: #fff;
  box-shadow:
    0 1px 2px rgba(17, 20, 24, 0.03),
    inset 0 0 0 1px rgba(17, 20, 24, 0.04);
}
.gd-mood-panel-head {
  display: flex; align-items: baseline; justify-content: space-between; gap: 8px;
  font-size: 10.5px; line-height: 14px; color: var(--gd-ink-3);
  font-variant-numeric: tabular-nums;
}
.gd-mood-panel-head span:first-child { font-weight: 600; color: var(--gd-ink-2); }
/* 周柱：柱子放在固定高轨道里并贴底，日期行与柱底永远在同一条基线上 */
.gd-mood-week { display: flex; justify-content: space-between; margin-top: 8px; padding: 0 2px; }
.gd-mood-col {
  display: flex; flex-direction: column; align-items: center;
  flex: 1; min-width: 0;
  padding: 3px 0 2px; border-radius: 9px;
}
.gd-mood-col.is-today { background: rgba(17, 17, 17, 0.04); }
.gd-mood-track { display: flex; align-items: flex-end; height: 46px; }
.gd-mood-bar {
  display: block; width: 14px;
  border-radius: 5px 5px 2px 2px;
  min-height: 5px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
}
.gd-mood-day { margin-top: 5px; font-size: 10.5px; color: var(--gd-ink-3); }
.gd-mood-day.is-today { color: var(--gd-ink); font-weight: 600; }
.gd-mood-ledger-btn {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  width: 100%; margin-top: 12px; padding: 8px 0 0;
  border: none; border-top: 1px dashed var(--gd-border); border-radius: 0;
  background: transparent; font-family: inherit; font-size: 12px; color: var(--gd-ink-2); cursor: pointer;
}
.gd-mood-ledger-btn:hover { color: var(--gd-ink); }

/* ===== AI 主动发现（扁平时间线） ===== */
.gd-icon-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  border: none; background: transparent; color: var(--gd-ink-3); cursor: pointer;
}
.gd-icon-btn:hover { background: #eceef1; color: var(--gd-ink); }
.gd-ai-entry {
  display: flex; align-items: center; gap: 12px;
  width: 100%; padding: 12px 13px;
  margin: 10px 0 2px;
  border: 1px solid var(--gd-border); border-radius: 14px;
  background: var(--gd-surface); cursor: pointer;
  box-shadow: 0 1px 2px rgba(17, 20, 24, 0.04);
  font-family: inherit; text-align: left;
  -webkit-tap-highlight-color: transparent;
}
.gd-ai-entry:active { background: #f7f8fa; }
.gd-ai-entry:focus-visible { outline: 2px solid var(--gd-accent); outline-offset: -2px; border-radius: 8px; }
.gd-ai-badge {
  flex: none; width: 34px; height: 34px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: #f5f6f8;
}
.gd-ai-badge-img {
  width: 28px; height: 28px; object-fit: contain;
  user-select: none; -webkit-user-select: none; -webkit-user-drag: none; pointer-events: none;
}
.gd-ai-entry-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.gd-ai-entry-title { font-size: 14px; font-weight: 600; color: var(--gd-ink); }
.gd-ai-entry-sub { font-size: 12px; line-height: 17px; color: var(--gd-ink-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gd-ai-chev { color: var(--gd-ink-quiet); flex: none; }

/* ===== 更多：单排横向滑动入口 ===== */
.gd-tile-scroll {
  margin: 10px -2px 0;
  overflow-x: auto; overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  scroll-snap-type: x proximity;
  /* 两侧渐隐：让滑出屏幕的入口自然淡掉，而不是被硬生生切一半 */
  mask-image: linear-gradient(to right, transparent 0, #000 12px, #000 calc(100% - 16px), transparent 100%);
  -webkit-mask-image: linear-gradient(to right, transparent 0, #000 12px, #000 calc(100% - 16px), transparent 100%);
}
.gd-tile-scroll::-webkit-scrollbar { display: none; }
.gd-tile-track {
  display: flex; align-items: flex-start; justify-content: center;
  gap: 12px; width: max-content; min-width: 100%;
  padding: 2px 2px 2px;
}
.gd-tile {
  flex: none; width: 58px; scroll-snap-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 0; border: none; background: transparent; cursor: pointer;
  font-family: inherit; -webkit-tap-highlight-color: transparent;
}
.gd-tile:active .gd-tile-chip { transform: scale(0.94); }
.gd-tile:focus-visible { outline: 2px solid var(--gd-accent); outline-offset: 2px; border-radius: 12px; }
.gd-tile-chip {
  width: 42px; height: 42px; border-radius: 13px;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s ease;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.6);
}
.gd-tile-label { font-size: 11px; line-height: 15px; color: var(--gd-ink-2); white-space: nowrap; }

/* ===== 心情台账弹窗 ===== */
.gd-ledger-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 6px; }
.gd-ledger-cell { aspect-ratio: 1; border-radius: 6px; min-height: 22px; }
.gd-ledger-legend { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 14px; }
.gd-ledger-lg { display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--gd-ink-2); }
.gd-ledger-lg i { width: 10px; height: 10px; border-radius: 3px; }
.gd-ledger-empty { margin: 16px 0 4px; font-size: 13px; color: var(--gd-ink-3); text-align: center; }
.gd-ledger-list { list-style: none; margin: 14px 0 0; padding: 0; max-height: 220px; overflow-y: auto; }
.gd-ledger-row { display: flex; align-items: center; gap: 8px; padding: 7px 0; }
.gd-ledger-row + .gd-ledger-row { border-top: 1px solid var(--gd-border); }
.gd-ledger-dot { flex: none; width: 10px; height: 10px; border-radius: 50%; }
.gd-ledger-lb { font-size: 13px; color: var(--gd-ink); }
.gd-ledger-src { margin-left: auto; font-size: 11px; color: var(--gd-ink-3); }
.gd-ledger-tm { font-size: 11px; color: var(--gd-ink-3); font-variant-numeric: tabular-nums; }
</style>
