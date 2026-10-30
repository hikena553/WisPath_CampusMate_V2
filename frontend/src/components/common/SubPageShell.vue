<template>
  <!-- 覆盖式全屏子页外壳：落位 + 进出场动画 + Esc + body 滚动锁。
       动画本体在 styles/subpage-transition.css（全站唯一实现），这里不重复定义样式。
       滚动锁用引用计数：搜索页里再开详情页时，详情关闭不会把搜索页的锁一起抹掉，
       并且要等离场动画播完（after-leave）才解锁。 -->
  <Teleport to="body" :disabled="!teleport">
    <Transition name="subpage" :duration="320" @after-leave="handleAfterLeave">
      <div
        v-if="modelValue"
        ref="rootEl"
        v-bind="$attrs"
        class="subpage-root"
        :class="{ 'is-inline': !teleport }"
        :style="{ zIndex }"
        role="dialog"
        aria-modal="true"
        :aria-label="ariaLabel || undefined"
        tabindex="-1"
        @keydown="onKeydown"
      >
        <slot />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * 覆盖式子页外壳
 *
 * - v-model 控制显隐；关闭动画播完后触发 after-leave，父页可据此复位状态；
 * - closeOnEsc 默认开启。带分级 Esc 语义的页面（搜索/详情）传 false，
 *   由页面脚本自己接管，避免两处监听各关一次；
 * - lockScroll 默认开启，按打开层数引用计数，离开动画结束才真正解锁。
 */
const props = withDefaults(
  defineProps<{
    modelValue: boolean
    teleport?: boolean
    lockScroll?: boolean
    closeOnEsc?: boolean
    zIndex?: number
    ariaLabel?: string
  }>(),
  {
    teleport: true,
    lockScroll: true,
    closeOnEsc: true,
    zIndex: 2600,
    ariaLabel: '',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'after-leave'): void
}>()

const rootEl = ref<HTMLElement | null>(null)

// ---------- body 滚动锁（引用计数） ----------
let lockCount = 0
let savedOverflow = ''

function lockBody() {
  if (!props.lockScroll) return
  lockCount += 1
  if (lockCount === 1) {
    savedOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
}

function unlockBody() {
  if (!props.lockScroll) return
  lockCount = Math.max(0, lockCount - 1)
  if (lockCount === 0) {
    document.body.style.overflow = savedOverflow
    savedOverflow = ''
  }
}

// ---------- Esc ----------
function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape' || !props.closeOnEsc) return
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  async (open, wasOpen) => {
    if (open) {
      lockBody()
      await nextTick()
      rootEl.value?.focus({ preventScroll: true })
    } else if (wasOpen) {
      // 解锁延后到离场动画结束：动画期间背景仍不可滚动，避免页面跟着滑
      // 由 handleAfterLeave 统一解锁，这里只处理「从未打开过」的异常路径
      if (!document.querySelector('.subpage-root')) unlockBody()
    }
  },
)

function handleAfterLeave() {
  unlockBody()
  emit('after-leave')
}

// 父页挂载时子页已是打开态（例如从 URL 深链直接进来），挂载后立刻补锁
onMounted(() => {
  if (props.modelValue) lockBody()
})

onBeforeUnmount(() => {
  // 页面卸载时若仍在打开态，补齐解锁，避免 body 永久锁死
  if (props.modelValue) unlockBody()
})
</script>
