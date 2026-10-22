<template>
  <Teleport to="body">
    <Transition name="award-fade">
      <div v-if="badge" class="award-overlay" @click.self="emit('next')">
        <!-- 烟花画布：只在解锁瞬间放一轮，粒子散完自动停 -->
        <canvas ref="fxCanvas" class="award-fx"></canvas>

        <button type="button" class="award-skip" @click.stop="emit('skip')">
          跳过{{ remaining > 0 ? `全部 ${remaining + 1} 枚` : '' }}
        </button>

        <!-- key 绑定勋章 code：连续解锁多枚时会重建节点，重放整段入场动画 -->
        <div :key="badge.code" class="award-stage">
          <div class="award-medal" :class="'tier-' + badge.tier">
            <span class="award-icon">{{ badge.icon }}</span>
          </div>

          <div class="award-copy">
            <p class="award-eyebrow">获得新勋章</p>
            <h3 class="award-name">{{ badge.name }}</h3>
            <p class="award-desc">{{ badge.desc }}</p>
            <p class="award-meta">{{ tierLabel }} · {{ badge.category }}</p>
          </div>

          <button type="button" class="award-btn" @click.stop="emit('next')">
            {{ remaining > 0 ? `收下，还有 ${remaining} 枚` : '收下' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import type { BadgeItem, BadgeTier } from '@/api/badge'

const props = defineProps<{
  badge: BadgeItem | null
  /** 队列中剩余的勋章数（不含当前这枚） */
  remaining: number
}>()

const emit = defineEmits<{ next: []; skip: [] }>()

const TIER_LABELS: Record<string, string> = {
  bronze: '铜质勋章',
  silver: '银质勋章',
  gold: '金质勋章',
  diamond: '钻石勋章',
}

/** 烟花配色：与稀有度同色系，低饱和，不刺眼 */
const TIER_COLORS: Record<BadgeTier, string[]> = {
  bronze: ['#e8b184', '#d18b4f', '#fff4e6'],
  silver: ['#cbd5e1', '#94a3b8', '#ffffff'],
  gold: ['#f4cf6a', '#e0a92c', '#fff8dc'],
  diamond: ['#8fd3ee', '#4aa8cf', '#eaf9ff'],
}

const tierLabel = computed(() => TIER_LABELS[props.badge?.tier || 'bronze'] || '')

const fxCanvas = ref<HTMLCanvasElement | null>(null)

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  maxLife: number
  color: string
  size: number
}

interface Rocket {
  x: number
  y: number
  vy: number
  targetY: number
  color: string
}

let raf = 0
let stopTimer: number | undefined
let particles: Particle[] = []
let rockets: Rocket[] = []
let canvasW = 0
let canvasH = 0
let dpr = 1

function resize() {
  const c = fxCanvas.value
  if (!c) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvasW = window.innerWidth
  canvasH = window.innerHeight
  c.width = canvasW * dpr
  c.height = canvasH * dpr
  c.style.width = `${canvasW}px`
  c.style.height = `${canvasH}px`
  const ctx = c.getContext('2d')
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
}

/** 在指定位置炸开一簇粒子 */
function burst(x: number, y: number, colors: string[]) {
  const count = 54
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.12
    const speed = 1.6 + Math.random() * 3.2
    particles.push({
      x,
      y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 0,
      maxLife: 58 + Math.random() * 32,
      color: colors[i % colors.length],
      size: 1.2 + Math.random() * 1.4,
    })
  }
}

/** 一枚升空弹：从落点下方 220px 起升，约 0.35 秒后炸开，避免长时间等待 */
function launch(x: number, targetY: number, colors: string[]) {
  rockets.push({ x, y: targetY + 220, vy: -(9 + Math.random() * 2), targetY, color: colors[0] })
}

function tick() {
  const c = fxCanvas.value
  const ctx = c?.getContext('2d')
  if (!c || !ctx) return
  ctx.clearRect(0, 0, canvasW, canvasH)
  ctx.globalCompositeOperation = 'lighter'

  for (let i = rockets.length - 1; i >= 0; i--) {
    const r = rockets[i]
    r.y += r.vy
    r.vy += 0.06
    ctx.beginPath()
    ctx.fillStyle = r.color
    ctx.arc(r.x, r.y, 1.6, 0, Math.PI * 2)
    ctx.fill()
    // 拖尾
    ctx.beginPath()
    ctx.strokeStyle = r.color
    ctx.globalAlpha = 0.45
    ctx.lineWidth = 1
    ctx.moveTo(r.x, r.y)
    ctx.lineTo(r.x, r.y + 10)
    ctx.stroke()
    ctx.globalAlpha = 1
    if (r.y <= r.targetY || r.vy >= 0) {
      burst(r.x, r.y, TIER_COLORS[props.badge?.tier || 'bronze'])
      rockets.splice(i, 1)
    }
  }

  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]
    p.life++
    p.x += p.vx
    p.y += p.vy
    p.vy += 0.045
    p.vx *= 0.985
    p.vy *= 0.985
    const k = 1 - p.life / p.maxLife
    if (k <= 0) { particles.splice(i, 1); continue }
    ctx.globalAlpha = Math.max(k, 0) * 0.9
    ctx.beginPath()
    ctx.fillStyle = p.color
    ctx.arc(p.x, p.y, p.size * (0.4 + k * 0.6), 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1
  ctx.globalCompositeOperation = 'source-over'

  if (rockets.length || particles.length) {
    raf = requestAnimationFrame(tick)
  } else {
    stopFx()
  }
}

/** 收尾：停掉循环并清空画布，保证不留残影 */
function stopFx() {
  cancelAnimationFrame(raf)
  raf = 0
  particles = []
  rockets = []
  const ctx = fxCanvas.value?.getContext('2d')
  if (ctx && canvasW && canvasH) ctx.clearRect(0, 0, canvasW, canvasH)
}

async function playFireworks() {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  // 等这一帧的 DOM 挂载完成再取 canvas：否则拿不到 ref，画布会停在默认 300×150
  await nextTick()
  stopFx()
  clearTimeout(stopTimer)
  resize()
  if (!canvasW || !canvasH) return
  const colors = TIER_COLORS[props.badge?.tier || 'bronze']
  // 三发错峰升空，落点分布在卡片上方的空白处
  launch(canvasW * 0.22, canvasH * 0.24, colors)
  setTimeout(() => launch(canvasW * 0.78, canvasH * 0.2, colors), 260)
  setTimeout(() => launch(canvasW * 0.5, canvasH * 0.14, colors), 540)
  raf = requestAnimationFrame(tick)
  // 看门狗：动画总时长封顶，避免渲染帧停摆时画布残留粒子
  stopTimer = window.setTimeout(stopFx, 3200)
}

watch(
  () => props.badge?.code,
  (code) => { if (code) playFireworks() },
  { immediate: true, flush: 'post' }
)

onBeforeUnmount(() => {
  clearTimeout(stopTimer)
  cancelAnimationFrame(raf)
})
</script>

<style scoped>
.award-overlay {
  position: fixed;
  inset: 0;
  z-index: 3200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(16, 19, 26, 0.58);
  backdrop-filter: blur(5px);
}
.award-fx {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.award-skip {
  position: absolute;
  top: calc(16px + env(safe-area-inset-top));
  right: 16px;
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  background: transparent;
  color: rgba(255, 255, 255, 0.78);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}

/* 白卡：一层细边、一层柔和投影，信息靠排版分层，不用深色渐变与旋转射线 */
.award-stage {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 30px 22px 20px;
  border-radius: 18px;
  border: 1px solid var(--tui-border, #eef0f3);
  background: var(--tui-surface, #fff);
  box-shadow: 0 24px 60px rgba(8, 12, 22, 0.32);
  animation: award-pop 0.46s cubic-bezier(0.22, 1.2, 0.36, 1) both;
}

/* 勋章本体：扁平圆盘，同色系浅底 + 细描边 */
.award-medal {
  width: 92px;
  height: 92px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--disc-bg);
  box-shadow: inset 0 0 0 1px var(--disc-ring);
  animation: award-medal-in 0.62s cubic-bezier(0.2, 1.35, 0.35, 1) 0.05s both;
}
.award-icon { font-size: 42px; line-height: 1; }
.tier-bronze { --disc-bg: #fbf3ec; --disc-ring: #ecd6c2; }
.tier-silver { --disc-bg: #f6f7f9; --disc-ring: #dfe4ea; }
.tier-gold { --disc-bg: #fdf7e8; --disc-ring: #efdfb6; }
.tier-diamond { --disc-bg: #eef7fb; --disc-ring: #cfe6f0; }

.award-copy {
  margin-top: 18px;
  animation: award-copy-in 0.45s ease-out 0.3s both;
}
.award-eyebrow {
  margin: 0;
  font-size: 11.5px;
  letter-spacing: 1.6px;
  color: var(--tui-text-tertiary, #8b929e);
}
.award-name {
  margin: 7px 0 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.2px;
  color: var(--tui-text, #1f2430);
}
.award-desc {
  margin: 7px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tui-text-secondary, #667085);
}
.award-meta {
  margin: 10px 0 0;
  font-size: 11px;
  color: var(--tui-text-quiet, #98a2b3);
}

/* 主按钮：中性深色实心，与全局弹窗规范一致 */
.award-btn {
  width: 100%;
  height: 42px;
  margin-top: 22px;
  border: none;
  border-radius: 10px;
  background: #1f2430;
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  animation: award-copy-in 0.45s ease-out 0.42s both;
}
.award-btn:active { background: #171a22; }

.award-fade-enter-active,
.award-fade-leave-active { transition: opacity 0.22s ease; }
.award-fade-enter-from,
.award-fade-leave-to { opacity: 0; }

@keyframes award-pop {
  from { transform: translateY(14px) scale(0.96); opacity: 0; }
  to { transform: translateY(0) scale(1); opacity: 1; }
}
@keyframes award-medal-in {
  0% { transform: scale(0.55); opacity: 0; }
  65% { transform: scale(1.04); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}
@keyframes award-copy-in {
  from { transform: translateY(8px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .award-stage, .award-medal, .award-copy, .award-btn { animation: none; }
}
</style>
