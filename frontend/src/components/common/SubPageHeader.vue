<template>
  <header v-if="isMobile" class="tui-appbar">
    <button class="tui-appbar-back" type="button" aria-label="返回" @click="goBack">
      <el-icon :size="20"><ArrowLeft /></el-icon>
    </button>
    <div class="tui-appbar-title">
      {{ title }}
      <span v-if="sub" class="tui-appbar-sub">{{ sub }}</span>
    </div>
    <div v-if="$slots.right" class="tui-appbar-actions">
      <slot name="right" />
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps<{
  /** 页面标题（移动端吸顶栏展示） */
  title: string
  /** 无历史记录时的兜底返回路径 */
  fallback: string
  /** 可选副标题，展示在标题下方 */
  sub?: string
}>()

const { isMobile } = useResponsive()
const router = useRouter()

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push(props.fallback)
  }
}
</script>