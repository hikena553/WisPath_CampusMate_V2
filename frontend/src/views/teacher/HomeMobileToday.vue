<template>
  <div>
    <!-- 移动端首页：逾期未处理提醒条 -->
    <div v-if="overdueCount > 0" class="overdue-home-bar" @click="emit('open-today')">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ overdueCount }} 个任务已逾期未处理，点击查看</span>
      <el-icon class="overdue-home-arrow"><DArrowRight /></el-icon>
    </div>

    <!-- 移动端：今日任务 + 公告 -->
    <div class="mobile-today-section">
      <div class="mobile-section-card" @click="emit('open-today')" style="cursor:pointer">
        <div class="mobile-section-header">
          <div class="section-title"><el-icon><Calendar /></el-icon><span>今日任务</span></div>
          <div style="display:flex;align-items:center;gap:6px">
            <span v-if="todayLeaves.length + todaySchedules.length > 0" style="font-size:12px;color:#9ca3af">{{ todayLeaves.length + todaySchedules.length }}项</span>
            <el-icon color="#ccc"><DArrowRight /></el-icon>
          </div>
        </div>
        <div v-if="todayLeaves.length === 0 && todaySchedules.length === 0" class="empty-tip-small">今日暂无待办事项</div>
        <div v-else class="task-preview">
          <div v-for="l in todayLeaves.slice(0, 2)" :key="'l-'+l.id" class="today-item" style="padding:6px 0">
            <div class="today-dot dot-leave"></div>
            <div class="today-info">
              <div class="today-title">{{ l.student_name }} 的请假申请</div>
            </div>
          </div>
          <div v-for="s in todaySchedules.slice(0, 2)" :key="'s-'+s.id" class="today-item" style="padding:6px 0">
            <div class="today-dot" :style="{ background: s.completed ? '#10b981' : s.urgency === 'urgent' ? '#ef4444' : '#3b82f6' }"></div>
            <div class="today-info">
              <div class="today-title" :class="{ 'today-done': s.completed }">{{ s.content }}</div>
            </div>
          </div>
          <div v-if="todayLeaves.length + todaySchedules.length > 4" style="font-size:11px;color:#9ca3af;text-align:center;padding-top:4px">
            还有 {{ todayLeaves.length + todaySchedules.length - 4 }} 项...
          </div>
        </div>
      </div>

      <div class="mobile-section-card">
        <div class="mobile-section-header">
          <div class="section-title"><el-icon><Bell /></el-icon><span>校园公告</span></div>
        </div>
        <div v-if="campusAnnouncements.length === 0" class="empty-tip-small">暂无校园公告</div>
        <a v-for="(item, index) in campusAnnouncements.slice(0, 5)" :key="'ca-'+index"
          :href="item.url || '#'" target="_blank" class="today-item today-link">
          <div class="today-dot dot-campus"></div>
          <div class="today-info">
            <div class="today-title">{{ item.title }}</div>
            <div class="today-meta">{{ item.date }}</div>
          </div>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Calendar, Bell, DArrowRight, WarningFilled } from '@element-plus/icons-vue'
import type { ScheduleItem } from '@/api/teacher'
import type { LeaveRequestOut, Announcement } from '@/types'

defineProps<{
  todayLeaves: LeaveRequestOut[]
  todaySchedules: ScheduleItem[]
  campusAnnouncements: Announcement[]
  overdueCount: number
}>()

const emit = defineEmits<{
  'open-today': []
}>()
</script>

<style scoped>
/* 移动端区块卡片（副本：与 HomePage 同名基础样式一致） */
.mobile-section-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.mobile-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.section-title:hover {
  opacity: 0.7;
}

.mobile-today-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.today-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.today-item:last-child {
  border-bottom: none;
}

.today-link {
  text-decoration: none;
  color: inherit;
}

.today-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-leave { background: #e6a23c; }
.dot-campus { background: #909399; }

.today-info {
  flex: 1;
  min-width: 0;
}

.today-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.today-meta {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.empty-tip-small {
  text-align: center;
  color: #bbb;
  padding: 14px 0;
  font-size: 12px;
}

/* 移动端首页顶部逾期提醒条 */
.overdue-home-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  padding: 9px 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(220, 38, 38, 0.35);
}
.overdue-home-bar span {
  flex: 1;
}
.overdue-home-arrow {
  opacity: 0.8;
}
</style>