<template>
  <!-- ===== 数据概览 KPI 卡 =====
       数字赋能风格（桌面端）：图标退为语义色标记，大号等宽数字成为视觉主体；
       当该指标存在真实分母（如「已闭环 / 预警总数」）时，底部补一条占比微条，
       把「一个数字」升级为「一个数字 + 它的处境」；没有真实分母的指标不画假进度。
       移动端沿用原有的「左图标 + 右数值」横排布局（见底部 media query）。 -->
  <div class="kpi-cards">
    <div
      class="kpi-card"
      v-for="card in cards"
      :key="card.label"
      :style="{ '--kpi-color': card.color }"
      @click="emit('navigate', card.link)"
    >
      <div class="kpi-icon">
        <el-icon :size="24"><component :is="card.icon" /></el-icon>
      </div>
      <div class="kpi-info">
        <div class="kpi-value">{{ card.value }}</div>
        <div class="kpi-label">{{ card.label }}</div>
        <div v-if="card.ratio !== undefined" class="kpi-meter">
          <span class="kpi-meter-track">
            <span class="kpi-meter-fill" :style="{ '--pct': card.ratio }" />
          </span>
          <span class="kpi-hint">{{ card.hint }}</span>
        </div>
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
  /** 真实占比（0~1）：存在分母时展示底部微条，例如「已闭环 / 预警总数」 */
  ratio?: number
  /** 占比微条右侧的一句处境说明，来自真实统计，不编造 */
  hint?: string
}

defineProps<{ cards: KpiCard[] }>()

const emit = defineEmits<{ navigate: [link: string] }>()
</script>

<style scoped>
/* ===== 桌面端：纵向数字卡（图标 → 标签 → 大号数字 → 占比微条） ===== */
.kpi-cards {
  display: grid;
  /* auto-fit：卡片数量变化时自动均分列数，避免落单 */
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}

.kpi-card {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  padding: 14px 16px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}
/* 顶部一条语义色细线：四张卡在无色差之下仍能靠色区分 */
.kpi-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: var(--kpi-color);
  opacity: 0.85;
}

.kpi-icon {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--kpi-color) 11%, white);
  color: var(--kpi-color);
  flex-shrink: 0;
}
.kpi-icon :deep(.el-icon) { font-size: 16px; }

.kpi-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

/* 桌面端把标签提到数字之上，让数字独占一行成为主角 */
.kpi-label {
  order: -1;
  font-size: 12.5px;
  color: var(--tui-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}

/* 真实占比微条 */
.kpi-meter {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 5px;
  min-height: 14px;
}
.kpi-meter-track {
  flex: 1;
  min-width: 0;
  height: 4px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
}
.kpi-meter-fill {
  display: block;
  height: 100%;
  width: calc(var(--pct, 0) * 100%);
  border-radius: 999px;
  background: var(--kpi-color);
}
.kpi-hint {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}

/* ===== 移动端：还原原有「左图标 + 右数值」横排布局 ===== */
@media (max-width: 767px) {
  .kpi-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin-bottom: 12px;
    position: relative;
    z-index: 1;
  }

  /* 卡片数为奇数时，最后一张通栏，避免落单 */
  .kpi-card:last-child:nth-child(odd) {
    grid-column: span 2;
  }

  .kpi-card {
    flex-direction: row;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
  }
  .kpi-card::before { display: none; }

  .kpi-icon {
    width: 38px;
    height: 38px;
    border-radius: 11px;
  }
  .kpi-icon :deep(.el-icon) { font-size: 24px; }

  .kpi-info { flex: 1; gap: 0; }
  /* 移动端恢复「数值在上、标签在下」的原顺序 */
  .kpi-label { order: 0; margin-top: 2px; font-size: 11.5px; color: var(--tui-text-quiet); }
  .kpi-value { font-size: 19px; line-height: 1.1; letter-spacing: 0; }

  /* 移动端不展示占比微条，保持原有紧凑结构 */
  .kpi-meter { display: none; }
}
</style>