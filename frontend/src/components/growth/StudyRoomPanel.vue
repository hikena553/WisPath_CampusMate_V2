<template>
  <div class="study-room">
    <!-- ==== 番茄钟 ==== -->
    <section class="sr-hero">
      <div class="sr-modes" role="tablist" aria-label="计时模式">
        <button
          v-for="m in MODES" :key="m.key"
          type="button" role="tab" :aria-selected="mode === m.key"
          class="sr-mode" :class="{ 'is-active': mode === m.key }"
          @click="switchMode(m.key)"
        >
          {{ m.label }}
        </button>
      </div>

      <div class="sr-dial">
        <svg viewBox="0 0 220 220" class="sr-ring" aria-hidden="true">
          <defs>
            <linearGradient id="srGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#1a4fd6" />
              <stop offset="100%" stop-color="#5f8bf0" />
            </linearGradient>
          </defs>
          <circle class="sr-ring-track" cx="110" cy="110" r="92" />
          <circle
            class="sr-ring-progress" cx="110" cy="110" r="92"
            :stroke-dasharray="RING_C" :stroke-dashoffset="dashOffset"
            transform="rotate(-90 110 110)"
          />
        </svg>
        <div class="sr-dial-inner">
          <p class="sr-clock">{{ clockText }}</p>
          <p class="sr-state">{{ stateLabel }}</p>
          <p v-if="title.trim()" class="sr-dial-task">{{ title }}</p>
        </div>
      </div>

      <!-- 时长自定义：倒计时模式可直接输入分钟数；自由模式正计时 -->
      <div v-if="mode !== 'free'" class="sr-duration">
        <span class="sr-duration-label">计时时长</span>
        <button type="button" class="sr-step" :disabled="durationLocked" @click="adjustDuration(-5)">−</button>
        <input
          v-model.number="durationMinutes" class="sr-duration-input"
          type="number" min="1" max="180" inputmode="numeric"
          :disabled="durationLocked" aria-label="计时时长（分钟）"
        />
        <span class="sr-duration-unit">分钟</span>
        <button type="button" class="sr-step" :disabled="durationLocked" @click="adjustDuration(5)">+</button>
      </div>
      <p v-else class="sr-free-hint">正计时 · 不设固定时长，结束时按实际学习时间记录</p>

      <div class="sr-task-field">
        <el-icon :size="14"><EditPen /></el-icon>
        <input
          v-model="title" maxlength="40" :disabled="running"
          placeholder="这次专注学什么？（选填）"
        />
      </div>

      <div v-if="todayPlanTasks.length" class="sr-chips">
        <span class="sr-chips-label">今日任务</span>
        <button
          v-for="t in todayPlanTasks" :key="t.title"
          type="button" class="sr-chip" :class="{ 'is-on': title === t.title }"
          :disabled="running" @click="title = t.title"
        >{{ t.title }}</button>
      </div>

      <div class="sr-actions">
        <button
          v-if="!running" type="button" class="sr-btn is-primary"
          :disabled="!canStart" @click="startOrResume"
        >{{ startLabel }}</button>
        <button v-else type="button" class="sr-btn" @click="pause">暂停</button>
        <button
          v-if="running || elapsed > 0" type="button" class="sr-btn is-ghost"
          @click="finishEarly"
        >结束</button>
        <button
          v-if="!running && elapsed > 0" type="button" class="sr-btn is-ghost"
          @click="reset"
        >重置</button>
      </div>
      <p class="sr-hint">时长可自由调整；自由模式正计时，结束时按实际学习时长记录</p>
    </section>

    <!-- ==== 今日专注 ==== -->
    <section class="sr-card">
      <div class="sr-card-head">
        <h3>今日专注</h3>
        <span class="sr-card-sub">
          <b>{{ overview.today.session_count }}</b> 次 · <b>{{ fmtDuration(overview.today.focus_minutes) }}</b>
        </span>
      </div>
      <ul v-if="todaySessions.length" class="sr-list">
        <li v-for="s in todaySessions" :key="s.id" class="sr-row">
          <span class="sr-row-ico"><el-icon :size="14"><Timer /></el-icon></span>
          <span class="sr-row-main">
            <b>{{ s.task_title || '专注学习' }}</b>
            <small>{{ timeRange(s) }}</small>
          </span>
          <span class="sr-row-min">{{ s.actual_minutes }}′</span>
        </li>
      </ul>
      <p v-else class="sr-empty">今天还没有专注记录，完成一个番茄钟就会出现在这里</p>
    </section>

    <!-- ==== 近两周 ==== -->
    <section class="sr-card">
      <div class="sr-card-head">
        <h3>近两周</h3>
        <span class="sr-card-sub">共 {{ fmtDuration(rangeMinutes) }}</span>
      </div>
      <div class="sr-bars">
        <div v-for="d in chartDays" :key="d.key" class="sr-bar-col" :title="`${d.month}月${d.day}日 · ${d.minutes} 分钟`">
          <span class="sr-bar-track">
            <span class="sr-bar" :class="{ 'is-today': d.isToday }" :style="{ height: d.height + 'px' }"></span>
          </span>
          <span class="sr-bar-lb" :class="{ 'is-today': d.isToday }">{{ d.day }}</span>
        </div>
      </div>
    </section>

    <!-- ==== 历史记录 ==== -->
    <section class="sr-card">
      <div class="sr-card-head">
        <h3>历史记录</h3>
        <span class="sr-card-sub">近 30 天</span>
      </div>
      <div v-if="historyGroups.length" class="sr-groups">
        <div v-for="g in historyGroups" :key="g.date" class="sr-group">
          <div class="sr-group-head">
            <span>{{ g.label }}</span>
            <span>{{ fmtDuration(g.minutes) }}</span>
          </div>
          <ul class="sr-list">
            <li v-for="s in g.sessions" :key="s.id" class="sr-row">
              <span class="sr-row-main">
                <b>{{ s.task_title || '专注学习' }}</b>
                <small>{{ timeRange(s) }}<template v-if="!s.completed"> · 提前结束</template></small>
              </span>
              <span class="sr-row-min">{{ s.actual_minutes }}′</span>
            </li>
          </ul>
        </div>
      </div>
      <div v-else class="sr-empty-block">
        <img :src="siteMascot" :alt="siteName" class="sr-empty-img" draggable="false" />
        <p>还没有历史专注记录</p>
        <small>完成第一个番茄钟，这里会留下你的学习节奏</small>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { EditPen, Timer } from '@element-plus/icons-vue'
import { getToday, type TodayTask } from '@/api/plan'
import {
  createStudySession,
  getStudyOverview,
  type StudyMode,
  type StudyOverview,
  type StudySession,
} from '@/api/studyRoom'
import { useSiteConfig } from '@/composables/useSiteConfig'

type TimerMode = StudyMode | 'free'

const MODES: { key: TimerMode; label: string; minutes: number }[] = [
  { key: 'free', label: '自由', minutes: 0 },
  { key: 'focus', label: '专注', minutes: 25 },
  { key: 'short_break', label: '短休', minutes: 5 },
  { key: 'long_break', label: '长休', minutes: 15 },
]

const RING_C = 2 * Math.PI * 92
const STORAGE_KEY = 'study-room-timer-v1'

const { siteMascot, siteName } = useSiteConfig()

const overview = ref<StudyOverview>({
  today: { date: '', focus_minutes: 0, session_count: 0 },
  days: [],
  sessions: [],
})
const todayPlanTasks = ref<TodayTask[]>([])

// ===== 计时状态 =====
const mode = ref<TimerMode>('focus')
const plannedSeconds = ref(25 * 60)
const elapsedBase = ref(0) // 暂停时已累计的秒数
const running = ref(false)
const runStartedAt = ref(0) // 本轮开始的本地时间戳(ms)
const sessionStartedAt = ref<string | null>(null) // 开始计时时的 ISO，用于记录
const title = ref('')
const tick = ref(0)

const elapsed = computed(() => {
  void tick.value
  const live = running.value ? Math.max(0, Math.floor((Date.now() - runStartedAt.value) / 1000)) : 0
  const total = elapsedBase.value + live
  return mode.value === 'free' ? total : Math.min(plannedSeconds.value, total)
})
const remaining = computed(() => Math.max(0, plannedSeconds.value - elapsed.value))
const canStart = computed(() => mode.value === 'free' || remaining.value > 0)
const durationLocked = computed(() => running.value || elapsed.value > 0)
const progressRatio = computed(() => {
  if (mode.value === 'free') return Math.min(1, elapsed.value / 3600)
  return plannedSeconds.value > 0 ? elapsed.value / plannedSeconds.value : 0
})
const dashOffset = computed(() => RING_C * (1 - progressRatio.value))

/** 可直接输入任意分钟数，不再固定 25/5/15 */
const durationMinutes = computed({
  get: () => Math.round(plannedSeconds.value / 60),
  set: (value: number) => {
    if (durationLocked.value) return
    const minutes = Math.min(180, Math.max(1, Math.round(Number(value) || 0)))
    plannedSeconds.value = minutes * 60
    persist()
  },
})

function fmtCountUp(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(s).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

const clockText = computed(() => {
  if (mode.value === 'free') return fmtCountUp(elapsed.value)
  const s = remaining.value
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})
const stateLabel = computed(() => {
  if (running.value) {
    if (mode.value === 'free') return '自由计时中'
    return mode.value === 'focus' ? '专注中' : '休息中'
  }
  if (elapsed.value > 0) return '已暂停'
  return '准备开始'
})
const startLabel = computed(() => {
  if (mode.value === 'free') return elapsed.value > 0 ? '继续计时' : '开始计时'
  const isFocus = mode.value === 'focus'
  if (elapsed.value > 0) return isFocus ? '继续专注' : '继续休息'
  return isFocus ? '开始专注' : '开始休息'
})

// ===== 数据展示 =====
const todaySessions = computed(() =>
  overview.value.sessions.filter(s => s.study_date === overview.value.today.date),
)
const rangeMinutes = computed(() => overview.value.days.reduce((sum, d) => sum + d.focus_minutes, 0))

const chartDays = computed(() => {
  const days = overview.value.days.slice(-14)
  const max = Math.max(1, ...days.map(d => d.focus_minutes))
  return days.map(d => {
    const minutes = d.focus_minutes
    return {
      key: d.date,
      minutes,
      month: Number(d.date.slice(5, 7)),
      day: Number(d.date.slice(8, 10)),
      isToday: d.date === overview.value.today.date,
      height: minutes ? Math.max(4, Math.round((minutes / max) * 48)) : 2,
    }
  })
})

const historyGroups = computed(() => {
  const groups: { date: string; label: string; minutes: number; sessions: StudySession[] }[] = []
  for (const s of overview.value.sessions) {
    if (s.study_date === overview.value.today.date) continue
    let g = groups.find(x => x.date === s.study_date)
    if (!g) {
      g = { date: s.study_date, label: groupLabel(s.study_date), minutes: 0, sessions: [] }
      groups.push(g)
    }
    g.sessions.push(s)
    g.minutes += s.actual_minutes
  }
  return groups.slice(0, 14)
})

function dateKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function groupLabel(date: string) {
  const today = overview.value.today.date
  const target = new Date(`${date}T00:00:00`)
  const yesterday = new Date(`${today}T00:00:00`)
  yesterday.setDate(yesterday.getDate() - 1)
  if (date === today) return '今天'
  if (date === dateKey(yesterday)) return '昨天'
  return `${target.getMonth() + 1}月${target.getDate()}日`
}
function timeRange(s: StudySession) {
  if (!s.start_time) return '专注'
  return s.end_time ? `${s.start_time} - ${s.end_time}` : s.start_time
}
function fmtDuration(minutes: number) {
  if (minutes < 60) return `${minutes} 分钟`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} 小时 ${m} 分` : `${h} 小时`
}

// ===== 计时操作 =====
function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      mode: mode.value,
      plannedSeconds: plannedSeconds.value,
      elapsedBase: elapsedBase.value,
      running: running.value,
      runStartedAt: runStartedAt.value,
      sessionStartedAt: sessionStartedAt.value,
      title: title.value,
    }))
  } catch { /* 本地存储不可用时仅影响刷新恢复 */ }
}

function restore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const s = JSON.parse(raw)
    if (MODES.some(m => m.key === s.mode)) mode.value = s.mode
    if (typeof s.plannedSeconds === 'number') plannedSeconds.value = Math.max(60, s.plannedSeconds)
    if (typeof s.elapsedBase === 'number') elapsedBase.value = Math.max(0, s.elapsedBase)
    if (typeof s.title === 'string') title.value = s.title
    if (typeof s.sessionStartedAt === 'string') sessionStartedAt.value = s.sessionStartedAt
    if (s.running && typeof s.runStartedAt === 'number') {
      running.value = true
      runStartedAt.value = s.runStartedAt
    }
  } catch { /* 损坏的本地状态直接忽略 */ }
}

function switchMode(next: TimerMode) {
  if (running.value) {
    ElMessage.info('先暂停或结束当前计时再切换模式')
    return
  }
  mode.value = next
  const cfg = MODES.find(m => m.key === next)
  plannedSeconds.value = next === 'free' ? 3600 : (cfg?.minutes ?? 25) * 60
  elapsedBase.value = 0
  sessionStartedAt.value = null
  persist()
}

function adjustDuration(delta: number) {
  if (durationLocked.value) return
  durationMinutes.value = durationMinutes.value + delta
}

function startOrResume() {
  if (running.value) return
  if (mode.value !== 'free' && remaining.value <= 0) reset()
  if (!sessionStartedAt.value) sessionStartedAt.value = new Date().toISOString()
  runStartedAt.value = Date.now()
  running.value = true
  persist()
}

function pause() {
  if (!running.value) return
  elapsedBase.value = elapsed.value
  running.value = false
  persist()
}

function reset() {
  running.value = false
  elapsedBase.value = 0
  runStartedAt.value = 0
  sessionStartedAt.value = null
  persist()
}

function vibrate() {
  try { navigator.vibrate?.(120) } catch { /* 部分浏览器不支持 */ }
}

async function complete() {
  if (!running.value || mode.value === 'free') return
  const wasFocus = mode.value === 'focus'
  const minutes = Math.round(plannedSeconds.value / 60)
  const startIso = sessionStartedAt.value
  running.value = false
  elapsedBase.value = 0
  runStartedAt.value = 0
  sessionStartedAt.value = null
  vibrate()

  if (wasFocus) {
    await saveFocus(minutes, true, startIso)
    ElMessage.success(`完成 ${minutes} 分钟专注，起来活动一下吧`)
    switchMode('short_break')
  } else {
    ElMessage.success('休息结束，准备下一段专注吧')
    switchMode('focus')
  }
  persist()
}

async function finishEarly() {
  const isFree = mode.value === 'free'
  const isStudy = mode.value === 'focus' || isFree
  const minutes = Math.round(elapsed.value / 60)
  const startIso = sessionStartedAt.value
  if (running.value) pause()

  if (isStudy && minutes >= 1) {
    // 自由模式按实际时长记一条；专注模式保留原计划时长用于区分是否提前结束
    const planned = isFree ? minutes : Math.round(plannedSeconds.value / 60)
    await saveFocus(minutes, isFree, startIso, planned)
    ElMessage.success(isFree ? `已记录本次自习 ${minutes} 分钟` : `已记录本次专注 ${minutes} 分钟`)
  } else if (isStudy && elapsed.value > 0) {
    ElMessage.info('不满 1 分钟，本次不记录')
  }
  reset()
}

async function saveFocus(
  actualMinutes: number,
  completed: boolean,
  startIso: string | null,
  plannedMinutes = Math.round(plannedSeconds.value / 60),
) {
  try {
    const actual = Math.max(1, Math.min(actualMinutes, 24 * 60))
    await createStudySession({
      mode: 'focus',
      task_title: title.value.trim() || null,
      planned_minutes: Math.max(actual, Math.min(Math.max(1, plannedMinutes), 24 * 60)),
      actual_minutes: actual,
      completed,
      started_at: startIso,
      ended_at: new Date().toISOString(),
    })
    await loadOverview()
  } catch { /* 失败不打断计时，下一次完成会继续尝试写入 */ }
}

let timer: number | undefined
function ensureTimer() {
  if (timer) return
  timer = window.setInterval(() => {
    tick.value++
    if (running.value && mode.value !== 'free' && remaining.value <= 0) void complete()
  }, 250)
}

watch(title, persist)

async function loadOverview() {
  try {
    overview.value = await getStudyOverview(30)
  } catch { /* 失败保持上一次数据 */ }
}
async function loadTodayTasks() {
  try {
    const tasks = await getToday()
    todayPlanTasks.value = tasks
      .filter(t => !t.checked_today && t.status !== 'done')
      .slice(0, 6)
  } catch { /* 失败则不展示快捷任务 */ }
}

onMounted(() => {
  restore()
  ensureTimer()
  void loadOverview()
  void loadTodayTasks()
})
onUnmounted(() => {
  // 离开自习室视为中断：先结算已专注秒数并暂停，避免把离开页面的时间也算进专注
  if (running.value) {
    elapsedBase.value = elapsed.value
    running.value = false
    persist()
  }
  if (timer) { window.clearInterval(timer); timer = undefined }
})
</script>

<style scoped>
.study-room {
  --sr-ink: #14171a;
  --sr-ink-2: #5b6470;
  --sr-ink-3: #8b939e;
  --sr-line: #e9ebee;
  --sr-soft: #f4f5f7;
  --sr-accent: #1a4fd6;

  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 520px;
  margin: 0 auto;
  padding: 14px 12px 18px;
  box-sizing: border-box;
  color: var(--sr-ink);
}

/* ==== 计时主卡 ==== */
.sr-hero {
  padding: 14px;
  background: #fff;
  border: 1px solid var(--sr-line);
  border-radius: 18px;
  box-shadow: 0 1px 2px rgba(20, 23, 26, 0.035);
}
.sr-modes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 3px;
  background: var(--sr-soft);
  border-radius: 12px;
}
.sr-mode {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 32px;
  border: none;
  border-radius: 9px;
  background: transparent;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--sr-ink-2);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background .18s ease, color .18s ease;
}
.sr-mode.is-active { background: var(--sr-ink); color: #fff; }

.sr-dial {
  position: relative;
  width: 200px;
  height: 200px;
  margin: 12px auto 4px;
}
.sr-ring { display: block; width: 100%; height: 100%; }
.sr-ring-track {
  fill: none;
  stroke: #eef0f3;
  stroke-width: 9;
}
.sr-ring-progress {
  fill: none;
  stroke: url(#srGrad);
  stroke-width: 9;
  stroke-linecap: round;
  transition: stroke-dashoffset .3s linear;
}
.sr-dial-inner {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
}
.sr-clock {
  margin: 0;
  font-size: 40px;
  line-height: 1.05;
  font-weight: 650;
  letter-spacing: -1px;
  font-variant-numeric: tabular-nums;
}
.sr-state { margin: 0; font-size: 11.5px; color: var(--sr-ink-3); }
.sr-dial-task {
  max-width: 140px;
  margin: 2px 0 0;
  font-size: 11.5px;
  line-height: 15px;
  color: var(--sr-ink-2);
  text-align: center;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.sr-task-field {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  padding: 0 11px;
  border: 1px solid var(--sr-line);
  border-radius: 11px;
  background: #fbfbfc;
  color: var(--sr-ink-3);
}

/* 自定义时长 */
.sr-duration {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 0 0 8px;
}
.sr-duration-label { font-size: 11px; color: var(--sr-ink-3); }
.sr-duration-unit { font-size: 11px; color: var(--sr-ink-3); }
.sr-step {
  width: 26px;
  height: 26px;
  padding: 0;
  border: 1px solid var(--sr-line);
  border-radius: 8px;
  background: #fff;
  font-family: inherit;
  font-size: 14px;
  line-height: 1;
  color: var(--sr-ink);
  cursor: pointer;
}
.sr-step:disabled { opacity: .4; }
.sr-duration-input {
  width: 46px;
  height: 26px;
  padding: 0;
  border: 1px solid var(--sr-line);
  border-radius: 8px;
  background: #fff;
  text-align: center;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--sr-ink);
  -moz-appearance: textfield;
  appearance: textfield;
}
.sr-duration-input::-webkit-outer-spin-button,
.sr-duration-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.sr-duration-input:disabled { color: var(--sr-ink-3); }
.sr-free-hint {
  margin: 0 0 8px;
  text-align: center;
  font-size: 11px;
  line-height: 16px;
  color: var(--sr-ink-3);
}
.sr-task-field input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--sr-ink);
}
.sr-task-field input::placeholder { color: #a8aeb6; }
.sr-task-field input:disabled { color: var(--sr-ink-3); }

.sr-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 9px;
  overflow-x: auto;
  scrollbar-width: none;
}
.sr-chips::-webkit-scrollbar { display: none; }
.sr-chips-label { flex: none; font-size: 11px; color: var(--sr-ink-3); }
.sr-chip {
  flex: none;
  max-width: 150px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--sr-line);
  border-radius: 999px;
  background: #fff;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--sr-ink-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}
.sr-chip.is-on { border-color: #c9d5ea; background: #eef3fd; color: var(--sr-accent); }

.sr-actions { display: flex; gap: 8px; margin-top: 13px; }
.sr-btn {
  flex: 1;
  height: 40px;
  border-radius: 11px;
  border: 1px solid var(--sr-line);
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--sr-ink);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.sr-btn.is-primary { flex: 1.6; border-color: transparent; background: var(--sr-ink); color: #fff; }
.sr-btn.is-ghost { flex: .8; border-color: transparent; background: transparent; color: var(--sr-ink-3); font-weight: 500; }
.sr-btn:active { transform: scale(.985); }
.sr-btn:disabled { opacity: .5; }
.sr-hint { margin: 9px 0 0; text-align: center; font-size: 10.5px; line-height: 15px; color: #a8aeb6; }

/* ==== 数据卡 ==== */
.sr-card {
  padding: 13px 14px;
  background: #fff;
  border: 1px solid var(--sr-line);
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(20, 23, 26, 0.035);
}
.sr-card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.sr-card-head h3 { margin: 0; font-size: 13.5px; font-weight: 600; color: var(--sr-ink); }
.sr-card-sub { font-size: 11px; color: var(--sr-ink-3); }
.sr-card-sub b { font-size: 13px; color: var(--sr-ink); font-weight: 600; font-variant-numeric: tabular-nums; }

.sr-list { list-style: none; margin: 8px 0 0; padding: 0; }
.sr-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 0;
  border-top: 1px solid #f1f2f4;
}
.sr-row:first-child { border-top: none; }
.sr-row-ico {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: #eef3fd;
  color: var(--sr-accent);
}
.sr-row-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.sr-row-main b { font-size: 12.5px; font-weight: 500; color: var(--sr-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sr-row-main small { font-size: 10.5px; color: var(--sr-ink-3); font-variant-numeric: tabular-nums; }
.sr-row-min { flex: none; font-size: 13px; font-weight: 600; color: var(--sr-ink); font-variant-numeric: tabular-nums; }
.sr-empty { margin: 10px 0 2px; font-size: 12px; line-height: 18px; color: var(--sr-ink-3); }

/* 近两周柱状 */
.sr-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 70px;
  margin-top: 10px;
}
.sr-bar-col { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.sr-bar-track { display: flex; align-items: flex-end; height: 48px; width: 100%; }
.sr-bar {
  width: 100%;
  max-width: 16px;
  margin: 0 auto;
  border-radius: 3px;
  background: #dfe4ea;
  transition: height .25s ease;
}
.sr-bar.is-today { background: var(--sr-accent); }
.sr-bar-lb { font-size: 9.5px; line-height: 12px; color: var(--sr-ink-3); font-variant-numeric: tabular-nums; }
.sr-bar-lb.is-today { color: var(--sr-accent); font-weight: 600; }

/* 历史分组 */
.sr-groups { margin-top: 6px; }
.sr-group { padding-top: 8px; }
.sr-group-head {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 11px;
  color: var(--sr-ink-3);
}
.sr-group-head span:first-child { color: var(--sr-ink-2); font-weight: 500; }
.sr-group + .sr-group { border-top: 1px solid #f1f2f4; }

.sr-empty-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 0 8px;
}
.sr-empty-img { width: 46px; height: 46px; object-fit: contain; opacity: .92; }
.sr-empty-block p { margin: 2px 0 0; font-size: 12.5px; color: var(--sr-ink-2); }
.sr-empty-block small { font-size: 11px; color: var(--sr-ink-3); }

@media (max-width: 360px) {
  .sr-clock { font-size: 36px; }
  .sr-dial { width: 176px; height: 176px; }
}
</style>
