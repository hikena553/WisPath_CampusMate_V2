<template>
  <div class="cwc-wrap">
    <!-- 空态：复用 .tui-empty -->
    <div v-if="!words.length" class="tui-empty cwc-empty">
      <span class="tui-empty-icon"><el-icon :size="26"><DataAnalysis /></el-icon></span>
      <span class="tui-empty-title">暂无敏感词数据</span>
      <span class="tui-empty-desc">预警命中关键词与摘要分词后将在此展示高频词</span>
    </div>

    <!-- 经典 Wordle 词云主体（d3-cloud 布局 + canvas 绘制） -->
    <div v-else ref="stageEl" class="cwc-stage"></div>

    <!-- 悬停提示 -->
    <div ref="tipEl" class="cwc-tip" role="tooltip" aria-hidden="true"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import cloud, { type CloudWord } from 'd3-cloud'

const props = defineProps<{
  words: { word: string; count: number }[]
}>()

const stageEl = ref<HTMLDivElement>()
const tipEl = ref<HTMLDivElement>()

/* ---------- 布局基准（画布实际尺寸由容器决定，此值仅用于等比缩放基准） ---------- */
const LAYOUT_W = 900
const LAYOUT_H = 400
const FONT_FAMILY = '"PingFang SC","Microsoft YaHei",sans-serif'

/* ---------- 语义色板：与 --tui-* 语义色同源（浅 / 暗），按词频区间取色 ---------- */
const PALETTES = {
  light: ['#2563eb', '#1d4ed8', '#0891b2', '#079455', '#b54708', '#d92d20', '#7c3aed', '#6b7280'],
  dark: ['#93b4ff', '#7aa2ff', '#5ecbdd', '#4bbf87', '#e0a458', '#ef6a60', '#c084fc', '#9ca3af'],
}

const minCount = computed(() => (props.words.length ? Math.min(...props.words.map(w => w.count)) : 0))
const maxCount = computed(() => (props.words.length ? Math.max(...props.words.map(w => w.count)) : 0))

/* ---------- canvas ---------- */
let canvas: HTMLCanvasElement | null = null
let ctx: CanvasRenderingContext2D | null = null
let W = 0
let H = 0
let baseScale = 1
const DPR = typeof window === 'undefined' ? 1 : window.devicePixelRatio || 1
let ro: ResizeObserver | null = null

interface Placed {
  w: CloudWord
  x: number
  y: number
  fs: number
  angle: number
  color: string
}

let placed: Placed[] = []
let layout: ReturnType<typeof cloud> | null = null
let layoutSeq = 0 // 布局版本号，防止旧结果覆盖新数据
let hover: Placed | null = null
const mouse = { x: 0, y: 0, cx: 0, cy: 0, in: false }

let isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
let darkObserver: MutationObserver | null = null

function ratioOf(count: number) {
  return maxCount.value === minCount.value ? 0.5 : (count - minCount.value) / (maxCount.value - minCount.value)
}

function sizeFor(count: number) {
  return Math.round(14 + ratioOf(count) * 24)
}

function colorFor(count: number) {
  const palette = PALETTES[isDark ? 'dark' : 'light']
  return palette[Math.min(palette.length - 1, Math.floor(ratioOf(count) * palette.length))]
}

function hexA(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`
}

function shade(hex: string, amt: number) {
  const n = parseInt(hex.slice(1), 16)
  const c = (v: number) => Math.max(0, Math.min(255, v + amt))
  return `rgb(${c(n >> 16 & 255)},${c(n >> 8 & 255)},${c(n & 255)})`
}

/* ---------- 布局：跟随容器实际尺寸，词频越大字号越大 ---------- */
function runLayout() {
  if (!props.words.length) {
    placed = []
    hover = null
    hideTip()
    return
  }
  ensureCanvas()
  const seq = ++layoutSeq
  const cloudWords: CloudWord[] = props.words
    .slice(0, 200)
    .map(w => ({ text: w.word, value: w.count, size: sizeFor(w.count) }))

  if (layout) layout.stop()
  // 取视觉尺寸（getBoundingClientRect）而非 clientWidth/clientHeight：
  // 后者在页面密度缩放下是局部像素，会和指针坐标（视觉像素）差一个 --ui-zoom 倍率，
  // 导致悬停命中检测整体偏移。
  const box = stageEl.value?.getBoundingClientRect()
  const lw = box ? Math.max(280, Math.round(box.width)) : LAYOUT_W
  const lh = box ? Math.max(180, Math.round(box.height)) : LAYOUT_H
  layout = cloud()
    .size([lw, lh])
    .words(cloudWords)
    .padding(3)
    .rotate(() => (Math.random() < 0.2 ? -90 : 0))
    .font(FONT_FAMILY)
    .fontSize(d => (d.size as number) ?? 14)
    .on('end', words => {
      if (seq !== layoutSeq) return
      placed = words
        .map(w => ({
          w,
          x: (w.x as number) ?? 0,
          y: (w.y as number) ?? 0,
          fs: (w.size as number) ?? 14,
          angle: (((w.rotate as number) ?? 0) * Math.PI) / 180,
          color: colorFor((w.value as number) ?? 0),
        }))
        .filter(p => p.fs >= 1)
      hover = null
      render()
    })
  layout.start()
}

/* ---------- 命中检测（0° / ±90° 旋转的包围盒） ---------- */
function findHit(): Placed | null {
  let best: Placed | null = null
  let bestDist = Infinity
  for (const p of placed) {
    const px = W / 2 + p.x * baseScale
    const py = H / 2 + p.y * baseScale
    const halfW = (((p.w.width as number) ?? p.fs * 1.6) * baseScale) / 2
    const halfH = (((p.w.height as number) ?? p.fs) * baseScale) / 2
    const vertical = Math.abs(p.angle) > 0.1
    const hw = vertical ? halfH : halfW
    const hh = vertical ? halfW : halfH
    if (Math.abs(mouse.x - px) <= hw && Math.abs(mouse.y - py) <= hh) {
      const d = (mouse.x - px) ** 2 + (mouse.y - py) ** 2
      if (d < bestDist) { bestDist = d; best = p }
    }
  }
  return best
}

/* ---------- 渲染 ---------- */
function render() {
  if (!ctx || !placed.length || !W) return
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0)
  ctx.clearRect(0, 0, W, H)

  hover = mouse.in ? findHit() : null
  const ox = W / 2
  const oy = H / 2
  const mid = (maxCount.value + minCount.value) / 2

  for (const p of placed) {
    const heavy = ((p.w.value as number) ?? 0) >= mid
    const isHover = p === hover
    const fs = Math.max(9, (isHover ? p.fs * 1.1 : p.fs) * baseScale)
    ctx.save()
    ctx.translate(ox + p.x * baseScale, oy + p.y * baseScale)
    ctx.rotate(p.angle)
    ctx.font = `${isHover || heavy ? 700 : 500} ${fs.toFixed(1)}px ${FONT_FAMILY}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = isHover ? shade(p.color, isDark ? 30 : -26) : p.color
    if (isHover) {
      ctx.shadowColor = hexA(p.color, 0.5)
      ctx.shadowBlur = 14
    }
    ctx.fillText(p.w.text, 0, 0)
    ctx.restore()
  }

  if (hover) showTip(`${hover.w.text} · ${hover.w.value} 次`)
  else hideTip()
}

/* ---------- tooltip（贴指针定位，限制在容器内） ---------- */
function showTip(text: string) {
  const tip = tipEl.value
  const wrap = tip?.parentElement
  if (!tip || !wrap) return
  tip.textContent = text
  tip.classList.add('on')
  const m = 6
  const bw = wrap.clientWidth
  const bh = wrap.clientHeight
  const tw = tip.offsetWidth
  const th = tip.offsetHeight
  tip.style.left = `${Math.max(m, Math.min(mouse.cx + 12, bw - tw - m))}px`
  tip.style.top = `${Math.max(m, Math.min(mouse.cy - th - 10, bh - th - m))}px`
}

function hideTip() {
  tipEl.value?.classList.remove('on')
}

function onPointerMove(e: PointerEvent) {
  if (!canvas) return
  const r = canvas.getBoundingClientRect()
  mouse.cx = e.clientX - r.left
  mouse.cy = e.clientY - r.top
  mouse.x = mouse.cx
  mouse.y = mouse.cy
  mouse.in = true
  const hit = findHit()
  if (hit !== hover) render()
}

function onPointerLeave() {
  mouse.in = false
  if (hover) {
    hover = null
    hideTip()
    render()
  }
}

/* ---------- 尺寸：位图密度恒定，画布与容器严格等宽高 ---------- */
function resize() {
  if (!canvas || !stageEl.value) return
  const box = stageEl.value.getBoundingClientRect()
  const w = Math.round(box.width)
  const h = Math.round(box.height)
  if (!w || !h) return
  W = w
  H = h
  canvas.width = Math.round(w * DPR)
  canvas.height = Math.round(h * DPR)
  baseScale = Math.min(w / LAYOUT_W, h / LAYOUT_H) * 0.95
  render()
}

/* ---------- canvas 生命周期：容器可能晚于挂载出现（数据异步返回），必须延迟创建 ---------- */
function ensureCanvas() {
  const stage = stageEl.value
  if (!stage || canvas) return
  canvas = document.createElement('canvas')
  canvas.className = 'cwc-canvas'
  stage.appendChild(canvas)
  ctx = canvas.getContext('2d')
  canvas.addEventListener('pointermove', onPointerMove)
  canvas.addEventListener('pointerleave', onPointerLeave)
  resize()
}

watch(
  () => props.words,
  val => {
    if (val.length) {
      nextTick(() => {
        ensureCanvas()
        runLayout()
      })
    } else {
      placed = []
      hover = null
      hideTip()
    }
  },
)

/* 容器渲染出来后（words 有值），立即创建 canvas 并接管尺寸 */
watch(
  () => stageEl.value,
  el => {
    if (!el) return
    if (!ro) {
      ro = new ResizeObserver(resize)
      ro.observe(el)
    }
    ensureCanvas()
  },
)

onMounted(() => {
  window.addEventListener('resize', resize)

  darkObserver = new MutationObserver(() => {
    isDark = document.documentElement.classList.contains('dark')
    render()
  })
  darkObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

  ensureCanvas()
  if (props.words.length) runLayout()
})

onBeforeUnmount(() => {
  ro?.disconnect()
  window.removeEventListener('resize', resize)
  darkObserver?.disconnect()
  layout?.stop()
  canvas?.removeEventListener('pointermove', onPointerMove)
  canvas?.removeEventListener('pointerleave', onPointerLeave)
  canvas?.remove()
  canvas = null
  ctx = null
})
</script>

<style scoped>
.cwc-wrap {
  position: relative;
}

.cwc-stage {
  position: relative;
  height: 300px;
  border-radius: var(--tui-radius-sm);
  overflow: hidden;
  background:
    radial-gradient(120% 100% at 50% 30%, var(--tui-danger-soft) 0%, transparent 62%),
    var(--tui-surface-muted);
}

.cwc-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.cwc-tip {
  position: absolute;
  z-index: 5;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.12s var(--tui-ease);
  background: var(--tui-surface);
  color: var(--tui-text);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius-xs);
  box-shadow: var(--tui-shadow-2);
  padding: 4px 9px;
  font-size: 12px;
  line-height: 17px;
  font-weight: 600;
  white-space: nowrap;
}

.cwc-tip.on { opacity: 1; }

/* 空态：收紧留白，避免词云区塌陷或撑高 */
.cwc-empty {
  padding: 30px 12px;
  gap: 8px;
}
.cwc-empty .tui-empty-icon { width: 46px; height: 46px; }

@media (max-width: 767px) {
  .cwc-stage { height: 230px; }
}
</style>