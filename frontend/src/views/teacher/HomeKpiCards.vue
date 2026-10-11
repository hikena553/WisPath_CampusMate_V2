<template>
  <!-- ===== 第一层：KPI统计卡片 ===== -->
  <div class="kpi-cards">
    <div class="kpi-card" v-for="card in cards" :key="card.label"
      :style="{ '--kpi-color': card.color }" @click="emit('navigate', card.link)">
      <div class="kpi-icon">
        <el-icon :size="24"><component :is="card.icon" /></el-icon>
      </div>
      <div class="kpi-info">
        <div class="kpi-value">{{ card.value }}</div>
        <div class="kpi-label">{{ card.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

export interface KpiCard {
  label: string
  value: number | string
  color: string
  icon: Component
  link: string
}

defineProps<{ cards: KpiCard[] }>()

const emit = defineEmits<{ navigate: [link: string] }>()
</script>

<style scoped>
/* ===== KPI 卡片（对齐设计稿：白卡 + 发丝线 + 38px 圆角图标块） ===== */
.kpi-cards {
  display: grid;
  /* auto-fit：卡片数量变化时自动均分列数，避免落单 */
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 14px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  cursor: pointer;
}

.kpi-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--kpi-color) 12%, white);
  color: var(--kpi-color);
  flex-shrink: 0;
}

.kpi-info { flex: 1; min-width: 0; }

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--tui-text);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.kpi-label {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  margin-top: 2px;
}

@media (max-width: 767px) {
  .kpi-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    position: relative;
    z-index: 1;
  }

  /* 卡片数为奇数时，最后一张通栏，避免落单 */
  .kpi-card:last-child:nth-child(odd) {
    grid-column: span 2;
  }

  .kpi-card {
    padding: 11px 12px;
    gap: 10px;
  }

  .kpi-value { font-size: 19px; }
}
</style>