<template>
  <div class="feedback-page">
    <div class="page-header">
      <h2 class="text-gradient">反馈管理</h2>
      <p class="subtitle">用户反馈查看与处理</p>
    </div>

    <!-- 筛选条件 -->
    <div class="filter-row">
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 150px">
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="processing" />
        <el-option label="已解决" value="resolved" />
        <el-option label="已拒绝" value="rejected" />
      </el-select>
      <el-select v-model="filters.type" placeholder="类型" clearable style="width: 150px">
        <el-option label="问题反馈" value="bug" />
        <el-option label="功能建议" value="feature" />
        <el-option label="投诉" value="complaint" />
        <el-option label="其他" value="other" />
      </el-select>
      <el-button type="primary" @click="loadFeedbacks">
        <el-icon><Search /></el-icon> 查询
      </el-button>
    </div>

    <!-- 反馈列表 -->
    <div class="feedback-list" v-loading="loading">
      <div v-if="feedbacks.length === 0" class="empty-state">
        <el-empty description="暂无反馈" />
      </div>
      
      <div v-for="item in feedbacks" :key="item.id" class="feedback-card">
        <div class="card-header">
          <div class="card-title">
            <el-tag :type="getTypeTag(item.type)" size="small">{{ getTypeLabel(item.type) }}</el-tag>
            <span class="title-text">{{ item.title }}</span>
          </div>
          <el-tag :type="getStatusTag(item.status)" size="small">{{ getStatusLabel(item.status) }}</el-tag>
        </div>
        
        <div class="card-content">{{ item.content }}</div>
        
        <div class="card-meta">
          <span>提交者：{{ item.user_name }}</span>
          <span>时间：{{ item.created_at }}</span>
          <span v-if="item.contact">联系方式：{{ item.contact }}</span>
        </div>
        
        <div v-if="item.reply" class="card-reply">
          <div class="reply-header">
            <el-icon><ChatDotRound /></el-icon>
            <span>管理员回复（{{ item.replier_name }}）</span>
            <span class="reply-time">{{ item.replied_at }}</span>
          </div>
          <div class="reply-content">{{ item.reply }}</div>
        </div>
        
        <div v-if="item.status === 'pending' || item.status === 'processing'" class="card-actions">
          <el-button type="primary" size="small" @click="openReplyDialog(item)">回复</el-button>
          <el-button type="danger" size="small" @click="handleReject(item)">拒绝</el-button>
        </div>
      </div>
    </div>

    <!-- 回复弹窗 -->
    <el-dialog v-model="replyDialogVisible" title="回复反馈" width="500px">
      <el-form :model="replyForm" label-width="80px">
        <el-form-item label="反馈内容">
          <div class="feedback-preview">{{ currentFeedback?.content }}</div>
        </el-form-item>
        <el-form-item label="回复内容">
          <el-input v-model="replyForm.reply" type="textarea" :rows="4" placeholder="请输入回复内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="replyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitReply" :loading="submitting">提交回复</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFeedbacks, replyFeedback, type Feedback } from '@/api/feedback'

const loading = ref(false)
const submitting = ref(false)
const feedbacks = ref<Feedback[]>([])
const replyDialogVisible = ref(false)
const currentFeedback = ref<Feedback | null>(null)

const filters = reactive({
  status: '',
  type: ''
})

const replyForm = reactive({
  reply: ''
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

function openReplyDialog(feedback: Feedback) {
  currentFeedback.value = feedback
  replyForm.reply = ''
  replyDialogVisible.value = true
}

async function handleSubmitReply() {
  if (!replyForm.reply.trim()) {
    ElMessage.warning('请输入回复内容')
    return
  }
  
  submitting.value = true
  try {
    await replyFeedback(currentFeedback.value!.id, {
      reply: replyForm.reply,
      status: 'resolved'
    })
    ElMessage.success('回复成功')
    replyDialogVisible.value = false
    loadFeedbacks()
  } catch (error) {
    ElMessage.error('回复失败')
  } finally {
    submitting.value = false
  }
}

async function handleReject(feedback: Feedback) {
  try {
    await ElMessageBox.confirm('确定要拒绝此反馈吗？', '确认')
    await replyFeedback(feedback.id, {
      reply: '已拒绝',
      status: 'rejected'
    })
    ElMessage.success('已拒绝')
    loadFeedbacks()
  } catch {}
}

async function loadFeedbacks() {
  loading.value = true
  try {
    const data = await getFeedbacks(filters)
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

.filter-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.feedback-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feedback-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-text {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-content {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  margin-bottom: 12px;
}

.card-meta {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
}

.card-reply {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
}

.reply-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.reply-time {
  margin-left: auto;
  font-size: 12px;
  color: #999;
}

.reply-content {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
}

.card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.feedback-preview {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  color: #333;
}

.empty-state {
  padding: 60px 0;
}
</style>
