<template>
  <!-- ===== AI 绵小城悬浮按钮 ===== -->
  <div class="ai-float" @click="router.push('/teacher/agent')">
    <img src="/images/mascot.png" alt="绵小城" class="ai-mascot" />
    <span class="ai-label">绵小城</span>
  </div>

  <!-- ===== AI 决策支持层（v3.0 实施文档 §4）：主动发现 + 推荐联系 ===== -->
  <div class="ai-decision-row">
    <div class="ai-decision-card">
      <div class="ai-card-header">
        <div class="ai-card-title">
          <el-icon class="ai-card-icon"><MagicStick /></el-icon>
          <span>AI 主动发现</span>
        </div>
        <div class="ai-card-actions">
          <el-button size="small" text circle :loading="aiLoading" @click="emit('refresh')">
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-button size="small" type="primary" plain round @click="router.push('/teacher/crisis')">
            预警工作台
            <el-icon class="el-icon--right"><DArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
      <div v-loading="aiLoading" class="ai-card-body">
        <el-empty v-if="!aiLoading && proactiveActions.length === 0" description="暂无新发现，班级状态平稳" :image-size="48" />
        <div v-for="act in proactiveActions" :key="act.trigger + '-' + act.student_id" class="ai-action-item">
          <el-tag :type="priorityTagType(act.priority)" size="small" effect="dark" class="ai-action-tag">
            {{ priorityText(act.priority) }}
          </el-tag>
          <div class="ai-action-main">
            <div class="ai-action-title">{{ act.title }}</div>
            <div class="ai-action-content">{{ act.content }}</div>
          </div>
          <el-button size="small" round type="primary" plain @click="router.push('/teacher/crisis')">处置</el-button>
        </div>
      </div>
    </div>

    <div class="ai-decision-card">
      <div class="ai-card-header">
        <div class="ai-card-title">
          <el-icon class="ai-card-icon ai-card-icon-orange"><Cpu /></el-icon>
          <span>AI 推荐联系学生</span>
        </div>
        <div class="ai-card-actions">
          <el-button
            v-if="contactSuggestions.length"
            size="small"
            type="primary"
            plain
            round
            :loading="batchLoading"
            @click="convertAll"
          >全部转为跟进</el-button>
          <el-tag size="small" effect="plain" type="success">TOP {{ contactSuggestions.length }}</el-tag>
        </div>
      </div>
      <div v-loading="aiLoading" class="ai-card-body">
        <el-empty v-if="!aiLoading && contactSuggestions.length === 0" description="暂无推荐联系对象" :image-size="48" />
        <div v-for="c in contactSuggestions" :key="c.student_id" class="ai-contact-item">
          <div class="ai-contact-avatar">{{ c.student_name.slice(0, 1) }}</div>
          <div class="ai-contact-main">
            <div class="ai-contact-name">
              {{ c.student_name }}
              <el-tag :type="contactTagType(c.priority)" size="small" effect="light">
                {{ c.priority === 'high' ? '建议尽快' : c.priority === 'medium' ? '建议关注' : '保持联系' }}
              </el-tag>
            </div>
            <div class="ai-contact-reason">{{ c.reason }}</div>
          </div>
          <div class="ai-contact-ops">
            <el-button size="small" round @click="router.push('/teacher/students')">查看档案</el-button>
            <el-button
              size="small"
              round
              type="primary"
              :plain="!convertedIds.has(c.student_id)"
              :loading="loadingIds.has(c.student_id)"
              :disabled="convertedIds.has(c.student_id)"
              @click="convert(c)"
            >{{ convertedIds.has(c.student_id) ? '已跟进' : '转为跟进' }}</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, Refresh, DArrowRight, Cpu } from '@element-plus/icons-vue'
import type { ProactiveAction } from '@/api/agent'
import { persistContactSuggestions, type ContactSuggestion } from '@/api/teacher'

const props = defineProps<{
  proactiveActions: ProactiveAction[]
  contactSuggestions: ContactSuggestion[]
  aiLoading: boolean
}>()

const emit = defineEmits<{ refresh: []; converted: [count: number] }>()

const router = useRouter()

/** 已转为跟进的学生 id（本地即时反馈，避免重复点击） */
const convertedIds = ref<Set<number>>(new Set())
const loadingIds = ref<Set<number>>(new Set())
const batchLoading = ref(false)

async function convert(c: ContactSuggestion) {
  if (convertedIds.value.has(c.student_id)) return
  loadingIds.value.add(c.student_id)
  try {
    const res = await persistContactSuggestions([c])
    convertedIds.value.add(c.student_id)
    ElMessage.success(res.created > 0 ? '已转为跟进任务' : '该学生已在跟进中')
    emit('converted', res.created)
  } catch {
    ElMessage.error('转为跟进失败')
  } finally {
    loadingIds.value.delete(c.student_id)
  }
}

async function convertAll() {
  batchLoading.value = true
  try {
    const res = await persistContactSuggestions(props.contactSuggestions)
    props.contactSuggestions.forEach((c) => convertedIds.value.add(c.student_id))
    ElMessage.success(res.created > 0 ? `已转为跟进任务 ${res.created} 条` : '推荐学生均已在跟进中')
    emit('converted', res.created)
  } catch {
    ElMessage.error('批量转为跟进失败')
  } finally {
    batchLoading.value = false
  }
}

function priorityText(p: number) {
  if (p >= 80) return '高危'
  if (p >= 60) return '关注'
  return '提醒'
}
function priorityTagType(p: number): 'danger' | 'warning' | 'info' {
  if (p >= 80) return 'danger'
  if (p >= 60) return 'warning'
  return 'info'
}
function contactTagType(p: string): 'danger' | 'warning' | 'info' {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}
</script>

<style scoped>
/* ===== AI Floating Button ===== */
.ai-float {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.ai-float:hover { transform: scale(1.1); }

.ai-mascot {
  width: 48px;
  height: 48px;
  object-fit: contain;
  animation: mascot-float 2s ease-in-out infinite;
}

@keyframes mascot-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.ai-label {
  margin-top: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #5b8def;
  background: rgba(255,255,255,0.9);
  padding: 1px 8px;
  border-radius: 8px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.08);
}

/* ===== AI 决策支持层（v3.0 实施文档 §4） ===== */
.ai-decision-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 16px 0;
}

.ai-decision-card {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 4px 16px rgba(31, 41, 55, 0.04);
}

.ai-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.ai-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 15px;
  color: #1f2937;
}

.ai-card-icon {
  color: #5b8def;
  font-size: 18px;
}

.ai-card-icon-orange {
  color: #f59e0b;
}

.ai-card-body {
  min-height: 110px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-action-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: #f7f9fc;
  border-radius: 10px;
}

.ai-action-tag {
  flex-shrink: 0;
  margin-top: 2px;
}

.ai-action-main {
  flex: 1;
  min-width: 0;
}

.ai-action-title {
  font-weight: 600;
  font-size: 13px;
  color: #1f2937;
}

.ai-action-content {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
  line-height: 1.5;
}

.ai-contact-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #f7f9fc;
  border-radius: 10px;
}

.ai-contact-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 15px;
  background: linear-gradient(135deg, #5b8def, #8ab4ff);
}

.ai-contact-main {
  flex: 1;
  min-width: 0;
}

.ai-contact-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 13px;
  color: #1f2937;
}

.ai-contact-reason {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.ai-contact-ops {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.ai-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 768px) {
  .ai-decision-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .ai-float {
    display: none;
  }
}
</style>