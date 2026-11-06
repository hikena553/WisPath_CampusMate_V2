<template>
  <div class="cs-wrap">
    <!-- 主行：返回 + 班级名 + 人数 -->
    <div class="cs-main">
      <button class="cs-back" type="button" aria-label="返回全部班级" @click="emit('back')">
        <el-icon :size="16"><ArrowLeft /></el-icon>
        <span>全部班级</span>
      </button>
      <span class="cs-sep" aria-hidden="true">/</span>
      <h2 class="cs-title">{{ cls.name }}</h2>
      <span class="cs-total">{{ cls.total }} 人</span>
    </div>

    <!--
      重点关注提示条：进班级后第一句要说的话。
      它同时是筛选开关 —— 点一下只看这几个人，再点回全部。
      不作为独立弹窗/抽屉：这里只是一次筛选，弹层会让「返回全部」多一步。
    -->
    <button
      v-if="cls.focus > 0"
      type="button"
      class="cs-focus"
      :class="{ 'is-on': onlyFocus }"
      :aria-pressed="onlyFocus"
      @click="emit('toggle-focus')"
    >
      <el-icon :size="15" class="cs-focus-ic"><WarningFilled /></el-icon>
      <span class="cs-focus-text">
        本班有 <b>{{ cls.focus }}</b> 人需要重点关注
        <em v-if="cls.severe">（{{ cls.severe }} 人必须今天处理）</em>
      </span>
      <span class="cs-focus-act">{{ onlyFocus ? '显示全部' : '只看这些人' }}</span>
    </button>
    <div v-else class="cs-focus is-clear">
      <el-icon :size="15" class="cs-focus-ic"><CircleCheckFilled /></el-icon>
      <span class="cs-focus-text">本班暂无需要重点关注的学生</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import type { ClassSummary } from '@/composables/useClassSummaries'

defineProps<{
  cls: ClassSummary
  onlyFocus: boolean
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'toggle-focus'): void
}>()
</script>

<style scoped>
.cs-wrap { display: flex; flex-direction: column; gap: 9px; }

.cs-main { display: flex; align-items: center; gap: 8px; min-width: 0; }
.cs-back {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 4px 9px 4px 6px;
  border: 1px solid #ebedf0;
  border-radius: 8px;
  background: #fff;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.cs-back:hover { border-color: #2563eb; color: #2563eb; background: #eff4ff; }
.cs-sep { color: #d0d5dd; flex-shrink: 0; }
.cs-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.3px;
  color: #101828;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cs-total {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 7px;
  background: #f2f4f7;
  font-size: 11.5px;
  font-weight: 600;
  color: #667085;
  font-variant-numeric: tabular-nums;
}

.cs-focus {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 11px;
  border: 1px solid #f6cfd6;
  border-radius: 9px;
  background: #fef3f2;
  font-family: inherit;
  font-size: 12.5px;
  color: #b42318;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.cs-focus:hover { background: #fdeaea; border-color: #f0b8c0; }
.cs-focus.is-on { background: #fbe0e3; border-color: #e79aa5; }
/* 没有重点关注时退化成一条绿色说明，不再可点 */
.cs-focus.is-clear {
  background: #ecfdf3;
  border-color: #c4e9de;
  color: #079455;
  cursor: default;
}
.cs-focus.is-clear:hover { background: #ecfdf3; border-color: #c4e9de; }
.cs-focus-ic { flex-shrink: 0; }
.cs-focus-text { flex: 1; min-width: 0; line-height: 1.5; }
.cs-focus-text b {
  font-size: 15px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  margin: 0 1px;
}
.cs-focus-text em { font-style: normal; opacity: 0.8; }
.cs-focus-act {
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.75);
  font-size: 11.5px;
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 767px) {
  .cs-title { font-size: 15px; }
  .cs-back span { display: none; }
  .cs-back { padding: 5px 7px; }
}
</style>
