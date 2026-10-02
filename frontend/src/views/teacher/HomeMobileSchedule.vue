<template>
  <div class="sub-page">
    <div class="sub-page-header">
      <el-button text circle @click="emit('close')"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
      <span class="sub-page-title">添加日程</span>
      <div style="width:36px"></div>
    </div>
    <div class="sub-page-body">
      <!-- 添加日程表单 -->
      <div class="schedule-form-card">
        <div class="form-section">
          <div class="form-label">
            <el-icon color="#667eea"><Calendar /></el-icon>
            <span>选择日期</span>
          </div>
          <el-date-picker
            v-model="scheduleDate"
            type="date"
            format="YYYY年MM月DD日"
            value-format="YYYY-MM-DD"
            placeholder="点击选择日期"
            style="width:100%"
            :clearable="false"
          />
        </div>

        <div class="form-section">
          <div class="form-label">
            <el-icon color="#667eea"><EditPen /></el-icon>
            <span>日程内容</span>
          </div>
          <el-input
            :model-value="content"
            type="textarea"
            :rows="4"
            placeholder="请输入日程内容，如：&#10;• 期中考试监考&#10;• 班级会议&#10;• 学生谈话"
            resize="none"
            @update:model-value="emit('update:content', $event)"
          />
        </div>

        <div class="form-section">
          <div class="form-label">
            <el-icon color="#667eea"><Flag /></el-icon>
            <span>任务等级</span>
          </div>
          <div class="form-urgency-options">
            <button
              v-for="u in urgencyOptions" :key="u.value"
              class="form-urgency-opt"
              :class="{ active: urgency === u.value, [u.value]: true }"
              @click="emit('update:urgency', u.value)"
            >{{ u.label }}</button>
          </div>
        </div>

        <button
          class="schedule-submit-btn"
          :class="{ active: content.trim() && scheduleDate }"
          :disabled="!content.trim() || !scheduleDate"
          @click="emit('add', scheduleDate)"
        >
          <el-icon><Check /></el-icon>
          保存日程
        </button>
      </div>

      <!-- 近期日程 -->
      <div class="schedule-upcoming-card">
        <div class="upcoming-header">
          <div class="upcoming-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <span class="upcoming-title">近期日程</span>
          <span class="upcoming-count" v-if="upcomingReminders.length">{{ upcomingReminders.length }}项</span>
        </div>
        <div v-if="upcomingReminders.length === 0" class="upcoming-empty">
          <el-icon :size="32" color="#e5e7eb"><Calendar /></el-icon>
          <span>暂无近期日程</span>
        </div>
        <div v-else class="upcoming-list">
          <div v-for="r in upcomingReminders" :key="r.id" class="upcoming-item">
            <div class="upcoming-date">
              <span class="upcoming-day">{{ new Date(r.date).getDate() }}</span>
              <span class="upcoming-month">{{ new Date(r.date).getMonth() + 1 }}月</span>
            </div>
            <div class="upcoming-info">
              <div class="upcoming-text">{{ r.content }}</div>
            </div>
            <button class="upcoming-delete" @click="emit('delete', r.id)">
              <el-icon><Delete /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowLeft, Calendar, EditPen, Flag, Check, Clock, Delete } from '@element-plus/icons-vue'
import type { ScheduleItem, ScheduleUrgency } from '@/api/teacher'

defineProps<{
  content: string
  urgency: ScheduleUrgency
  urgencyOptions: { value: ScheduleUrgency; label: string }[]
  upcomingReminders: ScheduleItem[]
}>()

const emit = defineEmits<{
  close: []
  'update:content': [v: string]
  'update:urgency': [v: ScheduleUrgency]
  add: [date: string]
  delete: [id: number]
}>()

// 表单日期为子页本地状态：内容/等级与桌面端弹窗共享（父级持有）
const scheduleDate = ref(new Date().toISOString().slice(0, 10))
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

/* ===== Responsive ===== */
@media (max-width: 767px) {
  /* ---- 添加日程子页面 ---- */
  .schedule-form-card {
    background: #fff;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }
  .form-section {
    margin-bottom: 20px;
  }
  .form-label {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }
  .form-label .el-icon {
    font-size: 18px;
  }
  :deep(.el-date-editor) {
    width: 100% !important;
  }
  :deep(.el-date-editor .el-input__wrapper) {
    border-radius: 12px;
    box-shadow: 0 0 0 1px #e5e7eb;
  }
  :deep(.el-date-editor .el-input__wrapper:hover) {
    box-shadow: 0 0 0 1px #667eea;
  }
  :deep(.el-textarea__inner) {
    border-radius: 12px;
    box-shadow: 0 0 0 1px #e5e7eb !important;
    font-size: 14px;
    line-height: 1.6;
    padding: 12px 16px;
  }
  :deep(.el-textarea__inner:focus) {
    box-shadow: 0 0 0 1px #667eea !important;
  }
  .schedule-submit-btn {
    width: 100%;
    height: 48px;
    border-radius: 12px;
    border: none;
    background: #e5e7eb;
    color: #9ca3af;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 4px;
  }
  .schedule-submit-btn.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #fff;
    box-shadow: 0 6px 20px rgba(102,126,234,0.4);
    transform: translateY(-1px);
  }
  .schedule-submit-btn:disabled {
    cursor: not-allowed;
  }

  .form-urgency-options {
    display: flex;
    gap: 8px;
  }
  .form-urgency-opt {
    flex: 1;
    height: 38px;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    background: #fff;
    color: #6b7280;
    font-size: 13px;
    cursor: pointer;
  }
  .form-urgency-opt.active {
    border-color: #667eea;
    background: #eef1ff;
    color: #5b5bd6;
    font-weight: 600;
  }
  .form-urgency-opt.active.important {
    border-color: #f59e0b;
    background: #fffbeb;
    color: #b45309;
  }
  .form-urgency-opt.active.urgent {
    border-color: #ef4444;
    background: #fef2f2;
    color: #dc2626;
  }

  .schedule-upcoming-card {
    background: #fff;
    border-radius: 16px;
    padding: 16px;
    margin-top: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }
  .upcoming-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }
  .upcoming-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .upcoming-title {
    font-size: 15px;
    font-weight: 600;
    color: #374151;
  }
  .upcoming-count {
    margin-left: auto;
    font-size: 12px;
    color: #9ca3af;
    background: #f3f4f6;
    padding: 2px 10px;
    border-radius: 10px;
  }
  .upcoming-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 30px 0;
    gap: 10px;
  }
  .upcoming-empty span {
    font-size: 13px;
    color: #9ca3af;
  }
  .upcoming-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .upcoming-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: #f9fafb;
    border-radius: 12px;
  }
  .upcoming-item:active {
    background: #f3f4f6;
  }
  .upcoming-date {
    flex-shrink: 0;
    width: 48px;
    text-align: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
    padding: 8px 4px;
  }
  .upcoming-day {
    display: block;
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }
  .upcoming-month {
    display: block;
    font-size: 10px;
    color: rgba(255,255,255,0.8);
    margin-top: 2px;
  }
  .upcoming-info {
    flex: 1;
    min-width: 0;
  }
  .upcoming-text {
    font-size: 14px;
    color: #374151;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .upcoming-delete {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: none;
    background: #fef2f2;
    color: #ef4444;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .upcoming-delete:active {
    background: #fee2e2;
    transform: scale(0.95);
  }
}
</style>