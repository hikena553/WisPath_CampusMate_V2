<template>
  <div class="deep-thinking">
    <div class="dt-header" @click="expanded = !expanded">
      <el-icon :size="14" :class="['dt-arrow', { expanded }]"><ArrowRight /></el-icon>
      <span class="dt-label">思考过程</span>
      <el-tag size="small" effect="plain" type="warning" style="margin-left:6px">深度思考</el-tag>
    </div>
    <Transition name="dt-expand">
      <div v-if="expanded" class="dt-body">
        <div class="dt-content" v-html="renderThinking(thinking)"></div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ thinking: string }>()

const expanded = ref(false)

function renderThinking(text: string): string {
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/\n/g, '<br>')
  return html
}
</script>

<style scoped>
.deep-thinking {
  margin-bottom: 8px;
  border-left: 3px solid #e6a23c;
  background: #fffbf0;
  border-radius: 6px;
  overflow: hidden;
}
.dt-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  color: #b37400;
}
.dt-header:hover {
  background: rgba(230, 162, 60, 0.08);
}
.dt-arrow {
  transition: transform 0.2s;
}
.dt-arrow.expanded {
  transform: rotate(90deg);
}
.dt-label {
  font-weight: 600;
  font-size: 12px;
}
.dt-body {
  padding: 0 10px 8px 10px;
}
.dt-content {
  font-size: 13px;
  line-height: 1.5;
  color: #8c6a1e;
  background: rgba(255,255,255,0.6);
  padding: 8px 10px;
  border-radius: 4px;
}
.dt-expand-enter-active,
.dt-expand-leave-active {
  transition: all 0.2s ease;
}
.dt-expand-enter-from,
.dt-expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
