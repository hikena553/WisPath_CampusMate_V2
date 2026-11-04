<template>
  <div class="board-wrap">
    <div class="board-toolbar">
      <div class="board-legend">
        <span class="lg-item"><i class="lg-dot station"></i>资讯站</span>
        <span class="lg-item"><i class="lg-dot account"></i>资讯账号</span>
        <span class="lg-item"><i class="lg-dot source"></i>资讯源连接</span>
        <span class="lg-tip">画布无边界 · 拖动节点排版 · 滚轮平移 · Ctrl+滚轮或 ± 缩放 · 连线中点 × 可断开（停止抓取与展示，内容保留）</span>
      </div>
      <div class="zoom-bar">
        <button class="zoom-btn" title="缩小" @click="zoomBy(-1)">−</button>
        <span class="zoom-pct">{{ Math.round(scale * 100) }}%</span>
        <button class="zoom-btn" title="放大" @click="zoomBy(1)">＋</button>
        <button class="zoom-text" @click="toggleAllCollapse">{{ allCollapsed ? '展开全部源' : '折叠全部源' }}</button>
        <button class="zoom-text" @click="resetView">重置视图</button>
        <button class="zoom-text" @click="resetLayout">重置布局</button>
      </div>
    </div>

    <div
      ref="canvasRef"
      class="board-canvas"
      :class="{ grabbing: panning || !!drag }"
      :style="{ height: canvasBox.h + 'px' }"
      @pointerdown="onCanvasPointerDown"
    >
      <!-- 固定的底层网格：铺满画布，不随世界层平移缩放 -->
      <div class="board-grid"></div>
      <div class="board-world" :style="worldStyle">
        <svg
          class="board-edges"
          :viewBox="`${contentBounds.x} ${contentBounds.y} ${contentBounds.w} ${contentBounds.h}`"
          :width="contentBounds.w"
          :height="contentBounds.h"
          :style="{ left: contentBounds.x + 'px', top: contentBounds.y + 'px' }"
        >
          <path
            v-for="e in edges"
            :key="e.key"
            :d="e.d"
            class="board-edge"
            :class="e.kind === 'station' ? 'edge-station' : 'edge-source'"
          />
        </svg>
        <button
          v-for="e in edges"
          :key="'cut-' + e.key"
          class="edge-cut"
          :style="{ left: e.mx + 'px', top: e.my + 'px' }"
          :title="e.kind === 'station' ? '断开资讯站与账号的连接（不删除账号）' : '断开账号与资讯源的连接（不删除资讯源）'"
          @pointerdown.stop
          @click.stop="cutEdge(e)"
        >×</button>

        <!-- 一级：绵小城 AI 资讯站 -->
        <div
          class="station-node"
          :class="{ dragging: isDragging('s'), off: !station.is_enabled }"
          :style="{ left: posOf('s').x + 'px', top: posOf('s').y + 'px', width: STATION_W + 'px' }"
          @pointerdown="onNodePointerDown('s', $event, STATION_W, 210)"
        >
          <div class="station-head">
            <div class="station-logo">绵</div>
            <div class="station-title-wrap">
              <div class="station-title">{{ station.name }}</div>
              <div class="station-sub">绵小城 AI 资讯站</div>
            </div>
            <span class="station-state" :class="station.is_enabled ? 'on' : 'off'">
              {{ station.is_enabled ? '运行中' : '已停用' }}
            </span>
          </div>
          <div class="station-desc">{{ station.description || '统一管理资讯账号、抓取节奏与发帖模式，断开连接只影响投递不删内容。' }}</div>
          <div class="station-meta">
            <div class="meta-cell">
              <span class="meta-k">抓取节奏</span>
              <span class="meta-v">{{ intervalLabel(station.ingest_interval_minutes) }}</span>
            </div>
            <div class="meta-cell">
              <span class="meta-k">每日汇总</span>
              <span class="meta-v">{{ String(station.digest_hour).padStart(2, '0') }}:00</span>
            </div>
            <div class="meta-cell">
              <span class="meta-k">发帖模式</span>
              <span class="meta-v">{{ publishModeLabel(station.publish_mode) }}</span>
            </div>
          </div>
          <div class="station-foot">
            <span class="station-stat">账号 {{ accounts.length }} · 已接入 {{ connectedCount }} · 资讯源 {{ totalLinks }}</span>
            <div class="station-actions">
              <button class="mini-btn light" @click.stop="emit('open-station')">站点设置</button>
              <button class="mini-btn light" @click.stop="emit('refresh')">触发抓取</button>
              <button class="mini-btn add" title="新增资讯账号" @click.stop="emit('add-account')">＋</button>
            </div>
          </div>
        </div>

        <!-- 二级：资讯账号 -->
        <div
          v-for="row in accounts"
          :key="'a' + row.id"
          class="acc-card board-card"
          :class="{
            'acc-card-disabled': !row.is_enabled,
            'acc-card-orphan': !row.station_connected,
            dragging: isDragging('a:' + row.id),
          }"
          :style="{ left: posOf('a:' + row.id).x + 'px', top: posOf('a:' + row.id).y + 'px', width: CARD_W + 'px' }"
          @pointerdown="onNodePointerDown('a:' + row.id, $event, CARD_W, 240)"
        >
          <div class="node-actions" @pointerdown.stop>
            <button
              :title="isCollapsed(row.id) ? '展开本账号的资讯源' : '折叠本账号的资讯源'"
              @click.stop="toggleCollapse(row.id)"
            >
              <el-icon :size="12" class="fold-icon" :class="{ folded: isCollapsed(row.id) }"><ChevronDown /></el-icon>
            </button>
            <button title="连接资讯源" @click.stop="emit('open-link-picker', row)">＋</button>
            <button title="删除资讯账号" @click.stop="emit('remove-account', row)">−</button>
          </div>
          <div class="acc-chips">
            <span class="acc-chip">资讯号</span>
            <span class="acc-chip" :class="row.is_enabled ? 'acc-chip-on' : 'acc-chip-off'">
              {{ row.is_enabled ? '自动发帖' : '待命' }}
            </span>
            <span class="acc-chip acc-chip-freq" :title="'发帖频率：' + relayFreqLabel(row.relay_interval_minutes)">
              {{ relayFreqShort(row.relay_interval_minutes) }}
            </span>
            <span v-if="isCollapsed(row.id)" class="acc-chip acc-chip-fold">
              已折叠 {{ (row.links || []).length }} 个源
            </span>
            <span v-if="!row.station_connected" class="acc-chip acc-chip-orphan">未接入资讯站</span>
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
              <div class="acc-link-head">
                <span>连接的资讯源（{{ (row.links || []).length }}）</span>
                <button class="link-add" @click.stop="emit('open-link-picker', row)">＋ 连接</button>
              </div>
              <div class="acc-linklist">
                <span v-for="link in row.links || []" :key="link.id" class="acc-linkchip">
                  <i class="acc-linkdot" :class="link.enabled && link.source_enabled ? 'on' : 'off'"></i>
                  {{ link.name }}
                  <button class="x" title="断开这条连接（不删除资讯源）" @click.stop="emit('remove-link', link)">×</button>
                </span>
                <span v-if="!(row.links || []).length" class="acc-linkempty">未连接资讯源，暂按内容方向转发</span>
              </div>
              <div class="acc-actions">
                <el-button
                  size="small" type="primary" round :disabled="!row.is_enabled || !row.station_connected"
                  :loading="publishingId === row.id"
                  @click.stop="emit('publish', row)"
                >立即发布</el-button>
                <el-button size="small" round @click.stop="emit('edit-account', row)">编辑</el-button>
                <el-button
                  size="small" round :type="row.is_enabled ? 'warning' : 'success'"
                  @click.stop="emit('toggle-account', row)"
                >{{ row.is_enabled ? '停用' : '启用' }}</el-button>
                <el-button
                  v-if="!row.station_connected"
                  size="small" round type="success" plain
                  @click.stop="emit('toggle-station-link', row, true)"
                >接入资讯站</el-button>
                <el-button size="small" round type="danger" plain @click.stop="emit('remove-account', row)">删除</el-button>
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

        <!-- 三级：资讯源连接 -->
        <template v-for="row in accounts" :key="'lgroup' + row.id">
          <div
            v-for="link in visibleLinks(row)"
            :key="'l' + link.id"
            class="link-node board-card"
            :class="{
              dragging: isDragging('l:' + link.id),
              'link-node-off': !link.enabled || !link.source_enabled,
            }"
            :style="{ left: posOf('l:' + link.id).x + 'px', top: posOf('l:' + link.id).y + 'px', width: LINK_W + 'px' }"
            @pointerdown="onNodePointerDown('l:' + link.id, $event, LINK_W, LINK_H)"
          >
            <div class="node-actions" @pointerdown.stop>
              <button title="编辑资讯源" @click.stop="emit('edit-source', link.feed_source_id)">✎</button>
              <button title="删除资讯源（内容一并删除）" @click.stop="emit('remove-source', link.feed_source_id, link.source_name)">−</button>
            </div>
            <div class="link-top">
              <span class="link-name" :title="link.name">{{ link.name }}</span>
              <span class="link-type">{{ typeLabel(link.source_type) }}</span>
            </div>
            <div class="link-source">
              <span class="link-srcname" :title="link.source_name">{{ link.source_name }}</span>
              <span class="link-kind">{{ kindLabel(link.source_kind) }}</span>
            </div>
            <div class="link-meta">
              <span class="link-count">已入库 {{ sourceOf(link)?.item_count ?? 0 }} 条</span>
              <span class="link-state" :class="link.enabled && link.source_enabled ? 'on' : 'off'">
                {{ !link.source_enabled ? '源已停用' : link.enabled ? '已连接' : '已断开' }}
              </span>
            </div>
            <div class="link-fetch">
              最近抓取 {{ formatTime(sourceOf(link)?.last_ingested_at || null) || '尚未抓取' }}
            </div>
            <div class="link-foot">
              <span class="link-owner">@{{ row.name }}</span>
              <button class="link-cut" @click.stop="emit('remove-link', link)">断开连接</button>
            </div>
          </div>
        </template>
      </div>

      <div class="board-zoom">
        <button class="zoom-btn" title="缩小" @click.stop="zoomBy(-1)">−</button>
        <span class="zoom-pct">{{ Math.round(scale * 100) }}%</span>
        <button class="zoom-btn" title="放大" @click.stop="zoomBy(1)">＋</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import type {
  FeedSourceType,
  MediaAccountGraph,
  MediaGraphSource,
  MediaSourceLink,
  MediaStationConfig,
} from '@/api/admin'

const props = defineProps<{
  station: MediaStationConfig
  accounts: MediaAccountGraph[]
  sources: MediaGraphSource[]
  publishingId: number | null
}>()

const emit = defineEmits<{
  'open-station': []
  'add-account': []
  'edit-account': [row: MediaAccountGraph]
  'toggle-account': [row: MediaAccountGraph]
  'remove-account': [row: MediaAccountGraph]
  publish: [row: MediaAccountGraph]
  'toggle-station-link': [row: MediaAccountGraph, connected: boolean]
  'open-link-picker': [row: MediaAccountGraph]
  'remove-link': [link: MediaSourceLink]
  'edit-source': [sourceId: number]
  'remove-source': [sourceId: number, sourceName: string]
  refresh: []
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
const kindLabel = (k: string) =>
  ({ rss: 'RSS', html: '网页', arxiv: 'arXiv', github: 'GitHub', gitee: 'Gitee', lmarena: '权威榜' }[k] || k)

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

const intervalLabel = (m: number) => (m >= 1440 ? '每天 1 次' : m >= 60 ? `每 ${m / 60} 小时` : `每 ${m} 分钟`)
const publishModeLabel = (m: string) =>
  ({ auto: '逐条+汇总', digest: '仅每日汇总', manual: '仅手动发布' }[m] || m)

function formatTime(t: string | null) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return String(t).slice(0, 19)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ---------- 画布尺寸 ----------
/**
 * 画布自身尺寸 = 视口剩余空间（挂载时按画布顶部到窗口底部的实际距离计算），
 * 世界层尺寸 = 内容实际占用范围与可视区域（canvas/scale）取大者。
 * 这样内容恰好铺满画布时，世界层渲染出来与画布（即屏幕可见区域）等大，
 * 不会再出现固定的 2600×2200 画布远大于屏幕占用的错位。
 */
const canvasBox = reactive({ w: 1200, h: 640 })

/** 量一次画布可用高度：画布在内容滚动容器里占满剩余空间（扣掉底部 24px 留白） */
function measureCanvas() {
  const el = canvasRef.value
  if (!el) return
  // 页签未激活时画布不可见（clientWidth=0），此时不量，等 ResizeObserver 拿到真实尺寸再算
  if (!el.clientWidth) return
  const box = el.getBoundingClientRect()
  const host = el.closest('.page-container') as HTMLElement | null
  const available = host
    ? host.clientHeight - (box.top - host.getBoundingClientRect().top) - 24
    : window.innerHeight - box.top - 24
  // 500px 以下的小窗口也别撑出滚动条：宁可画布矮一些，也要和可视区域保持一致
  canvasBox.h = Math.max(320, Math.min(2400, Math.round(available)))
  canvasBox.w = el.clientWidth
}

/** 所有节点的包围盒（允许负坐标：节点可以拖到世界原点左/上方，画布没有边界） */
const contentBounds = computed(() => {
  let minX = 0
  let minY = 0
  let maxX = 0
  let maxY = 0
  const keys = new Set([...Object.keys(autoPos.value), ...Object.keys(layout.pos)])
  keys.forEach((key) => {
    const p = posOf(key)
    const w = key === 's' ? STATION_W : key.startsWith('a:') ? CARD_W : LINK_W
    const h = key === 's' ? 260 : key.startsWith('a:') ? 240 : LINK_H
    minX = Math.min(minX, p.x)
    minY = Math.min(minY, p.y)
    maxX = Math.max(maxX, p.x + w)
    maxY = Math.max(maxY, p.y + h)
  })
  const PAD = 48
  return {
    x: minX - PAD,
    y: minY - PAD,
    w: maxX - minX + PAD * 2,
    h: maxY - minY + PAD * 2,
  }
})

const worldSize = computed(() => {
  const viewW = canvasBox.w / scale.value
  const viewH = canvasBox.h / scale.value
  const b = contentBounds.value
  return {
    w: Math.min(8000, Math.max(viewW, b.x + b.w)),
    h: Math.min(8000, Math.max(viewH, b.y + b.h)),
  }
})
const CARD_W = 252
const LINK_W = 212
const LINK_H = 138
const STATION_W = 306

// ---------- 位置记忆（本地浏览器） ----------
const LS_KEY = 'admin.mediaBoardLayout.v3'
interface Pos { x: number; y: number }
interface LayoutCache { pos: Record<string, Pos>; pan: Pos; scale: number }

const saved = (() => {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return null
    const v = JSON.parse(raw)
    if (typeof v !== 'object' || v === null) return null
    return v as LayoutCache
  } catch {
    return null
  }
})()

const layout = reactive<{ pos: Record<string, Pos>; pan: Pos }>({
  pos: saved?.pos ?? {},
  pan: saved?.pan ?? { x: 0, y: 0 },
})
const scale = ref(clampScale(saved?.scale ?? 1))

function persist() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({ pos: layout.pos, pan: layout.pan, scale: scale.value }))
  } catch { /* 隐私模式写入失败可接受 */ }
}

let persistTimer: ReturnType<typeof setTimeout> | undefined
/** 滚轮平移会连续触发，合并成一次写入，避免频繁写 localStorage */
function persistSoon() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(persist, 200)
}

/** 默认排布：资讯站居左中部；账号按两列均衡分布，每个账号的资讯源排在它右侧。
 *  二级账号改为按分类拆分后数量变多，单列会纵向拉得过长，两列能让一屏看到全部账号。 */
const autoPos = computed<Record<string, Pos>>(() => {
  const map: Record<string, Pos> = {}
  const layoutOf = (n: number) => {
    // 每个账号的资讯源最多 3 行，超出向右分列
    const cols = Math.max(1, Math.ceil(n / 3))
    const rows = Math.max(1, Math.ceil(n / cols))
    return { cols, rows, span: Math.max(280, rows * 152 + 20) }
  }
  // 贪心分列：账号放进当前较矮的一列，两列高度尽量均衡
  const columns: { accounts: MediaAccountGraph[]; height: number }[] = [
    { accounts: [], height: 0 },
    { accounts: [], height: 0 },
  ]
  props.accounts.forEach((acc) => {
    const target = columns[0].height <= columns[1].height ? columns[0] : columns[1]
    target.accounts.push(acc)
    target.height += layoutOf((acc.links || []).length).span + 16
  })

  let x = 470
  const bottom: number[] = []
  columns.forEach((col) => {
    let y = 30
    const maxCols = col.accounts.reduce(
      (m, a) => Math.max(m, layoutOf((a.links || []).length).cols), 1,
    )
    col.accounts.forEach((acc) => {
      const links = acc.links || []
      const { rows, span } = layoutOf(links.length)
      map[`a:${acc.id}`] = { x, y }
      links.forEach((link, j) => {
        const colIdx = Math.floor(j / rows)
        const rowIdx = j % rows
        map[`l:${link.id}`] = { x: x + CARD_W + 64 + colIdx * 232, y: y + 20 + rowIdx * 152 }
      })
      y += span
    })
    bottom.push(y)
    x += CARD_W + 64 + maxCols * 232 + 120
  })

  // 资讯站纵向居中于两列账号之间
  const totalH = Math.max(...bottom, 620)
  map.s = { x: 60, y: Math.max(60, (totalH - 260) / 2) }
  return map
})

function posOf(key: string): Pos {
  return layout.pos[key] || autoPos.value[key] || { x: 0, y: 0 }
}

const connectedCount = computed(() => props.accounts.filter((a) => a.station_connected).length)
const totalLinks = computed(() =>
  props.accounts.reduce((n, a) => n + (a.links || []).length, 0),
)

const sourceOf = (link: MediaSourceLink) => props.sources.find((s) => s.id === link.feed_source_id)

// ---------- 画布平移 / 缩放 ----------
const canvasRef = ref<HTMLElement>()
const panning = ref(false)
let panStart: { px: number; py: number; ox: number; oy: number } | null = null

function clampScale(v: number) {
  // 允许缩到 25%，方便一次看全三级结构；画布内始终可平移，不会出现到不了的区域
  return Math.max(0.25, Math.min(2, v))
}

const worldStyle = computed(() => ({
  width: worldSize.value.w + 'px',
  height: worldSize.value.h + 'px',
  transform: `translate(${layout.pan.x}px, ${layout.pan.y}px) scale(${scale.value})`,
}))

/** 以视口中心缩放（按钮） */
function zoomBy(dir: 1 | -1) {
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  applyZoom(rect.width / 2, rect.height / 2, dir > 0 ? 1.15 : 1 / 1.15)
}

/** 以指针为锚点缩放，保证鼠标下的世界坐标点不动 */
function applyZoom(px: number, py: number, factor: number) {
  const next = clampScale(scale.value * factor)
  if (next === scale.value) return
  const wx = (px - layout.pan.x) / scale.value
  const wy = (py - layout.pan.y) / scale.value
  scale.value = next
  layout.pan.x = px - wx * next
  layout.pan.y = py - wy * next
  persist()
}

/**
 * 滚轮默认平移画布（Shift 横向），不再“鼠标一放上去滚动就缩放”；
 * 缩放改为 Ctrl/⌘ + 滚轮或工具栏 ± 按钮。
 */
function onWheel(ev: WheelEvent) {
  if ((ev.target as HTMLElement).closest('.board-zoom')) return
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  ev.preventDefault()
  if (ev.ctrlKey || ev.metaKey) {
    applyZoom(ev.clientX - rect.left, ev.clientY - rect.top, ev.deltaY < 0 ? 1.12 : 1 / 1.12)
    return
  }
  if (ev.shiftKey) {
    layout.pan.x -= ev.deltaY
  } else {
    layout.pan.x -= ev.deltaX
    layout.pan.y -= ev.deltaY
  }
  persistSoon()
}

function resetView() {
  scale.value = 1
  layout.pan = { x: 0, y: 0 }
  persist()
}

/** 重置布局：清掉本地记忆，全部回默认排布 */
function resetLayout() {
  layout.pos = {}
  layout.pan = { x: 0, y: 0 }
  scale.value = 1
  persist()
  nextTick(fitView)
}

/** 首次进入/重置布局时自动适配视口，让内容居中铺满画布 */
function fitView() {
  measureCanvas()
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect || !rect.width || !rect.height) return
  const b = contentBounds.value
  const next = clampScale(Math.min(1, rect.width / (b.w + 80), rect.height / (b.h + 80)))
  scale.value = next
  layout.pan = {
    x: (rect.width - b.w * next) / 2 - b.x * next,
    y: (rect.height - b.h * next) / 2 - b.y * next,
  }
  persist()
}

// ---------- 节点拖拽 ----------
interface DragState { key: string; dx: number; dy: number; w: number; h: number; sx: number; sy: number; moved: boolean }
const drag = ref<DragState | null>(null)
const expandedId = ref<number | null>(null)

/** 每个二级账号的三级资讯源可独立折叠，避免账号变多后画布过大 */
const collapsedIds = reactive(new Set<number>())
const isCollapsed = (id: number) => collapsedIds.has(id)
const visibleLinks = (row: MediaAccountGraph) => (isCollapsed(row.id) ? [] : (row.links || []))
const allCollapsed = computed(
  () => props.accounts.length > 0 && props.accounts.every((a) => collapsedIds.has(a.id)),
)

function toggleCollapse(id: number) {
  if (collapsedIds.has(id)) collapsedIds.delete(id)
  else collapsedIds.add(id)
}

function toggleAllCollapse() {
  if (allCollapsed.value) collapsedIds.clear()
  else props.accounts.forEach((a) => collapsedIds.add(a.id))
}

const isDragging = (key: string) => drag.value?.key === key

function onNodePointerDown(key: string, ev: PointerEvent, w: number, h: number) {
  if ((ev.target as HTMLElement).closest('button, a, input, textarea, .acc-foot, .node-actions')) return
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  ev.preventDefault()
  const p = posOf(key)
  const worldX = (ev.clientX - rect.left - layout.pan.x) / scale.value
  const worldY = (ev.clientY - rect.top - layout.pan.y) / scale.value
  drag.value = { key, dx: worldX - p.x, dy: worldY - p.y, w, h, sx: ev.clientX, sy: ev.clientY, moved: false }
}

function onCanvasPointerDown(ev: PointerEvent) {
  if ((ev.target as HTMLElement).closest('.board-card, .station-node, .edge-cut, .board-zoom')) return
  panning.value = true
  panStart = { px: ev.clientX, py: ev.clientY, ox: layout.pan.x, oy: layout.pan.y }
}

function onPointerMove(ev: PointerEvent) {
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return
  if (drag.value) {
    if (Math.abs(ev.clientX - drag.value.sx) > 4 || Math.abs(ev.clientY - drag.value.sy) > 4) {
      drag.value.moved = true
    }
    const worldX = (ev.clientX - rect.left - layout.pan.x) / scale.value
    const worldY = (ev.clientY - rect.top - layout.pan.y) / scale.value
    // 画布无边界：允许任意方向拖拽（含负坐标），世界层与连线会随内容重新计算包围盒
    layout.pos[drag.value.key] = {
      x: worldX - drag.value.dx,
      y: worldY - drag.value.dy,
    }
  } else if (panStart) {
    layout.pan.x = panStart.ox + (ev.clientX - panStart.px)
    layout.pan.y = panStart.oy + (ev.clientY - panStart.py)
  }
}

function onPointerUp() {
  if (drag.value) {
    // 单击（未拖动）根节点 = 打开资讯站设置
    if (!drag.value.moved && drag.value.key === 's') emit('open-station')
    drag.value = null
    persist()
  } else if (panStart) {
    panStart = null
    panning.value = false
    persist()
  }
}

let canvasObserver: ResizeObserver | null = null
let autoFitDone = false

/** 画布从隐藏（未激活页签）变为可见时，补一次尺寸测量与自动适配 */
function maybeAutoFit() {
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect || !rect.width) return
  measureCanvas()
  if (autoFitDone) return
  autoFitDone = true
  if (!saved || !saved.pos || Object.keys(saved.pos).length === 0) fitView()
}

function onResize() {
  measureCanvas()
}

onMounted(() => {
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('resize', onResize)
  canvasRef.value?.addEventListener('wheel', onWheel, { passive: false })
  if ('ResizeObserver' in window && canvasRef.value) {
    canvasObserver = new ResizeObserver(() => maybeAutoFit())
    canvasObserver.observe(canvasRef.value)
  }
  // 先按真实视口剩余空间定高，再决定是否自动适配（避免用固定高度造成画布与屏幕错位）
  nextTick(maybeAutoFit)
})
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('resize', onResize)
  canvasRef.value?.removeEventListener('wheel', onWheel)
  canvasObserver?.disconnect()
  canvasObserver = null
})

// ---------- 连线 ----------
interface Edge {
  key: string
  kind: 'station' | 'link'
  account: MediaAccountGraph
  link?: MediaSourceLink
  d: string
  mx: number
  my: number
}

function curve(x1: number, y1: number, x2: number, y2: number) {
  const dx = Math.max(50, Math.abs(x2 - x1) * 0.5)
  const cx1 = x1 + dx
  const cx2 = x2 - dx
  return {
    d: `M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`,
    mx: (x1 + 3 * cx1 + 3 * cx2 + x2) / 8,
    my: (y1 + 3 * y1 + 3 * y2 + y2) / 8,
  }
}

const edges = computed<Edge[]>(() => {
  const out: Edge[] = []
  const sp = posOf('s')
  props.accounts.forEach((acc) => {
    const ap = posOf(`a:${acc.id}`)
    if (acc.station_connected) {
      const c = curve(sp.x + STATION_W, sp.y + 110, ap.x, ap.y + 56)
      out.push({ key: `s-${acc.id}`, kind: 'station', account: acc, ...c })
    }
    // 折叠后的账号只保留站→账号连线，三级资讯源及连线一并隐藏
    if (isCollapsed(acc.id)) return
    ;(acc.links || []).forEach((link) => {
      const lp = posOf(`l:${link.id}`)
      const c = curve(ap.x + CARD_W, ap.y + 56, lp.x, lp.y + LINK_H / 2)
      out.push({ key: `l-${link.id}`, kind: 'link', account: acc, link, ...c })
    })
  })
  return out
})

function cutEdge(e: Edge) {
  if (e.kind === 'station') {
    emit('toggle-station-link', e.account, false)
    return
  }
  if (e.link) emit('remove-link', e.link)
}

defineExpose({ resetLayout, resetView })
</script>

<style scoped>
.board-wrap {
  position: relative;
}
.board-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.board-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: #8a94a6;
  flex-wrap: wrap;
}
.lg-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.lg-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.lg-dot.station {
  background: #1e2227;
}
.lg-dot.account {
  background: #3b6ff5;
}
.lg-dot.source {
  background: #b9c8f5;
}
.lg-tip {
  color: #a5aec1;
}
.zoom-bar {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.zoom-btn {
  width: 26px;
  height: 26px;
  border: 1px solid #dbe2f0;
  background: #fff;
  color: #475569;
  border-radius: 7px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  transition: all 0.15s;
}
.zoom-btn:hover {
  border-color: #3b6ff5;
  color: #3b6ff5;
}
.zoom-pct {
  min-width: 42px;
  text-align: center;
  font-size: 12px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}
.zoom-text {
  border: none;
  background: none;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  padding: 2px 4px;
}
.zoom-text:hover {
  color: #3b6ff5;
}

.board-canvas {
  position: relative;
  /* 实际高度由脚本按「画布顶部到窗口底部」实时计算，这里只作兜底 */
  height: 620px;
  min-height: 320px;
  border: 1px solid #e3e8f7;
  border-radius: 12px;
  overflow: hidden;
  cursor: grab;
  background: #fbfcff;
  user-select: none;
  touch-action: none;
}
.board-canvas.grabbing {
  cursor: grabbing;
}
/* 底层网格固定铺满画布，只有节点与连线随平移/缩放移动 */
.board-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(circle, #dfe4f2 1.2px, transparent 1.2px);
  background-size: 22px 22px;
  background-position: 0 0;
}
.board-world {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
}
.board-edges {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}
.board-edge {
  fill: none;
  stroke-width: 1.6;
  stroke-dasharray: 6 5;
}
.edge-station {
  stroke: #9db2e8;
}
.edge-source {
  stroke: #c4d2f5;
}

/* 连线中点断开按钮：默认低调，hover 才凸显 */
.edge-cut {
  position: absolute;
  width: 18px;
  height: 18px;
  margin-left: -9px;
  margin-top: -9px;
  border-radius: 50%;
  border: 1px solid #e2e8f4;
  background: #fff;
  color: #b0bacb;
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.55;
  transition: all 0.15s;
  z-index: 3;
}
.edge-cut:hover {
  opacity: 1;
  color: #64748b;
  border-color: #94a3b8;
  transform: scale(1.12);
}

/* ---------- 根节点：资讯站 ---------- */
.station-node {
  position: absolute;
  background: linear-gradient(160deg, #232a33 0%, #1b1f25 100%);
  border-radius: 14px;
  padding: 16px 18px 14px;
  color: #f5f7fa;
  cursor: grab;
  box-shadow: 0 6px 20px rgba(23, 30, 40, 0.22);
  touch-action: none;
  z-index: 2;
}
.station-node.off {
  filter: grayscale(0.35);
  opacity: 0.9;
}
.station-node.dragging {
  cursor: grabbing;
  z-index: 6;
  box-shadow: 0 10px 26px rgba(23, 30, 40, 0.3);
}
.station-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.station-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}
.station-title-wrap {
  min-width: 0;
  flex: 1;
}
.station-title {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.station-sub {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 2px;
}
.station-state {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  white-space: nowrap;
  flex-shrink: 0;
}
.station-state.on {
  background: rgba(52, 199, 123, 0.16);
  color: #6ee7a8;
}
.station-state.off {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
}
.station-desc {
  font-size: 11.5px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.62);
  margin: 10px 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.station-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.meta-cell {
  background: rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  padding: 7px 9px;
  min-width: 0;
}
.meta-k {
  display: block;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 3px;
  white-space: nowrap;
}
.meta-v {
  display: block;
  font-size: 11.5px;
  color: #edf2f8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.station-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
}
.station-stat {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  white-space: nowrap;
}
.station-actions {
  display: inline-flex;
  gap: 6px;
}
.mini-btn {
  border-radius: 6px;
  font-size: 11px;
  padding: 4px 8px;
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
}
.mini-btn.light {
  background: rgba(255, 255, 255, 0.1);
  color: #e8eef7;
  border-color: rgba(255, 255, 255, 0.14);
}
.mini-btn.light:hover {
  background: rgba(255, 255, 255, 0.18);
}
.mini-btn.add {
  width: 24px;
  padding: 4px 0;
  text-align: center;
  background: #fff;
  color: #1e2227;
  font-weight: 700;
}
.mini-btn.add:hover {
  background: #e9eef9;
}

/* ---------- 通用节点 ---------- */
.board-card {
  position: absolute;
  background: #fff;
  border: 1px solid #e3e8f7;
  border-radius: 12px;
}
.node-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: inline-flex;
  gap: 4px;
  z-index: 4;
}
.node-actions button {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 1px solid #e2e8f4;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.node-actions button:hover {
  border-color: #3b6ff5;
  color: #3b6ff5;
  background: #f4f7ff;
}
.fold-icon {
  transition: transform 0.15s;
}
.fold-icon.folded {
  transform: rotate(-90deg);
}

/* ---------- 账号卡片 ---------- */
.acc-card {
  padding: 14px 16px 0;
  display: flex;
  flex-direction: column;
  cursor: grab;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  touch-action: none;
  z-index: 2;
}
.acc-card:hover {
  border-color: #b9c8f5;
  box-shadow: 0 3px 12px rgba(59, 111, 245, 0.1);
  transform: translateY(-2px);
}
.acc-card.dragging {
  cursor: grabbing;
  box-shadow: 0 6px 18px rgba(59, 111, 245, 0.16);
  border-color: #b9c8f5;
  transform: translateY(0) scale(1.02);
  z-index: 5;
}
.acc-card-disabled {
  background: #f8f9fb;
}
.acc-card-disabled .acc-title,
.acc-card-disabled .acc-desc {
  color: #9aa3b2;
}
.acc-card-orphan {
  border-style: dashed;
  border-color: #d7dde8;
  background: #fbfbfd;
}
.acc-chips {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
  padding-right: 84px;
  flex-wrap: wrap;
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
.acc-chip-fold {
  border-color: #ecd9b4;
  color: #a1742a;
  background: #fdf8ec;
}
.acc-chip-freq {
  border-color: #d8e4f8;
  color: #3b6ff5;
  background: #f0f5ff;
}
.acc-chip-orphan {
  border-color: #e2e5ea;
  color: #8a94a6;
  background: #f4f5f7;
}
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
.accpop-enter-active {
  animation: accpop 0.18s ease-out;
}
@keyframes accpop {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
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
.acc-link-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #475569;
  margin-bottom: 6px;
}
.link-add {
  border: 1px solid #dbe2f0;
  background: #fff;
  color: #3b6ff5;
  border-radius: 5px;
  font-size: 11px;
  padding: 3px 7px;
  cursor: pointer;
}
.link-add:hover {
  border-color: #3b6ff5;
}
.acc-linklist {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.acc-linkchip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  padding: 3px 6px;
  border-radius: 5px;
  border: 1px solid #e2e8f4;
  background: #f8faff;
  color: #475569;
  max-width: 100%;
}
.acc-linkchip .x {
  border: none;
  background: none;
  color: #97a3b6;
  cursor: pointer;
  font-size: 11px;
  line-height: 1;
  padding: 0 1px;
}
.acc-linkchip .x:hover {
  color: #475569;
}
.acc-linkdot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.acc-linkdot.on {
  background: #34c77b;
}
.acc-linkdot.off {
  background: #c2c9d4;
}
.acc-linkempty {
  font-size: 11.5px;
  color: #a5aec1;
}
.acc-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}
.acc-actions .el-button + .el-button {
  margin-left: 4px;
}

/* ---------- 资讯源连接节点 ---------- */
.link-node {
  padding: 12px 14px;
  cursor: grab;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  touch-action: none;
  z-index: 2;
}
.link-node:hover {
  border-color: #b9c8f5;
  box-shadow: 0 3px 12px rgba(59, 111, 245, 0.1);
  transform: translateY(-2px);
}
.link-node.dragging {
  cursor: grabbing;
  box-shadow: 0 6px 18px rgba(59, 111, 245, 0.16);
  z-index: 5;
}
.link-node-off {
  background: #fafbfd;
  border-style: dashed;
}
.link-top {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 52px;
  margin-bottom: 6px;
}
.link-name {
  font-size: 13.5px;
  font-weight: 700;
  color: #1f2d3d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.link-type {
  font-size: 10.5px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f0f5ff;
  color: #3b6ff5;
  border: 1px solid #d8e4f8;
  white-space: nowrap;
  flex-shrink: 0;
}
.link-source {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #64748b;
  margin-bottom: 7px;
}
.link-srcname {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.link-kind {
  font-size: 10px;
  color: #94a3b8;
  border: 1px solid #e2e8f4;
  border-radius: 4px;
  padding: 1px 4px;
  flex-shrink: 0;
}
.link-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #8a94a6;
}
.link-state {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.link-state::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #c2c9d4;
}
.link-state.on::before {
  background: #34c77b;
}
.link-state.off::before {
  background: #c2c9d4;
}
.link-fetch {
  margin-top: 5px;
  font-size: 10.5px;
  color: #a5aec1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.link-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px dashed #edf0f7;
}
.link-owner {
  font-size: 10.5px;
  color: #a5aec1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.link-cut {
  border: 1px solid #e2e8f4;
  background: #fff;
  color: #64748b;
  border-radius: 4px;
  font-size: 10.5px;
  padding: 2px 6px;
  cursor: pointer;
  white-space: nowrap;
}
.link-cut:hover {
  border-color: #94a3b8;
  color: #334155;
}

/* 画布右下角悬浮缩放条 */
.board-zoom {
  position: absolute;
  right: 12px;
  bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #e3e8f7;
  border-radius: 9px;
  padding: 5px 7px;
  z-index: 8;
  backdrop-filter: blur(4px);
}
</style>
