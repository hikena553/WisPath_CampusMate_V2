<template>
  <!-- 页面特色头部（仅桌面端使用）：
       左侧是「语义色图标 + 标题 + 副标题」，右侧是当前页面自己的关键指标。
       每个页面传入不同的 tone / icon / 指标，避免各页顶部千篇一律。
       样式定义在 teacher-ui.css 的 .tui-hero 区块。 -->
  <header class="tui-hero" :class="`is-${tone}`">
    <div class="tui-hero-lead">
      <span class="tui-hero-icon">
        <el-icon :size="19"><component :is="icon" /></el-icon>
      </span>
      <div class="tui-hero-text">
        <h2 class="tui-hero-title">{{ title }}</h2>
        <p v-if="sub" class="tui-hero-sub">{{ sub }}</p>
      </div>
    </div>

    <div v-if="$slots.default || $slots.actions" class="tui-hero-side">
      <slot />
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(
  defineProps<{
    /** 页面标题 */
    title: string
    /** 一句话说明该页面的职责 */
    sub?: string
    /** 页面图标 */
    icon: Component
    /** 语义色：决定左缘色条、图标底色与强调指标的颜色 */
    tone?: 'brand' | 'danger' | 'warn' | 'success' | 'violet' | 'cyan'
  }>(),
  { tone: 'brand', sub: '' }
)
</script>