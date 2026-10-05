<template>
  <div class="sub-page">
    <div class="sub-page-header">
      <el-button text circle @click="emit('close')"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
      <span class="sub-page-title">危机预警</span>
      <div style="width:36px"></div>
    </div>
    <div class="sub-page-body">
      <!-- 待随访提醒条 -->
      <div v-if="followUpDue.length" class="fu-banner">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ followUpDue.length }} 条随访已到期，请及时跟进</span>
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

      <div v-if="visibleAlerts.length === 0" class="empty-tip-small" style="padding:40px 0;text-align:center">
        {{ view === 'follow_up' ? '暂无到期随访' : '暂无危机预警' }}
      </div>
      <div v-for="a in visibleAlerts" :key="a.id" class="mobile-section-card" style="margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <el-tag :type="a.level === 'severe' ? 'danger' : a.level === 'moderate' ? 'warning' : 'info'" size="small">
            {{ a.level === 'severe' ? '高危' : a.level === 'moderate' ? '中危' : '低危' }}
          </el-tag>
          <small style="color:#999">{{ a.created_at?.slice(0, 10) }}</small>
        </div>
        <div style="font-size:14px;font-weight:500;color:#333;margin-bottom:4px">{{ a.student_name || '未知学生' }}</div>
        <div style="font-size:13px;color:#666;line-height:1.5">{{ a.summary }}</div>
        <div v-if="a.keywords_matched" style="margin-top:6px;font-size:12px;color:#999">关键词：{{ a.keywords_matched }}</div>
        <div v-if="isDue(a)" class="fu-tag">
          <el-icon :size="12"><Clock /></el-icon>随访到期：{{ a.follow_up_date }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, WarningFilled, Clock } from '@element-plus/icons-vue'
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
/* 子页面（移动端全屏覆盖层）：父级共享类副本（scoped 隔离，父级样式无法命中子组件内部元素） */
.sub-page {
  position: fixed; inset: 0; background: #f5f7fa;
  z-index: 100; display: flex; flex-direction: column;
}
.sub-page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #fff;
  border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
}
.sub-page-title {
  font-size: 16px; font-weight: 600; color: #1a1a1a;
}
.sub-page-body {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}

/* 待随访提醒条 */
.fu-banner {
  display: flex; align-items: center; gap: 6px;
  background: #fffaeb; color: #b54708;
  border: 1px solid #fedf89; border-radius: 10px;
  padding: 10px 12px; font-size: 13px;
}

/* 筛选 chips */
.crisis-chips { display: flex; gap: 8px; }
.crisis-chip {
  flex: 1; padding: 7px 0; border: 1px solid #e5e7eb; border-radius: 999px;
  background: #fff; color: #6b7280; font-size: 13px; cursor: pointer; font-family: inherit;
}
.crisis-chip.active { border-color: #3b82f6; background: #eff6ff; color: #2563eb; font-weight: 600; }

.fu-tag {
  display: inline-flex; align-items: center; gap: 4px;
  margin-top: 8px; font-size: 12px; color: #b54708; font-weight: 600;
}

/* 移动端区块卡片（副本） */
.mobile-section-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.empty-tip-small {
  text-align: center;
  color: #bbb;
  padding: 14px 0;
  font-size: 12px;
}
</style>
