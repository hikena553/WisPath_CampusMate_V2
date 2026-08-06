<template>
  <div class="milestone">
    <div class="dot" :style="{ background: colorMap[record.type] }" />
    <div class="content">
      <div class="header">
        <el-tag :type="tagMap[record.type]" size="small">{{ typeLabel[record.type] }}</el-tag>
        <span class="date">{{ record.date }}</span>
      </div>
      <h4>{{ record.title }}</h4>
      <p v-if="record.description">{{ record.description }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GrowthRecord } from '@/types'

defineProps<{ record: GrowthRecord }>()

const colorMap: Record<string, string> = {
  honor: '#e6a23c', competition: '#409eff', award: '#67c23a', practice: '#909399',
}
const tagMap: Record<string, string> = {
  honor: 'warning', competition: 'primary', award: 'success', practice: 'info',
}
const typeLabel: Record<string, string> = {
  honor: '荣誉', competition: '竞赛', award: '获奖', practice: '实践',
}
</script>

<style scoped>
.milestone { display: flex; gap: 16px; padding: 16px 0; border-left: 2px solid #eee; padding-left: 20px; position: relative; }
.dot { width: 12px; height: 12px; border-radius: 50%; position: absolute; left: -7px; top: 20px; }
.content { flex: 1; }
.header { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.date { color: #999; font-size: 13px; }
</style>
