<!--
  审批类列表通用的移动端卡片叠层：
  - 顶牌跟手左右滑动切换，松手过阈值飞出、下一张原地接上；
  - 叠层是左右两层：左滑露出「下一条」，右滑露出「上一条」，
    两层与顶牌同尺寸同位置，静止时被顶牌完全盖住；
  - 到头的那一侧不放卡片，改为收尾 / 起始提示卡，避免拖开时露出空白；
  - 换牌只做位移，不做透明度与缩放入场动画：顶牌一旦变半透明就会
    透出叠层，交接瞬间还会跳内容，那才是「闪」的来源。
  卡片内容由父级默认插槽决定（插槽参数为 row），组件只负责切换与分层。
-->
<template>
  <div
    v-if="topItem"
    class="stack"
    @touchstart.passive="onTouchStart"
    @touchmove.passive="onTouchMove"
    @touchend="onTouchEnd"
    @touchcancel="onTouchEnd"
  >
    <!-- 上一条那一层（向右拖时露出来），到第一条时退化为提示卡 -->
    <div
      class="stack-peek"
      :class="{ 'is-front': dragSign > 0, 'is-hint': !prevItem }"
      aria-hidden="true"
      :inert="true"
    >
      <slot v-if="prevItem" :row="prevItem" />
      <span v-else class="stack-peek-hint">{{ startHint }}</span>
    </div>

    <!-- 下一条那一层（向左拖时露出来），到最后一条时退化为提示卡 -->
    <div
      class="stack-peek"
      :class="{ 'is-front': dragSign <= 0, 'is-hint': !nextItem }"
      aria-hidden="true"
      :inert="true"
    >
      <slot v-if="nextItem" :row="nextItem" />
      <span v-else class="stack-peek-hint">{{ endHint }}</span>
    </div>

    <!-- key 换牌：飞出中的旧牌直接销毁（不回弹、不复用），新牌原地接上 -->
    <div
      :key="index"
      class="stack-top"
      :class="{ 'is-dragging': dragging }"
      :style="topStyle"
    >
      <slot :row="topItem" />
    </div>
  </div>

  <!-- 翻牌进度与兜底入口（只有一张时不需要） -->
  <div v-if="showBar && items.length > 1" class="stack-bar">
    <button type="button" class="stack-nav" :disabled="index <= 0" aria-label="上一张" @click="step(-1)">
      <el-icon><ArrowLeft /></el-icon>
    </button>
    <span class="stack-count">{{ index + 1 }} / {{ items.length }}</span>
    <button
      type="button"
      class="stack-nav"
      :disabled="index >= items.length - 1"
      aria-label="下一张"
      @click="step(1)"
    >
      <el-icon><ArrowRight /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    /** 牌堆数据；只用于切换，卡片长什么样由父级插槽决定 */
    items: any[]
    /** 已经是最后一条时，左滑露出的提示 */
    endHint?: string
    /** 已经是第一条时，右滑露出的提示 */
    startHint?: string
    /** 底部进度 / 翻牌条：与分页器共存时可关掉，避免两套导航 */
    showBar?: boolean
  }>(),
  {
    endHint: '已经是最后一条了',
    startHint: '已经是第一条了',
    showBar: true,
  },
)

const SWIPE_THRESHOLD = 50 // 触发翻牌的横向位移阈值
const AXIS_LOCK = 6 // 至少移动这么多才判定手势方向，避免抖动误判
const FLY_MS = 220 // 飞出动画时长，与 .stack-top 的 transition 对齐

const index = ref(0)
const dragX = ref(0)
const dragging = ref(false)
const flying = ref(false)
let startX = 0
let startY = 0
let axis: '' | 'x' | 'y' = ''
let touchId: number | null = null
let flyTimer: number | null = null
let flyTarget = 0

const topItem = computed(() => props.items[index.value] ?? null)
const nextItem = computed(() => props.items[index.value + 1] ?? null)
const prevItem = computed(() => props.items[index.value - 1] ?? null)

/** 往哪边拖：负=往左（看下一条），正=往右（看上一条）。决定露天的是哪一层 */
const dragSign = computed(() => (dragX.value < 0 ? -1 : 1))

const topStyle = computed(() => {
  const x = dragX.value
  // 跟手时轻微倾斜：滑得越远倾角越大，上限 10°
  const rotate = Math.max(-10, Math.min(10, x / 24))
  return { transform: `translate3d(${x}px, 0, 0) rotate(${rotate}deg)` }
})

/** 取当前手势那根手指的坐标：多指时按 identifier 认人，避免 touches[0] 串味 */
function pointOf(e: TouchEvent, fromChanged = false): { x: number; y: number } | null {
  const arr = Array.from((fromChanged ? e.changedTouches : e.touches) || [])
  if (!arr.length) return null
  const t = arr.find((p) => p.identifier === touchId) ?? arr[0]
  return { x: t.clientX, y: t.clientY }
}

/** 上一张还在飞出时被新手势打断：直接落位到目标索引，绝不吞掉这次手势 */
function settleFly() {
  if (flyTimer !== null) {
    window.clearTimeout(flyTimer)
    flyTimer = null
  }
  if (!flying.value) return
  index.value = Math.min(flyTarget, Math.max(0, props.items.length - 1))
  dragX.value = 0
  flying.value = false
}

function onTouchStart(e: TouchEvent) {
  settleFly()
  const t = e.touches[0]
  if (!t) return
  touchId = t.identifier
  startX = t.clientX
  startY = t.clientY
  axis = ''
  dragging.value = true
}

function onTouchMove(e: TouchEvent) {
  if (!dragging.value) return
  const p = pointOf(e)
  if (!p) return
  const dx = p.x - startX
  const dy = p.y - startY
  // 先判方向：横向位移占优才认作翻牌，否则交给页面纵向滚动
  if (!axis) {
    if (Math.abs(dx) < AXIS_LOCK && Math.abs(dy) < AXIS_LOCK) return
    axis = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y'
  }
  if (axis !== 'x') return
  dragX.value = dx
}

function onTouchEnd(e: TouchEvent) {
  if (!dragging.value) return
  dragging.value = false

  // 快甩时可能一个 touchmove 都没派发，用 touchend 的落点补齐位移
  const p = pointOf(e, true)
  if (p) {
    const dx = p.x - startX
    const dy = p.y - startY
    if (!axis && (Math.abs(dx) >= AXIS_LOCK || Math.abs(dy) >= AXIS_LOCK)) {
      axis = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y'
    }
    if (axis === 'x') dragX.value = dx
  }
  if (axis !== 'x') {
    dragX.value = 0
    return
  }

  const dx = dragX.value
  if (dx <= -SWIPE_THRESHOLD) fly(1)
  else if (dx >= SWIPE_THRESHOLD) fly(-1)
  else dragX.value = 0 // 没过阈值：回弹
}

/** 顶牌按滑动方向飞出，落位后再换牌——新牌与叠层里已露出的那张位置一致，
    所以交接时画面没有跳动 */
function fly(dir: 1 | -1) {
  const next = index.value + dir
  if (next < 0 || next >= props.items.length) {
    dragX.value = 0 // 已经是头 / 尾，滑不动，回弹
    return
  }
  flying.value = true
  flyTarget = next
  dragX.value = dir > 0 ? -window.innerWidth : window.innerWidth
  flyTimer = window.setTimeout(() => {
    flyTimer = null
    index.value = Math.min(flyTarget, Math.max(0, props.items.length - 1))
    dragX.value = 0
    flying.value = false
  }, FLY_MS)
}

/** 底部按钮：下一张复用飞出动画（正好露出叠层里那张，画面连贯）；
    上一张不涉及叠层，直接回退即可 */
function step(dir: 1 | -1) {
  settleFly()
  if (dir > 0) {
    fly(1)
    return
  }
  index.value = Math.max(index.value - 1, 0)
}

// 列表被审批动作改变（少了一条）时收敛索引，避免停在空牌上
watch(
  () => props.items.length,
  (len) => {
    if (index.value > len - 1) index.value = Math.max(0, len - 1)
  },
)
</script>

<style scoped>
/* ========== 叠层本体 ========== */
.stack {
  position: relative;
  /* 横向手势交给手指拖牌，纵向仍可正常滚动 */
  touch-action: pan-y;
}

/* 叠层左右各一层：与顶牌同尺寸、同位置，静止时被顶牌完全盖住，
   只有把顶牌往对应方向拖开时才露出来——所以不做出边、不加偏移 */
.stack-peek {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  overflow: hidden;
  border-radius: var(--tui-radius);
  pointer-events: none;
}
/* 拖动方向对应的那一层压在上面，露出的才是该露的那张 */
.stack-peek.is-front {
  z-index: 2;
}

/* 到头的那一侧：这一层自己画壳的提示卡（同样只在拖动时露出） */
.stack-peek.is-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  text-align: center;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  box-shadow: var(--tui-shadow-1);
}
.stack-peek-hint {
  font-size: 12px;
  color: var(--tui-text-quiet);
}

/* 顶牌：只做跟手位移，永远压在两层叠层之上 */
.stack-top {
  position: relative;
  z-index: 3;
  will-change: transform;
  transition: transform 0.22s var(--tui-ease);
}
.stack-top.is-dragging {
  transition: none;
}

/* ========== 进度 / 翻牌条 ========== */
.stack-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 12px;
}
.stack-nav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--tui-border);
  border-radius: 50%;
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.15s var(--tui-ease), color 0.15s var(--tui-ease);
}
.stack-nav:not(:disabled):active {
  border-color: var(--tui-brand);
  color: var(--tui-brand);
}
.stack-nav:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.stack-count {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text-quiet);
}
</style>