<template>
  <div class="approval-page">
    <SubPageHeader title="审批管理" fallback="/teacher" />
    <div class="page-header">
      <h2>审批管理</h2>
      <p class="page-sub">共 <strong>{{ totalPending }}</strong> 条待审批事项</p>
    </div>

    <el-tabs v-model="activeTab" @tab-change="loadData" class="approval-tabs">
      <el-tab-pane label="待审批" name="pending">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><Document /></el-icon> 请假申请</h3>
            <el-tag v-if="pendingLeaves.length" type="warning" effect="plain" size="small">
              {{ pendingLeaves.length }} 条待批
            </el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedPendingLeaves" v-if="pendingLeaves.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="student_name" label="学生" width="100" />
              <el-table-column prop="leave_type" label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="start_date" label="开始日期" width="110" />
              <el-table-column prop="end_date" label="结束日期" width="110" />
              <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
              <el-table-column label="AI 分析" min-width="200">
                <template #default="{ row }">
                  <div v-if="analysisMap[row.id]" class="ai-analyze">
                    <el-tag :type="analysisMap[row.id].suggestion === 'approve' ? 'success' : 'danger'" size="small" effect="plain">
                      {{ analysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                    </el-tag>
                    <el-tooltip placement="top" :show-after="200">
                      <template #content>
                        <div style="max-width:280px;line-height:1.6;font-size:13px">{{ analysisMap[row.id].reason }}</div>
                      </template>
                      <el-icon class="analyze-tip"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </div>
                  <el-tag v-else type="info" size="small" effect="plain" class="analyzing-tag">
                    <el-icon class="is-loading"><Loading /></el-icon> 分析中
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="success" size="small" @click="handleApprove(row)">
                    <el-icon><Check /></el-icon> 通过
                  </el-button>
                  <el-button type="danger" size="small" plain @click="showReject(row)">
                    <el-icon><Close /></el-icon> 拒绝
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedPendingLeaves.length">
            <div class="mobile-card" v-for="row in paginatedPendingLeaves" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">日期</span>
                  <span class="mobile-card-value">{{ row.start_date }} ~ {{ row.end_date }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reason">
                  <span class="mobile-card-label">原因</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reason }}</span>
                </div>
                <div class="mobile-card-row" v-if="analysisMap[row.id]">
                  <span class="mobile-card-label">AI 分析</span>
                  <span class="mobile-card-value">
                    <el-tag :type="analysisMap[row.id].suggestion === 'approve' ? 'success' : 'danger'" size="small" effect="plain">
                      {{ analysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                    </el-tag>
                    <span class="mobile-ai-reason">{{ analysisMap[row.id].reason }}</span>
                  </span>
                </div>
                <div class="mobile-card-row" v-else>
                  <span class="mobile-card-label">AI 分析</span>
                  <span class="mobile-card-value">
                    <el-tag type="info" size="small" effect="plain" class="analyzing-tag">
                      <el-icon class="is-loading"><Loading /></el-icon> 分析中
                    </el-tag>
                  </span>
                </div>
              </div>
              <div class="mobile-card-actions">
                <el-button type="success" size="small" @click="handleApprove(row)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="showReject(row)">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </div>
            </div>
          </div>
          <div class="pagination-wrapper" v-if="pendingLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageLeaves"
              v-model:page-size="pageSizeLeaves"
              :page-sizes="[50, 100, 200]"
              :total="pendingLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleLeaveSizeChange"
              @current-change="handleLeaveCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无待批请假" :image-size="80" />
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><Tickets /></el-icon> 办事申请</h3>
            <el-tag v-if="pendingTickets.length" type="warning" effect="plain" size="small">
              {{ pendingTickets.length }} 条待批
            </el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedPendingTickets" v-if="pendingTickets.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="type" label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.type === 'leave' ? '请假' : '证明' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
              <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="success" size="small" @click="showTicketReview(row, 'approve')">
                    <el-icon><Check /></el-icon> 通过
                  </el-button>
                  <el-button type="danger" size="small" plain @click="showTicketReview(row, 'reject')">
                    <el-icon><Close /></el-icon> 拒绝
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedPendingTickets.length">
            <div class="mobile-card" v-for="row in paginatedPendingTickets" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.title }}</span>
                <el-tag size="small" effect="plain">{{ row.type === 'leave' ? '请假' : '证明' }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row" v-if="row.content">
                  <span class="mobile-card-label">内容</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.content }}</span>
                </div>
              </div>
              <div class="mobile-card-actions">
                <el-button type="success" size="small" @click="showTicketReview(row, 'approve')">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="showTicketReview(row, 'reject')">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </div>
            </div>
          </div>
          <div class="pagination-wrapper" v-if="pendingTickets.length > 0">
            <el-pagination
              v-model:current-page="currentPageTickets"
              v-model:page-size="pageSizeTickets"
              :page-sizes="[50, 100, 200]"
              :total="pendingTickets.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleTicketSizeChange"
              @current-change="handleTicketCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无待办申请" :image-size="80" />
        </div>

        <!-- 材料档案审批 -->
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><FolderOpened /></el-icon> 材料档案</h3>
            <el-tag v-if="pendingMaterials.length" type="warning" effect="plain" size="small">
              {{ pendingMaterials.length }} 条待归档
            </el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="pendingMaterials" v-if="pendingMaterials.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="applicant_name" label="学生" width="100" />
              <el-table-column prop="title" label="材料名称" min-width="180" show-overflow-tooltip />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="success" size="small" @click="handleMaterialApprove(row.id)">
                    <el-icon><Check /></el-icon> 通过归档
                  </el-button>
                  <el-button type="danger" size="small" plain @click="handleMaterialReject(row.id)">
                    <el-icon><Close /></el-icon> 驳回
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && pendingMaterials.length">
            <div class="mobile-card" v-for="row in pendingMaterials" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.applicant_name }}</span>
                <el-tag size="small" effect="plain">材料档案</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">材料</span>
                  <span class="mobile-card-value">{{ row.title }}</span>
                </div>
                <div class="mobile-card-row">
                  <span class="mobile-card-label">提交时间</span>
                  <span class="mobile-card-value">{{ row.created_at ? row.created_at.slice(0, 16) : '' }}</span>
                </div>
              </div>
              <div class="mobile-card-actions">
                <el-button type="success" size="small" @click="handleMaterialApprove(row.id)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="handleMaterialReject(row.id)">
                  <el-icon><Close /></el-icon> 驳回
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无待归档材料" :image-size="80" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="已通过" name="approved">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleCheck /></el-icon> 已通过请假</h3>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedApprovedLeaves" v-if="approvedLeaves.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="student_name" label="学生" width="100" />
              <el-table-column prop="leave_type" label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="start_date" label="开始日期" width="110" />
              <el-table-column prop="end_date" label="结束日期" width="110" />
              <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
              <el-table-column label="状态" width="90">
                <template #default>
                  <el-tag type="success" size="small" effect="dark">已通过</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedApprovedLeaves.length">
            <div class="mobile-card" v-for="row in paginatedApprovedLeaves" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">日期</span>
                  <span class="mobile-card-value">{{ row.start_date }} ~ {{ row.end_date }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reason">
                  <span class="mobile-card-label">原因</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reason }}</span>
                </div>
              </div>
              <div class="mobile-card-footer">
                <el-tag type="success" size="small" effect="dark">已通过</el-tag>
              </div>
            </div>
          </div>
          <div class="pagination-wrapper" v-if="approvedLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageApprovedLeaves"
              v-model:page-size="pageSizeApprovedLeaves"
              :page-sizes="[50, 100, 200]"
              :total="approvedLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleApprovedLeaveSizeChange"
              @current-change="handleApprovedLeaveCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无已通过请假" :image-size="80" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="已拒绝" name="rejected">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleClose /></el-icon> 已拒绝请假</h3>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedRejectedLeaves" v-if="rejectedLeaves.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="student_name" label="学生" width="100" />
              <el-table-column prop="leave_type" label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="start_date" label="开始日期" width="110" />
              <el-table-column prop="end_date" label="结束日期" width="110" />
              <el-table-column prop="reason" label="原因" min-width="140" show-overflow-tooltip />
              <el-table-column prop="reject_reason" label="拒绝理由" min-width="140" show-overflow-tooltip />
              <el-table-column label="状态" width="90">
                <template #default>
                  <el-tag type="danger" size="small" effect="dark">已拒绝</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedRejectedLeaves.length">
            <div class="mobile-card" v-for="row in paginatedRejectedLeaves" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">日期</span>
                  <span class="mobile-card-value">{{ row.start_date }} ~ {{ row.end_date }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reason">
                  <span class="mobile-card-label">原因</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reason }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reject_reason">
                  <span class="mobile-card-label">拒绝理由</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reject_reason }}</span>
                </div>
              </div>
              <div class="mobile-card-footer">
                <el-tag type="danger" size="small" effect="dark">已拒绝</el-tag>
              </div>
            </div>
          </div>
          <div class="pagination-wrapper" v-if="rejectedLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageRejectedLeaves"
              v-model:page-size="pageSizeRejectedLeaves"
              :page-sizes="[50, 100, 200]"
              :total="rejectedLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleRejectedLeaveSizeChange"
              @current-change="handleRejectedLeaveCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无已拒绝请假" :image-size="80" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="rejectVisible" title="拒绝理由" width="420px" :close-on-click-modal="false">
      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules">
        <el-form-item label="拒绝理由" prop="reason">
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="请填写拒绝理由，如：请假天数超出规定" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认拒绝</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rejectMaterialVisible" title="驳回材料" width="420px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="驳回理由" required>
          <el-input v-model="rejectMaterialReason" type="textarea" :rows="3" placeholder="请填写驳回理由，如：材料不清晰、格式不符合要求" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectMaterialVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmMaterialReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <el-dialog :title="ticketReviewAction === 'approve' ? '通过申请' : '拒绝申请'" v-model="ticketReviewVisible" width="420px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item :label="ticketReviewAction === 'approve' ? '审批意见（选填）' : '拒绝意见（必填）'" :required="ticketReviewAction === 'reject'">
          <el-input v-model="ticketReviewComment" type="textarea" :rows="3" :placeholder="ticketReviewAction === 'approve' ? '可填写审批意见，如：同意，注意返校日期' : '请填写拒绝意见，如：材料不全，请补充后重新提交'" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ticketReviewVisible = false">取消</el-button>
        <el-button :type="ticketReviewAction === 'approve' ? 'success' : 'danger'" @click="confirmTicketReview">
          {{ ticketReviewAction === 'approve' ? '确认通过' : '确认拒绝' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { ElMessage } from 'element-plus'
import {
  Document, Tickets, CircleCheck, CircleClose,
  InfoFilled, Loading, Check, Close, FolderOpened
} from '@element-plus/icons-vue'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi } from '@/api/service'
import { getApprovalPending, reviewApproval, getApprovalStats, type ApprovalItem, type ApprovalStats } from '@/api/approval'
import type { LeaveRequestOut, ServiceTicket } from '@/types'
import { useResponsive } from '@/composables/useResponsive'

const { isMobile } = useResponsive()

const activeTab = ref('pending')
const pendingLeaves = ref<LeaveRequestOut[]>([])
const pendingTickets = ref<ServiceTicket[]>([])
const pendingMaterials = ref<ApprovalItem[]>([])
const stats = ref<ApprovalStats | null>(null)
const approvedLeaves = ref<LeaveRequestOut[]>([])
const rejectedLeaves = ref<LeaveRequestOut[]>([])
const analysisMap = ref<Record<number, { suggestion: string; reason: string }>>({})
const rejectVisible = ref(false)
const rejectTarget = ref<LeaveRequestOut | null>(null)
const rejectFormRef = ref<any>()
const rejectForm = reactive({ reason: '' })
// 材料档案驳回弹窗状态
const rejectMaterialTarget = ref<number | null>(null)
const rejectMaterialReason = ref('')
const rejectMaterialVisible = ref(false)
// 工单审批弹窗状态
const ticketReviewVisible = ref(false)
const ticketReviewTarget = ref<ServiceTicket | null>(null)
const ticketReviewAction = ref<'approve' | 'reject'>('approve')
const ticketReviewComment = ref('')
const rejectRules = {
  reason: [{ required: true, message: '请填写拒绝理由', trigger: 'blur' }],
}
// 请假分页相关状态
const currentPageLeaves = ref(1)
const pageSizeLeaves = ref(50)

// 工单分页相关状态
const currentPageTickets = ref(1)
const pageSizeTickets = ref(50)

// 已通过请假分页相关状态
const currentPageApprovedLeaves = ref(1)
const pageSizeApprovedLeaves = ref(50)

// 已拒绝请假分页相关状态
const currentPageRejectedLeaves = ref(1)
const pageSizeRejectedLeaves = ref(50)

const totalPending = computed(() => pendingLeaves.value.length + pendingTickets.value.length + pendingMaterials.value.length)

const paginatedPendingLeaves = computed(() => {
  const start = (currentPageLeaves.value - 1) * pageSizeLeaves.value
  const end = start + pageSizeLeaves.value
  return pendingLeaves.value.slice(start, end)
})

const paginatedPendingTickets = computed(() => {
  const start = (currentPageTickets.value - 1) * pageSizeTickets.value
  const end = start + pageSizeTickets.value
  return pendingTickets.value.slice(start, end)
})

const paginatedApprovedLeaves = computed(() => {
  const start = (currentPageApprovedLeaves.value - 1) * pageSizeApprovedLeaves.value
  const end = start + pageSizeApprovedLeaves.value
  return approvedLeaves.value.slice(start, end)
})

const paginatedRejectedLeaves = computed(() => {
  const start = (currentPageRejectedLeaves.value - 1) * pageSizeRejectedLeaves.value
  const end = start + pageSizeRejectedLeaves.value
  return rejectedLeaves.value.slice(start, end)
})

function handleLeaveSizeChange() {
  currentPageLeaves.value = 1
}

function handleLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleTicketSizeChange() {
  currentPageTickets.value = 1
}

function handleTicketCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleApprovedLeaveSizeChange() {
  currentPageApprovedLeaves.value = 1
}

function handleApprovedLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleRejectedLeaveSizeChange() {
  currentPageRejectedLeaves.value = 1
}

function handleRejectedLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

async function loadData() {
  loadStats()
  if (activeTab.value === 'pending') {
    try {
      pendingLeaves.value = await getPendingLeaves()
      loadAnalysis()
    } catch {}
    try { pendingTickets.value = (await getTickets()).filter((t: ServiceTicket) => t.status === 'pending' || t.status === 'processing') } catch {}
    try { pendingMaterials.value = await getApprovalPending({ kind: 'material', status: 'pending' }) } catch { pendingMaterials.value = [] }
  } else if (activeTab.value === 'approved') {
    try { approvedLeaves.value = await getAllLeaves('approved') } catch {}
  } else if (activeTab.value === 'rejected') {
    try { rejectedLeaves.value = await getAllLeaves('rejected') } catch {}
  }
}

async function loadStats() {
  try { stats.value = await getApprovalStats(30) } catch { stats.value = null }
}

async function handleMaterialApprove(id: number) {
  try {
    await reviewApproval('material', id, 'approve')
    ElMessage.success('已通过归档')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function handleMaterialReject(id: number) {
  rejectMaterialTarget.value = id
  rejectMaterialReason.value = ''
  rejectMaterialVisible.value = true
}

async function confirmMaterialReject() {
  if (!rejectMaterialTarget.value) return
  if (!rejectMaterialReason.value.trim()) return ElMessage.warning('请填写驳回原因')
  try {
    await reviewApproval('material', rejectMaterialTarget.value, 'reject', rejectMaterialReason.value)
    ElMessage.success('已驳回')
    rejectMaterialVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function chunk<T>(arr: T[], size: number): T[][] {
  const result: T[][] = []
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size))
  }
  return result
}

async function loadAnalysis() {
  // 筛选尚未分析的记录
  const todo = pendingLeaves.value.filter((leave) => !analysisMap.value[leave.id])
  // 先放占位符，UI 立即显示"分析中"
  for (const leave of todo) {
    analysisMap.value[leave.id] = { suggestion: 'approve', reason: '分析中...' }
  }
  // 分批并发（每批 4 个）
  const batches = chunk(todo, 4)
  for (const batch of batches) {
    const results = await Promise.all(
      batch.map(async (leave) => {
        try {
          const result = await analyzeLeave(leave.id)
          console.log('[AI分析]', leave.id, result)
          return { id: leave.id, result }
        } catch (e) {
          console.error('[AI分析失败]', leave.id, e)
          return { id: leave.id, result: { suggestion: 'approve', reason: 'AI分析暂时不可用' } }
        }
      })
    )
    for (const { id, result } of results) {
      analysisMap.value[id] = result
    }
  }
}

async function handleApprove(row: LeaveRequestOut) {
  try {
    await reviewLeaveApi(row.id, 'approve')
    ElMessage.success('已通过')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function showReject(row: LeaveRequestOut) {
  rejectTarget.value = row
  rejectForm.reason = ''
  rejectFormRef.value?.clearValidate?.()
  rejectVisible.value = true
}

async function confirmReject() {
  if (!rejectTarget.value) return
  if (rejectFormRef.value) {
    try { await rejectFormRef.value.validate() } catch { return }
  }
  try {
    await reviewLeaveApi(rejectTarget.value.id, 'reject', rejectForm.reason || undefined)
    ElMessage.success('已拒绝')
    rejectVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function showTicketReview(row: ServiceTicket, action: 'approve' | 'reject') {
  ticketReviewTarget.value = row
  ticketReviewAction.value = action
  ticketReviewComment.value = ''
  ticketReviewVisible.value = true
}

async function confirmTicketReview() {
  if (!ticketReviewTarget.value) return
  if (ticketReviewAction.value === 'reject' && !ticketReviewComment.value.trim()) {
    ElMessage.warning('请填写拒绝意见')
    return
  }
  try {
    await approveTicketApi(ticketReviewTarget.value.id, ticketReviewAction.value, ticketReviewComment.value.trim() || undefined)
    ElMessage.success(ticketReviewAction.value === 'approve' ? '已通过' : '已拒绝')
    ticketReviewVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

onMounted(loadData)
</script>

<style scoped>
.approval-page { height: 100%; overflow-y: auto; overflow-x: hidden; padding: 8px 4px; }

.page-header {
  display: flex; align-items: baseline; gap: 10px;
  margin-bottom: 12px; padding: 0 4px;
}
.page-header h2 {
  font-size: 18px; font-weight: 700; color: #1a1a2e; margin: 0;
}
.page-sub { font-size: 12px; color: #888; margin: 0; }
.page-sub strong { color: #e6a23c; }

.approval-tabs { --el-tabs-header-height: 40px; }
.approval-tabs :deep(.el-tabs__header) { margin-bottom: 14px; }
.approval-tabs :deep(.el-tabs__item) { font-size: 13px; font-weight: 500; }
.approval-tabs :deep(.el-tabs__item.is-active) { font-weight: 600; }

.section-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px;
}
.section-header h3 {
  font-size: 14px; font-weight: 600; color: #1a1a2e; margin: 0;
  display: flex; align-items: center; gap: 6px;
}

.ai-analyze { display: flex; align-items: center; gap: 6px; }
.analyze-tip { cursor: pointer; color: #909399; font-size: 14px; }
.analyze-tip:hover { color: #409eff; }
.analyzing-tag { display: inline-flex; align-items: center; gap: 4px; }

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
  padding: 8px 0;
}

/* ========== 移动端卡片（默认隐藏） ========== */
.mobile-cards { display: none; }

/* ========== 移动端响应式 ========== */
@media (max-width: 767px) {
  .approval-page {
    padding: 6px 8px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    margin-bottom: 10px;
  }

  .section-card {
    padding: 10px;
    margin-bottom: 10px;
  }

  /* 隐藏桌面表格，显示移动端卡片 */
  .desktop-table { display: none; }
  .mobile-cards { display: block; }

  /* 移动端卡片样式 */
  .mobile-card {
    background: #fff;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    display: flex;
    flex-direction: column;
  }

  .mobile-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .mobile-card-student {
    font-size: 15px;
    font-weight: 600;
    color: #1a1a2e;
  }

  .mobile-card-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 10px;
  }

  .mobile-card-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 13px;
    line-height: 1.5;
  }

  .mobile-card-label {
    flex-shrink: 0;
    width: 56px;
    color: #909399;
    font-weight: 500;
  }

  .mobile-card-value {
    flex: 1;
    color: #333;
    word-break: break-all;
  }

  .mobile-card-reason {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .mobile-ai-reason {
    display: block;
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
    line-height: 1.4;
  }

  .mobile-card-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    padding-top: 10px;
    border-top: 1px solid rgba(0,0,0,0.05);
  }

  .mobile-card-footer {
    display: flex;
    justify-content: flex-end;
    padding-top: 10px;
    border-top: 1px solid rgba(0,0,0,0.05);
  }

  /* 分页居中 */
  .pagination-wrapper {
    justify-content: center;
  }

  .pagination-wrapper :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
  }

  :deep(.el-dialog) {
    width: 92vw !important;
    max-height: 70vh;
    margin: 0 auto !important;
    border-radius: 16px 16px 0 0 !important;
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    top: auto !important;
  }

  :deep(.el-dialog__body) {
    max-height: 50vh;
    overflow-y: auto;
  }
}
</style>
