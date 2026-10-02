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
/* ===== KPI Cards ===== */
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.kpi-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--kpi-color) 12%, white);
  color: var(--kpi-color);
  flex-shrink: 0;
}

.kpi-info {
  flex: 1;
}

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.kpi-label {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}

@media (max-width: 1200px) {
  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 767px) {
  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    position: relative;
    z-index: 1;
  }

  .kpi-card {
    padding: 10px;
  }

  .kpi-icon {
    width: 36px;
    height: 36px;
  }

  .kpi-value {
    font-size: 18px;
  }

  .kpi-label {
    font-size: 11px;
  }
}
</style>