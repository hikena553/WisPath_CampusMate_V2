<template>
  <div class="board-wrap">
    <div class="board-hint">拖拽卡片摆放 · 按住空白处平移画布 · 点击「展开」管理</div>
    <div ref="canvasRef" class="board-canvas" :class="{ grabbing: panning || !!dragId }" @pointerdown="onCanvasPointerDown">
      <!-- 世界层：随平移移动，点状网格画在它上面保证网格跟着画布走 -->
      <div class="board-world" :style="worldStyle">
        <svg class="board-edges" :width="WORLD_W" :height="WORLD_H">
          <line
            v-for="e in edges" :key="e.key"
            :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
            class="board-edge" :class="{ faint: e.faint }"
          />
        </svg>

        <!-- 内容分类：固定源节点，不可拖拽 -->
        <div
          v-for="c in CATEGORY_NODES" :key="c.key"
          class="cat-node" :style="{ left: c.x + 'px', top: c.y + 'px' }"
        >{{ c.label }}</div>

        <!-- 账号卡片：自由拖拽 -->
        <div
          v-for="row in accounts" :key="row.id"
          class="acc-card board-card"
          :class="{ 'acc-card-disabled': !row.is_enabled, dragging: dragId === row.id }"
          :style="cardPos(row.id)"
          @pointerdown="onCardPointerDown(row, $event)"
        >
          <div class="acc-chips">
            <span class="acc-chip">资讯号</span>
            <span class="acc-chip" :class="row.is_enabled ? 'acc-chip-on' : 'acc-chip-off'">
              {{ row.is_enabled ? '自动发帖' : '待命' }}
            </span>
            <span class="acc-chip acc-chip-freq" :title="'发帖频率：' + relayFreqLabel(row.relay_interval_minutes)">
              {{ relayFreqShort(row.relay_interval_minutes) }}
            </span>
            <i class="acc-grip" aria-hidden="true"><GripVertical /></i>
          </div>
          <div class="acc-idrow">
            <el-avatar :size="36" :src="row.avatar || undefined" class="acc-avatar">
              {{ (row.name || '资').slice(0, 1) }}
            </el-avatar>
            <div class="acc-idmeta">
              <div class="acc-title">{{ row.name }}</div>
              <div class="acc-username">@{{ row.username }}</div>
            </div>
          </div>
          <div class="acc-desc">{{ row.signature || '暂无签名' }}</div>
          <Transition name="accpop">
            <div v-if="expandedId === row.id" class="acc-more">
            <div class="acc-meta-line">发帖频率：{{ relayFreqLabel(row.relay_interval_minutes) }}</div>
            <div class="acc-scope">
              <template v-if="row.content_scope?.length">
                <el-tag v-for="t in row.content_scope" :key="t" size="small" effect="light">{{ typeLabel(t) }}</el-tag>
              </template>
              <el-tag v-else size="small" effect="plain" type="info">全部分类</el-tag>
            </div>
            <div class="acc-actions">
              <el-button
                size="small" type="primary" round :disabled="!row.is_enabled"
                :loading="publishingId === row.id"
                @click="emit('publish', row)"
              >立即发布</el-button>
              <el-button size="small" round @click="emit('edit', row)">编辑</el-button>
              <el-button
                size="small" round :type="row.is_enabled ? 'warning' : 'success'"
                @click="emit('toggle', row)"
              >{{ row.is_enabled ? '停用' : '启用' }}</el-button>
              <el-button size="small" round type="danger" plain @click="emit('remove', row)">删除</el-button>
            </div>
          </div>
          </Transition>
          <div class="acc-foot" @click.stop="expandedId = expandedId === row.id ? null : row.id">
            <span class="acc-foot-status">
              <i class="acc-dot" :class="row.is_enabled ? 'on' : 'off'"></i>
              已发 {{ row.post_count }} 帖 · 最近 {{ formatTime(row.last_posted_at) || '—' }}
            </span>
            <span class="acc-expand">
              {{ expandedId === row.id ? '收起' : '展开' }}
              <el-icon :size="13" class="acc-chevron" :class="{ open: expandedId === row.id }"><ChevronDown /></el-icon>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { ChevronDown, GripVertical } from 'lucide-vue-next'
import type { MediaAccount, FeedSourceType } from '@/api/admin'

const props = defineProps<{
  accounts: MediaAccount[]
  publishingId: number | null
}>()

const emit = defineEmits<{
  publish: [row: MediaAccount]
  edit: [row: MediaAccount]
  toggle: [row: MediaAccount]
  remove: [row: MediaAccount]
}>()

const FEED_TYPE_LABELS: Record<FeedSourceType, string> = {
  papers: 'AI 论文',
  opensource: '开源项目榜',
  agents: '智能体榜',
  news: '时政要闻',
  ai_news: 'AI 行业',
  rankings: '权威排行榜',
  cn_ai: '国产模型',
}
const typeLabel = (t: string) => FEED_TYPE_LABELS[t as FeedSourceType] || t

const RELAY_FREQ_LABELS: Record<number, string> = {
  0: '不逐条转发 · 仅每日汇总',
  30: '跟随抓取 · 约 30 分钟',
  60: '每 1 小时',
  180: '每 3 小时',
  360: '每 6 小时',
  720: '每 12 小时',
  1440: '每天 1 次',
}
const relayFreqLabel = (v: number | null | undefined) => RELAY_FREQ_LABELS[v ?? 30] || '跟随抓取 · 约 30 分钟'

// 卡片收起态的频率短文案（完整文案见展开区 / 悬浮 title）
const RELAY_FREQ_SHORT: Record<number, string> = {
  0: '仅汇总',
  30: '每 30 分钟',
  60: '每小时',
  180: '每 3 小时',
  360: '每 6 小时',
  720: '每 12 小时',
  1440: '每天 1 转',
}
const relayFreqShort = (v: number | null | undefined) => RELAY_FREQ_SHORT[v ?? 30] || '每 30 分钟'

function formatTime(t: string | null) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return String(t).slice(0, 19)
  // 画布卡片状态条空间有限：只到分钟，避免把「展开」挤成竖排
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ---------- 世界坐标与源节点 ----------
const WORLD_W = 1700
const WORLD_H = 1500
const CARD_W = 250
const NODE_W = 128
const NODE_H = 56
// 分类源节点固定在左侧纵排（key 与 external_feed_items.source_type 对应）
const CATEGORY_NODES: { key: FeedSourceType; label: string; x: number; y: number }[] =
  (Object.keys(FEED_TYPE_LABELS) as FeedSourceType[]).map((key, i) => ({
    key, label: FEED_TYPE_LABELS[key], x: 24, y: 36 + i * 88,
  }))

// ---------- 位置记忆（仅本地浏览器） ----------
const LS_KEY = 'admin.mediaBoardLayout.v1'
interface Pos { x: number; y: number }
const saved = (() => {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return null
    const v = JSON.parse(raw)
    if (typeof v !== 'object' || v === null) return null
    return v as { cards: Record<string, Pos>; pan: Pos }
  } catch {
    return null
  }
})()
const layout = reactive({
  cards: (saved?.cards ?? {}) as Record<string, Pos>,
  pan: (saved?.pan ?? { x: 0, y: 0 }) as Pos,
})

function persist() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({ cards: layout.cards, pan: layout.pan }))
  } catch { /* 隐私模式等场景下写入失败可接受 */ }
}

/** 没有拖拽过的卡片按序自动排在右侧两列，保证初始就好看 */
function autoPos(index: number): Pos {
  const col = index % 2
  const row = Math.floor(index / 2)
  return { x: 470 + col * 290, y: 36 + row * 250 }
}

const cardPos = (id: number) => {
  const idx = props.accounts.findIndex((a) => a.id === id)
  const pos = layout.cards[String(id)] ?? autoPos(Math.max(idx, 0))
  return { left: pos.x + 'px', top: pos.y + 'px', width: CARD_W + 'px' }
}

const worldStyle = computed(() => ({
  width: WORLD_W + 'px',
  height: WORLD_H + 'px',
  transform: `translate(${layout.pan.x}px, ${layout.pan.y}px)`,
}))

// ---------- 连线：账号卡 → 其内容方向的分类节点 ----------
const edges = computed(() => {
  const list: { key: string; x1: number; y1: number; x2: number; y2: number; faint: boolean }[] = []
  props.accounts.forEach((acc) => {
    const idx = props.accounts.findIndex((a) => a.id === acc.id)
    const pos = layout.cards[String(acc.id)] ?? autoPos(Math.max(idx, 0))
    const all = !acc.content_scope?.length
    const scope = all ? CATEGORY_NODES.map((c) => c.key) : acc.content_scope!
    scope.forEach((key) => {
      const node = CATEGORY_NODES.find((c) => c.key === key)
      if (!node) return
      list.push({
        key: `${acc.id}-${key}`,
        x1: node.x + NODE_W,
        y1: node.y + NODE_H / 2,
        x2: pos.x,
        y2: pos.y + 56, // 锚在卡片头像/名称行中心，展开收起不影响端点
        faint: all,
      })
    })
  })
  return list
})

// ---------- 画布平移 ----------
const canvasRef = ref<HTMLElement>()
const panning = ref(false)
let panStart: { px: number; py: number; ox: number; oy: number } | null = null

function onPanMove(ev: PointerEvent) {
  if (!panStart) return
  layout.pan.x = panStart.ox + (ev.clientX - panStart.px)
  layout.pan.y = panStart.oy + (ev.clientY - panStart.py)
}

function endPan() {
  if (!panStart) return
  panStart = null
  panning.value = false
  persist()
}

// ---------- 卡片拖拽 ----------
const expandedId = ref<number | null>(null)
const dragId = ref<number | null>(null)
let drag: { id: number; dx: number; dy: number } | null = null

function onCardPointerDown(row: MediaAccount, ev: PointerEvent) {
  // 按钮 / 展开条 / 链接上按下时不进入拖拽，保留点击语义
  if ((ev.target as HTMLElement).closest('button, .acc-foot, a, input, textarea')) return
  ev.preventDefault()
  const idx = props.accounts.findIndex((a) => a.id === row.id)
  const pos = layout.cards[String(row.id)] ?? autoPos(Math.max(idx, 0))
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  const worldX = ev.clientX - rect.left - layout.pan.x
  const worldY = ev.clientY - rect.top - layout.pan.y
  drag = { id: row.id, dx: worldX - pos.x, dy: worldY - pos.y }
  dragId.value = row.id
}

function onDragMove(ev: PointerEvent) {
  if (!drag) return
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  const worldX = ev.clientX - rect.left - layout.pan.x
  const worldY = ev.clientY - rect.top - layout.pan.y
  layout.cards[String(drag.id)] = {
    x: Math.max(0, Math.min(WORLD_W - CARD_W, worldX - drag.dx)),
    y: Math.max(0, Math.min(WORLD_H - 120, worldY - drag.dy)),
  }
}

function endDrag() {
  if (!drag) return
  drag = null
  dragId.value = null
  persist()
}

function onPointerMove(ev: PointerEvent) {
  if (drag) onDragMove(ev)
  else if (panStart) onPanMove(ev)
}
function onPointerUp() {
  if (drag) endDrag()
  else endPan()
}

function onCanvasPointerDown(ev: PointerEvent) {
  // 空白处按下 → 平移画布；世界层内的卡片会先在自己的事件里处理并冒泡到这里，
  // 因此只有非卡片的按下才进入平移
  if ((ev.target as HTMLElement).closest('.board-card')) return
  panning.value = true
  panStart = { px: ev.clientX, py: ev.clientY, ox: layout.pan.x, oy: layout.pan.y }
}

window.addEventListener('pointermove', onPointerMove)
window.addEventListener('pointerup', onPointerUp)
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
})

/** 重置布局：清掉本地记忆，全部回默认排布（供父组件的「重置布局」按钮调用） */
function resetLayout() {
  layout.cards = {}
  layout.pan = { x: 0, y: 0 }
  persist()
}
defineExpose({ resetLayout })
</script>

<style scoped>
.board-wrap {
  position: relative;
}
.board-hint {
  position: absolute;
  top: 8px;
  right: 12px;
  z-index: 3;
  font-size: 12px;
  color: #a5aec1;
  pointer-events: none;
}
.board-canvas {
  position: relative;
  height: 560px;
  border: 1px solid #e3e8f7;
  border-radius: 12px;
  overflow: hidden;
  cursor: grab;
  background: #fbfcff;
  user-select: none;
}
.board-canvas.grabbing {
  cursor: grabbing;
}
.board-world {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  background-image: radial-gradient(circle, #dfe4f2 1.2px, transparent 1.2px);
  background-size: 22px 22px;
}
.board-edges {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}
.board-edge {
  stroke: #b9c8f5;
  stroke-width: 1.5;
  stroke-dasharray: 6 4;
}
.board-edge.faint {
  stroke: #d9e1f5;
}
.cat-node {
  position: absolute;
  width: 128px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #dbe2f0;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  box-shadow: 0 1px 3px rgba(31, 45, 61, 0.05);
  user-select: none;
}

/* ---- 账号卡片（与原卡片流同款观感，改为画布内绝对定位） ---- */
.board-card {
  position: absolute;
  background: #fff;
  padding: 14px 16px 0;
  display: flex;
  flex-direction: column;
  cursor: grab;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  touch-action: none;
}
.board-card:hover {
  border-color: #b9c8f5;
  box-shadow: 0 3px 12px rgba(59, 111, 245, 0.1);
  transform: translateY(-2px);
}
.board-card.dragging {
  cursor: grabbing;
  box-shadow: 0 6px 18px rgba(59, 111, 245, 0.16);
  border-color: #b9c8f5;
  transform: translateY(0) scale(1.02);
  z-index: 5;
}
.board-card:active {
  cursor: grabbing;
}
.acc-card-disabled {
  background: #f8f9fb;
}
.acc-card-disabled .acc-title,
.acc-card-disabled .acc-desc {
  color: #9aa3b2;
}
.acc-chips {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}
.acc-chip {
  font-size: 11px;
  line-height: 1;
  padding: 4px 7px;
  border-radius: 5px;
  border: 1px solid #dbe2f0;
  color: #64748b;
  background: #f8faff;
  white-space: nowrap;
  flex-shrink: 0;
}
.acc-chip-on {
  border-color: #c8ecd4;
  color: #2f9e5b;
  background: #f0fbf4;
}
.acc-chip-off {
  border-color: #e2e5ea;
  color: #98a1ad;
  background: #f4f5f7;
}
.acc-chip-freq {
  border-color: #d8e4f8;
  color: #3b6ff5;
  background: #f0f5ff;
}
/* 拖拽把手：hover 才浮现，提示卡片可拖；绝对定位不挤 chip 行 */
.acc-grip {
  position: absolute;
  top: 10px;
  right: 10px;
  color: #b6bfd0;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
  display: inline-flex;
}
.board-card:hover .acc-grip {
  opacity: 1;
}
/* 身份行：头像 + 名称/账号名 */
.acc-idrow {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.acc-avatar {
  flex-shrink: 0;
  background: #e8efff;
  color: #3b6ff5;
  font-weight: 600;
}
.acc-idmeta {
  min-width: 0;
}
.acc-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2d3d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.acc-username {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 1px;
}
/* 展开面板出现动效 */
.accpop-enter-active {
  animation: accpop 0.18s ease-out;
}
@keyframes accpop {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
}
.acc-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 21px;
}
.acc-foot {
  margin-top: auto;
  border-top: 1px solid #edf0f7;
  background: #f8faff;
  margin-left: -16px;
  margin-right: -16px;
  padding: 9px 16px;
  border-radius: 0 0 12px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.acc-card-disabled .acc-foot {
  background: #f4f5f7;
}
.acc-foot-status {
  font-size: 12px;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.acc-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.acc-dot.on {
  background: #34c77b;
  box-shadow: 0 0 0 3px rgba(52, 199, 123, 0.15);
}
.acc-dot.off {
  background: #c2c9d4;
}
.acc-expand {
  font-size: 12px;
  color: #3b6ff5;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
  flex-shrink: 0;
}
.acc-chevron {
  transition: transform 0.2s;
}
.acc-chevron.open {
  transform: rotate(180deg);
}
.acc-more {
  padding: 4px 0 12px;
}
.acc-meta-line {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}
.acc-scope {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.acc-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}
.acc-actions .el-button + .el-button {
  margin-left: 4px;
}
</style>
