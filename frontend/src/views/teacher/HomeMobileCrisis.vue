<template>
  <div class="sub-page">
    <div class="sub-page-header">
      <el-button text circle @click="emit('close')"><el-icon :size="18"><ArrowLeft /></el-icon></el-button>
      <span class="sub-page-title">危机预警</span>
      <div class="sub-page-head-spacer"></div>
    </div>
    <div class="sub-page-body">
      <!-- 待随访提醒条 -->
      <div v-if="followUpDue.length" class="fu-banner">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ followUpDue.length }} 条随访已到期，请及时跟进</span>
      </div>

      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><WarningFilled /></el-icon>危机预警</h3>
          <div class="tui-section-extra"><span class="cx-count">{{ visibleAlerts.length }} 条</span></div>
        </div>
        <div class="tui-section-hint danger">
          <el-icon><InfoFilled /></el-icon>
          <span>按等级由高到低处置；带「随访到期」标记的预警需尽快回访并记录，避免风险反复。</span>
        </div>

        <!-- 筛选 -->
        <div class="crisis-chips">
          <button class="crisis-chip" :class="{ active: view === 'all' }" @click="view = 'all'">
            全部 {{ alerts.length }}
          </button>
          <button class="crisis-chip" :class="{ active: view === 'follow_up' }" @click="view = 'follow_up'">
            待随访 {{ followUpDue.length }}
          </button>
        </div>

        <div v-if="visibleAlerts.length === 0" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="22"><WarningFilled /></el-icon></span>
          <span class="tui-empty-title">{{ view === 'follow_up' ? '暂无到期随访' : '暂无危机预警' }}</span>
          <span class="tui-empty-desc">{{ view === 'follow_up' ? '当前没有需要回访的预警，保持关注即可' : '班级状态平稳，出现风险信号时会在此提示' }}</span>
        </div>
        <div v-for="a in visibleAlerts" :key="a.id" class="cx-card">
          <div class="cx-card-head">
            <span class="tui-tag" :class="levelTagClass(a.level)">{{ levelText(a.level) }}</span>
            <small class="cx-date">{{ a.created_at?.slice(0, 10) }}</small>
          </div>
          <div class="cx-name">{{ a.student_name || '未知学生' }}</div>
          <div class="cx-summary">{{ a.summary }}</div>
          <div v-if="a.keywords_matched" class="cx-keywords">关键词：{{ a.keywords_matched }}</div>
          <div v-if="isDue(a)" class="fu-tag">
            <el-icon :size="12"><Clock /></el-icon>随访到期：{{ a.follow_up_date }}
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, Clock, InfoFilled, WarningFilled } from '@element-plus/icons-vue'
import { getFollowUpDue } from '@/api/crisis'
import type { CrisisAlert } from '@/types'

const props = defineProps<{
  alerts: CrisisAlert[]
}>()

const emit = defineEmits<{
  close: []
}>()

const view = ref<'all' | 'follow_up'>('all')
const followUpDue = ref<CrisisAlert[]>([])

function isDue(a: CrisisAlert) {
  if (a.resolved || !a.follow_up_date) return false
  return a.follow_up_date <= new Date().toISOString().slice(0, 10)
}

function levelText(level: string) {
  return level === 'severe' ? '高危' : level === 'moderate' ? '中危' : '低危'
}
function levelTagClass(level: string) {
  return level === 'severe' ? 'tui-tag-danger' : level === 'moderate' ? 'tui-tag-warn' : ''
}

const visibleAlerts = computed(() => {
  if (view.value === 'follow_up') return followUpDue.value
  return props.alerts
})

async function loadFollowUp() {
  try {
    followUpDue.value = await getFollowUpDue()
  } catch {
    followUpDue.value = props.alerts.filter(isDue)
  }
}

onMounted(loadFollowUp)
</script>

<style scoped>
/* 子页面（移动端全屏覆盖层） */
.sub-page {
  position: fixed; inset: 0; background: var(--tui-bg);
  z-index: 100; display: flex; flex-direction: column;
}
.sub-page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: var(--tui-surface);
  border-bottom: 1px solid var(--tui-border); flex-shrink: 0;
}
.sub-page-title {
  font-size: 15px; font-weight: 600; color: var(--tui-text);
}
.sub-page-head-spacer { width: 32px; }
.sub-page-body {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.sub-page-body .tui-empty { padding: 22px 12px; gap: 8px; }
.sub-page-body .tui-empty-icon { width: 46px; height: 46px; }

/* 待随访提醒条 */
.fu-banner {
  display: flex; align-items: center; gap: 6px;
  background: var(--tui-warn-soft); color: var(--tui-warn);
  border: 1px solid var(--tui-border); border-radius: var(--tui-radius-sm);
  padding: 9px 11px; font-size: 12.5px;
}

/* 筛选 chips */
.crisis-chips { display: flex; gap: 8px; margin-bottom: 10px; }
.crisis-chip {
  flex: 1; padding: 6px 0; border: 1px solid var(--tui-border-strong); border-radius: 999px;
  background: var(--tui-surface); color: var(--tui-text-tertiary); font-size: 12.5px; cursor: pointer; font-family: inherit;
}
.crisis-chip.active { border-color: var(--tui-brand); background: var(--tui-brand-soft); color: var(--tui-brand-strong); font-weight: 600; }

.cx-count { font-size: 11.5px; color: var(--tui-text-quiet); }

/* 预警卡片（收紧尺寸） */
.cx-card {
  background: var(--tui-surface-muted);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  padding: 10px;
  margin-bottom: 8px;
}
.cx-card-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px;
}
.cx-date { font-size: 11.5px; color: var(--tui-text-quiet); }
.cx-name { font-size: 13.5px; font-weight: 600; color: var(--tui-text); margin-bottom: 4px; }
.cx-summary { font-size: 12.5px; color: var(--tui-text-secondary); line-height: 1.5; }
.cx-keywords { margin-top: 6px; font-size: 11.5px; color: var(--tui-text-quiet); }

.fu-tag {
  display: inline-flex; align-items: center; gap: 4px;
  margin-top: 8px; font-size: 11.5px; color: var(--tui-warn); font-weight: 600;
}
</style>