<template>
  <!-- 产品形象 + 智能体式加载反馈
       三态共用一套骨架，仅切换动作与文案，避免同一页面出现三种视觉语言：
       loading  —— 形象安静呼吸 + 打点/轮换文案/不确定进度条（与对话里 AI 的工作态同构）
       error    —— 形象「挠头」+ 明确的失败原因 + 重试
       empty    —— 形象「待命」+ 说明 + 可选行动
       加载态刻意不用「绕圈的点阵」和「转圈图标」：一圈匀速旋转既不表达进度，
       又最容易让人误判成卡死；真正有用的是「它在做哪一步」+「还在继续」两件事，
       所以文案按节奏轮换、下面压一条不确定进度条。 -->
  <div class="tui-mascot-state" :class="[`is-${state}`, { 'is-compact': compact }]">
    <div class="tui-mascot-stage">
      <div class="tui-mascot-halo" aria-hidden="true"></div>
      <img :src="siteMascot" :alt="siteName" class="tui-mascot-img" draggable="false" />
    </div>

    <!-- 加载中：交给统一的 AgentLoading（打点 + 轮换文案 + 进度条） -->
    <AgentLoading
      v-if="state === 'loading'"
      :text="title"
      :tips="loadingTips"
      size="md"
      block
    />

    <template v-else>
      <p class="tui-mascot-title">{{ displayTitle }}</p>
      <p v-if="displayDesc" class="tui-mascot-desc">{{ displayDesc }}</p>

      <div v-if="$slots.actions || retryText" class="tui-mascot-actions">
        <slot name="actions">
          <button type="button" class="tui-mascot-btn" :disabled="busy" @click="$emit('retry')">
            <el-icon v-if="busy" class="is-spin" :size="13"><Loading /></el-icon>
            {{ busy ? retryBusyText : retryText }}
          </button>
        </slot>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import AgentLoading from '@/components/common/AgentLoading.vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

const props = withDefaults(
  defineProps<{
    /** 状态：加载中 / 失败 / 空数据 */
    state?: 'loading' | 'error' | 'empty'
    /** 主文案：不传时按 state 取默认值（loading 态下轮换 loadingTips） */
    title?: string
    /** 辅助说明：失败原因、下一步提示 */
    desc?: string
    /** 加载态轮换文案池：不传用通用默认值 */
    tips?: string[]
    /** 重试按钮文案（传空串则不渲染按钮） */
    retryText?: string
    /** 重试进行中：按钮禁用并显示转圈 */
    busy?: boolean
    retryBusyText?: string
    /** 紧凑模式：用于卡片内局部占位，缩小形象与间距 */
    compact?: boolean
  }>(),
  {
    state: 'loading',
    title: '',
    desc: '',
    tips: () => [],
    retryText: '',
    busy: false,
    retryBusyText: '正在重试',
    compact: false,
  }
)

defineEmits<{ retry: [] }>()

const { siteMascot, siteName } = useSiteConfig()

const DEFAULT_TITLE: Record<string, string> = {
  loading: '',
  error: '今日重点暂时打不开',
  empty: '今天暂时没有需要处理的事',
}
const DEFAULT_DESC: Record<string, string> = {
  loading: '',
  error: '可能是网络波动或服务繁忙，稍后再试一次',
  empty: '有新任务、预警或请假时，会自动出现在这里',
}

/** 通用加载文案池：页面没给专属文案时用它，保证任何等待都有进展感 */
const FALLBACK_TIPS = ['正在读取最新数据', '还在核对细节', '快好了，稍等一下']

const loadingTips = computed(() => (props.tips.length ? props.tips : FALLBACK_TIPS))
const displayTitle = computed(() => props.title || DEFAULT_TITLE[props.state] || '')
const displayDesc = computed(() => props.desc || DEFAULT_DESC[props.state] || '')
</script>

<style scoped>
.tui-mascot-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  /* 空页面上把等待内容放到视觉中心：只写 padding 时它会贴着内容区顶部，
     桌面端一整屏空白里孤零零挂在最上面，看起来像「页面没加载完就停住了」 */
  min-height: clamp(240px, 44vh, 420px);
  padding: 24px;
  text-align: center;
}

.tui-mascot-state.is-compact {
  min-height: 0;
  padding: 22px 16px 20px;
}

/* ---------------- 形象舞台 ---------------- */
.tui-mascot-stage {
  position: relative;
  width: 132px;
  height: 132px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}

.tui-mascot-state.is-compact .tui-mascot-stage {
  width: 88px;
  height: 88px;
}

/* 加载态：把舞台收小，让「打点 + 文案」成为视觉主体，形象退为安静的陪伴 */
.tui-mascot-state.is-loading .tui-mascot-stage {
  width: 104px;
  height: 104px;
  margin-bottom: 0;
}

.tui-mascot-halo {
  position: absolute;
  inset: 6%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.14) 0%, rgba(37, 99, 235, 0) 68%);
  animation: tui-halo 2.6s var(--tui-ease, ease) infinite;
}

.tui-mascot-img {
  position: relative;
  z-index: 2;
  width: 84px;
  height: 84px;
  object-fit: contain;
  user-select: none;
  pointer-events: none;
  animation: tui-float 3.4s var(--tui-ease, ease) infinite;
  filter: drop-shadow(0 6px 14px rgba(37, 99, 235, 0.14));
}

.tui-mascot-state.is-loading .tui-mascot-img {
  width: 68px;
  height: 68px;
  /* 加载中不要大幅上下浮动：轻微呼吸即可，动得越大越像在「跳迪斯科」 */
  animation: tui-breathe 2.8s var(--tui-ease, ease) infinite;
}

.tui-mascot-state.is-compact .tui-mascot-img {
  width: 54px;
  height: 54px;
  animation-duration: 4s;
}

/* 失败态：形象略微下沉并停止上浮，读起来像「停下来了」 */
.tui-mascot-state.is-error .tui-mascot-img {
  animation: tui-tilt 3.2s ease-in-out infinite;
  filter: drop-shadow(0 4px 10px rgba(15, 17, 21, 0.1)) saturate(0.75);
}
.tui-mascot-state.is-error .tui-mascot-halo {
  background: radial-gradient(circle, rgba(107, 114, 128, 0.14) 0%, rgba(107, 114, 128, 0) 68%);
  animation-duration: 4s;
}

/* ---------------- 文案 ---------------- */
.tui-mascot-title {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--tui-text, #0f1115);
  letter-spacing: 0.2px;
}

.tui-mascot-desc {
  margin: 6px 0 0;
  max-width: 260px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tui-text-tertiary, #6b7280);
}

.tui-mascot-actions {
  margin-top: 16px;
}

.tui-mascot-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 34px;
  padding: 0 18px;
  border: 0;
  border-radius: 10px;
  background: var(--tui-brand, #2563eb);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.18s var(--tui-ease, ease), transform 0.12s var(--tui-ease, ease);
}

.tui-mascot-btn:hover:not(:disabled) { background: var(--tui-brand-strong, #1d4ed8); }
.tui-mascot-btn:active:not(:disabled) { transform: scale(0.97); }
.tui-mascot-btn:disabled { opacity: 0.7; cursor: default; }

.is-spin { animation: tui-spin 0.9s linear infinite; }

/* ---------------- 动效 ---------------- */
@keyframes tui-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

/* 呼吸：只有 2px 的位移 + 1% 的缩放，安静但不死板 */
@keyframes tui-breathe {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-2px) scale(1.015); }
}

@keyframes tui-tilt {
  0%, 100% { transform: translateY(2px) rotate(-2deg); }
  50% { transform: translateY(5px) rotate(2deg); }
}

@keyframes tui-halo {
  0%, 100% { transform: scale(0.94); opacity: 0.75; }
  50% { transform: scale(1.06); opacity: 1; }
}

@keyframes tui-spin {
  to { transform: rotate(360deg); }
}

/* 尊重「减少动效」偏好：只留静态形象 */
@media (prefers-reduced-motion: reduce) {
  .tui-mascot-img,
  .tui-mascot-halo { animation: none !important; }
}
</style>
