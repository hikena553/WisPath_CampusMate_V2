<template>
  <Teleport to="body" :disabled="!teleport">
    <!-- 覆盖式子页的标准外壳：动画名固定 subpage（见 styles/subpage-transition.css），
         时长 320 = CSS 0.3s + 20ms 余量，兜底把离场元素从 DOM 里摘掉，
         避免它滞留在文档流里影响后续布局。 -->
    <Transition
      name="subpage"
      :duration="duration"
      @after-enter="emit('after-enter')"
      @after-leave="handleAfterLeave"
    >
      <div
        v-if="modelValue"
        ref="rootEl"
        v-bind="passthroughAttrs"
        :class="rootClass"
        :style="rootStyle"
        :role="role ?? undefined"
        :aria-modal="role === 'dialog' ? 'true' : undefined"
        :aria-label="ariaLabel || undefined"
      >
        <!-- 插槽透出 close：子页顶栏的返回按钮直接 @click="close" 即可 -->
        <slot :close="close" />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * SubPageShell - 移动端「覆盖式子页」外壳（校园资讯详情 / 搜索 / 结果页在用）
 *
 * 把子页里每次都重复、又每次都能写错的那几行收成一个组件：
 *   ① Teleport 到 body（不受父级 transform / overflow / stacking context 影响）
 *   ② Transition name="subpage" + duration 320（动画本体在 styles/subpage-transition.css）
 *   ③ 整屏骨架 .subpage-root（fixed inset:0 / flex column / 不透明 / 裁切溢出）
 *   ④ Esc 关闭
 *   ⑤ 打开时锁 body 滚动、退场播完再解锁（引用计数，多层叠放不会互相拆锁）
 *   ⑥ 退场动画播完才 emit('after-leave')，父页此时才卸载子树，动画不会被掐断
 *
 * 用法（带参数的 open 用 composable 管状态，见 useSubPageTransition）：
 *   <SubPageShell v-model="visible" aria-label="资讯详情" @after-leave="emit('closed')">
 *     <div class="adp-root">            ← 页面自己的内容列
 *       <header class="adp-head"> … </header>
 *       <div class="adp-scroll"> … </div>
 *     </div>
 *   </SubPageShell>
 *
 * ⚠️ 页面样式要写在**插槽里的这个元素**上，不要试图写外壳根节点：
 *    根节点由本组件模板渲染，父组件的 `<style scoped>` 命中不了它
 *    （Vue 的 scopeId 只继承「组件根节点」，这里根节点是 Teleport/Transition，继承会断）。
 *    把 `class="adp-root"` 传给 <SubPageShell> 只能拿到全局样式，拿不到 scoped 样式。
 *    插槽里的元素带 flex:1 即可填满外壳的纵向布局。
 *
 * 只触发动画、不承载整屏语义的层（例如搜索结果页盖在搜索页之上）用 teleport=false：
 * 此时不加 .subpage-root 骨架，几何由页面自己的类（如 .csp-result-page 的 absolute inset:0）决定。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useAttrs, watch } from 'vue'
import type { CSSProperties, StyleValue } from 'vue'
import { lockBodyScroll } from '@/utils/bodyScrollLock'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    /** 显隐：v-model 绑定。false 后开始播退场动画，:duration 到点才真正移除 */
    modelValue: boolean
    /** 是否 Teleport 到 body。false = 留在父级文档流里（叠在子页之上的内层） */
    teleport?: boolean
    /** Vue Transition 的 duration（毫秒），默认 320 = 0.3s 动画 + 20ms 余量 */
    duration?: number
    /** 层级，默认 2600（高于底部导航 1000 / 顶栏 100） */
    zIndex?: number
    /** 语义角色。整屏子页用默认的 dialog；内层分区传 'region' 或 null */
    role?: string | null
    /** 无障碍名称，如「资讯详情：xxx」 */
    ariaLabel?: string
    /** 是否锁 body 滚动，默认 true。内层（父层已锁）可传 false */
    lockScroll?: boolean
    /** Esc 是否关闭自己，默认 true。页面自己有优先级更高的 Esc 逻辑时传 false，改用 @esc */
    closeOnEsc?: boolean
  }>(),
  {
    teleport: true,
    duration: 320,
    zIndex: 2600,
    role: 'dialog',
    ariaLabel: '',
    lockScroll: true,
    closeOnEsc: true,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  /** 进场动画播完 */
  'after-enter': []
  /** 退场动画播完、元素即将移除；父页应在这里卸载本子页 */
  'after-leave': []
  /** 收到 Esc（无论是否自动关闭）。给「Esc 有分级语义」的页面用 */
  esc: []
}>()

const rootEl = ref<HTMLElement | null>(null)
const attrs = useAttrs()

/** class 透传给页面自己的类（只有全局样式生效，scoped 样式请写在插槽元素上）；
    骨架类只在整屏（teleport）模式下加 */
const rootClass = computed(() => [
  attrs.class,
  { 'subpage-root': props.teleport },
])

/** style 与页面传进来的 style（如 --kb-offset 键盘偏移变量）合并，zIndex 由本组件统一给。
    用 style 数组而不是对象展开：样式可能是对象、数组或字符串，展开会把后两者弄坏。 */
const rootStyle = computed<StyleValue>(() => {
  const own: CSSProperties = { zIndex: props.zIndex }
  const incoming = attrs.style as StyleValue | undefined
  return incoming ? [incoming, own] : own
})

/** 除 class/style 外的其余属性（id、data-*、aria-* 等）原样落到根元素 */
const passthroughAttrs = computed(() => {
  const rest: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class' || key === 'style') continue
    rest[key] = value
  }
  return rest
})

/* ==================== 滚动锁 ====================
   打开时加锁（等一帧，元素已在文档里），退场动画播完才解锁 ——
   提前解锁会让下层页面在子页还在滑出时就能被滑动。
   用引用计数版：搜索子页 + 详情子页同时开着时，详情关闭不会把搜索的锁一起拆掉。 */
let releaseScrollLock: (() => void) | null = null

function applyScrollLock() {
  if (!props.lockScroll || !props.modelValue) return
  if (!releaseScrollLock) releaseScrollLock = lockBodyScroll()
}

function releaseLock() {
  releaseScrollLock?.()
  releaseScrollLock = null
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return // 关闭方向等 after-leave，动画期间保持锁定
    await nextTick()
    applyScrollLock()
  },
  { immediate: true },
)

// 运行中改 lockScroll（少见，但别留一个悬空的锁）
watch(
  () => props.lockScroll,
  (on) => {
    if (on) applyScrollLock()
    else releaseLock()
  },
)

/* ==================== Esc ==================== */

function close() {
  if (!props.modelValue) return
  emit('update:modelValue', false)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape' || !props.modelValue) return
  emit('esc')
  if (props.closeOnEsc) close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))

/* ==================== 收尾 ==================== */

function handleAfterLeave() {
  releaseLock()
  emit('after-leave')
}

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  releaseLock()
})

defineExpose({ close, rootEl })
</script>
