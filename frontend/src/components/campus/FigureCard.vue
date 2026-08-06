<template>
  <div class="figure-card" @click="emit('click')">
    <div class="fig-avatar-wrap">
      <el-avatar :size="72" :src="figure.avatar" class="fig-avatar">{{ figure.name[0] }}</el-avatar>
    </div>
    <h3 class="fig-name">{{ figure.name }}</h3>
    <span class="fig-title">{{ figure.title }}</span>
    <p class="fig-desc">{{ figure.description }}</p>
    <span class="fig-more">点击查看详情 →</span>
  </div>
</template>

<script setup lang="ts">
import type { CampusFigure } from '@/types'
defineProps<{ figure: CampusFigure }>()
const emit = defineEmits<{ click: [] }>()
</script>

<style scoped>
.figure-card {
  background: #fff; border-radius: 14px; padding: 24px 20px 20px;
  text-align: center; border: 1px solid rgba(0,0,0,.04);
  box-shadow: 0 2px 10px rgba(0,0,0,.03);
  transition: transform .2s, box-shadow .2s; cursor: pointer;
}
.figure-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,.06); }
.fig-avatar-wrap { margin-bottom: 12px; }
.fig-avatar { border: 3px solid rgba(64,158,255,.1); }
.fig-name { font-size: 16px; font-weight: 600; color: #1a1a2e; margin: 0 0 4px; }
.fig-title { font-size: 12px; color: #409eff; background: rgba(64,158,255,.08); padding: 2px 12px; border-radius: 10px; display: inline-block; margin-bottom: 10px; }
.fig-desc {
  font-size: 13px; color: #666; line-height: 1.5; margin: 0; text-align: left;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; text-overflow: ellipsis;
}
.fig-more { font-size: 12px; color: #409eff; margin-top: 10px; display: inline-block; }
</style>
