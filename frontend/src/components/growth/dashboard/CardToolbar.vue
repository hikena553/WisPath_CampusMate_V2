<template>
  <div class="gd-edit-bar">
    <button type="button" class="tb-btn" :disabled="!canUp" aria-label="上移" @click="emit('up')">
      <el-icon :size="14"><ArrowUp /></el-icon>
    </button>
    <button type="button" class="tb-btn" :disabled="!canDown" aria-label="下移" @click="emit('down')">
      <el-icon :size="14"><ArrowDown /></el-icon>
    </button>
    <button
      type="button"
      class="tb-btn"
      :class="{ 'tb-btn--off': hidden }"
      :aria-label="hidden ? '显示该卡片' : '隐藏该卡片'"
      @click="emit('toggle')"
    >
      <el-icon :size="14"><View v-if="!hidden" /><Hide v-else /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ArrowUp, ArrowDown, View, Hide } from '@element-plus/icons-vue'

defineProps<{ canUp: boolean; canDown: boolean; hidden: boolean }>()
const emit = defineEmits<{ (e: 'up'): void; (e: 'down'): void; (e: 'toggle'): void }>()
</script>

<style scoped>
.gd-edit-bar {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--gd-border, rgba(0, 0, 0, 0.08));
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}
.tb-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--gd-ink-2, #666666);
  border-radius: 7px;
  cursor: pointer;
}
.tb-btn:hover:not(:disabled) { background: var(--gd-muted, #f6f8fc); color: var(--gd-primary, #409eff); }
.tb-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.tb-btn--off { color: var(--gd-danger, #f56c6c); }
</style>