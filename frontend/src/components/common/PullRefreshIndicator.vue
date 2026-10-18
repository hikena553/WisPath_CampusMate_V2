<template>
  <div class="ptr-ind" :style="indicatorStyle" aria-hidden="true">
    <img class="ptr-mascot" :class="{ jumping: active }" :src="siteMascot" alt="" />
  </div>
</template>

<script setup lang="ts">
/**
 * 下拉刷新指示器（模块化复用单元）
 *
 * 放在滚动容器内：自身高度即下拉位移，靠指示器撑开的高度把下方内容下移。
 * 页面若有吸顶头，指示器要放在头部**之后**，头部才能保持不动（见 usePullRefresh 注释）。
 * 高度与过渡由 usePullRefresh 的 indicatorStyle 提供，起跳状态由 active 提供，
 * 因此教师端首页 / 学生端页面 / 消息页共用同一套吉祥物动画，改一处即全端生效。
 */
import type { CSSProperties } from 'vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

defineProps<{
  /** 下拉位移与收起过渡，取自 usePullRefresh().indicatorStyle */
  indicatorStyle: CSSProperties
  /** 拉过阈值或刷新中：吉祥物起跳 */
  active: boolean
}>()

const { siteMascot } = useSiteConfig()
</script>

<style scoped>
.ptr-ind {
  height: 0;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden; pointer-events: none; flex-shrink: 0;
}
.ptr-mascot { width: 30px; height: 30px; object-fit: contain; flex-shrink: 0; display: block; }
/* 拉过阈值 / 刷新中：吉祥物起跳（按压-腾空-落地），替代文字状态提示 */
.ptr-mascot.jumping { animation: ptr-jump .7s ease-in-out infinite; }
@keyframes ptr-jump {
  0%, 100% { transform: translateY(0) scale(1, 1); }
  22% { transform: translateY(-7px) scale(0.96, 1.05); }
  55% { transform: translateY(0) scale(1.04, 0.95); }
}
@media (prefers-reduced-motion: reduce) {
  .ptr-mascot.jumping { animation: none; }
}
</style>