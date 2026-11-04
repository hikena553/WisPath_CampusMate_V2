<template>
  <img
    class="ai-mascot-mark"
    :src="siteMascot"
    :alt="siteName"
    draggable="false"
    :style="{ width: `${size}px`, height: `${size}px` }"
  />
</template>

<script setup lang="ts">
import { useSiteConfig } from '@/composables/useSiteConfig'

withDefaults(defineProps<{ size?: number }>(), { size: 16 })

const { siteMascot, siteName } = useSiteConfig()
</script>

<style scoped>
/* AI 标记统一改用产品形象：透明底、等比缩放，不裁切 */
.ai-mascot-mark {
  display: inline-block;
  flex: 0 0 auto;
  object-fit: contain;
  vertical-align: middle;
  user-select: none;
  -webkit-user-drag: none;
}
</style>
