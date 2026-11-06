<template>
  <div class="lt-wrap">
    <!--
      两档语义必须一眼看懂，所以用文字 + 说明的方式，而不是只有两段的分段控件：
      教师需要知道「不分层」意味着「按老样子的网格看」，「危机分层」意味着「按三档排队」。
    -->
    <div class="lt-seg" role="tablist" aria-label="名单展示方式">
      <button
        v-for="o in options"
        :key="o.value"
        type="button"
        role="tab"
        class="lt-opt"
        :class="{ 'is-on': modelValue === o.value }"
        :aria-selected="modelValue === o.value"
        :title="o.hint"
        @click="emit('update:modelValue', o.value)"
      >
        <el-icon :size="13" class="lt-ic"><component :is="o.icon" /></el-icon>
        {{ o.label }}
      </button>
    </div>
    <span class="lt-hint">{{ current.hint }}</span>
  </div>
</template>

<script lang="ts">
/**
 * 分层模式：不分层（平铺网格）/ 危机分层（三档排队）。
 * 单独放在普通 script 块里导出 —— `<script setup>` 不允许 `export`，
 * 页面需要一个类型来做 `ref<LayerMode>` 与 localStorage 的取值校验。
 */
export type LayerMode = 'none' | 'crisis'
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { Menu, Grid } from '@element-plus/icons-vue'

const props = defineProps<{ modelValue: LayerMode }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: LayerMode): void }>()

const options = [
  { value: 'crisis' as LayerMode, label: '危机分层', hint: '按危机等级分三档排队，先看要紧的', icon: Menu },
  { value: 'none' as LayerMode, label: '不分层', hint: '全部学生平铺一屏，按分数/姓名浏览', icon: Grid },
]

const current = computed(() => options.find(o => o.value === props.modelValue) || options[0])
</script>

<style scoped>
.lt-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}
.lt-seg {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border-radius: 9px;
  background: #f1f4f9;
  flex-shrink: 0;
}
.lt-opt {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: none;
  border-radius: 7px;
  background: transparent;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: #78849a;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}
.lt-opt:hover { color: #1b4fd1; }
.lt-opt.is-on {
  background: #fff;
  color: #16233a;
  box-shadow: 0 1px 2px rgba(16, 23, 37, 0.09);
}
.lt-ic { flex-shrink: 0; }
.lt-hint {
  font-size: 11.5px;
  color: #98a2b3;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 移动端：说明文字空间紧张，让分段控件独占一行 */
@media (max-width: 767px) {
  .lt-wrap { gap: 6px; width: 100%; }
  .lt-seg { flex: 1; }
  .lt-opt { flex: 1; justify-content: center; padding: 6px 8px; }
  .lt-hint { display: none; }
}
</style>
