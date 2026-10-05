<template>
  <div class="kpi" :class="`kpi-${tone}`">
    <div class="kpi-value">
      {{ value }}<span v-if="unit" class="kpi-unit">{{ unit }}</span>
    </div>
    <div class="kpi-label">{{ label }}</div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string | number
    unit?: string
    tone?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral'
  }>(),
  { unit: '', tone: 'neutral' }
)
</script>

<style scoped>
.kpi {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 12px 11px;
  background: #ffffff;
  border: 1px solid var(--gd-border, rgba(0, 0, 0, 0.06));
  border-radius: var(--gd-radius-md, 12px);
}
.kpi-value {
  font-size: 22px;
  line-height: 1.05;
  font-weight: 800;
  color: var(--gd-ink, #1a1a2e);
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}
.kpi-unit {
  margin-left: 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gd-ink-3, #999);
}
.kpi-label {
  font-size: 11.5px;
  color: var(--gd-ink-2, #666);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kpi-primary .kpi-value { color: var(--gd-primary, #409eff); }
.kpi-success .kpi-value { color: #34b369; }
.kpi-warning .kpi-value { color: var(--gd-warning, #e6a23c); }
.kpi-danger .kpi-value { color: var(--gd-danger, #f56c6c); }
</style>