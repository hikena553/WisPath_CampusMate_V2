<template>
  <div class="feedback-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="page-title-row">
        <h2>反馈管理</h2>
        <span class="page-sub">用户反馈查看与处理</span>
      </div>
    </div>

    <!-- 统计概览卡片 -->
    <div class="stats-grid">
      <div class="stat-card total">
        <div class="stat-icon"><el-icon><MessageSquare /></el-icon></div>
        <div class="stat-info">
          <span class="stat-value">{{ statsLoading ? '—' : stats.total }}</span>
          <span class="stat-label">全部反馈</span>
        </div>
      </div>
      <div class="stat-card pending">
        <div class="stat-icon"><el-icon><Clock /></el-icon></div>
        <div class="stat-info">
          <span class="stat-value">{{ statsLoading ? '—' : stats.pending }}</span>
          <span class="stat-label">待处理</span>
        </div>
      </div>
      <div class="stat-card processing">
        <div class="stat-icon"><el-icon><Loader2 /></el-icon></div>
        <div class="stat-info">
          <span class="stat-value">{{ statsLoading ? '—' : stats.processing }}</span>
          <span class="stat-label">处理中</span>
        </div>
      </div>
      <div class="stat-card resolved">
        <div class="stat-icon"><el-icon><CircleCheck /></el-icon></div>
        <div class="stat-info">
          <span class="stat-value">{{ statsLoading ? '—' : stats.resolved }}</span>
          <span class="stat-label">已解决</span>
        </div>
      </div>
      <div class="stat-card rejected">
        <div class="stat-icon"><el-icon><CircleX /></el-icon></div>
        <div class="stat-info">
          <span class="stat-value">{{ statsLoading ? '—' : stats.rejected }}</span>
          <span class="stat-label">已拒绝</span>
        </div>
      </div>
    </div>

    <!-- 反馈重点词云 -->
    <FeedbackWordCloud :words="wordCloudWords" :loading="wordCloudLoading" @refresh="loadWordCloud" />

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px">
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="processing" />
        <el-option label="已解决" value="resolved" />
        <el-option label="已拒绝" value="rejected" />
      </el-select>
      <el-select v-model="filters.type" placeholder="类型" clearable style="width: 140px">
        <el-option label="问题反馈" value="bug" />
        <el-option label="功能建议" value="feature" />
        <el-option label="投诉" value="complaint" />
        <el-option label="其他" value="other" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索标题 / 内容 / 提交者" clearable style="width: 240px">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" @click="handleSearch">
        <el-icon><Search /></el-icon> 查询
      </el-button>
      <el-button @click="handleReset">
        <el-icon><RefreshCw /></el-icon> 重置
      </el-button>
    </div>

    <!-- 反馈列表 -->
    <el-table :data="paginatedFeedbacks" v-loading="loading" style="width: 100%">
      <el-table-column label="类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="getTypeTag(row.type)" size="small" effect="light" round>{{ getTypeLabel(row.type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">
          <div class="feedback-title-cell">
            <span class="feedback-title">{{ row.title }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="内容" min-width="280" show-overflow-tooltip />
      <el-table-column label="提交者" width="110">
        <template #default="{ row }">
          <div class="user-cell">
            <el-avatar :size="24" :src="''">{{ row.user_name?.[0] || '?' }}</el-avatar>
            <span>{{ row.user_name || '匿名用户' }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" width="150" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="getStatusTag(row.status)" size="small" effect="dark" round>{{ getStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="132" align="center">
        <template #default="{ row }">
          <div class="table-actions">
            <el-tooltip content="查看详情" placement="top">
              <el-button class="action-btn info" circle @click="openDetail(row)">
                <el-icon><Eye /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip v-if="row.status === 'pending' || row.status === 'processing'" content="回复" placement="top">
              <el-button class="action-btn primary" circle @click="openReplyDialog(row)">
                <el-icon><MessageSquare /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip v-if="row.status === 'pending' || row.status === 'processing'" content="拒绝" placement="top">
              <el-button class="action-btn delete" circle @click="handleReject(row)">
                <el-icon><X /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="feedbacks.length > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="filteredFeedbacks.length"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="反馈详情" size="420px">
      <template v-if="currentFeedback">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTag(currentFeedback.status)" size="small" effect="dark" round>{{ getStatusLabel(currentFeedback.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="getTypeTag(currentFeedback.type)" size="small" round>{{ getTypeLabel(currentFeedback.type) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提交者">{{ currentFeedback.user_name || '匿名用户' }}</el-descriptions-item>
          <el-descriptions-item label="联系方式">{{ currentFeedback.contact || '无' }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ currentFeedback.created_at }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-content">
          <div class="detail-label">反馈内容</div>
          <div class="detail-box">{{ currentFeedback.content }}</div>
        </div>
        <div v-if="currentFeedback.reply" class="detail-content">
          <div class="detail-label">管理员回复（{{ currentFeedback.replier_name || '管理员' }}）</div>
          <div class="detail-box reply-box">{{ currentFeedback.reply }}</div>
        </div>
      </template>
    </el-drawer>

    <!-- 回复弹窗 -->
    <el-dialog v-model="replyDialogVisible" title="回复反馈" width="640px" :close-on-click-modal="false">
      <el-form :model="replyForm" label-width="100px">
        <el-form-item label="反馈内容">
          <div class="feedback-preview">{{ currentFeedback?.content }}</div>
        </el-form-item>
        <el-form-item label="回复内容" required>
          <el-input v-model="replyForm.reply" type="textarea" :rows="4" placeholder="请输入回复内容" maxlength="500" show-word-limit />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { Search, RefreshCw, MessageSquare, Eye, X, Clock, Loader2, CircleCheck, CircleX } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFeedbacks, getFeedbackWordCloud, replyFeedback, type Feedback, type FeedbackWord } from '@/api/feedback'
import FeedbackWordCloud from '@/components/feedback/FeedbackWordCloud.vue'

const loading = ref(false)
const submitting = ref(false)
const statsLoading = ref(true)
const feedbacks = ref<Feedback[]>([])
const replyDialogVisible = ref(false)
const detailVisible = ref(false)
const currentFeedback = ref<Feedback | null>(null)

// 词云数据
const wordCloudWords = ref<FeedbackWord[]>([])
const wordCloudLoading = ref(false)

const filters = reactive({
  status: '',
  type: '',
  keyword: ''
})

const replyForm = reactive({
  reply: ''
})

// 分页
const currentPage = ref(1)
const pageSize = ref(10)

// 统计
const stats = computed(() => {
  const s = { total: feedbacks.value.length, pending: 0, processing: 0, resolved: 0, rejected: 0 }
  feedbacks.value.forEach(f => {
    if (f.status === 'pending') s.pending++
    else if (f.status === 'processing') s.processing++
    else if (f.status === 'resolved') s.resolved++
    else if (f.status === 'rejected') s.rejected++
  })
  return s
})

const filteredFeedbacks = computed(() => {
  const kw = filters.keyword.trim().toLowerCase()
  return feedbacks.value.filter(f => {
    if (filters.status && f.status !== filters.status) return false
    if (filters.type && f.type !== filters.type) return false
    if (kw) {
      const hay = `${f.title} ${f.content} ${f.user_name || ''}`.toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})

const paginatedFeedbacks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredFeedbacks.value.slice(start, start + pageSize.value)
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

function handleSearch() {
  currentPage.value = 1
  loadFeedbacks()
}

function handleReset() {
  filters.status = ''
  filters.type = ''
  filters.keyword = ''
  currentPage.value = 1
  loadFeedbacks()
}

function handleSizeChange() {
  currentPage.value = 1
}

function handleCurrentChange() {
  // 分页切换即可，数据已在本地
}

function openDetail(feedback: Feedback) {
  currentFeedback.value = feedback
  detailVisible.value = true
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
    await ElMessageBox.confirm(`确定要拒绝反馈「${feedback.title}」吗？`, '确认拒绝', {
      type: 'warning',
      confirmButtonText: '确认拒绝',
      cancelButtonText: '取消'
    })
    await replyFeedback(feedback.id, {
      reply: '已拒绝',
      status: 'rejected'
    })
    ElMessage.success('已拒绝')
    loadFeedbacks()
  } catch {}
}

async function loadWordCloud() {
  wordCloudLoading.value = true
  try {
    const data = await getFeedbackWordCloud()
    wordCloudWords.value = data
  } catch (error) {
    console.error('加载词云失败:', error)
  } finally {
    wordCloudLoading.value = false
  }
}

async function loadFeedbacks() {
  loading.value = true
  statsLoading.value = true
  try {
    const data = await getFeedbacks(filters)
    feedbacks.value = data
    currentPage.value = 1
  } catch (error) {
    console.error('加载反馈失败:', error)
  } finally {
    statsLoading.value = false
    loading.value = false
  }
}

onMounted(() => {
  loadFeedbacks()
  loadWordCloud()
})
</script>

<style scoped>
.feedback-page {
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

/* 页头 */
.page-header {
  margin-bottom: 14px;
}

.page-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #1a1a2e);
}

.page-sub {
  font-size: 13px;
  color: var(--text-secondary, #666);
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}

.stat-card:hover {
  box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08);
  transform: translateY(-2px);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon .el-icon {
  font-size: 20px;
  color: #fff;
}

.stat-card.total .stat-icon { background: #409eff; }
.stat-card.pending .stat-icon { background: #e6a23c; }
.stat-card.processing .stat-icon { background: #409eff; }
.stat-card.resolved .stat-icon { background: #67c23a; }
.stat-card.rejected .stat-icon { background: #f56c6c; }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
  color: #2b3245;
}

.stat-label {
  font-size: 12px;
  color: #8a91a4;
}

/* 表格内细节 */
.feedback-title-cell {
  display: flex;
  align-items: center;
}

.feedback-title {
  font-weight: 500;
  color: #333a4d;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-cell .el-avatar {
  background: #eef4ff;
  color: #409eff;
  font-size: 12px;
  flex-shrink: 0;
}

/* 详情抽屉 */
.detail-content {
  margin-top: 16px;
}

.detail-label {
  font-size: 13px;
  font-weight: 600;
  color: #333a4d;
  margin-bottom: 6px;
}

.detail-box {
  background: #f8f9fc;
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  color: #4b5264;
  line-height: 1.6;
}

.detail-box.reply-box {
  background: #f0f9eb;
  color: #3c5b2a;
}

.feedback-preview {
  background: #f8f9fc;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #4b5264;
  line-height: 1.6;
  max-height: 120px;
  overflow-y: auto;
}

/* 响应式 */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* 暗色适配 */
html.dark .stat-card {
  background: #1e1e20;
  border-color: rgba(255, 255, 255, 0.08);
}

html.dark .stat-value {
  color: #e8e8ea;
}

html.dark .stat-label {
  color: #a0a0a8;
}

html.dark .detail-box {
  background: rgba(255, 255, 255, 0.05);
  color: #cdd3e0;
}

html.dark .detail-box.reply-box {
  background: rgba(103, 194, 58, 0.1);
}

html.dark .feedback-preview {
  background: rgba(255, 255, 255, 0.05);
  color: #cdd3e0;
}

html.dark .feedback-title {
  color: #e8e8ea;
}
</style>