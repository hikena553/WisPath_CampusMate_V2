<template>
  <div class="tui-seg" role="tablist">
    <button
      v-for="opt in options"
      :key="String(opt.value)"
      type="button"
      role="tab"
      class="tui-seg-item"
      :class="{ active: modelValue === opt.value }"
      :aria-selected="modelValue === opt.value"
      @click="select(opt.value)"
    >
      {{ opt.label }}
      <span v-if="opt.count !== undefined" class="seg-count">{{ opt.count }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * 移动端分段控件（Segmented Control）
 * 形态参考 Ant Design Mobile / Vant 的 Segmented，用于替代在窄屏下表现不佳的裸 el-tabs。
 */
export interface SegmentedOption {
  value: string | number
  label: string
  count?: number
}

defineProps<{
  modelValue: string | number
  options: SegmentedOption[]
}>()

const emit = defineEmits<{ 'update:modelValue': [value: string | number] }>()

function select(value: string | number) {
  emit('update:modelValue', value)
}
</script>

<style scoped>
.seg-count {
  margin-left: 4px;
  font-size: 11px;
  font-weight: 500;
  opacity: 0.72;
}
</style>