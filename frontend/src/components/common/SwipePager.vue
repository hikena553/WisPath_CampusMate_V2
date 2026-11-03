<template>
  <!-- 裁切层：overflow:hidden 必须挂在「不参与位移」的这一层上。
       挂在会 translate 的轨道上时，裁切框会跟着轨道一起移走 ——
       轨道平移到 ±一页宽时，可视区正好落在裁切框之外，整页变成空白。 -->
  <div
    class="sw-pager-viewport"
    :class="{ 'is-dragging': dragging, 'is-animating': animating }"
    :style="{ '--sw-duration': `${duration}ms` }"
  >
    <div
      ref="trackEl"
      class="sw-pager"
      :class="{
        'is-dragging': dragging,
        'is-resetting': resetting,
        'is-jumping': jumping,
        'is-open': open,
        'is-animating': animating,
      }"
      :style="{ transform }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
      @click.capture="onClickCapture"
      @dragstart.prevent
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * SwipePager —— 横向分页轨道（左右滑动切页）
 *
 * 从「校园资讯」的分类分页原样抽出，行为口径与那边完全一致：
 *   · 手指拖动时整条轨道 1:1 跟手，邻居页从屏幕边缘同步进来，
 *     不是松手后才补动画；
 *   · 松手按「位移 / 甩动速度」判定：吸附到相邻页，或回弹归位；
 *   · 吸附完成后才切换当前页：轨道瞬时归零、卸载邻居页 ——
 *     当前页始终是轨道里同一个 DOM 节点（:key 由调用方给），换页不重建、不闪；
 *   · 邻居页只在拖动开始时渲染，静止时只有当前页（页面高度不被邻居撑高）；
 *   · 首 / 尾页没有对应方向的邻居：该方向直接不接手势，卡片一动不动 ——
 *     不做阻尼回弹，避免在边缘拉出一条白色空档；
 *   · 纵向为主的滑动会被让回给页面滚动（threshold 内先定方向）。
 *
 * 用法（v-for 由调用方渲染，这样调用方可以继续用 v-memo 冻住页面子树，
 * 拖动时每帧只重算位移，不重排整页 DOM）：
 *
 *   <SwipePager ref="pagerRef" :model-value="activeKey" :pages="keys"
 *               start-selector=".feed" @update:model-value="onChange">
 *     <div v-for="k in pages" :key="k" class="sw-pager-page">…</div>
 *   </SwipePager>
 *
 * 调用方负责：① 每个页根元素带 `sw-pager-page` 类（轨道据此排成等宽行）；
 * ② 把 `renderedPages` 映射成要渲染的页（含邻居）；③ 当前页数据的取用。
 *
 * 页外观通过 CSS 变量覆盖：`--sw-page-bg` / `--sw-page-radius`（页面自身样式由调用方给）、
 * `--sw-track-bg`（拖动时轨道底色，用于邻居页偏矮时补白）。
 */
interface Props {
  /** 当前页 key */
  modelValue: string
  /** 全部页 key（有序）：组件据此判断左右邻居与首尾边界 */
  pages: readonly string[]
  /** 只有从匹配这个选择器的元素上起手才接管手势；不传 = 整条轨道都可拖 */
  startSelector?: string
  /** 落在匹配这些选择器的元素上不接管（默认按钮，点按优先） */
  ignoreSelector?: string
  /** 进入拖动态的最小水平位移（px）：低于它算点击 */
  dragThreshold?: number
  /** 松手判定翻页的最小位移（px） */
  swipeThreshold?: number
  /** 速度阈值（px/ms）：快甩时即使位移不够也翻页 */
  flingVelocity?: number
  /** 吸附 / 回弹 / 换页时长（ms），与 CSS 里的 transform 过渡一致 */
  duration?: number
}

const props = withDefaults(defineProps<Props>(), {
  startSelector: '',
  ignoreSelector: 'button',
  dragThreshold: 12,
  swipeThreshold: 56,
  flingVelocity: 0.35,
  duration: 200,
})

const emit = defineEmits<{
  /** 用户切到另一页（拖动吸附完成、或点 Tab 触发 slideTo 的那一刻） */
  (e: 'update:modelValue', key: string): void
  /** 切页动画收尾：key = 新页，dir = 1 向前 / -1 向后 */
  (e: 'change', key: string, dir: 1 | -1): void
}>()

const trackEl = ref<HTMLElement | null>(null)

/** 一页的宽度（px）：页宽 = 容器宽度，吸附位移与边界判断都按它算 */
const width = ref(0)
/** 轨道相对「当前页居中」的位移（px，向左为负） */
const x = ref(0)
/** 是否渲染左右邻居页（拖动开始 → 吸附完成） */
const open = ref(false)
/** 轨道正在跟手（关过渡） */
const dragging = ref(false)
/** 换页后瞬时归位（关过渡）：切数据与轨道归零必须在同一帧完成 */
const resetting = ref(false)
/** 吸附 / 回弹 / 换页动画进行中：不接新手势 */
const animating = ref(false)
/** 轨道瞬时落到「出发页」位（关过渡）：只作用于轨道，不影响外部 Tab 滑条的过渡 */
const jumping = ref(false)

/**
 * 点 Tab 换页（不是拖动，但同样要「出发页滑出、目标页滑入」）。
 * 有它时轨道只摆两页（顺序按页先后），外部滑条 / 染色不再跟位移走 ——
 * 点击后当前页已经直接落到目标位，这两者交给各自的过渡。
 */
interface PageSlide {
  from: string
  to: string
  dir: 1 | -1
}
const slide = ref<PageSlide | null>(null)

/** 内部当前页：props.modelValue 的即时副本，吸附 / 换页那一帧就更新，不等父级回灌 */
const currentKey = ref(props.modelValue)

watch(
  () => props.modelValue,
  (v) => {
    if (v === currentKey.value) return
    // 外部直接换页（深链、底部导航回填）：不播动画，瞬时归位
    currentKey.value = v
    if (!slide.value) {
      closeImmediately()
    }
  },
)

/**
 * 轨道上要渲染的页（交给调用方 v-for）：
 *   拖动 / 吸附中 = [上一页?, 当前页, 下一页?]；静止 = [当前页]；
 *   点 Tab 换页 = 只摆「出发页 + 目标页」，两页一次对滑 —— 跨多页也只走一次时长。
 */
const renderedPages = computed<string[]>(() => {
  const s = slide.value
  if (s) return s.dir > 0 ? [s.from, s.to] : [s.to, s.from]
  const list = props.pages
  const i = list.indexOf(currentKey.value)
  if (i < 0) return [currentKey.value]
  const keys: string[] = []
  if (open.value && i > 0) keys.push(list[i - 1])
  keys.push(list[i])
  if (open.value && i < list.length - 1) keys.push(list[i + 1])
  return keys
})

/** 当前页在渲染数组里的下标：0 = 最左，1 = 中间，2 = 最右 */
const anchor = computed(() => Math.max(0, renderedPages.value.indexOf(slide.value ? slide.value.to : currentKey.value)))

/**
 * 轨道位移 = 「把当前页挪到中点」的基准偏移 + 手指位移。
 * 收尾换页时 currentKey 变化会改变基准偏移，同时位移归零 —— 两者在同一次渲染里
 * 相互抵消，画面上当前页仍停在原处，所以看不到跳动。
 */
const transform = computed(() => `translate3d(${-anchor.value * width.value + x.value}px, 0, 0)`)

/** 跟手进度（0~1）：拖动时 = |位移| / 页宽，供外部滑条 / 染色与手指同步 */
const progress = computed<number | null>(() => {
  if (slide.value || !width.value) return null
  return Math.min(1, Math.abs(x.value) / width.value)
})

/** 拖动方向：1 = 去下一页，-1 = 去上一页，0 = 未动 */
const direction = computed<1 | -1 | 0>(() => (x.value < 0 ? 1 : x.value > 0 ? -1 : 0))

/** 点 Tab 换页动画进行中（外部据此关掉「逐字扫过」一类延迟过渡） */
const sliding = computed(() => !!slide.value)

defineExpose({ renderedPages, dragging, resetting, sliding, animating, open, progress, direction, slideTo, cancel })

/* ==================== 位移提交 ==================== */

function measure() {
  if (trackEl.value) width.value = trackEl.value.clientWidth
}

function pageWidth() {
  return width.value || trackEl.value?.clientWidth || window.innerWidth || 320
}

/** 跟手位移按帧提交：同一帧内多次 pointermove 只触发一次渲染 */
let rafId = 0
let pendingX = 0

function queueX(v: number) {
  pendingX = v
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = 0
    x.value = pendingX
  })
}

/** 吸附 / 回弹要直接写目标值：先丢掉还排队的跟手帧，避免它把动画目标覆盖回去 */
function cancelQueuedX() {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = 0
  }
  pendingX = 0
}

let timer: number | undefined

function clearTimer() {
  window.clearTimeout(timer)
  timer = undefined
}

/* ==================== 手势 ==================== */

interface DragState {
  pointerId: number
  startX: number
  startY: number
  lastX: number
  lastTime: number
  /** 已越过阈值、进入拖动 */
  active: boolean
  /** 已判定为纵向滚动，本次手势彻底放弃 */
  locked: boolean
}

let drag: DragState | null = null
/** 上一次手势是滑动（而非轻点）：随后紧跟着的 click 要吞掉，否则一滑完就点进了行内容 */
let suppressClick = false

function onPointerDown(e: PointerEvent) {
  // 每次按下先复位：避免上一次滑动没产生 click 时，把下一次正常点击吞掉
  suppressClick = false
  cancelQueuedX()
  if (animating.value) return
  // 只处理主键 / 单指；右键与双指不接管
  if (e.pointerType === 'mouse' && e.button !== 0) return
  if (!e.isPrimary) return
  const target = e.target as HTMLElement | null
  if (!target) return
  // 只从指定区域起手（例如信息流本体，让内部的轮播 / 地图有自己的拖动）
  if (props.startSelector && !target.closest(props.startSelector)) return
  if (props.ignoreSelector && target.closest(props.ignoreSelector)) return
  measure()
  drag = {
    pointerId: e.pointerId,
    startX: e.clientX,
    startY: e.clientY,
    lastX: e.clientX,
    lastTime: Date.now(),
    active: false,
    locked: false,
  }
}

function onPointerMove(e: PointerEvent) {
  const d = drag
  if (!d || d.pointerId !== e.pointerId || d.locked) return
  const dx = e.clientX - d.startX
  const dy = e.clientY - d.startY
  const index = props.pages.indexOf(currentKey.value)
  // 这个方向有没有邻居页：往右拖要有上一页，往左拖要有下一页
  const hasTarget = dx < 0 ? index < props.pages.length - 1 : index > 0

  // 未越过阈值：先定方向。纵向为主 → 交还页面滚动，本次手势放弃
  if (!d.active) {
    if (Math.abs(dy) > props.dragThreshold && Math.abs(dy) > Math.abs(dx)) {
      d.locked = true
      return
    }
    if (Math.abs(dx) <= props.dragThreshold) return
    // 已在首页 / 末页：该方向没有邻居页，不接管手势 —— 轨道固定不动，
    // 既不露白也不回弹；手指抬起后仍是普通点击
    if (!hasTarget) return
    d.active = true
    // 邻居页与位移同一次渲染上屏：从第一帧起三页就在轨道上
    open.value = true
    dragging.value = true
    // 捕获指针：手指滑出区域也不丢 up 事件
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  }

  d.lastX = e.clientX
  d.lastTime = Date.now()
  // 1:1 跟手；起步后把方向反向拉过起点（该方向没有邻居）时硬停在 0，同样不露白
  queueX(hasTarget ? dx : 0)
}

function onPointerUp(e: PointerEvent) {
  const d = drag
  drag = null
  if (!d || d.pointerId !== e.pointerId) return
  // 松手后由吸附 / 回弹直接写目标值，丢掉还没落地的跟手帧
  cancelQueuedX()

  // 没进入拖动（轻点）或已判定为纵向滚动：直接归位，click 照常交给页面内容
  if (!d.active || d.locked) {
    x.value = 0
    dragging.value = false
    return
  }

  // 滑动过：吞掉随后那次 click
  suppressClick = true
  window.setTimeout(() => { suppressClick = false }, 350)

  const dx = e.clientX - d.startX
  const dt = Math.max(1, Date.now() - d.lastTime)
  const velocity = (e.clientX - d.lastX) / dt
  const wantNext = dx < 0 && (Math.abs(dx) > props.swipeThreshold || velocity < -props.flingVelocity)
  const wantPrev = dx > 0 && (Math.abs(dx) > props.swipeThreshold || velocity > props.flingVelocity)

  const index = props.pages.indexOf(currentKey.value)
  const targetIndex = wantNext ? index + 1 : wantPrev ? index - 1 : -1

  // 已到首页 / 末页，或位移不够：回弹
  if (targetIndex < 0 || targetIndex >= props.pages.length) {
    springBack()
    return
  }

  snap(wantNext ? 'next' : 'prev', props.pages[targetIndex])
}

function onPointerCancel() {
  // 被系统打断（来电、手势返回、双指缩放）：回弹，不翻页
  drag = null
  cancelQueuedX()
  if (!open.value) {
    x.value = 0
    dragging.value = false
    return
  }
  springBack()
}

/** 滑动结束后那一次 click 在此截停：不让它落到行内容或按钮上 */
function onClickCapture(e: MouseEvent) {
  if (!suppressClick) return
  suppressClick = false
  e.preventDefault()
  e.stopPropagation()
}

/* ==================== 吸附 / 回弹 ==================== */

/** 回弹：轨道滑回当前页，动画结束后收起邻居页（当前页仍在原位，卸载邻居不产生位移） */
function springBack() {
  cancelQueuedX()
  animating.value = true
  dragging.value = false
  x.value = 0
  clearTimer()
  timer = window.setTimeout(closeNeighbours, props.duration + 20)
}

/**
 * 吸附到相邻页：轨道滑到 ±页宽（此时邻居正好落在中位）。
 * 动画结束后在同一帧里做三件事：切当前页、轨道归零、卸载邻居 ——
 * 当前页始终是同一个 DOM 节点（:key 由调用方按页 key 给），画面不重建、不闪。
 */
function snap(dir: 'next' | 'prev', key: string) {
  const w = pageWidth()
  cancelQueuedX()
  animating.value = true
  dragging.value = false
  x.value = dir === 'next' ? -w : w
  clearTimer()
  timer = window.setTimeout(() => {
    resetting.value = true
    currentKey.value = key
    emit('update:modelValue', key)
    open.value = false
    x.value = 0
    requestAnimationFrame(() => {
      // 强制结算归位后的这一帧，再恢复过渡，避免残留目标值再补一段动画
      void trackEl.value?.offsetWidth
      resetting.value = false
      animating.value = false
      emit('change', key, dir === 'next' ? 1 : -1)
    })
  }, props.duration + 20)
}

/** 收起邻居页：当前页仍在原位，卸载邻居不产生视觉位移 */
function closeNeighbours() {
  cancelQueuedX()
  resetting.value = true
  open.value = false
  x.value = 0
  requestAnimationFrame(() => {
    void trackEl.value?.offsetWidth
    resetting.value = false
    animating.value = false
  })
}

/** 外部直接换页：瞬时归位，不播动画 */
function closeImmediately() {
  clearTimer()
  cancelQueuedX()
  drag = null
  slide.value = null
  animating.value = false
  dragging.value = false
  jumping.value = true
  resetting.value = true
  open.value = false
  x.value = 0
  requestAnimationFrame(() => {
    void trackEl.value?.offsetWidth
    jumping.value = false
    resetting.value = false
  })
}

/* ==================== 点 Tab 换页 ==================== */

/**
 * 换到指定页，并把「出发页 → 目标页」这一趟滑动作出来（点 Tab 时调用）。
 *   ① 同一帧里把轨道瞬时摆到「出发页」（关过渡，只关轨道，外部滑条照常走过渡）；
 *   ② 强制结算这一帧后放开过渡、把位移推到 0 —— 出发页滑出、目标页滑入；
 *   ③ 时长 + 30ms 后卸载出发页、轨道瞬时归零（与吸附换页同一套归位做法）。
 * 当前页在①就落到目标位（emit update:modelValue），所以外部 Tab 的高亮 / 滑条
 * 全程是目标态，不会等到动画结束才追上来。
 */
function slideTo(key: string) {
  const from = currentKey.value
  if (!props.pages.includes(key)) return
  if (key === from && !slide.value && !open.value) {
    cancel()
    return
  }
  const fromIndex = props.pages.indexOf(from)
  const toIndex = props.pages.indexOf(key)
  if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return

  // 收掉拖动 / 吸附残留（不走 cancel 的 rAF：起手帧要自己控制）
  clearTimer()
  cancelQueuedX()
  drag = null
  dragging.value = false
  open.value = false

  measure()
  const w = pageWidth()
  const dir: 1 | -1 = toIndex > fromIndex ? 1 : -1

  jumping.value = true
  animating.value = true
  slide.value = { from, to: key, dir }
  currentKey.value = key
  x.value = dir > 0 ? w : -w
  emit('update:modelValue', key)

  requestAnimationFrame(() => {
    // 先让「关过渡 + 起点位移」结算成上一帧样式，再放开过渡推向终点
    void trackEl.value?.offsetWidth
    jumping.value = false
    x.value = 0
    clearTimer()
    timer = window.setTimeout(finishSlide, props.duration + 30)
  })
}

/** 点 Tab 换页收尾：卸载出发页、轨道瞬时归零（当前页是同一个 DOM 节点，画面不跳） */
function finishSlide() {
  const key = currentKey.value
  const dir: 1 | -1 = slide.value?.dir ?? 1
  jumping.value = true
  slide.value = null
  x.value = 0
  requestAnimationFrame(() => {
    void trackEl.value?.offsetWidth
    jumping.value = false
    animating.value = false
    // 复用 change 事件：外部若有「换页完成」的收尾动作，两条路径共用一处
    emit('change', key, dir)
  })
}

/** 中止轨道上的一切位移 / 定时器：瞬时归位、收起邻居，不再接后续动作 */
function cancel() {
  closeImmediately()
}

/* ==================== 生命周期 ==================== */

function onResize() {
  if (dragging.value) return
  measure()
}

onMounted(() => {
  measure()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  clearTimer()
  cancelQueuedX()
})
</script>

<style scoped>
/* 裁切层：不参与位移，只负责把轨道多余的部分裁掉（邻居页不会溢到页面边距里） */
.sw-pager-viewport {
  position: relative;
  width: 100%;
  flex-shrink: 0;
  overflow: hidden;
}

/* 轨道：页与页首尾相接排成一行，位移由内联 transform 驱动。
   过渡只管「吸附 / 回弹 / 换页」，跟手与瞬时归位时由状态类关掉。 */
.sw-pager {
  display: flex;
  width: 100%;
  flex-shrink: 0;
  transition: transform var(--sw-duration, 200ms) cubic-bezier(.22, .61, .36, 1);
  touch-action: pan-y; /* 横向手势交给 Pointer 逻辑，纵向仍归页面滚动 */
  -webkit-user-select: none;
  user-select: none;
}

.sw-pager.is-dragging,
.sw-pager.is-resetting,
.sw-pager.is-jumping {
  transition: none;
}

.sw-pager.is-dragging {
  will-change: transform;
}

/* 吸附 / 回弹动画进行中不响应点按：避免落在还没停稳的邻居页上误开内容 */
.sw-pager.is-animating {
  pointer-events: none;
}

/* 拖动 / 吸附过程中整条轨道垫底：边界回弹时露出的边缘也是这张底，
   不会闪出一条页面底色；收起邻居页后撤掉（当前页自带底色）。 */
.sw-pager.is-open {
  background: var(--sw-track-bg, transparent);
}

/* 一页 = 一个满宽单元。实际外观（底色、圆角）由调用方给。 */
.sw-pager :deep(.sw-pager-page) {
  flex: 0 0 100%;
  width: 100%;
}
</style>
