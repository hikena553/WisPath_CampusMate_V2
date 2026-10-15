<template>
  <div class="vm" :class="[`s-${state}`]" :style="{ width: size + 'px' }">
    <!-- 光环：随状态与音量呼吸 -->
    <div class="vm-aura" :style="{ transform: `scale(${auraScale})`, opacity: auraOpacity }" />
    <div class="vm-aura vm-aura-2" />
    <!-- 播报声波环 -->
    <div v-if="state === 'speaking'" class="vm-wave" :style="{ transform: `scale(${waveScale})`, opacity: waveOpacity }" />

    <!-- 产品形象（MYCC 吉祥物，取自站点配置）：外层负责浮动/倾斜，内层做音量形变 -->
    <div class="vm-bob">
      <img
        class="vm-img"
        :src="siteMascot"
        :alt="agentName"
        draggable="false"
        :style="imgStyle"
      />
    </div>

    <!-- 思考气泡点 -->
    <div v-if="state === 'thinking'" class="vm-think">
      <i v-for="d in 3" :key="d" :style="{ animationDelay: (d * 0.16) + 's' }" />
    </div>

    <!-- 漂浮粒子 -->
    <div class="vm-particles">
      <i v-for="n in 8" :key="n" :class="`p${n}`" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

const props = withDefaults(defineProps<{
  state?: 'idle' | 'listening' | 'thinking' | 'speaking'
  /** 平滑后的音量 0~1，用于驱动形象形变与光环强弱 */
  level?: number
  /** 渲染像素尺寸（正方形） */
  size?: number
}>(), { state: 'idle', level: 0, size: 240 })

// 直接使用产品形象（管理端「吉祥物」配置，默认 /images/mascot.png）
const { siteMascot, agentName } = useSiteConfig()

const level = computed(() => Math.max(0, Math.min(1, props.level || 0)))

// 播报时随音量轻微"吐字式"形变（纵向拉伸 + 横向收窄），叠加在浮动动画之上
const imgStyle = computed(() => {
  if (props.state !== 'speaking') return {}
  const l = level.value
  return {
    transform: `translateY(${(-2 - l * 5).toFixed(1)}px) scale(${(1 + l * 0.055).toFixed(3)}, ${(1 - l * 0.035).toFixed(3)})`,
  }
})

const auraScale = computed(() => (props.state === 'idle' ? 1 : 1.04 + level.value * 0.24).toFixed(3))
const auraOpacity = computed(() => {
  if (props.state === 'idle') return 0.5
  if (props.state === 'listening') return 0.75
  if (props.state === 'thinking') return 0.82
  return 0.7 + level.value * 0.3
})
const waveScale = computed(() => (1 + level.value * 0.28).toFixed(3))
const waveOpacity = computed(() => (0.55 - level.value * 0.3).toFixed(3))
</script>

<style scoped>
.vm {
  position: relative;
  aspect-ratio: 1 / 1;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}

.vm-aura {
  position: absolute;
  inset: 6%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(47, 84, 235, 0.34) 0%, rgba(47, 84, 235, 0.12) 46%, transparent 72%);
  transition: transform 0.18s ease-out, opacity 0.3s ease;
  animation: vm-breathe 4.2s ease-in-out infinite;
}
.vm-aura-2 {
  inset: 20%;
  background: radial-gradient(circle, rgba(143, 107, 255, 0.26) 0%, transparent 66%);
  animation: vm-breathe 3.2s ease-in-out infinite reverse;
}
@keyframes vm-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

/* 播报声波环 */
.vm-wave {
  position: absolute;
  inset: 12%;
  border-radius: 50%;
  border: 2px solid rgba(47, 84, 235, 0.4);
  transition: transform 0.12s linear, opacity 0.2s ease;
}

/* 形象主体 */
.vm-bob {
  position: relative;
  z-index: 2;
  width: 84%;
  height: 84%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: vm-float 4s ease-in-out infinite;
}
@keyframes vm-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-7px); }
}

.vm-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none;
  filter: drop-shadow(0 14px 26px rgba(47, 84, 235, 0.22));
  transition: transform 0.1s linear;
}

/* 播报：吐字式点头 */
.vm.s-speaking .vm-bob { animation: vm-talk-bob 0.9s ease-in-out infinite; }
@keyframes vm-talk-bob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  30% { transform: translateY(-2px) rotate(-1.3deg); }
  70% { transform: translateY(-2px) rotate(1.3deg); }
}

/* 聆听：微微前倾放大 */
.vm.s-listening .vm-bob { animation: vm-listen 2.6s ease-in-out infinite; }
@keyframes vm-listen {
  0%, 100% { transform: scale(1) rotate(0deg); }
  50% { transform: scale(1.035) rotate(-1deg); }
}

/* 思考：摇头晃脑 */
.vm.s-thinking .vm-bob { animation: vm-wobble 1.4s ease-in-out infinite; }
@keyframes vm-wobble {
  0%, 100% { transform: rotate(0deg) translateY(0); }
  30% { transform: rotate(-3deg) translateY(-3px); }
  70% { transform: rotate(3deg) translateY(-3px); }
}

/* 思考气泡 */
.vm-think {
  position: absolute;
  right: 16%;
  top: 8%;
  z-index: 3;
  display: flex;
  gap: 5px;
  align-items: flex-end;
}
.vm-think i {
  width: 7px; height: 7px; border-radius: 50%;
  background: linear-gradient(135deg, #8f6bff, #2f54eb);
  animation: vm-dot 1.3s ease-in-out infinite;
}
.vm-think i:nth-child(2) { width: 9px; height: 9px; }
.vm-think i:nth-child(3) { width: 11px; height: 11px; }
@keyframes vm-dot {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.35; }
  40% { transform: translateY(-7px); opacity: 1; }
}

/* 粒子 */
.vm-particles { position: absolute; inset: 0; pointer-events: none; }
.vm-particles i {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(90, 130, 255, 0.9) 0%, transparent 70%);
  opacity: 0;
  animation: vm-p-rise 4.4s ease-in-out infinite;
}
.vm-particles .p1 { width: 6px; height: 6px; left: 12%; bottom: 30%; animation-delay: 0s; }
.vm-particles .p2 { width: 5px; height: 5px; left: 82%; bottom: 36%; animation-delay: 0.6s; }
.vm-particles .p3 { width: 4px; height: 4px; left: 22%; bottom: 64%; animation-delay: 1.2s; }
.vm-particles .p4 { width: 5px; height: 5px; left: 86%; bottom: 58%; animation-delay: 1.8s; }
.vm-particles .p5 { width: 4px; height: 4px; left: 8%; bottom: 50%; animation-delay: 2.4s; }
.vm-particles .p6 { width: 5px; height: 5px; left: 72%; bottom: 20%; animation-delay: 3s; }
.vm-particles .p7 { width: 4px; height: 4px; left: 44%; bottom: 76%; animation-delay: 3.6s; }
.vm-particles .p8 { width: 5px; height: 5px; left: 90%; bottom: 68%; animation-delay: 4.2s; }
@keyframes vm-p-rise {
  0% { transform: translateY(0) scale(0); opacity: 0; }
  25% { opacity: 0.6; transform: scale(1); }
  80% { opacity: 0.15; }
  100% { transform: translateY(-64px) scale(0.35); opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .vm-aura, .vm-bob, .vm-particles i, .vm-think i { animation: none !important; }
}
</style>