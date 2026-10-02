<template>
  <div class="wordcloud-card">
    <div class="wc-header">
      <div class="wc-title-wrap">
        <span class="wc-icon"><el-icon><ChartColumn /></el-icon></span>
        <div class="wc-title-text">
          <h3>反馈重点词云</h3>
          <span class="wc-sub">词频越高字号越大 · 拖拽平移 · Ctrl+滚轮缩放 · 双击复位</span>
        </div>
      </div>
      <div class="wc-tools">
        <span v-if="words.length" class="wc-total">{{ words.length }} 个热点词</span>
        <el-button text size="small" :loading="loading" @click="$emit('refresh')">
          <el-icon><RefreshCw /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="wc-body">
      <!-- 加载中且无数据：骨架屏 -->
      <el-skeleton v-if="loading && !words.length" :rows="3" animated class="wc-skeleton" />

      <!-- 经典 Wordle 词云主体（d3-cloud 开源方案，词频越大字号越大、平滑聚拢） -->
      <div v-else-if="words.length" ref="stageEl" class="wc-cloud"></div>

      <el-empty v-else description="暂无反馈数据，产生反馈后将在此展示热点词" :image-size="64" />
    </div>

    <div v-if="words.length" class="wc-foot">
      <span>最近刷新：{{ refreshedAt }}</span>
    </div>

    <!-- 悬停提示 -->
    <div ref="tipEl" class="wc-tip" role="tooltip" aria-hidden="true"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChartColumn, RefreshCw } from 'lucide-vue-next'
import cloud, { type CloudWord } from 'd3-cloud'
import type { FeedbackWord } from '@/api/feedback'

const props = defineProps<{
  words: FeedbackWord[]
  loading?: boolean
}>()

defineEmits<{ (e: 'refresh'): void }>()

const stageEl = ref<HTMLDivElement>()
const tipEl = ref<HTMLDivElement>()
const refreshedAt = ref('')

/* ---------- 布局参数（经典 Wordle：居中聚拢、分级字号、少量竖直旋转） ---------- */
const LAYOUT_W = 1000
const LAYOUT_H = 640
const FONT_FAMILY = '"PingFang SC","Microsoft YaHei",sans-serif'

/* ---------- 柔和多彩色板（浅 / 暗，按词频区间取色） ---------- */
const PALETTES = {
  light: ['#2f6bff', '#3b7cff', '#5b8def', '#3fa7c9', '#34c48a', '#66b877', '#f2a33c', '#e8885f', '#e8686e', '#8b6ff0', '#a0a8bc'],
  dark: ['#9db8ff', '#7aa2ff', '#82b0f0', '#6fd3e6', '#61d8a6', '#90d491', '#f5b85c', '#f0a07a', '#f07f84', '#b3a1f5', '#8a93a6'],
}

const minCount = computed(() => (props.words.length ? Math.min(...props.words.map(w => w.count)) : 0))
const maxCount = computed(() => (props.words.length ? Math.max(...props.words.map(w => w.count)) : 0))

/* ---------- canvas ---------- */
let canvas: HTMLCanvasElement | null = null
let ctx: CanvasRenderingContext2D | null = null
let W = 0
let H = 0
let baseScale = 1
const DPR = window.devicePixelRatio || 1
let ro: ResizeObserver | null = null

/* ---------- 词云状态 ---------- */
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

/* ---------- 拖拽平移 / 滚轮缩放（以鼠标为中心缩放，双击复位） ---------- */
let panX = 0
let panY = 0
let zoom = 1
let dragging = false
let dragStart = { x: 0, y: 0, px: 0, py: 0 }
const MIN_ZOOM = 0.4
const MAX_ZOOM = 4

let isDark = document.documentElement.classList.contains('dark')
let darkObserver: MutationObserver | null = null

function sizeFor(count: number) {
  const ratio = maxCount.value === minCount.value ? 0.5 : (count - minCount.value) / (maxCount.value - minCount.value)
  return Math.round(16 + ratio * 28)
}

function colorFor(count: number) {
  const palette = PALETTES[isDark ? 'dark' : 'light']
  const ratio = maxCount.value === minCount.value ? 0.5 : (count - minCount.value) / (maxCount.value - minCount.value)
  return palette[Math.min(palette.length - 1, Math.floor(ratio * palette.length))]
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
    .slice(0, 400)
    .map(w => ({ text: w.word, value: w.count, size: sizeFor(w.count) }))

  if (layout) layout.stop()
  // 布局尺寸跟随容器实际大小：词越大、图越大，不再被固定基准缩小
  const stage = stageEl.value
  const lw = stage ? Math.max(300, stage.clientWidth) : LAYOUT_W
  const lh = stage ? Math.max(200, stage.clientHeight) : LAYOUT_H
  layout = cloud()
    .size([lw, lh])
    .words(cloudWords)
    .padding(3)
    .rotate(() => (Math.random() < 0.25 ? -90 : 0))
    .font(FONT_FAMILY)
    .fontSize(d => (d.size as number) ?? 16)
    .on('end', words => {
      if (seq !== layoutSeq) return
      placed = words
        .map(w => ({
          w,
          x: (w.x as number) ?? 0,
          y: (w.y as number) ?? 0,
          fs: (w.size as number) ?? 16,
          angle: (((w.rotate as number) ?? 0) * Math.PI) / 180,
          color: colorFor((w.value as number) ?? 0),
        }))
        .filter(p => p.fs >= 1)
      hover = null
      render()
    })
  layout.start()
}

/* ---------- 命中检测（0° / ±90° 旋转的包围盒，含 pan/zoom 变换） ---------- */
function findHit(): Placed | null {
  let best: Placed | null = null
  let bestDist = Infinity
  for (const p of placed) {
    const px = W / 2 + panX + p.x * baseScale * zoom
    const py = H / 2 + panY + p.y * baseScale * zoom
    const halfW = (((p.w.width as number) ?? p.fs * 1.6) * baseScale * zoom) / 2
    const halfH = (((p.w.height as number) ?? p.fs) * baseScale * zoom) / 2
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

/* ---------- 渲染（经典 Wordle：平面展示，支持拖拽平移与滚轮缩放） ---------- */
function render() {
  if (!ctx || !placed.length || !W) return
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0)
  ctx.clearRect(0, 0, W, H)

  hover = mouse.in && !dragging ? findHit() : null
  const ox = W / 2 + panX
  const oy = H / 2 + panY
  const mid = (maxCount.value + minCount.value) / 2

  for (const p of placed) {
    const heavy = ((p.w.value as number) ?? 0) >= mid
    const isHover = p === hover
    const fs = Math.max(8, (isHover ? p.fs * 1.1 : p.fs) * baseScale)
    ctx.save()
    ctx.translate(ox + p.x * baseScale * zoom, oy + p.y * baseScale * zoom)
    ctx.scale(zoom, zoom)
    ctx.rotate(p.angle)
    ctx.font = `${isHover || heavy ? 700 : 500} ${fs.toFixed(1)}px ${FONT_FAMILY}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = isHover ? shade(p.color, isDark ? 30 : -26) : p.color
    if (isHover) {
      ctx.shadowColor = hexA(p.color, 0.5)
      ctx.shadowBlur = 16
    }
    ctx.fillText(p.w.text, 0, 0)
    ctx.restore()
  }

  if (hover) showTip(`${hover.w.text} · ${hover.w.value} 次`)
  else hideTip()
}

/* ---------- tooltip ---------- */
function showTip(text: string) {
  const tip = tipEl.value
  if (!tip) return
  tip.textContent = text
  tip.classList.add('on')
  const m = 12
  const tw = tip.offsetWidth
  const th = tip.offsetHeight
  tip.style.left = `${Math.max(m, Math.min(mouse.cx + 14, window.innerWidth - tw - m))}px`
  tip.style.top = `${Math.max(m, Math.min(mouse.cy - th - 12, window.innerHeight - th - m))}px`
}

function hideTip() {
  tipEl.value?.classList.remove('on')
}

/* ---------- 事件（拖拽平移 + 滚轮缩放，悬停高亮） ---------- */
function onPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  dragging = true
  dragStart = { x: e.clientX, y: e.clientY, px: panX, py: panY }
  canvas?.setPointerCapture(e.pointerId)
  if (canvas) canvas.style.cursor = 'grabbing'
}

function onPointerMove(e: PointerEvent) {
  const r = canvas!.getBoundingClientRect()
  mouse.cx = e.clientX
  mouse.cy = e.clientY
  mouse.x = e.clientX - r.left
  mouse.y = e.clientY - r.top
  if (dragging) {
    panX = dragStart.px + (e.clientX - dragStart.x)
    panY = dragStart.py + (e.clientY - dragStart.y)
    render()
    return
  }
  mouse.in = true
  const hit = findHit()
  if (hit !== hover) render()
}

function onPointerUp(e: PointerEvent) {
  if (!dragging) return
  dragging = false
  if (canvas) canvas.style.cursor = 'grab'
  try {
    canvas?.releasePointerCapture(e.pointerId)
  } catch { /* ignore */ }
}

function onPointerLeave() {
  mouse.in = false
  if (!dragging && hover) {
    hover = null
    hideTip()
    render()
  }
}

function onWheel(e: WheelEvent) {
  // 普通滚轮不拦截，让页面正常滚动；仅 Ctrl/Cmd + 滚轮才缩放（与地图/编辑器交互一致）
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  if (!canvas || !W) return
  const r = canvas.getBoundingClientRect()
  const mx = e.clientX - r.left
  const my = e.clientY - r.top
  const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12
  const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom * factor))
  if (next === zoom) return
  // 以鼠标位置为锚点缩放：保持光标下的点不动
  const k = next / zoom
  panX = mx - (mx - panX) * k
  panY = my - (my - panY) * k
  zoom = next
  render()
}

function onDblClick() {
  panX = 0
  panY = 0
  zoom = 1
  render()
}

/* ---------- 尺寸 ---------- */
function resize() {
  if (!canvas || !stageEl.value) return
  const w = stageEl.value.clientWidth
  const h = stageEl.value.clientHeight
  if (!w || !h) return
  W = w
  H = h
  canvas.width = Math.round(w * DPR)
  canvas.height = Math.round(h * DPR)
  canvas.style.width = `${w}px`
  canvas.style.height = `${h}px`
  baseScale = Math.min(w / LAYOUT_W, h / LAYOUT_H) * 0.95
  render()
}

/* ---------- 数据变化 ---------- */
watch(
  () => props.words,
  val => {
    const d = new Date()
    refreshedAt.value = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
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
  }
)

/* ---------- canvas 生命周期：容器可能晚于挂载出现（数据异步返回），必须延迟创建 ---------- */
function ensureCanvas() {
  const stage = stageEl.value
  if (!stage || canvas) return
  canvas = document.createElement('canvas')
  canvas.className = 'wc-canvas'
  canvas.style.cursor = 'grab'
  stage.appendChild(canvas)
  ctx = canvas.getContext('2d')
  canvas.addEventListener('pointerdown', onPointerDown)
  canvas.addEventListener('pointermove', onPointerMove)
  canvas.addEventListener('pointerup', onPointerUp)
  canvas.addEventListener('pointercancel', onPointerUp)
  canvas.addEventListener('pointerleave', onPointerLeave)
  canvas.addEventListener('wheel', onWheel, { passive: false })
  canvas.addEventListener('dblclick', onDblClick)
  resize()
}

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
  }
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
  canvas?.removeEventListener('pointerdown', onPointerDown)
  canvas?.removeEventListener('pointermove', onPointerMove)
  canvas?.removeEventListener('pointerup', onPointerUp)
  canvas?.removeEventListener('pointercancel', onPointerUp)
  canvas?.removeEventListener('pointerleave', onPointerLeave)
  canvas?.removeEventListener('wheel', onWheel)
  canvas?.removeEventListener('dblclick', onDblClick)
  canvas?.remove()
  canvas = null
  ctx = null
})
</script>

<style scoped>
.wordcloud-card {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
  margin-bottom: 14px;
  padding: 14px 16px;
  transition: box-shadow 0.25s ease;
}

.wordcloud-card:hover {
  box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08);
}

.wc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.wc-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.wc-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff, #3377ff);
  flex-shrink: 0;
}

.wc-icon .el-icon {
  font-size: 18px;
  color: #fff;
}

.wc-title-text h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #2b3245;
}

.wc-sub {
  font-size: 12px;
  color: #8a91a4;
}

.wc-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.wc-total {
  font-size: 12px;
  color: #8a91a4;
  background: #f4f6fa;
  border-radius: 999px;
  padding: 3px 10px;
  white-space: nowrap;
}

.wc-skeleton {
  padding: 12px 4px;
}

.wc-cloud {
  position: relative;
  height: 360px;
  border-radius: 10px;
  overflow: hidden;
  background:
    radial-gradient(120% 100% at 50% 30%, rgba(59, 124, 255, 0.09) 0%, transparent 62%),
    #f7f9fc;
  transition: background 0.25s ease;
}

.wc-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.wc-tip {
  position: fixed;
  z-index: 3000;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.12s ease;
  background: #fff;
  color: #2b3245;
  border: 1px solid #eef0f4;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(16, 24, 40, 0.12);
  padding: 5px 10px;
  font-size: 13px;
  line-height: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.wc-tip.on { opacity: 1; }

.wc-foot {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px dashed #eef0f4;
  font-size: 12px;
  color: #a0a6b4;
  text-align: right;
}

@media (max-width: 640px) {
  .wc-cloud { height: 280px; }
}

/* 暗色适配 */
html.dark .wordcloud-card {
  background: #1e1e20;
  border-color: rgba(255, 255, 255, 0.08);
}

html.dark .wc-title-text h3 {
  color: #e8e8ea;
}

html.dark .wc-sub {
  color: #a0a0a8;
}

html.dark .wc-total {
  background: rgba(255, 255, 255, 0.06);
  color: #a0a0a8;
}

html.dark .wc-cloud {
  background:
    radial-gradient(120% 100% at 50% 30%, rgba(122, 162, 255, 0.12) 0%, transparent 62%),
    #16181d;
}

html.dark .wc-tip {
  background: #26262b;
  color: #e8e8ea;
  border-color: rgba(255, 255, 255, 0.1);
}

html.dark .wc-foot {
  border-top-color: rgba(255, 255, 255, 0.1);
  color: #7c7c84;
}
</style>