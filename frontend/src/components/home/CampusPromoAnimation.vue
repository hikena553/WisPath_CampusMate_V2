<template>
  <div
    ref="rootRef"
    class="promo"
    :class="{ 'is-paused': paused }"
    role="img"
    :aria-label="ariaLabel"
  >
    <!-- ===== 粒子层 ===== -->
    <canvas ref="canvasRef" class="promo-particles" aria-hidden="true"></canvas>
    <div class="promo-grid" aria-hidden="true"></div>
    <div class="promo-scan" aria-hidden="true"></div>

    <!-- ===== 分镜 ===== -->
    <template v-if="!reduced">
      <section
        v-for="(s, i) in scenes"
        :key="s.key"
        class="scene"
        :class="{ active: i === sceneIndex }"
      >
        <!-- ① 项目简介：纯文字 + 流程图 -->
        <div v-if="s.type === 'intro'" class="scene-body">
          <span class="kicker anim" :style="delay(0)">{{ s.kicker }}</span>
          <h3 class="title anim" :style="delay(1)">{{ s.title }}</h3>
          <p class="desc anim" :style="delay(2)">{{ s.desc }}</p>
          <ol class="flow">
            <li v-for="(f, fi) in s.flow" :key="f.label" class="anim" :style="delay(3 + fi)">
              <em>{{ fi + 1 }}</em>
              <div class="row-txt"><b>{{ f.label }}</b><small>{{ f.hint }}</small></div>
            </li>
          </ol>
        </div>

        <!-- ② 产品功能：小窗演示 + 留白说明 -->
        <div v-else-if="s.type === 'feature'" class="scene-body feature-body">
          <div class="feature-text">
            <span class="kicker anim" :style="delay(0)">{{ s.kicker }}</span>
            <h3 class="title anim" :style="delay(1)">{{ s.title }}</h3>
            <p class="desc anim" :style="delay(2)">{{ s.desc }}</p>
            <div class="chips">
              <span v-for="(c, ci) in s.chips" :key="c" class="chip anim" :style="delay(3 + ci)">{{ c }}</span>
            </div>
          </div>
          <div class="pip anim" :style="delay(1)">
            <span class="pip-bar"><i class="pip-dot"></i>功能演示</span>
            <video
              class="pip-video"
              :src="s.video"
              :poster="s.poster"
              muted
              loop
              playsinline
              preload="metadata"
            />
          </div>
        </div>

        <!-- ③ 测试与质量 -->
        <div v-else-if="s.type === 'test'" class="scene-body">
          <span class="kicker anim" :style="delay(0)">{{ s.kicker }}</span>
          <h3 class="title anim" :style="delay(1)">{{ s.title }}</h3>
          <p class="desc anim" :style="delay(2)">{{ s.desc }}</p>
          <ul class="points">
            <li v-for="(p, pi) in s.points" :key="p" class="anim" :style="delay(3 + pi)">{{ p }}</li>
          </ul>
        </div>

        <!-- ④ 未来展望 · 演进路线 -->
        <div v-else-if="s.type === 'roadmap'" class="scene-body">
          <span class="kicker anim" :style="delay(0)">{{ s.kicker }}</span>
          <h3 class="title anim" :style="delay(1)">{{ s.title }}</h3>
          <p class="desc anim" :style="delay(2)">{{ s.desc }}</p>
          <ol class="roadmap">
            <li v-for="(r, ri) in s.phases" :key="r.phase" class="anim" :style="delay(3 + ri)">
              <em>{{ r.phase }}</em>
              <b>{{ r.title }}</b>
              <small>{{ r.desc }}</small>
            </li>
          </ol>
        </div>

        <!-- ⑤ 未来展望 · 实时运行 -->
        <div v-else class="scene-body">
          <span class="kicker anim" :style="delay(0)">{{ s.kicker }}</span>
          <h3 class="title anim" :style="delay(1)">{{ s.title }}</h3>
          <p class="desc anim" :style="delay(2)">{{ s.desc }}</p>
          <div class="metrics">
            <div v-for="(m, mi) in futureMetrics" :key="m.label" class="metric anim" :style="delay(3 + mi)">
              <b>{{ m.value }}</b><span>{{ m.label }}</span>
            </div>
          </div>
          <div class="highlights">
            <span v-for="(h, hi) in s.highlights" :key="h" class="chip anim" :style="delay(7 + hi)">{{ h }}</span>
          </div>
          <span class="live-line anim" :style="delay(10)">
            覆盖 <b>{{ collegeCount }}</b> 个学院 · 平均响应 <b>{{ avgResponseTime.toFixed(1) }}</b>s
          </span>
          <span class="slogan anim" :style="delay(11)">{{ s.slogan }}</span>
        </div>
      </section>
    </template>

    <!-- ===== 静态兜底（减弱动态效果） ===== -->
    <div v-else class="promo-static">
      <span class="kicker">{{ copy.intro.kicker }}</span>
      <h3 class="title">{{ copy.intro.title }}</h3>
      <p class="desc">{{ copy.intro.desc }}</p>
      <div class="static-feats">
        <span v-for="f in copy.features" :key="f.key">{{ f.title }}</span>
      </div>
      <span class="slogan">{{ copy.future.slogan }}</span>
    </div>

    <!-- 当前分镜进度 -->
    <div class="progress" aria-hidden="true">
      <i :class="{ on: barOn }" :style="{ transitionDuration: barDuration }"></i>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * 宣传文案由 tokenplan（阿里云百炼）模型生成后落库，
 * 分镜结构：项目简介（文字+流程图）→ 产品功能（小窗演示+留白说明）→ 测试与质量 → 未来展望（路线图 + 实时运行）。
 */
const copy = {
  intro: {
    kicker: '项目简介',
    title: '智慧校园新篇章',
    desc: 'AI 赋能高校数字化服务',
    flow: [
      { label: '用户入口', hint: '师生登录平台' },
      { label: 'AI 智能体', hint: '绵小城极速响应' },
      { label: '数据与知识', hint: '调用校园信息库' },
      { label: '服务与预警', hint: '办事流转三级预警' },
    ],
  },
  features: [
    { key: 'chat', title: '智能对话', desc: '绵小城有问必答', chips: ['流式回复', '文件上传'] },
    { key: 'voice', title: '语音交互', desc: '开口即达轻松办事', chips: ['语音输入', '实时播报'] },
    { key: 'schedule', title: '学业管理', desc: '课表成绩一目了然', chips: ['课表查询', '成绩分析'] },
    { key: 'service', title: '办事服务', desc: '请假审批线上流转', chips: ['在线申请', '审批流转'] },
  ],
  test: {
    kicker: '测试与质量',
    title: '质量保障',
    desc: '全链路守护稳定运行',
    points: ['后端用例验证', '前端类型检查', 'CI 流水线构建', '容器部署冒烟'],
  },
  roadmap: {
    kicker: '未来展望',
    title: '演进路线',
    desc: '从校园助手走向智慧中枢',
    phases: [
      { phase: '阶段一', title: '校园问答助手', desc: '快速解答常见问题' },
      { phase: '阶段二', title: '主动服务管家', desc: '打通办事与提醒' },
      { phase: '阶段三', title: '智慧决策中枢', desc: '数据驱动管理洞察' },
      { phase: '阶段四', title: '开放生态平台', desc: '连接校园与未来' },
    ],
  },
  future: {
    kicker: '未来展望',
    title: '迈向智慧校园新生态',
    desc: '从助手到中枢，开放协同赋能成长',
    highlights: ['多智能体协同', '个性化学业规划', '全校数据智脑'],
    slogan: '懂校园，更懂你',
  },
}

/** 核心功能操作录屏（public/videos），海报取项目介绍截图以避免黑帧 */
const VIDEO_META: Record<string, { video: string; poster?: string }> = {
  chat: { video: '/videos/chat.webm', poster: '/images/intro/01-chat.png' },
  voice: { video: '/videos/voice.webm', poster: '/images/intro/01-chat.png' },
  schedule: { video: '/videos/schedule.webm', poster: '/images/intro/03-schedule.png' },
  service: { video: '/videos/service.webm', poster: '/images/intro/05-service.png' },
}

const props = withDefaults(
  defineProps<{
    studentCount?: number
    teacherCount?: number
    collegeCount?: number
    conversationCount?: number
    knowledgeCount?: number
    avgResponseTime?: number
  }>(),
  {
    studentCount: 0,
    teacherCount: 0,
    collegeCount: 0,
    conversationCount: 0,
    knowledgeCount: 0,
    avgResponseTime: 0,
  },
)

function fmt(v: number | null | undefined) {
  return (v ?? 0).toLocaleString('zh-CN')
}

type SceneType = 'intro' | 'feature' | 'test' | 'roadmap' | 'future'

interface Scene {
  key: string
  type: SceneType
  seconds: number
  kicker: string
  title: string
  desc: string
  flow?: { label: string; hint: string }[]
  video?: string
  poster?: string
  chips?: string[]
  points?: string[]
  phases?: { phase: string; title: string; desc: string }[]
  highlights?: string[]
  slogan?: string
}

/** 各分镜时长（秒）：简介/未来给足阅读时间 */
const scenes: Scene[] = [
  {
    key: 'intro',
    type: 'intro',
    seconds: 5,
    kicker: copy.intro.kicker,
    title: copy.intro.title,
    desc: copy.intro.desc,
    flow: copy.intro.flow,
  },
  ...copy.features.map<Scene>((f, i) => ({
    key: f.key,
    type: 'feature',
    seconds: 4,
    kicker: `产品功能 · 0${i + 1}`,
    title: f.title,
    desc: f.desc,
    video: VIDEO_META[f.key]?.video,
    poster: VIDEO_META[f.key]?.poster,
    chips: f.chips,
  })),
  {
    key: 'test',
    type: 'test',
    seconds: 4.5,
    kicker: copy.test.kicker,
    title: copy.test.title,
    desc: copy.test.desc,
    points: copy.test.points,
  },
  {
    key: 'roadmap',
    type: 'roadmap',
    seconds: 5.5,
    kicker: copy.roadmap.kicker,
    title: copy.roadmap.title,
    desc: copy.roadmap.desc,
    phases: copy.roadmap.phases,
  },
  {
    key: 'future',
    type: 'future',
    seconds: 6,
    kicker: copy.future.kicker,
    title: copy.future.title,
    desc: copy.future.desc,
    highlights: copy.future.highlights,
    slogan: copy.future.slogan,
  },
]

/** 未来分镜的实时运行数据：随首页看板数据变化而更新 */
const futureMetrics = computed(() => [
  { label: '在校学生', value: fmt(props.studentCount) },
  { label: '在职教师', value: fmt(props.teacherCount) },
  { label: 'AI 会话', value: fmt(props.conversationCount) },
  { label: '知识库条目', value: fmt(props.knowledgeCount) },
])

const ariaLabel = `产品宣传动画：${copy.intro.title}；${copy.roadmap.desc}；${copy.future.slogan}`

/* ===== 分镜推进 ===== */
const ITEM_STEP = 0.12

const reduced = typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const sceneIndex = ref(0)
const paused = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)

/** 场景内元素逐个入场的延迟 */
function delay(i: number) {
  return { animationDelay: `${(0.18 + ITEM_STEP * i).toFixed(2)}s` }
}

const sceneMs = () => (scenes[sceneIndex.value]?.seconds ?? 4) * 1000

let sceneTimer: ReturnType<typeof setTimeout> | null = null

function clearSceneTimer() {
  if (sceneTimer) {
    clearTimeout(sceneTimer)
    sceneTimer = null
  }
}

/** 按当前分镜时长调度下一个分镜 */
function scheduleScene() {
  clearSceneTimer()
  if (reduced) return
  sceneTimer = setTimeout(() => {
    sceneIndex.value = (sceneIndex.value + 1) % scenes.length
  }, sceneMs())
}

/* ===== 进度条：每个分镜单独走满一次 ===== */
const barOn = ref(false)
const barDuration = ref('0ms')
let barRaf = 0

function runBar(ms: number) {
  cancelAnimationFrame(barRaf)
  barOn.value = false
  barDuration.value = '0ms'
  barRaf = requestAnimationFrame(() => {
    barRaf = requestAnimationFrame(() => {
      barDuration.value = `${ms}ms`
      barOn.value = true
    })
  })
}

/* ===== 视频播放：仅当前分镜播放，其余暂停 ===== */
function syncVideo() {
  const root = rootRef.value
  if (!root) return
  root.querySelectorAll('video').forEach((v) => v.pause())
  const active = root.querySelector<HTMLVideoElement>('.scene.active video')
  if (active) {
    try {
      active.currentTime = 0
    } catch {
      /* 元数据未就绪时忽略 */
    }
    active.play().catch(() => {
      /* 自动播放被拦截时静默降级为海报帧 */
    })
  }
}

watch(sceneIndex, () => {
  nextTick(() => {
    syncVideo()
    runBar(sceneMs())
  })
  scheduleScene()
})

/* ===== 粒子系统 ===== */
const PARTICLE_COUNT = 46
const LINK_DISTANCE = 92

interface Particle { x: number; y: number; vx: number; vy: number; r: number; rgb: string }

let ctx: CanvasRenderingContext2D | null = null
let particles: Particle[] = []
let rafId = 0
let width = 0
let height = 0
let dpr = 1
let resizeObserver: ResizeObserver | null = null

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  width = Math.max(1, rect.width)
  height = Math.max(1, rect.height)
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(width * dpr)
  canvas.height = Math.round(height * dpr)
  ctx = canvas.getContext('2d')
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function seedParticles() {
  particles = Array.from({ length: PARTICLE_COUNT }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.24,
    vy: (Math.random() - 0.5) * 0.24,
    r: Math.random() * 1.5 + 0.7,
    rgb: Math.random() < 0.5 ? '125,211,252' : '196,181,253',
  }))
}

function frame() {
  const c = ctx
  if (!c) return
  c.clearRect(0, 0, width, height)

  for (const p of particles) {
    p.x += p.vx
    p.y += p.vy
    if (p.x < 0 || p.x > width) p.vx *= -1
    if (p.y < 0 || p.y > height) p.vy *= -1
  }

  for (let i = 0; i < particles.length; i++) {
    const a = particles[i]
    for (let j = i + 1; j < particles.length; j++) {
      const b = particles[j]
      const dx = a.x - b.x
      const dy = a.y - b.y
      const d2 = dx * dx + dy * dy
      if (d2 < LINK_DISTANCE * LINK_DISTANCE) {
        const alpha = (1 - Math.sqrt(d2) / LINK_DISTANCE) * 0.32
        c.strokeStyle = `rgba(125,211,252,${alpha.toFixed(3)})`
        c.lineWidth = 0.7
        c.beginPath()
        c.moveTo(a.x, a.y)
        c.lineTo(b.x, b.y)
        c.stroke()
      }
    }
  }

  for (const p of particles) {
    c.fillStyle = `rgba(${p.rgb},0.85)`
    c.beginPath()
    c.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    c.fill()
  }

  rafId = requestAnimationFrame(frame)
}

function startParticles() {
  if (reduced || rafId) return
  rafId = requestAnimationFrame(frame)
}
function stopParticles() {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = 0
  }
}

/* ===== 可见性：切到后台暂停，回到前台恢复 ===== */
function onVisibility() {
  const hidden = document.hidden
  paused.value = hidden
  if (hidden) {
    clearSceneTimer()
    stopParticles()
    rootRef.value?.querySelectorAll('video').forEach((v) => v.pause())
  } else {
    scheduleScene()
    startParticles()
    syncVideo()
    runBar(sceneMs())
  }
}

onMounted(() => {
  if (reduced) return
  resizeCanvas()
  seedParticles()
  startParticles()
  nextTick(() => {
    syncVideo()
    runBar(sceneMs())
  })
  scheduleScene()

  resizeObserver = new ResizeObserver(() => {
    resizeCanvas()
    seedParticles()
  })
  if (canvasRef.value) resizeObserver.observe(canvasRef.value)

  document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
  clearSceneTimer()
  cancelAnimationFrame(barRaf)
  stopParticles()
  resizeObserver?.disconnect()
  resizeObserver = null
  rootRef.value?.querySelectorAll('video').forEach((v) => v.pause())
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped>
.promo {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: radial-gradient(ellipse 72% 62% at 50% 40%, #14264a 0%, #0c1730 55%, #070c1a 100%);
  color: #e8eefc;
  font-family: 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'Microsoft YaHei', system-ui, sans-serif;
}

/* ===== 粒子与背景 ===== */
.promo-particles { position: absolute; inset: 0; width: 100%; height: 100%; }

.promo-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(125, 211, 252, 0.09) 1px, transparent 1px),
    linear-gradient(90deg, rgba(125, 211, 252, 0.09) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: radial-gradient(ellipse 82% 72% at 50% 45%, #000 35%, transparent 100%);
  -webkit-mask-image: radial-gradient(ellipse 82% 72% at 50% 45%, #000 35%, transparent 100%);
  animation: gridDrift 12s linear infinite;
}
@keyframes gridDrift { from { background-position: 0 0, 0 0; } to { background-position: 0 34px, 34px 0; } }

.promo-scan {
  position: absolute;
  left: 0;
  right: 0;
  height: 84px;
  background: linear-gradient(180deg, rgba(125, 211, 252, 0) 0%, rgba(125, 211, 252, 0.08) 50%, rgba(125, 211, 252, 0) 100%);
  animation: scanMove 7s ease-in-out infinite;
}
@keyframes scanMove { 0% { top: -84px; } 100% { top: 100%; } }

/* ===== 分镜容器 ===== */
.scene {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.6s ease;
}
.scene.active { opacity: 1; }

.scene-body {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 9px;
  padding: 20px 18px 46px;
}

/* ===== 元素入场 ===== */
.anim { opacity: 1; }
.scene.active .anim {
  animation: riseIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes riseIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.kicker {
  font-size: 11px;
  letter-spacing: 0.16em;
  color: #7dd3fc;
  padding: 2px 9px;
  border: 1px solid rgba(125, 211, 252, 0.42);
  border-radius: 999px;
  background: rgba(10, 20, 40, 0.55);
  backdrop-filter: blur(3px);
}
.title {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
  color: #fff;
  text-shadow: 0 2px 16px rgba(4, 9, 22, 0.95);
}
.desc {
  margin: 0;
  font-size: 12.5px;
  color: #cbd8ee;
  text-shadow: 0 1px 10px rgba(4, 9, 22, 0.9);
}

/* ===== ① 流程图 ===== */
.flow {
  position: relative;
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  width: 100%;
  max-width: 300px;
  display: flex;
  flex-direction: column;
}
.flow::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 2%;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #7dd3fc;
  box-shadow: 0 0 12px 3px rgba(125, 211, 252, 0.75);
  animation: flowDot 3.4s ease-in-out infinite;
}
@keyframes flowDot {
  0% { top: 2%; opacity: 0; }
  12% { opacity: 1; }
  88% { opacity: 1; }
  100% { top: 92%; opacity: 0; }
}
.flow li {
  position: relative;
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 10px;
  align-items: flex-start;
  text-align: left;
  padding-bottom: 11px;
}
.flow li:last-child { padding-bottom: 0; }
.flow li::before {
  content: '';
  position: absolute;
  left: 10.5px;
  top: 22px;
  bottom: 0;
  width: 1px;
  background: linear-gradient(180deg, rgba(125, 211, 252, 0.5), rgba(125, 211, 252, 0.12));
}
.flow li:last-child::before { display: none; }
.flow em {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-style: normal;
  font-size: 11px;
  font-weight: 800;
  color: #0b1220;
  background: linear-gradient(135deg, #7dd3fc, #c4b5fd);
}
.row-txt b { display: block; font-size: 12.5px; color: #fff; }
.row-txt small { font-size: 10.5px; color: #b7c6e6; }

/* ===== ② 功能小窗 + 留白说明 ===== */
.feature-body {
  display: grid;
  grid-template-columns: 1fr 0.94fr;
  gap: 14px;
  align-items: center;
  text-align: left;
  padding: 20px 18px 46px;
}
.feature-text { display: flex; flex-direction: column; align-items: flex-start; gap: 7px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }

.pip {
  position: relative;
  aspect-ratio: 16 / 10;
  border-radius: 11px;
  overflow: hidden;
  background: #060c1a;
  border: 1px solid rgba(125, 211, 252, 0.4);
  box-shadow: 0 10px 26px rgba(5, 12, 28, 0.55), 0 0 0 3px rgba(125, 211, 252, 0.06);
}
.pip-video { width: 100%; height: 100%; object-fit: cover; display: block; }
.pip-bar {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 9.5px;
  color: #dbe7f5;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(6, 12, 28, 0.68);
  border: 1px solid rgba(125, 211, 252, 0.3);
  backdrop-filter: blur(3px);
}
.pip-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #f56c6c;
  animation: pipBlink 1.4s ease-in-out infinite;
}
@keyframes pipBlink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }

.chip {
  font-size: 10.5px;
  color: #dbe7f5;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(125, 211, 252, 0.1);
  border: 1px solid rgba(125, 211, 252, 0.26);
}

/* ===== ③ 质量要点 ===== */
.points { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-wrap: wrap; justify-content: center; gap: 7px; }
.points li {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #dbe7f5;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(23, 42, 77, 0.62);
  border: 1px solid rgba(125, 211, 252, 0.26);
}
.points li::before { content: '✓'; color: #7dd3fc; font-weight: 700; }

/* ===== ④ 演进路线 ===== */
.roadmap {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  width: 100%;
  max-width: 330px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.roadmap li {
  display: grid;
  grid-template-columns: 48px 1fr;
  grid-template-areas: 'phase title' 'phase desc';
  align-items: center;
  gap: 0 9px;
  text-align: left;
  padding: 7px 10px;
  border-radius: 9px;
  background: rgba(23, 42, 77, 0.6);
  border-left: 2px solid #7dd3fc;
}
.roadmap em {
  grid-area: phase;
  font-style: normal;
  font-size: 9.5px;
  color: #7dd3fc;
  text-align: center;
  padding: 2px 0;
  border: 1px solid rgba(125, 211, 252, 0.4);
  border-radius: 999px;
}
.roadmap b { grid-area: title; font-size: 12.5px; color: #fff; }
.roadmap small { grid-area: desc; font-size: 10.5px; color: #b7c6e6; }

/* ===== ⑤ 实时运行 ===== */
.metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; width: 100%; max-width: 300px; margin-top: 2px; }
.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 8px;
  border-radius: 9px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.24), rgba(118, 75, 162, 0.2));
  border: 1px solid rgba(125, 211, 252, 0.24);
}
.metric b { font-size: 19px; font-weight: 800; color: #7dd3fc; line-height: 1.1; font-variant-numeric: tabular-nums; }
.metric span { font-size: 10.5px; color: #b7c6e6; }

.highlights { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; margin-top: 2px; }
.live-line { font-size: 11px; color: #b7c6e6; }
.live-line b { color: #7dd3fc; font-weight: 700; font-variant-numeric: tabular-nums; }
.slogan {
  margin-top: 2px;
  font-size: 15px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.04em;
  text-shadow: 0 2px 16px rgba(4, 9, 22, 0.95);
}

/* ===== 进度条 ===== */
.progress { position: absolute; top: 0; left: 0; right: 0; height: 2px; background: rgba(125, 211, 252, 0.14); }
.progress i {
  display: block;
  height: 100%;
  transform: scaleX(0);
  transform-origin: left center;
  background: linear-gradient(90deg, #7dd3fc, #a78bfa);
  transition-property: transform;
  transition-timing-function: linear;
}
.progress i.on { transform: scaleX(1); }

/* ===== 暂停（后台） ===== */
.is-paused .promo-grid,
.is-paused .promo-scan,
.is-paused .scene.active .anim {
  animation-play-state: paused;
}

/* ===== 静态兜底 ===== */
.promo-static {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  padding: 22px 20px 46px;
}
.static-feats { display: flex; flex-wrap: wrap; gap: 6px; }
.static-feats span {
  font-size: 11px;
  color: #dbe7f5;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(125, 211, 252, 0.12);
  border: 1px solid rgba(125, 211, 252, 0.28);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .scene-body { padding: 16px 14px 42px; gap: 7px; }
  .feature-body { padding: 16px 14px 42px; }
  .title { font-size: 16px; }
  .desc { font-size: 11.5px; }
  .metric b { font-size: 17px; }
  .slogan { font-size: 13.5px; }
  .points li { font-size: 10px; }
  .roadmap li { padding: 6px 9px; }
}
@media (max-width: 520px) {
  .feature-body { grid-template-columns: 1fr; gap: 10px; }
  .pip { max-width: 220px; }
}

/* ===== 减弱动态效果 ===== */
@media (prefers-reduced-motion: reduce) {
  .promo-particles, .promo-scan, .progress { display: none; }
  .promo-grid, .scene, .anim, .flow::after, .pip-dot { animation: none !important; }
}
</style>