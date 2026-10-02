<template>
  <!-- 待批请假弹窗 -->
  <el-dialog v-model="dialogVisible" title="待处理事项" width="420px">
    <div v-if="leaves.length === 0" class="empty-tip">今日无待处理事项</div>
    <div v-for="l in leaves" :key="l.id" class="schedule-item" @click="emit('navigate')">
      <div class="schedule-dot dot-warning"></div>
      <div class="schedule-content">
        <div class="schedule-title">{{ l.student_name }} 的请假申请</div>
        <div class="schedule-meta">{{ l.start_date }} ~ {{ l.end_date }} · {{ typeLabel(l.leave_type) }}</div>
      </div>
      <el-button text size="small" type="primary" @click.stop="emit('navigate')">详情</el-button>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LeaveRequestOut } from '@/types'

const props = defineProps<{ visible: boolean; leaves: LeaveRequestOut[] }>()
const emit = defineEmits<{ 'update:visible': [value: boolean]; navigate: [] }>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (v: boolean) => emit('update:visible', v),
})

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}
</script>

<style scoped>
.empty-tip {
  text-align: center;
  color: #bbb;
  padding: 24px 0;
  font-size: 13px;
}

.schedule-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.schedule-item:hover {
  background: rgba(91,141,239,0.05);
}

.schedule-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-warning { background: #e6a23c; }

.schedule-content {
  flex: 1;
  min-width: 0;
}

.schedule-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.schedule-meta {
  font-size: 11px;
  color: #999;
  margin-top: 1px;
}
</style>