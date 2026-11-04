<template>
  <!--
    滑动下划线标签栏（全站唯一实现）
    ------------------------------------------------------------------
    从「校园资讯」移动端分类 Tab 里抽出来的那套动画，原样复用：

    1. 下划线不画在选中项的 ::after 上（那样只能整块闪一下），而是一条独立滑条，
       位置 / 宽度按「当前项 → 目标项」的进度插值；拖动时由父级逐帧喂 progress，
       点按 / 吸附时交给 CSS 过渡走完。
    2. 文字「随条染色」：每个标签里叠两层同款文字，底层永远是静色，上层是强调色并用
       clip-path 只留滑条覆盖的那一段 —— 条走到相邻两项中间时，左边那段字是深色、
       右边那段字是灰色，分界线与滑条严格重合。两层字必须同字体同字重同宽度，
       所以本组件的选中态只允许改颜色，不允许改字重（改了宽度，裁剪就会错位）。

    外观全部走 CSS 变量，默认值就是校园资讯那一版，其它页面按需覆盖即可：
      --st-font            字号（默认 15px）
      --st-gap             标签间距（默认 16px）
      --st-pad             整行内边距（默认 8px 16px 10px）
      --st-height          整行高度（默认由内容撑开）
      --st-justify         主轴对齐（默认 flex-start；居中传 center）
      --st-bg              背景（默认 #fff）
      --st-shadow          底部分隔（默认 0 1px 0 #f0f1f3）
      --st-tab-pad-b       标签底部留白（默认 8px，给下划线让位；行高固定时传 0）
      --st-indicator-bottom 滑条距行底部距离（默认 10px）
      --st-indicator-w     下划线宽度策略由内容决定，不需要配
  -->
  <nav
    ref="navEl"
    class="st-tabs"
    :class="{
      'is-sticky': !!stickyTop,
      'is-dragging': dragging,
      'is-resetting': resetting,
      'is-instant': instantSweep,
      'is-initial': !animate,
    }"
    :style="stickyTop ? { top: stickyTop } : undefined"
    role="tablist"
  >
    <button
      v-for="t in tabs"
      :key="t.key"
      :ref="(el) => setTabRef(t.key, el)"
      type="button"
      role="tab"
      class="st-tab"
      :aria-selected="modelValue === t.key"
      @click="onSelect(t.key)"
    >
      <span class="st-tab-label">{{ t.label }}</span>
      <!-- 同一段文字的强调色副本：叠在同一个文字框里，只渲染滑条所占的那一段。
           放在按钮内部是为了复用同一个文字框，两层字的字体 / 宽度必然一致，
           不会像「另起一行复制」那样差几个像素而重影。 -->
      <span
        class="st-tab-label st-tab-label-dark"
        :style="darkClip[t.key]"
        aria-hidden="true"
      >{{ t.label }}</span>
    </button>
    <span class="st-tab-indicator" :style="indicatorStyle" aria-hidden="true" />
  </nav>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

export interface SlidingTabItem {
  key: string
  label: string
}

const props = withDefaults(
  defineProps<{
    tabs: SlidingTabItem[]
    /** 当前选中项（受控，组件自己不切） */
    modelValue: string
    /** 拖动进度 0~1：父级横向翻页时逐帧传入；null 表示不做插值 */
    progress?: number | null
    /** 拖动方向：1 = 滑向下一项，-1 = 滑向上一项，0 = 无位移 */
    direction?: 1 | -1 | 0
    /** 拖动中：颜色 / 裁剪 / 滑条全部关掉过渡（逐帧写入，走过渡会滞后） */
    dragging?: boolean
    /** 归零复位中：裁剪与滑条关过渡，避免倒着补一段动画 */
    resetting?: boolean
    /** 点按换页期间：文字不走「扫过」过渡，随滑条直接落位到目标态 */
    instantSweep?: boolean
    /** 吸顶时距顶部的位置（如 '56px'）；不传则不吸顶 */
    stickyTop?: string
  }>(),
  {
    progress: null,
    direction: 0,
    dragging: false,
    resetting: false,
    instantSweep: false,
    stickyTop: '',
  },
)

const emit = defineEmits<{
  /** 点了某一项（组件不改状态，由父级决定切还是不切） */
  (e: 'select', key: string): void
}>()

function onSelect(key: string) {
  emit('select', key)
}

/**
 * 首帧不做过渡
 * ------------------------------------------------------------------
 * 组件刚挂载时 metrics 还是空的：滑条渲染成 0 宽、选中项的强调色文字整块被裁掉；
 * 紧接着的 nextTick / 字体 ready 测量才把它们推到正确位置。这段如果走 CSS 过渡，
 * 从别的页面切过来时就会看到「下划线从左边滑过来 + 选中文字从左往右被刷出来」——
 * 单看是个不错的入场动画，但页面本身已经在做转场，这一层是重影，纯干扰。
 *
 * 所以默认把过渡关掉（is-initial），等用户真正操作（换项 / 开始拖动）再打开。
 * 用「用户操作」而不是「计时器」当开关：字体异步加载完成后的补测、容器宽度变化、
 * 父级翻页位移在挂载瞬间的抖动，都不该抢跑动画，而它们发生的时机并不可控。
 * 注意 progress / direction 变化不能当成「用户在操作」—— 父级量完分页宽度的第一帧
 * 就会改一次 progress，那一下会把开关提前打开，紧接着的字体补测就又会滑一次。
 */
const animate = ref(false)
watch(
  () => props.modelValue,
  () => { animate.value = true },
)
watch(
  () => props.dragging,
  (v) => { if (v) animate.value = true },
)

/* ---------------- 测量 ----------------
   位置用按钮的 offsetLeft / offsetWidth 量（行本身可横向滚动，滑条要跟着一起滚）。
   nav 是 sticky 定位元素，天然就是 offsetParent，offsetLeft 即相对本行的 padding box。 */
const navEl = ref<HTMLElement | null>(null)
const tabEls = new Map<string, HTMLElement>()
const metrics = ref<{ left: number; width: number }[]>([])

function setTabRef(key: string, el: unknown) {
  if (el instanceof HTMLElement) tabEls.set(key, el)
  else tabEls.delete(key)
}

function measure() {
  metrics.value = props.tabs.map((t) => {
    const el = tabEls.get(t.key)
    return el ? { left: el.offsetLeft, width: el.offsetWidth } : { left: 0, width: 0 }
  })
}

/** 尺寸变化的来源有三处：字体异步加载完成换字宽、容器宽度变化、标签项本身增删改 */
let observer: ResizeObserver | null = null
function observeTargets() {
  const ro = observer
  if (!ro) return
  ro.disconnect()
  if (navEl.value) ro.observe(navEl.value)
  tabEls.forEach((el) => ro.observe(el))
}

/* ---------------- 滑条几何 ---------------- */
const bar = computed(() => {
  const index = props.tabs.findIndex((t) => t.key === props.modelValue)
  const cur = metrics.value[index]
  if (!cur) return null
  // progress 为 null 时不做插值：点按换页的位移只是为了推动页面轨道，
  // 滑条已经直接落到目标位、交给 CSS 过渡，不能再按位移比例插值，
  // 否则跨项点一下会先滑到隔壁再折回。
  const progress = props.progress == null ? 0 : Math.min(1, Math.max(0, props.progress))
  const next = props.direction ? metrics.value[index + props.direction] : undefined
  return {
    left: next ? cur.left + (next.left - cur.left) * progress : cur.left,
    width: next ? cur.width + (next.width - cur.width) * progress : cur.width,
  }
})

const indicatorStyle = computed(() => {
  const b = bar.value
  if (!b) return { transform: 'translate3d(0, 0, 0)', width: '0px', opacity: '0' }
  return {
    transform: `translate3d(${b.left}px, 0, 0)`,
    width: `${b.width}px`,
    opacity: '1',
  }
})

/**
 * 每一项的强调色文字裁多少：把滑条的左右边界换算到该项自己的文字框里。
 * 左右内缩只作用于这一格，所以「条到哪儿，深色字就渲染到哪儿」，
 * 不需要额外一层整行文字对齐，天然不会重影。
 *
 * 样式对象按项复用：拖动时通常只有「当前 / 目标」两格的 inset 在变，
 * 其余项拿到同一个对象引用，Vue 的 vnode diff 会直接跳过 style patch。
 * 每格只保留最近一次，缓存不会随拖动无限增长。
 */
const clipCache = new Map<string, { value: string; style: { clipPath: string } }>()
function clipStyle(key: string, clipPath: string) {
  const hit = clipCache.get(key)
  if (hit && hit.value === clipPath) return hit.style
  const style = { clipPath }
  clipCache.set(key, { value: clipPath, style })
  return style
}

const darkClip = computed(() => {
  const b = bar.value
  const clips: Record<string, { clipPath: string }> = {}
  props.tabs.forEach((t, i) => {
    const rect = metrics.value[i]
    if (!b || !rect || !rect.width) {
      clips[t.key] = clipStyle(t.key, 'inset(0 100% 0 0)')
      return
    }
    const left = Math.min(Math.max(b.left - rect.left, 0), rect.width)
    const right = Math.min(
      Math.max(rect.left + rect.width - (b.left + b.width), 0),
      rect.width - left,
    )
    clips[t.key] = clipStyle(t.key, `inset(0 ${right}px 0 ${left}px)`)
  })
  return clips
})

watch(
  () => props.tabs.map((t) => `${t.key}:${t.label}`).join('|'),
  () => {
    void nextTick(() => {
      measure()
      observeTargets()
    })
  },
)

onMounted(() => {
  observer = new ResizeObserver(() => measure())
  void nextTick(() => {
    measure()
    observeTargets()
  })
  // 字体是异步加载的：ready 之后再补量一次，否则首帧按回退字体的宽度定位
  void document.fonts?.ready.then(() => measure())
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  tabEls.clear()
  clipCache.clear()
})
</script>

<style scoped>
.st-tabs {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--st-gap, 16px);
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  justify-content: var(--st-justify, flex-start);
  height: var(--st-height, auto);
  margin: 0;
  padding: var(--st-pad, 8px 16px 10px);
  background: var(--st-bg, #ffffff);
  box-shadow: var(--st-shadow, 0 1px 0 #f0f1f3);
  border-bottom: 0;
  border-radius: 0;
  -webkit-tap-highlight-color: transparent;
}
.st-tabs::-webkit-scrollbar {
  display: none;
}
/* 吸顶：行本身是 sticky，位置随内容横向滚动，滑条跟着一起走 */
.st-tabs.is-sticky {
  position: sticky;
  z-index: var(--st-z, 25);
}

.st-tab {
  position: relative;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  padding: 0 0 var(--st-tab-pad-b, 8px);
  background: none;
  border: 0;
  font-size: var(--st-font, 15px);
  /* 按钮默认字体不继承页面：强调色文字层用的是同款 span，必须显式继承，
     两层文字的字体 / 字宽才会完全一致，裁剪边界才对得上 */
  font-family: inherit;
  font-weight: var(--st-font-weight, 400);
  color: var(--st-color, #86909c);
  cursor: pointer;
  transition: color 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}
/* 拖动中颜色是逐帧写入的，走过渡会滞后于滑条与页面 */
.st-tabs.is-dragging .st-tab {
  transition: none;
}

/* 标签文字：两层同宽文字叠在同一个内容框里。
   底层恒为静色；上层同款强调色，用 clip-path 只留滑条覆盖的那一段。 */
.st-tab-label {
  display: block;
  white-space: nowrap;
  text-align: left;
}
.st-tab-label-dark {
  position: absolute;
  /* 四边贴着按钮内容框：底部让开与按钮相同的留白，与真实文字框完全重合 */
  inset: 0 0 var(--st-tab-pad-b, 8px) 0;
  color: var(--st-color-active, #1d2129);
  pointer-events: none;
  transition: clip-path 200ms cubic-bezier(0.22, 0.61, 0.36, 1);
}
.st-tabs.is-dragging .st-tab-label-dark,
.st-tabs.is-resetting .st-tab-label-dark,
.st-tabs.is-instant .st-tab-label-dark {
  transition: none;
}

/* 选中下划线：独立滑条（不是 is-active::after），宽度随标签文字宽度变化。
   拖动时关过渡、跟手指在相邻项之间挪；点按 / 吸附时开过渡，与页面同一段缓动。 */
.st-tab-indicator {
  position: absolute;
  left: 0;
  bottom: var(--st-indicator-bottom, 10px);
  height: var(--st-indicator-h, 3px);
  width: 0;
  border-radius: var(--st-indicator-radius, 0);
  background: var(--st-color-active, #1d2129);
  pointer-events: none;
  will-change: transform, width;
  transition:
    transform 200ms cubic-bezier(0.22, 0.61, 0.36, 1),
    width 200ms cubic-bezier(0.22, 0.61, 0.36, 1);
}
.st-tabs.is-dragging .st-tab-indicator,
.st-tabs.is-resetting .st-tab-indicator {
  transition: none;
}

/* 首帧（还没被用户操作过）：滑条、文字裁剪、文字颜色全都不走过渡。
   挂载瞬间的测量跳变因此是「直接出现在正确位置」，而不是从 0 宽滑过去、
   或者选中文字被从左往右刷出来 —— 换页进入本页时不该有这一层入场动画。 */
.st-tabs.is-initial .st-tab,
.st-tabs.is-initial .st-tab-label-dark,
.st-tabs.is-initial .st-tab-indicator {
  transition: none;
}
</style>
