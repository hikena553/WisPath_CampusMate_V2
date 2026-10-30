<template>
  <!-- 待批请假弹窗 -->
  <!-- 待处理事项（短列表：移动端=底部动作面板） -->
  <ActionSheet
    v-model="dialogVisible"
    title="待处理事项"
    width="380px"
    class="tui-dialog"
  >
    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>以下为今日待你处理的请假申请，点击「详情」可进入审批管理逐条办理。</span>
    </div>
    <div v-if="leaves.length === 0" class="empty-tip">今日无待处理事项</div>
    <div v-for="l in leaves" :key="l.id" class="schedule-item" @click="emit('navigate')">
      <div class="schedule-dot dot-warning"></div>
      <div class="schedule-content">
        <div class="schedule-title">{{ l.student_name }} 的请假申请</div>
        <div class="schedule-meta">{{ l.start_date }} ~ {{ l.end_date }} · {{ typeLabel(l.leave_type) }}</div>
      </div>
      <el-button text size="small" type="primary" @click.stop="emit('navigate')">详情</el-button>
    </div>
  </ActionSheet>
</template>

<script setup lang="ts">
import { computed } from 'vue'
// v6.1 弹窗减负：短列表提示走底部动作面板
import ActionSheet from '@/components/common/ActionSheet.vue'
import { InfoFilled } from '@element-plus/icons-vue'
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
  color: var(--tui-text-quiet);
  padding: 20px 0;
  font-size: 12.5px;
}

.schedule-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.schedule-item:hover {
  background: var(--tui-surface-muted);
}

.schedule-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-warning { background: var(--tui-warn); }

.schedule-content {
  flex: 1;
  min-width: 0;
}

.schedule-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--tui-text);
}

.schedule-meta {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  margin-top: 2px;
}
</style>