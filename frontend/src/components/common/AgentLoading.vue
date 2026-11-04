<template>
  <!-- 智能体式加载反馈（全端统一）
       逻辑取自对话里的 AI 工作态，而不是「转圈图标」：
       1) 即时反馈——先出现三颗呼吸打点，任何一次取数都不留空白；
       2) 有进展感——一句状态文案按 2.2s 轮换（「正在读取课表」→「还在核对…」），
          让人知道它在做事，而不是卡住；
       3) 软收尾——文案换词走淡出淡入，加载结束由调用方用 .tui-enter 让内容上浮入场，
          不做硬切；
       4) block 模式追加一条不确定进度条（2px、从左滑到右），只在整块区域等待时出现。
       刻意不用 el-icon 的 is-loading 转圈：一圈匀速旋转既不表明进度，也最容易让人误判「卡死」。 -->
  <div
    class="agent-loading"
    :class="[`is-${size}`, { 'is-block': block }]"
    role="status"
    aria-live="polite"
  >
    <span class="al-dots" aria-hidden="true"><i /><i /><i /></span>

    <Transition name="al-swap" mode="out-in">
      <span :key="currentTip" class="al-text">{{ currentTip }}</span>
    </Transition>

    <span v-if="block" class="al-track" aria-hidden="true"><i /></span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 固定文案：传了就不再轮换 */
    text?: string
    /** 轮换文案池：不传 text 时使用 */
    tips?: string[]
    /** sm：行内小字（列表、地址簿、卡片局部）；md：整块等待 */
    size?: 'sm' | 'md'
    /** 块级：居中撑开一块区域，并在文案下方带一条不确定进度条 */
    block?: boolean
    /** 文案轮换间隔（毫秒） */
    interval?: number
  }>(),
  {
    text: '',
    tips: () => ['正在读取最新数据', '还在核对，马上就好'],
    size: 'sm',
    block: false,
    interval: 2200,
  }
)

const DEFAULT_FIXED = '正在加载'
const index = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const pool = computed(() => (props.tips.length ? props.tips : ['正在加载']))

const currentTip = computed(() => props.text || pool.value[index.value % pool.value.length] || DEFAULT_FIXED)

function stop() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(
  () => [props.text, props.tips, props.interval] as const,
  () => {
    stop()
    index.value = 0
    // 固定文案没有轮换的必要
    if (props.text || pool.value.length <= 1) return
    timer = setInterval(() => {
      index.value = (index.value + 1) % pool.value.length
    }, props.interval)
  },
  { immediate: true, deep: true }
)

onBeforeUnmount(stop)
</script>

<style scoped>
.agent-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--tui-text-tertiary, #6b7280);
  font-size: 12px;
  line-height: 1.4;
  min-width: 0;
}

.agent-loading.is-md { font-size: 13px; gap: 9px; }

/* ---------------- 打点 ---------------- */
.al-dots { display: inline-flex; align-items: center; gap: 3px; flex-shrink: 0; }

.al-dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--tui-brand, #2563eb);
  opacity: 0.35;
  animation: al-dot 1.15s ease-in-out infinite;
}
.al-dots i:nth-child(2) { animation-delay: 0.16s; }
.al-dots i:nth-child(3) { animation-delay: 0.32s; }

.agent-loading.is-md .al-dots { gap: 4px; }
.agent-loading.is-md .al-dots i { width: 5px; height: 5px; }

/* ---------------- 文案 ---------------- */
.al-text {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 换词：淡出淡入，几乎不留模糊（13px 字号上 1.5px 的模糊会被看成「花了」） */
.al-swap-enter-active,
.al-swap-leave-active { transition: opacity 0.2s ease, filter 0.2s ease; }
.al-swap-enter-from { opacity: 0; filter: blur(0.6px); }
.al-swap-leave-to { opacity: 0; filter: blur(0.6px); }

/* ---------------- 块级布局 ---------------- */
.agent-loading.is-block {
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding: 26px 16px 22px;
  text-align: center;
}

.agent-loading.is-block .al-text { white-space: normal; }

.al-track {
  position: relative;
  width: 108px;
  height: 2px;
  border-radius: 2px;
  overflow: hidden;
  background: color-mix(in srgb, var(--tui-brand, #2563eb) 12%, transparent);
}

.al-track i {
  position: absolute;
  inset: 0 auto 0 0;
  width: 42%;
  border-radius: 2px;
  background: var(--tui-brand, #2563eb);
  animation: al-slide 1.35s cubic-bezier(0.45, 0, 0.35, 1) infinite;
}

@keyframes al-dot {
  0%, 100% { opacity: 0.28; transform: translateY(0) scale(0.86); }
  40% { opacity: 1; transform: translateY(-2px) scale(1); }
}

@keyframes al-slide {
  0% { transform: translateX(-105%); }
  100% { transform: translateX(255%); }
}

/* 尊重「减少动效」：只留静态文案 */
@media (prefers-reduced-motion: reduce) {
  .al-dots i,
  .al-track i { animation: none; }
  .al-track i { width: 100%; opacity: 0.5; }
  .al-swap-enter-active,
  .al-swap-leave-active { transition: none; }
}
</style>
