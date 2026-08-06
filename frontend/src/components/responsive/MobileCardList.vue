<template>
  <div class="mobile-card-list">
    <div v-if="!data.length" class="empty-state">
      <el-empty description="暂无数据" :image-size="64" />
    </div>
    <div
      v-for="row in data"
      :key="row[rowKey || 'id']"
      class="mobile-card"
    >
      <div class="card-header">
        <slot name="card-header" :row="row">
          <span class="card-title">{{ getPrimaryValue(row) }}</span>
        </slot>
      </div>
      <div class="card-body">
        <div
          v-for="col in displayColumns"
          :key="col.key"
          class="card-field"
        >
          <span class="field-label">{{ col.label }}</span>
          <span class="field-value">
            <el-tag v-if="col.tag" :type="col.tagType?.(row[col.key]) || 'info'" size="small">
              {{ row[col.key] || '--' }}
            </el-tag>
            <span v-else>{{ row[col.key] || '--' }}</span>
          </span>
        </div>
      </div>
      <div v-if="$slots.actions" class="card-actions">
        <slot name="actions" :row="row" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface Column {
  key: string
  label: string
  primary?: boolean
  tag?: boolean
  tagType?: (val: string) => string
  hideOnMobile?: boolean
}

const props = withDefaults(defineProps<{
  data: any[]
  columns: Column[]
  rowKey?: string
}>(), {
  rowKey: 'id'
})

const displayColumns = computed(() =>
  props.columns.filter(c => !c.primary && !c.hideOnMobile)
)

function getPrimaryValue(row: any) {
  const primaryCol = props.columns.find(c => c.primary)
  return primaryCol ? row[primaryCol.key] : row[props.rowKey]
}
</script>

<style scoped>
.mobile-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.card-header {
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-body {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.card-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 12px;
  color: #999;
}

.field-value {
  font-size: 14px;
  color: #333;
  word-break: break-word;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.empty-state {
  padding: 40px 0;
}
</style>
