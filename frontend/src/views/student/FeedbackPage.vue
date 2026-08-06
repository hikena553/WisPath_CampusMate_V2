<template>
  <div class="feedback-page">
    <div class="page-header">
      <h2 class="text-gradient">意见反馈</h2>
      <p class="subtitle">您的意见是我们改进的动力</p>
    </div>

    <div class="content-row">
      <!-- 提交反馈表单 -->
      <div class="form-section">
        <div class="form-card">
          <h3>提交反馈</h3>
          <el-form :model="form" label-width="80px">
            <el-form-item label="反馈类型">
              <el-select v-model="form.type" placeholder="请选择反馈类型" style="width: 100%">
                <el-option label="问题反馈" value="bug" />
                <el-option label="功能建议" value="feature" />
                <el-option label="投诉" value="complaint" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
            <el-form-item label="标题">
              <el-input v-model="form.title" placeholder="请简要描述您的反馈" maxlength="100" show-word-limit />
            </el-form-item>
            <el-form-item label="详细内容">
              <el-input v-model="form.content" type="textarea" :rows="5" placeholder="请详细描述您的问题或建议" maxlength="1000" show-word-limit />
            </el-form-item>
            <el-form-item label="联系方式">
              <el-input v-model="form.contact" placeholder="手机号/邮箱（选填，方便我们联系您）" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSubmit" :loading="submitting">提交反馈</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- 我的反馈记录 -->
      <div class="history-section">
        <div class="history-card">
          <h3>我的反馈</h3>
          <div class="feedback-list" v-loading="loading">
            <div v-if="feedbacks.length === 0" class="empty-state">
              <el-empty description="暂无反馈记录" :image-size="60" />
            </div>
            <div v-for="item in feedbacks" :key="item.id" class="feedback-item">
              <div class="item-header">
                <el-tag :type="getTypeTag(item.type)" size="small">{{ getTypeLabel(item.type) }}</el-tag>
                <el-tag :type="getStatusTag(item.status)" size="small" effect="plain">{{ getStatusLabel(item.status) }}</el-tag>
              </div>
              <div class="item-title">{{ item.title }}</div>
              <div class="item-content">{{ item.content }}</div>
              <div class="item-time">{{ item.created_at }}</div>
              <div v-if="item.reply" class="item-reply">
                <div class="reply-label">管理员回复：</div>
                <div class="reply-text">{{ item.reply }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { createFeedback, getFeedbacks, type Feedback, type FeedbackCreate } from '@/api/feedback'

const loading = ref(false)
const submitting = ref(false)
const feedbacks = ref<Feedback[]>([])

const form = ref<FeedbackCreate>({
  type: 'other',
  title: '',
  content: '',
  contact: ''
})

function getTypeLabel(type: string) {
  const map: Record<string, string> = {
    bug: '问题反馈',
    feature: '功能建议',
    complaint: '投诉',
    other: '其他'
  }
  return map[type] || type
}

function getTypeTag(type: string) {
  const map: Record<string, string> = {
    bug: 'danger',
    feature: 'primary',
    complaint: 'warning',
    other: 'info'
  }
  return map[type] || ''
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    resolved: '已解决',
    rejected: '已拒绝'
  }
  return map[status] || status
}

function getStatusTag(status: string) {
  const map: Record<string, string> = {
    pending: 'warning',
    processing: 'primary',
    resolved: 'success',
    rejected: 'danger'
  }
  return map[status] || ''
}

function resetForm() {
  form.value = {
    type: 'other',
    title: '',
    content: '',
    contact: ''
  }
}

async function handleSubmit() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!form.value.content.trim()) {
    ElMessage.warning('请输入详细内容')
    return
  }
  
  submitting.value = true
  try {
    await createFeedback(form.value)
    ElMessage.success('反馈已提交，感谢您的意见！')
    resetForm()
    loadFeedbacks()
  } catch (error) {
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}

async function loadFeedbacks() {
  loading.value = true
  try {
    const data = await getFeedbacks()
    feedbacks.value = data
  } catch (error) {
    console.error('加载反馈失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadFeedbacks()
})
</script>

<style scoped>
.feedback-page {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.text-gradient {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.content-row {
  display: flex;
  gap: 24px;
}

.form-section {
  flex: 1;
  min-width: 0;
}

.history-section {
  width: 400px;
  flex-shrink: 0;
}

.form-card, .history-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.form-card h3, .history-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 20px;
}

.feedback-list {
  max-height: 500px;
  overflow-y: auto;
}

.feedback-item {
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.feedback-item:last-child {
  border-bottom: none;
}

.item-header {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
  margin-bottom: 6px;
}

.item-content {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-time {
  font-size: 12px;
  color: #999;
}

.item-reply {
  margin-top: 10px;
  padding: 10px 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.reply-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.reply-text {
  font-size: 13px;
  color: #333;
}

.empty-state {
  padding: 40px 0;
}

/* ===== Mobile ===== */
@media (max-width: 767px) {
  .feedback-page { padding: 16px; }
  .page-header h2 { font-size: 18px; }
  .content-row { flex-direction: column; gap: 16px; }
  .history-section { width: 100%; }
  .form-card, .history-card { padding: 16px; }
  .form-card h3, .history-card h3 { font-size: 15px; margin-bottom: 14px; }
}
</style>
