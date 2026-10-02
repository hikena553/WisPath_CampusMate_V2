<template>
  <div class="sub-page">
    <div class="sub-page-header">
      <el-button text circle @click="emit('close')"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
      <span class="sub-page-title">危机预警</span>
      <div style="width:36px"></div>
    </div>
    <div class="sub-page-body">
      <div v-if="alerts.length === 0" class="empty-tip-small" style="padding:40px 0;text-align:center">暂无危机预警</div>
      <div v-for="a in alerts" :key="a.id" class="mobile-section-card" style="margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <el-tag :type="a.level === 'severe' ? 'danger' : a.level === 'moderate' ? 'warning' : 'info'" size="small">
            {{ a.level === 'severe' ? '高危' : a.level === 'moderate' ? '中危' : '低危' }}
          </el-tag>
          <small style="color:#999">{{ a.created_at?.slice(0, 10) }}</small>
        </div>
        <div style="font-size:14px;font-weight:500;color:#333;margin-bottom:4px">{{ a.student_name || '未知学生' }}</div>
        <div style="font-size:13px;color:#666;line-height:1.5">{{ a.summary }}</div>
        <div v-if="a.keywords_matched" style="margin-top:6px;font-size:12px;color:#999">关键词：{{ a.keywords_matched }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import type { CrisisAlert } from '@/types'

defineProps<{
  alerts: CrisisAlert[]
}>()

const emit = defineEmits<{
  close: []
}>()
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